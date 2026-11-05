"""Stage 12 - versioned static data for the web dashboard (web/public/data/*.json).

The dashboard never recomputes models; it reads these exports. Light client-side arithmetic (miner economics,
scenario hash price, decision-tree traversal) uses exactly the formulas and the fitted tree exported here.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .config import ARTIFACTS, INTERIM, PROCESSED, ROOT, WEB_DATA, cfg, read_json, write_json


def _r(x, n=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def _sig(x, n=4):
    """Round to n significant digits (hash rate spans 20 orders of magnitude)."""
    if x is None or not np.isfinite(x) or x == 0:
        return None if x is None or not np.isfinite(x) else 0.0
    return float(f"{x:.{n}g}")


def timeline() -> list:
    d = pd.read_parquet(PROCESSED / "days.parquet")
    d = d[d.index <= pd.Timestamp(cfg()["sources"]["last_day"], tz="UTC")]
    w = d.resample("W-MON", label="left", closed="left").agg({
        "hashrate_ths": "mean", "price_usd": "mean", "hashprice_usd_th_day": "mean", "breakeven_usd_kwh": "mean",
        "solo_p_year_bitaxe": "mean", "nakamoto": "mean", "top1_share": "mean", "fee_share": "mean",
        "empty_share": "mean", "unknown_share": "mean", "frontier_j_per_th": "last", "era": "last",
        "solo_blocks": "sum", "blocks": "sum", "frontier_name": "last"})
    wk = pd.read_parquet(PROCESSED / "weeks.parquet")
    wk = wk.set_index(wk.columns[0])
    w = w.join(wk[["kmeans", "hier_ward", "dbscan"]], how="left")
    rows = []
    for t, r in w.iterrows():
        rows.append({"w": str(t.date()), "h": _sig(r["hashrate_ths"] / 1e6), "p": _r(r["price_usd"], 2),
                     "hp": _sig(r["hashprice_usd_th_day"]), "be": _sig(r["breakeven_usd_kwh"]),
                     "sp": _sig(r["solo_p_year_bitaxe"]), "nk": _r(r["nakamoto"], 2), "t1": _r(r["top1_share"]),
                     "fs": _r(r["fee_share"]), "es": _r(r["empty_share"]), "us": _r(r["unknown_share"]),
                     "fr": _r(r["frontier_j_per_th"], 2), "hw": r["frontier_name"], "era": r["era"],
                     "km": None if pd.isna(r["kmeans"]) else int(r["kmeans"]),
                     "hw2": None if pd.isna(r["hier_ward"]) else int(r["hier_ward"]),
                     "db": None if pd.isna(r["dbscan"]) else int(r["dbscan"]),
                     "sb": int(r["solo_blocks"]), "b": int(r["blocks"])})
    return rows


def who_mines() -> dict:
    b = pd.read_parquet(INTERIM / "blocks.parquet", columns=["time", "miner", "is_solo"])
    b = b[b["time"] < pd.Timestamp(cfg()["sources"]["last_day"], tz="UTC") + pd.Timedelta(days=1)]
    q = b["time"].dt.to_period("Q").astype(str)
    top = b.loc[(b["miner"] != "Unknown") & ~b["is_solo"] & (b["time"] >= pd.Timestamp("2019-01-01", tz="UTC")),
                "miner"].value_counts().head(8).index.tolist()
    grp = np.where(b["is_solo"], "Solo services",
                   np.where(b["miner"] == "Unknown", "Unattributed", np.where(b["miner"].isin(top), b["miner"], "Other pools")))
    t = pd.crosstab(q, grp, normalize="index")
    order = ["Unattributed", "Solo services", "Other pools", *top]
    t = t[[c for c in order if c in t]]
    solo = b[b["is_solo"]]
    return {"quarters": t.index.tolist(), "groups": {c: [round(float(x), 4) for x in t[c]] for c in t.columns},
            "solo_by_year": solo.groupby(solo["time"].dt.year).size().to_dict(),
            "solo_by_service": solo["miner"].value_counts().to_dict(),
            "solo_recent": [{"height": int(r.id), "time": str(r.time), "service": r.miner}
                            for r in pd.read_parquet(INTERIM / "blocks.parquet", columns=["id", "time", "miner", "is_solo"])
                            .query("is_solo").tail(25).itertuples()]}


def tree_and_examples() -> dict:
    ex = read_json(ARTIFACTS / "explanations.json")
    sel = read_json(ARTIFACTS / "model_selection.json")
    feats = sel["features"]
    pred = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    f = pd.read_parquet(PROCESSED / "block_features.parquet")
    f = f.merge(pred[["id", "y", "pred", "solo_score"]], on="id", how="left")
    test = f[f["id"].isin(pred["id"])]
    seed = cfg()["project"]["random_seed"]
    picks = pd.concat([test[test["is_solo"]]] +
                      [g.sample(min(len(g), 12), random_state=seed) for _, g in test[~test["is_solo"]].groupby("miner")])
    stats = f[feats].describe(percentiles=[0.01, 0.5, 0.99]).T
    return {"tree": ex["tree_export"], "features": feats,
            "feature_ranges": {k: {"min": _r(stats.loc[k, "1%"]), "max": _r(stats.loc[k, "99%"]),
                                   "median": _r(stats.loc[k, "50%"]),
                                   "binary": bool(f[k].nunique() <= 2)} for k in feats},
            "examples": [{"height": int(r["id"]), "time": str(r["time"])[:16], "miner": r["miner"], "class": r["y"],
                          "x": {k: _r(r[k], 5) for k in feats}} for _, r in picks.iterrows()],
            "traces": ex["traces"], "root_split": ex["root_split_worked"], "knn_example": ex.get("knn_example")}


def radar() -> dict:
    dec = read_json(ARTIFACTS / "decisions.json")
    pred = pd.read_parquet(PROCESSED / "test_predictions.parquet").tail(240)
    b = pd.read_parquet(PROCESSED / "block_features.parquet",
                        columns=["id", "time", "miner", "transaction_count", "fullness", "rel_fee_rate", "ver_rolled",
                                 "is_empty", "witness_byte_share"])
    m = pred.merge(b, on=["id", "time", "miner"], how="left")
    feed = [{"height": int(r.id), "time": str(r.time)[:19], "miner": r.miner, "true": r.y, "pred": r.pred,
             "solo": _r(r.solo_score), "tx": int(r.transaction_count), "full": _r(r.fullness, 3),
             "fee": _r(r.rel_fee_rate, 3), "roll": int(r.ver_rolled), "wit": _r(r.witness_byte_share, 3)}
            for r in m.itertuples()]
    return {"test_tail": feed, "new_blocks": dec["new_blocks"], "unknown_attribution": dec["unknown_attribution"]}


def run() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    c = cfg()
    tm = read_json(ARTIFACTS / "test_metrics.json")
    ms = read_json(ARTIFACTS / "model_search.json")
    sel = read_json(ARTIFACTS / "model_selection.json")
    fs = read_json(ARTIFACTS / "feature_selection.json")
    ex = read_json(ARTIFACTS / "explanations.json")
    cl = read_json(ARTIFACTS / "clusters.json")
    ru = read_json(ARTIFACTS / "rules.json")
    dec = read_json(ARTIFACTS / "decisions.json")
    fu = read_json(ARTIFACTS / "future.json")
    q = read_json(ARTIFACTS / "quality_report.json")
    src = read_json(ARTIFACTS / "source_manifest.json")
    split = read_json(ARTIFACTS / "split_manifest.json")
    team = read_json(ROOT / "configs" / "team.json")
    tl = timeline()
    last = [r for r in tl if r["h"]][-2]
    s21 = next(a for a in dec["advisor"] if a["device"] == "Antminer S21")
    meta = {
        "project": c["project"]["name"], "data_version": c["project"]["data_version"],
        "model_version": c["project"]["model_version"], "freeze_day": c["sources"]["freeze_day"],
        "last_day": c["sources"]["last_day"], "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "counts": {"blocks": q["rows_loaded"], "height_max": q["height_range"][1], "weeks": len(tl),
                   "modern_blocks": sum(v["rows"] for k, v in split.items() if k in ("train", "validation", "test", "new")),
                   "solo_blocks": q["labels"]["solo_blocks"], "pool_definitions": src["pool_definitions"]["n_definitions"],
                   "label_audit_blocks": q["label_audit"].get("blocks_compared"),
                   "label_audit_agreement": q["label_audit"].get("agreement")},
        "headline": {"hashrate_eh": last["h"], "price_usd": last["p"], "hashprice": last["hp"],
                     "solo_p_bitaxe": last["sp"], "nakamoto": dec["unknown_attribution"]["nakamoto_by_pool_name"],
                     "nakamoto_family": dec["unknown_attribution"]["nakamoto_after_family_merge"],
                     "macro_f1_test": tm["families"][tm["operational_family"]]["macro_f1"],
                     "macro_f1_ci": tm["bootstrap"]["macro_f1_95ci"], "operational_family": tm["operational_family"],
                     "top3": tm["families"][tm["operational_family"]].get("top3_accuracy"), "n_classes": len(sel["classes"]),
                     "halving_p50": fu["halving"]["date_p50"], "breakeven_s21": s21["breakeven_usd_kwh"],
                     "era_ari": cl["ari_vs_hardware_eras"]["kmeans"], "rules": ru["n_rules"]},
        "sources": [
            {"name": "Blockchair daily block dumps", "url": "https://blockchair.com/dumps", "use": "every block since 2009"},
            {"name": "mempool.space mining-pool definitions & API", "url": "https://github.com/mempool/mining-pools",
             "use": "coinbase-tag labels, solo-service lists, label audit"},
            {"name": "blockchain.com charts API", "url": "https://www.blockchain.com/explorer/charts",
             "use": "daily hash rate, price, miner revenue"},
            {"name": "GlobalPetrolPrices electricity prices", "url": c["sources"]["electricity_url"],
             "use": "household and business USD/kWh by country (dated snapshot)"},
        ],
        "team": team,
    }
    out = {
        "meta": meta, "timeline": tl, "whomines": who_mines(),
        "models": {"selection": sel, "split": split, "class_map": read_json(ARTIFACTS / "class_map.json"),
                   "feature_selection": fs, "search": {k: {kk: vv for kk, vv in v.items() if kk != "grid"}
                                                       for k, v in ms["families"].items()},
                   "nested_cv": ms["nested_cv_tree"], "test": tm, "importance": ex["permutation_importance"][:20],
                   "complexity": ex["complexity"], "svm_coef": ex["svm_linear_solo_coefficients"]},
        "tree": tree_and_examples(), "radar": radar(),
        "clusters": {k: v for k, v in cl.items() if k != "ward_dendrogram_truncated"},
        "rules": ru,
        "advisor": {"network": dec["network_state"], "electricity": dec["electricity"], "devices": dec["devices"],
                    "pool_fee": c["decision"]["pool_fee"], "hardware": pd.read_csv(ARTIFACTS / "hardware_frontier.csv").to_dict(orient="records"),
                    "source": dec["electricity_source"]},
        "future": fu,
        "quality": {"report": q, "dictionary": pd.read_csv(ARTIFACTS / "data_dictionary.csv").to_dict(orient="records"),
                    "sources": src},
    }
    for k, v in out.items():
        write_json(WEB_DATA / f"{k}.json", v, indent=None)
    sizes = {p.name: p.stat().st_size for p in WEB_DATA.glob("*.json")}
    print("web data:", {k: f"{v / 1024:.0f} KB" for k, v in sizes.items()})
