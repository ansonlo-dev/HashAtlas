"""Load block dumps and API responses into a common schema, then label and audit them.

Coinbase tags, payout guesses and solo-service lists supply miner labels. Quality
checks record gaps, duplicates and missing fields. Consensus-valid timestamp
reversals are retained as observations."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .acquire import SOLO_POOLS
from .config import ARTIFACTS, INTERIM, RAW, cfg, ensure_dirs, read_json, write_json

USECOLS = ["id", "time", "median_time", "size", "stripped_size", "weight", "version", "nonce", "bits",
           "difficulty", "coinbase_data_hex", "transaction_count", "witness_count", "input_count", "output_count",
           "input_total", "output_total", "fee_total", "fee_per_kwu", "cdd_total", "generation", "reward",
           "guessed_miner"]
DTYPES = {"id": "int64", "size": "int64", "stripped_size": "int64", "weight": "int64", "version": "int64",
          "nonce": "int64", "bits": "int64", "difficulty": "float64", "coinbase_data_hex": "string",
          "transaction_count": "int64", "witness_count": "int64", "input_count": "int64", "output_count": "int64",
          "input_total": "float64", "output_total": "float64", "fee_total": "float64", "fee_per_kwu": "float64",
          "cdd_total": "float64", "generation": "float64", "reward": "float64", "guessed_miner": "string"}

# Blockchair's display names that differ from mempool.space's names for the same pool.
NAME_FIX = {"SlushPool": "Braiins Pool", "Slush": "Braiins Pool", "Foundry USA Pool": "Foundry USA",
            "MARA Pool": "MARA Pool", "Marathon": "MARA Pool", "BTC.TOP": "BTC.TOP", "Huobi": "Huobi.pool",
            "OKEx": "OKExPool", "OKKONG": "OKKONG", "Binance": "Binance Pool", "1THash&58COIN": "1THash",
            "Bitdeer": "BTC.com", "CloverPool": "CloverPool", "Ocean": "OCEAN", "Luxor": "Luxor"}


def _read(p) -> pd.DataFrame:
    return pd.read_csv(p, sep="\t", usecols=USECOLS, dtype=DTYPES, na_values=[""], keep_default_na=False)


def load_dumps() -> tuple[pd.DataFrame, dict]:
    folder = RAW / "blockchair_blocks"
    c = cfg()["sources"]
    days = []
    d, end = date.fromisoformat(c["first_day"]), date.fromisoformat(c["dumps_last_day"])
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    paths = [folder / f"{x:%Y%m%d}.tsv.gz" for x in days]
    missing_files = [p.name for p in paths if not p.exists()]  # filled from mempool.space by height
    with ThreadPoolExecutor(8) as ex:
        frames = list(ex.map(_read, [p for p in paths if p.exists()]))
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["median_time"] = pd.to_datetime(df["median_time"], utc=True)
    return df, {"files_expected": len(paths), "files_missing": missing_files, "rows_loaded": len(df)}


def load_mempool() -> tuple[pd.DataFrame, dict]:
    """Blocks from mempool.space (2019+ per pool, plus isolated gap heights), mapped to the dump schema."""
    import gzip
    import json

    rows = []
    files = sorted((RAW / "mempool_blocks").glob("*.jsonl.gz")) + [RAW / "mempool_gap_blocks.jsonl.gz"]
    for p in files:
        if p.exists():
            with gzip.open(p, "rt") as fh:
                rows.extend(json.loads(line) for line in fh)
    m = pd.DataFrame(rows)
    stale = int((m["stale"].fillna(0) == 1).sum())
    m = m[m["stale"].fillna(0) != 1]
    fee_min = m["feeRange"].map(lambda r: r[0] if isinstance(r, list) and r else np.nan)
    # feeRange = effective fee-rate percentiles [min, 10, 25, 50, 75, 90, max] (sat/vB)
    pct = {f"fee_p{q}": m["feeRange"].map(lambda r, i=i: r[i] if isinstance(r, list) and len(r) == 7 else np.nan)
           for i, q in ((1, 10), (2, 25), (4, 75), (5, 90))}
    df = pd.DataFrame({
        "id": m["height"].astype("int64"),
        "time": pd.to_datetime(m["timestamp"], unit="s", utc=True),
        "median_time": pd.to_datetime(m["mediantime"], unit="s", utc=True),
        "size": m["size"].astype("int64"), "weight": m["weight"].astype("int64"),
        "stripped_size": ((m["weight"] - m["size"]) // 3).astype("int64"),
        "version": m["version"].astype("int64"), "nonce": m["nonce"].astype("int64"), "bits": m["bits"].astype("int64"),
        "difficulty": m["difficulty"].astype(float), "coinbase_data_hex": m["coinbaseRaw"].astype("string"),
        "transaction_count": m["tx_count"].astype("int64"), "witness_count": m["segwitTotalTxs"].fillna(0).astype("int64"),
        "input_count": m["totalInputs"].fillna(0).astype("int64"), "output_count": m["totalOutputs"].fillna(0).astype("int64"),
        "input_total": np.nan, "output_total": np.nan, "fee_total": m["totalFees"].astype(float),
        "fee_per_kwu": m["totalFees"].astype(float) / m["weight"].clip(lower=1) * 1000, "cdd_total": np.nan,
        "generation": (m["reward"] - m["totalFees"]).astype(float), "reward": m["reward"].astype(float),
        "guessed_miner": m["pool"].fillna("Unknown").astype("string"),
        "fee_min": fee_min.astype(float), "fee_median": m["medianFee"].astype(float),
        "match_rate": m["matchRate"].astype(float),
        **{k: v.astype(float) for k, v in pct.items()},
    }).drop_duplicates("id")
    return df, {"mempool_rows": len(df), "mempool_stale_removed": stale}


def coinbase_ascii(hexstr) -> str:
    if hexstr is None or pd.isna(hexstr):
        return ""
    try:
        b = bytes.fromhex(str(hexstr))
    except ValueError:
        return ""
    return "".join(chr(x) if 32 <= x < 127 else " " for x in b)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower()).replace("pool", "")


def tag_labels(asc: pd.Series, tags: list) -> pd.Series:
    """Our transparent labeller: first coinbase tag (mempool.space definitions, file order) found in the text."""
    label = pd.Series(pd.NA, index=asc.index, dtype="string")
    for tag, name in tags:
        hit = label.isna() & asc.str.contains(tag, regex=False)
        label[hit] = name
    return label


def label_miners(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict]:
    pools = read_json(RAW / "pools-v2.json")
    tags = [(t, p["name"]) for p in pools for t in p["tags"]]
    asc = df["coinbase_data_hex"].map(coinbase_ascii)
    from_mempool = df["source"] == "mempool"
    label = pd.Series(pd.NA, index=df.index, dtype="string")
    source = pd.Series("none", index=df.index, dtype="string")
    label[from_mempool] = df.loc[from_mempool, "guessed_miner"]
    source[from_mempool] = "mempool_attribution"
    tl = tag_labels(asc[~from_mempool], tags)
    label[~from_mempool] = tl
    source[~from_mempool & label.notna()] = "coinbase_tag"
    known = {_norm(p["name"]): p["name"] for p in pools}
    gm = df["guessed_miner"].fillna("Unknown")
    mapped = gm.map(lambda g: NAME_FIX.get(g) or known.get(_norm(g)) or g)
    fb = label.isna() & (gm != "Unknown") & ~from_mempool
    label[fb] = mapped[fb]
    source[fb] = "blockchair_address_guess"
    label = label.fillna("Unknown")
    solo = read_json(RAW / "solo_blocks.json")
    solo_map = {r["height"]: r["pool"] for r in solo}
    is_solo = df["id"].isin(solo_map)
    changed = int((label[is_solo] != df.loc[is_solo, "id"].map(solo_map)).sum())
    label[is_solo] = df.loc[is_solo, "id"].map(solo_map)
    source[is_solo] = "mempool_solo_list"
    stats = {"by_source": source.value_counts().to_dict(), "solo_overrides_changed": changed,
             "tag_definitions": len(tags), "solo_blocks": int(is_solo.sum())}
    return label, source, stats


def audit_labels(df: pd.DataFrame) -> dict:
    """How accurate is the coinbase-tag labeller used for 2009-2018? Apply it to every 2019+ block and compare
    with mempool.space's attribution (tags + payout addresses + manual curation) for the same blocks."""
    pools = read_json(RAW / "pools-v2.json")
    tags = [(t, p["name"]) for p in pools for t in p["tags"]]
    m = df[df["source"] == "mempool"]
    ours = tag_labels(m["coinbase_ascii"], tags).fillna("Unknown")
    ref = m["miner"]
    agree = ours == ref
    attributed = ours != "Unknown"
    dis = pd.DataFrame({"ref": ref, "ours": ours})[~agree].value_counts().head(12)
    return {"method": "coinbase-tag labeller re-applied to mempool.space-labelled blocks (2019+)",
            "blocks_compared": int(len(m)), "agreement": float(agree.mean()),
            "precision_when_tag_found": float(agree[attributed].mean()),
            "coverage_tag_found": float(attributed.mean()),
            "top_disagreements": [{"mempool": a, "ours": b, "n": int(n)} for (a, b), n in dis.items()]}


def era_of(t: pd.Series) -> pd.Series:
    eras = cfg()["eras"]
    out = pd.Series(eras[0]["name"], index=t.index, dtype="string")
    for e in eras[1:]:
        out[t >= pd.Timestamp(e["start"], tz="UTC")] = e["name"]
    return out


def quality(df: pd.DataFrame, load: dict) -> dict:
    h = df["id"].to_numpy()
    expected = np.arange(h.min(), h.max() + 1)
    missing_heights = np.setdiff1d(expected, h)
    dt = df["time"].diff().dt.total_seconds()
    retarget = (df["id"] % 2016 != 0) & (df["bits"].diff().fillna(0) != 0) & (df["id"].diff() == 1)
    na = df[USECOLS].isna().sum()
    q = {
        **load,
        "height_range": [int(h.min()), int(h.max())],
        "duplicate_heights": int(df["id"].duplicated().sum()),
        "missing_heights": len(missing_heights),
        "missing_values": {k: int(v) for k, v in na.items() if v},
        "timestamp_earlier_than_previous_block": int((dt < 0).sum()),
        "timestamp_earlier_than_previous_share": float((dt < 0).mean()),
        "max_backwards_seconds": float(-dt.min()),
        "intervals_over_2h": int((dt > 7200).sum()),
        "time_minus_median_time_negative": int(((df["time"] - df["median_time"]).dt.total_seconds() <= 0).sum()),
        "difficulty_changes_off_retarget": int(retarget.sum()),
        "empty_blocks": int((df["transaction_count"] == 1).sum()),
        "under_claimed_reward_blocks": int((df["generation"].astype("int64")
                                            < (50e8 / 2 ** (df["id"] // 210000)).astype("int64")).sum()),
        "weight_over_limit": int((df["weight"] > 4_000_000).sum()),
        "coinbase_hex_missing": int(df["coinbase_data_hex"].isna().sum()),
        "unknown_miner_share_by_year": df.assign(y=df["time"].dt.year, u=df["miner"] == "Unknown")
        .groupby("y")["u"].mean().round(4).to_dict(),
        "handling": {
            "out_of_order_timestamps": "kept: allowed by consensus (must exceed median of previous 11 blocks); "
                                        "they carry miner clock / ntime-rolling behaviour, so they are a feature",
            "missing_values": "fee_per_kwu recomputed as fee_total / weight * 1000 where missing; input_total, "
                              "output_total and cdd_total are not provided by mempool.space (2019+) and are not used; "
                              "fee_min / fee_median / match_rate exist only for mempool.space rows (2019+), which is "
                              "the only period where block fingerprints are modelled",
            "noise": "heavy-tailed counts (fees, cdd, transactions) are log-transformed in features; "
                     "no extreme values are deleted because extremes (e.g. inscription-era blocks) are genuine",
            "labels": "Unknown miner is a genuine 'not attributable' state, not a missing value; Unknown blocks are "
                      "excluded from supervised training and become the application set",
        },
    }
    return q


DICTIONARY = [
    # name, description, conceptual type, discrete/continuous, role
    ("id", "Block height (position in the chain)", "ordinal", "discrete", "identifier / time index (never a feature)"),
    ("time", "Timestamp written by the miner (UTC)", "interval", "continuous", "split key; derived offsets only"),
    ("median_time", "Median timestamp of the previous 11 blocks", "interval", "continuous", "derived offset only"),
    ("size", "Serialised size in bytes", "ratio", "discrete", "feature (derived)"),
    ("stripped_size", "Size without witness data (bytes)", "ratio", "discrete", "feature (derived)"),
    ("weight", "Block weight (consensus limit 4,000,000)", "ratio", "discrete", "feature (fullness)"),
    ("version", "32-bit version field; BIP9 signalling and ASICBoost version rolling", "nominal (bit field)",
     "discrete", "feature after bit decomposition (an integer value is not a quantity)"),
    ("nonce", "32-bit nonce found by the miner", "nominal (bit field)", "discrete",
     "feature after byte decomposition"),
    ("bits", "Compact difficulty target", "ordinal", "discrete", "excluded (same for all miners in a period)"),
    ("difficulty", "Mining difficulty", "ratio", "continuous", "network context (day level), not a block fingerprint"),
    ("coinbase_data_hex", "Coinbase input script (miners write their tag here)", "nominal (text)", "discrete",
     "LABEL SOURCE: excluded from features to prevent leakage"),
    ("transaction_count", "Transactions in the block incl. coinbase", "ratio", "discrete", "feature"),
    ("witness_count", "Transactions with witness data", "ratio", "discrete", "feature (as share)"),
    ("input_count", "Inputs spent", "ratio", "discrete", "feature (as ratio)"),
    ("output_count", "Outputs created", "ratio", "discrete", "feature (as ratio)"),
    ("input_total", "Total input value (satoshi)", "ratio", "continuous", "excluded (economic activity, not miner)"),
    ("output_total", "Total output value (satoshi)", "ratio", "continuous", "excluded (economic activity, not miner)"),
    ("fee_total", "Total fees collected (satoshi)", "ratio", "continuous", "feature (log, and share of reward)"),
    ("fee_per_kwu", "Fee per 1,000 weight units (satoshi)", "ratio", "continuous", "feature (log)"),
    ("cdd_total", "Coin-days destroyed", "ratio", "continuous", "candidate feature (removed by selection)"),
    ("generation", "Block subsidy (satoshi), halves every 210,000 blocks", "ratio", "discrete", "day-level economics"),
    ("reward", "Subsidy + fees (satoshi)", "ratio", "continuous", "day-level economics"),
    ("guessed_miner", "Blockchair's miner guess (coinbase address/tag)", "nominal", "discrete",
     "LABEL SOURCE (fallback): excluded from features"),
    ("fee_min", "Lowest effective fee rate included in the block (sat/vB), mempool.space 2019+", "ratio", "continuous",
     "feature (log, day-relative): template inclusion policy"),
    ("fee_median", "Median effective fee rate in the block (sat/vB), mempool.space 2019+", "ratio", "continuous",
     "feature (day-relative)"),
    ("fee_p10 / fee_p25 / fee_p75 / fee_p90", "Effective fee-rate percentiles inside the block (sat/vB), mempool.space 2019+",
     "ratio", "continuous", "features (day-relative): out-of-band 'accelerated' low-fee transactions show up here"),
    ("match_rate", "mempool.space similarity of the block to its projected template (2023+ only)", "ratio", "continuous",
     "excluded: missing before 2023 and computed by a third party"),
    ("source", "Row origin: Blockchair dump (2009-2018) or mempool.space (2019+, and dump gaps)", "nominal", "discrete",
     "provenance only"),
    ("miner", "Our cleaned miner label (pool name, solo service, or Unknown)", "nominal", "discrete", "class label"),
    ("era", "Hardware era by date (CPU, GPU, FPGA, ASIC, industrial ASIC)", "ordinal", "discrete",
     "external reference for checking clusters (never a feature)"),
]


def run() -> dict:
    ensure_dirs()
    dumps, load = load_dumps()
    mp, mload = load_mempool()
    start = cfg()["sources"]["mempool_start_height"]
    dumps = dumps[dumps["id"] < start].assign(source="blockchair", fee_min=np.nan, fee_median=np.nan, match_rate=np.nan,
                                               fee_p10=np.nan, fee_p25=np.nan, fee_p75=np.nan, fee_p90=np.nan)
    mp = mp[(mp["id"] >= start) | ~mp["id"].isin(dumps["id"])].assign(source="mempool")
    load.update(mload)
    load["rows_from_dumps"], load["rows_from_mempool"] = int(len(dumps)), int(len(mp))
    df = pd.concat([dumps, mp], ignore_index=True)
    df = df.sort_values("id").drop_duplicates("id", keep="first").reset_index(drop=True)
    df = df[df["time"] < pd.Timestamp(cfg()["sources"]["last_day"], tz="UTC") + pd.Timedelta(days=1)].reset_index(drop=True)
    load["rows_loaded"] = int(len(df))
    miss = df["fee_per_kwu"].isna()
    df.loc[miss, "fee_per_kwu"] = df.loc[miss, "fee_total"] / df.loc[miss, "weight"].clip(lower=1) * 1000
    df["coinbase_ascii"] = df["coinbase_data_hex"].map(coinbase_ascii)
    df["miner"], df["label_source"], label_stats = label_miners(df)
    df["is_solo"] = df["miner"].isin(SOLO_POOLS)
    df["era"] = era_of(df["time"])
    q = quality(df, load)
    q["labels"] = label_stats
    q["label_audit"] = audit_labels(df)
    df.drop(columns=["coinbase_data_hex"]).to_parquet(INTERIM / "blocks.parquet", index=False)
    write_json(ARTIFACTS / "quality_report.json", q)
    pd.DataFrame(DICTIONARY, columns=["attribute", "description", "conceptual_type", "discrete_continuous",
                                      "role"]).to_csv(ARTIFACTS / "data_dictionary.csv", index=False)
    print(f"blocks: {len(df):,}; solo: {int(df['is_solo'].sum())}; audit: {q['label_audit'].get('agreement')}")
    return q
