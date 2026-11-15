"""Unit tests for the core data-mining logic (no network, no large data needed)."""
from itertools import combinations

import numpy as np
import pandas as pd
import pytest

from hashatlas.clean import coinbase_ascii, era_of
from hashatlas.decide import advise, nakamoto
from hashatlas.explain import entropy, gini
from hashatlas.features import BLOCK_FEATURES_BASE, ROLL_MASK, block_features
from hashatlas.future import simulate
from hashatlas.rules import apriori, brute_force_check, rules_from


def _blocks(n=6):
    t0 = pd.Timestamp("2025-01-01", tz="UTC")
    return pd.DataFrame({
        "id": np.arange(n), "time": [t0 + pd.Timedelta(minutes=10 * i) for i in range(n)],
        "median_time": [t0 - pd.Timedelta(minutes=30) + pd.Timedelta(minutes=10 * i) for i in range(n)],
        "version": [0x20000000, 0x20000000 | (1 << 13) | (1 << 20), 0x3FFFE000, 0x20000004, 0x20000000, 0x20000000],
        "nonce": [0, 1, 2 ** 31, 0xFFFFFFFF, 5, 6],
        "transaction_count": [1, 3000, 2500, 10, 4000, 3500], "weight": [1000, 3_990_000, 3_000_000, 50_000, 3_999_000, 3_998_000],
        "size": [250, 1_500_000, 1_200_000, 20_000, 1_600_000, 1_550_000], "stripped_size": [250, 800_000, 700_000, 15_000, 900_000, 850_000],
        "witness_count": [0, 2500, 2000, 5, 3500, 3000], "input_count": [1, 7000, 6000, 20, 9000, 8000],
        "output_count": [1, 9000, 7000, 25, 11000, 10000], "fee_total": [0, 2e6, 1e6, 1e4, 3e6, 2.5e6],
        "fee_per_kwu": [0, 500.0, 333.0, 200.0, 750.0, 625.0], "reward": [3.125e8, 3.145e8, 3.135e8, 3.1251e8, 3.155e8, 3.15e8],
        "cdd_total": [0, 1e4, 5e3, 10, 2e4, 1e4], "fee_min": [0, 1.0, 1.1, 2.0, 0.1, 1.0], "fee_median": [0, 3.0, 2.5, 4.0, 5.0, 3.5],
    })


def test_version_and_nonce_bits_are_decomposed():
    f = block_features(_blocks())
    assert f.loc[0, "ver_rolled"] == 0 and f.loc[1, "ver_rolled"] == 1
    assert f.loc[1, "ver_roll_popcount"] == 2 and f.loc[2, "ver_roll_popcount"] == bin(ROLL_MASK).count("1")
    assert f.loc[1, "ver_b13"] == 1 and f.loc[1, "ver_b20"] == 1 and f.loc[1, "ver_b14"] == 0
    assert f.loc[2, "nonce_b31"] == 1 and f.loc[2, "nonce_b0"] == 0 and f.loc[3, [f"nonce_b{i}" for i in range(32)]].sum() == 32
    assert f.loc[3, "ver_signal_bits"] == 1          # bit 2 set
    assert f.loc[0, "is_empty"] == 1 and f.loc[1, "is_empty"] == 0
    assert set(BLOCK_FEATURES_BASE) <= set(f.columns)


def test_features_exclude_label_and_time_sources():
    banned = {"coinbase_data_hex", "coinbase_ascii", "guessed_miner", "miner", "id", "time", "difficulty"}
    assert not banned & set(BLOCK_FEATURES_BASE)


def test_day_relative_features_compare_with_the_day_median():
    b = _blocks()
    f = block_features(b)
    med = b["fee_per_kwu"].median()
    assert np.allclose(f["rel_fee_rate"], np.log1p(b["fee_per_kwu"]) - np.log1p(med))
    assert f.loc[b["fee_per_kwu"].idxmax(), "rel_fee_rate"] > 0 > f.loc[b["fee_per_kwu"].idxmin(), "rel_fee_rate"]


def test_coinbase_ascii_and_eras():
    assert "/Foundry USA Pool/" in coinbase_ascii("2f466f756e6472792055534120506f6f6c2f00ff")
    assert coinbase_ascii(None) == "" and coinbase_ascii("zz") == ""
    t = pd.Series(pd.to_datetime(["2009-06-01", "2010-08-01", "2012-01-01", "2014-01-01", "2020-01-01"], utc=True))
    assert era_of(t).tolist() == ["CPU", "GPU", "FPGA/early ASIC", "ASIC", "Industrial ASIC"]


def test_impurity_measures():
    assert gini(np.array([5.0, 5.0])) == pytest.approx(0.5)
    assert entropy(np.array([5.0, 5.0])) == pytest.approx(1.0)
    assert gini(np.array([10.0, 0.0])) == 0.0


def test_apriori_matches_brute_force_and_rules():
    rs = np.random.RandomState(0)
    M = rs.rand(400, 8) < np.array([0.6, 0.5, 0.4, 0.3, 0.5, 0.2, 0.7, 0.35])
    M[:, 1] |= M[:, 0] & (rs.rand(400) < 0.7)       # plant an association 0 -> 1
    names = [f"i{k}" for k in range(7)] + ["miner=X"]
    sup, trace = apriori(M, names, min_count=40, max_len=4)
    for k in (1, 2, 3):
        for c in combinations(range(8), k):
            n = int(np.logical_and.reduce(M[:, list(c)], axis=1).sum())
            assert (n >= 40) == (c in sup)
            if c in sup:
                assert sup[c] == n
    assert brute_force_check(M, sup, 40, max_items=8, max_len=3)["passed"]
    assert trace[1]["counted"] <= trace[1]["candidates"]
    for r in rules_from(sup, names, len(M), 0.3):
        assert r["consequent"] == "miner=X" and r["lift"] == pytest.approx(r["confidence"] / r["consequent_base_rate"])


def test_advise_economics_and_nakamoto():
    a = advise(200, 3500, 0.10, 1e9, 0.05, 0.02)
    assert a["pool_income_usd_day"] == pytest.approx(9.8)
    assert a["electricity_usd_day"] == pytest.approx(8.4)
    assert a["recommendation"].startswith("pool")
    small = advise(1.2, 18, 0.30, 1e9, 0.05, 0.02)
    assert small["solo_p_block_per_year"] == pytest.approx(1 - np.exp(-1.2 / 1e9 * 144 * 365))
    assert "lottery" in small["recommendation"]
    assert nakamoto(pd.Series({"a": 30, "b": 25, "c": 20, "d": 25})) == 2
    assert nakamoto(pd.Series({"a": 51, "b": 49})) == 1


def test_bootstrap_paths_start_at_origin_and_use_only_the_past():
    idx = pd.date_range("2017-01-01", periods=1000, freq="D", tz="UTC")
    logh = pd.Series(np.linspace(0, 2, 1000), index=idx)
    origin = idx[600]
    p = simulate(logh, origin, "2017-01-01", 120, 50, 1)
    assert p.shape == (50, 121)
    assert np.allclose(p[:, 0], logh.iloc[600])
    step = logh.diff().iloc[1]
    assert np.allclose(np.diff(p, axis=1), step)   # constant history -> every resampled step equals it
