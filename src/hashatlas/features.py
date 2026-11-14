"""Build block fingerprints and daily network-economics tables.

Fingerprints use version/nonce bits, block composition, log transforms and
within-day comparisons. Label sources, height and calendar time are excluded
from model inputs. Daily aggregates and the hardware-efficiency frontier support
the era analysis and decision scenarios."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import ARTIFACTS, INTERIM, PROCESSED, RAW, cfg, ensure_dirs, write_json

ROLL_MASK = 0x1FFFE000   # BIP320 general-purpose bits 13-28 used for ASICBoost version rolling

# Approximate manufacturer specifications of milestone hardware (efficiency frontier). Used only for
# break-even electricity prices and the decision/future scenarios, never for fitting classifiers.
HARDWARE = [
    {"date": "2009-01-03", "name": "CPU (Core 2 Duo)", "ths": 2e-6, "watts": 65, "kind": "CPU"},
    {"date": "2010-07-18", "name": "GPU (Radeon HD 5870)", "ths": 4e-4, "watts": 190, "kind": "GPU"},
    {"date": "2011-06-01", "name": "FPGA (ZTEX 1.15x)", "ths": 2.1e-4, "watts": 7.9, "kind": "FPGA"},
    {"date": "2013-01-31", "name": "Avalon Batch 1", "ths": 0.066, "watts": 620, "kind": "ASIC"},
    {"date": "2013-12-01", "name": "Antminer S1", "ths": 0.18, "watts": 360, "kind": "ASIC"},
    {"date": "2014-12-01", "name": "Antminer S5", "ths": 1.155, "watts": 590, "kind": "ASIC"},
    {"date": "2015-09-01", "name": "Antminer S7", "ths": 4.73, "watts": 1293, "kind": "ASIC"},
    {"date": "2016-06-01", "name": "Antminer S9", "ths": 14.0, "watts": 1372, "kind": "ASIC"},
    {"date": "2019-04-01", "name": "Antminer S17 Pro", "ths": 53.0, "watts": 2094, "kind": "ASIC"},
    {"date": "2020-05-01", "name": "Antminer S19 Pro", "ths": 110.0, "watts": 3250, "kind": "ASIC"},
    {"date": "2022-07-01", "name": "Antminer S19 XP", "ths": 140.0, "watts": 3010, "kind": "ASIC"},
    {"date": "2023-10-01", "name": "Antminer S21", "ths": 200.0, "watts": 3500, "kind": "ASIC"},
    {"date": "2024-10-01", "name": "Antminer S21 XP", "ths": 270.0, "watts": 3645, "kind": "ASIC"},
]

BLOCK_FEATURES_BASE = [
    "ver_rolled", "ver_roll_popcount", "ver_bip9", "ver_signal_bits",
    *[f"ver_b{b}" for b in range(13, 29)],
    *[f"nonce_b{b}" for b in range(32)],
    "ts_minus_median_s", "interval_prev_s", "log_tx_count", "is_empty", "fullness", "witness_tx_share",
    "witness_byte_share", "io_ratio", "avg_tx_vbytes", "log_fee_total", "log_fee_per_kwu", "fee_share",
    "log_min_fee", "rel_fee_rate", "rel_min_fee", "rel_median_fee", "rel_fee_p10", "rel_fee_p25", "rel_fee_p75",
    "rel_fee_p90", "fee_spread", "rel_tx_count", "rel_fullness",
    "hour_sin", "hour_cos",
]


def block_features(b: pd.DataFrame) -> pd.DataFrame:
    v = b["version"].to_numpy(dtype=np.int64) & 0xFFFFFFFF
    n = b["nonce"].to_numpy(dtype=np.int64) & 0xFFFFFFFF
    rolled = v & ROLL_MASK
    f = pd.DataFrame(index=b.index)
    f["ver_rolled"] = (rolled != 0).astype(np.int8)
    f["ver_roll_popcount"] = np.array([int(x).bit_count() for x in rolled], dtype=np.int16)
    f["ver_bip9"] = ((v >> 29) == 0b001).astype(np.int8)
    f["ver_signal_bits"] = np.array([int(x).bit_count() for x in (v & 0x1FFF)], dtype=np.int16)
    for bit in range(13, 29):
        f[f"ver_b{bit}"] = ((v >> bit) & 1).astype(np.int8)
    for bit in range(32):
        f[f"nonce_b{bit}"] = ((n >> bit) & 1).astype(np.int8)
    f["ts_minus_median_s"] = (b["time"] - b["median_time"]).dt.total_seconds().clip(-7200, 14400)
    f["interval_prev_s"] = b["time"].diff().dt.total_seconds().fillna(600).clip(-7200, 14400)
    tx = b["transaction_count"].clip(lower=1)
    f["log_tx_count"] = np.log1p(tx)
    f["is_empty"] = (tx == 1).astype(np.int8)
    f["fullness"] = (b["weight"] / 4_000_000).clip(0, 1)
    f["witness_tx_share"] = (b["witness_count"] / (tx - 1).clip(lower=1)).clip(0, 1)
    f["witness_byte_share"] = ((b["size"] - b["stripped_size"]) / b["size"].clip(lower=1)).clip(0, 1)
    f["io_ratio"] = np.log1p(b["output_count"]) - np.log1p(b["input_count"])
    f["avg_tx_vbytes"] = np.log1p((b["weight"] / 4) / tx)
    f["log_fee_total"] = np.log1p(b["fee_total"])
    f["log_fee_per_kwu"] = np.log1p(b["fee_per_kwu"].fillna(0))
    f["fee_share"] = (b["fee_total"] / b["reward"].clip(lower=1)).clip(0, 1)
    fmin = b["fee_min"] if "fee_min" in b else pd.Series(np.nan, index=b.index)
    fmed = b["fee_median"] if "fee_median" in b else pd.Series(np.nan, index=b.index)
    f["log_min_fee"] = np.log1p(fmin.clip(lower=0))
    day = b["time"].dt.floor("D")
    for col, src in (("rel_fee_rate", b["fee_per_kwu"].fillna(0)), ("rel_tx_count", tx.astype(float)),
                     ("rel_fullness", f["fullness"]), ("rel_min_fee", fmin.clip(lower=0)),
                     ("rel_median_fee", fmed.clip(lower=0)),
                     *[(f"rel_fee_p{q}", (b[f"fee_p{q}"] if f"fee_p{q}" in b else pd.Series(np.nan, index=b.index)).clip(lower=0))
                       for q in (10, 25, 75, 90)]):
        med = src.groupby(day).transform("median")
        f[col] = np.log1p(src) - np.log1p(med)
    p10 = b["fee_p10"] if "fee_p10" in b else pd.Series(np.nan, index=b.index)
    p90 = b["fee_p90"] if "fee_p90" in b else pd.Series(np.nan, index=b.index)
    f["fee_spread"] = np.log1p(p90.clip(lower=0)) - np.log1p(p10.clip(lower=0))   # how wide the fee ladder is
    hour = b["time"].dt.hour + b["time"].dt.minute / 60
    f["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    f["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return f


def _chart(name: str) -> pd.Series:
    vals = json.loads((RAW / f"chart_{name}.json").read_text())["values"]
    s = pd.Series({pd.Timestamp(v["x"], unit="s", tz="UTC").floor("D"): v["y"] for v in vals}, dtype=float)
    return s[~s.index.duplicated()].sort_index()


def frontier(days: pd.DatetimeIndex) -> pd.DataFrame:
    hw = pd.DataFrame(HARDWARE)
    hw["date"] = pd.to_datetime(hw["date"], utc=True)
    hw["j_per_th"] = hw["watts"] / hw["ths"]
    hw = hw.sort_values("date")
    best = hw.assign(j=hw["j_per_th"].cummin())
    idx = np.searchsorted(best["date"].to_numpy(), days.to_numpy(), side="right") - 1
    return pd.DataFrame({"frontier_j_per_th": best["j"].to_numpy()[idx],
                         "frontier_name": best["name"].to_numpy()[idx]}, index=days)


def day_table(b: pd.DataFrame) -> pd.DataFrame:
    b = b.assign(day=b["time"].dt.floor("D"))
    g = b.groupby("day")
    d = pd.DataFrame({
        "blocks": g.size(),
        "height_last": g["id"].max(),
        "difficulty": g["difficulty"].last(),
        "empty_share": g["transaction_count"].apply(lambda s: (s == 1).mean()),
        "tx_per_block": g["transaction_count"].mean(),
        "fullness": g["weight"].mean() / 4_000_000,
        "fee_btc": g["fee_total"].sum() / 1e8,
        "subsidy_btc": g["generation"].sum() / 1e8,
        "unknown_share": g["miner"].apply(lambda s: (s == "Unknown").mean()),
        "solo_blocks": g["is_solo"].sum(),
        "distinct_miners": g["miner"].nunique(),
        "era": g["era"].first(),
    })
    # concentration over a trailing 7-day window (daily counts are too noisy): HHI and Nakamoto coefficient
    counts = b[b["miner"] != "Unknown"].groupby(["day", "miner"]).size().unstack(fill_value=0)
    counts = counts.reindex(d.index, fill_value=0).rolling(7, min_periods=1).sum()
    shares = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0)
    d["hhi"] = (shares ** 2).sum(axis=1)
    srt = np.sort(shares.fillna(0).to_numpy(), axis=1)[:, ::-1]
    d["nakamoto"] = (np.cumsum(srt, axis=1) < 0.5).sum(axis=1) + 1
    d["top1_share"] = srt[:, 0]
    d["fee_share"] = d["fee_btc"] / (d["fee_btc"] + d["subsidy_btc"])
    for name, col in (("hash-rate", "hashrate_ths"), ("market-price", "price_usd"),
                      ("miners-revenue", "revenue_usd"), ("transaction-fees", "fees_btc_chart")):
        d[col] = _chart(name).reindex(d.index).interpolate(limit=7)
    # Hash rate implied by difficulty and the realised block count (cross-check of the chart, section 4)
    d["hashrate_implied_ths"] = d["difficulty"] * 2 ** 32 * d["blocks"] / 86400 / 1e12
    d["revenue_btc"] = d["fee_btc"] + d["subsidy_btc"]
    d["hashprice_usd_th_day"] = d["revenue_btc"] * d["price_usd"] / d["hashrate_ths"].clip(lower=1e-12)
    d["hashprice_btc_th_day"] = d["revenue_btc"] / d["hashrate_ths"].clip(lower=1e-12)
    d = d.join(frontier(d.index))
    # break-even electricity price (USD/kWh) of the best hardware of the day: revenue per TH per day divided by
    # energy per TH per day (J/TH * 86400 s / 3.6e6 J/kWh)
    d["breakeven_usd_kwh"] = d["hashprice_usd_th_day"] / (d["frontier_j_per_th"] * 86400 / 3.6e6)
    # probability that ONE Bitaxe-class device (1.2 TH/s) wins at least one block in a year, at today's hash rate
    d["solo_p_year_bitaxe"] = 1 - np.exp(-1.2 / d["hashrate_ths"].clip(lower=1e-12) * 144 * 365)
    d["log_hashrate"] = np.log10(d["hashrate_ths"].clip(lower=1e-12))
    d["hashrate_growth_30d"] = d["log_hashrate"].diff(30)
    d["price_change_30d"] = np.log(d["price_usd"].replace(0, np.nan)).diff(30)
    return d


def run() -> dict:
    ensure_dirs()
    b = pd.read_parquet(INTERIM / "blocks.parquet")
    d = day_table(b)
    d.to_parquet(PROCESSED / "days.parquet")
    c = cfg()["classification"]
    modern = b[b["time"] >= pd.Timestamp(c["start"], tz="UTC")].copy()
    f = block_features(b).loc[modern.index]
    keep = ["id", "time", "miner", "is_solo", "label_source", "transaction_count", "version", "nonce"]
    out = pd.concat([modern[keep].reset_index(drop=True), f.reset_index(drop=True)], axis=1)
    out.to_parquet(PROCESSED / "block_features.parquet", index=False)
    pd.DataFrame(HARDWARE).to_csv(ARTIFACTS / "hardware_frontier.csv", index=False)
    summary = {"days": len(d), "modern_blocks": len(out), "candidate_block_features": len(BLOCK_FEATURES_BASE),
               "hashrate_chart_vs_implied_median_ratio": float((d["hashrate_ths"] / d["hashrate_implied_ths"])
                                                               .loc["2016":].median())}
    write_json(ARTIFACTS / "features_summary.json", summary)
    print(summary)
    return summary
