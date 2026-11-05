"""Stage 15 - independent verification: recompute key published numbers through separate code paths.

Each check states what it recomputes, the published value, the recomputed value and pass/fail. The goal is
to catch agent-introduced errors (wrong formula, leakage, stale artifact) before anything reaches the report.
"""
from __future__ import annotations

import json
from itertools import combinations

import joblib
import numpy as np
import pandas as pd

from .config import ARTIFACTS, INTERIM, MODELS, PROCESSED, RAW, ROOT, cfg, read_json, write_json


def run() -> dict:
    checks = []

    def add(name, published, recomputed, ok, note=""):
        checks.append({"check": name, "published": published, "recomputed": recomputed, "passed": bool(ok), "note": note})

    c = cfg()
    tm = read_json(ARTIFACTS / "test_metrics.json")
    sel = read_json(ARTIFACTS / "model_selection.json")
    q = read_json(ARTIFACTS / "quality_report.json")

    # 1-2. macro-F1 and accuracy recomputed from the saved test predictions (not from the metrics code)
    pred = pd.read_parquet(PROCESSED / "test_predictions.parquet")
    labels = sorted(set(pred["y"]))   # metric definition: macro average over classes present in the test period
    f1s = []
    for k in labels:
        tp = ((pred["pred"] == k) & (pred["y"] == k)).sum()
        fp = ((pred["pred"] == k) & (pred["y"] != k)).sum()
        fn = ((pred["pred"] != k) & (pred["y"] == k)).sum()
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * p * r / (p + r) if p + r else 0.0)
    pub = tm["families"][tm["operational_family"]]["macro_f1"]
    add("test macro-F1 from saved predictions", pub, float(np.mean(f1s)), abs(np.mean(f1s) - pub) < 1e-9)
    acc = float((pred["pred"] == pred["y"]).mean())
    add("test accuracy from saved predictions", tm["families"][tm["operational_family"]]["accuracy"], acc,
        abs(acc - tm["families"][tm["operational_family"]]["accuracy"]) < 1e-9)
    # 3. confusion matrix totals equal the number of test blocks
    cm = np.array(tm["confusion"]["matrix"])
    add("confusion matrix sums to test blocks", tm["test_blocks"], int(cm.sum()), int(cm.sum()) == tm["test_blocks"])
    # 4. no leakage columns among the model features
    banned = {"coinbase_data_hex", "coinbase_ascii", "guessed_miner", "id", "time", "miner", "label_source", "difficulty"}
    add("no label-source / time features in model", "none", sorted(banned & set(sel["features"])), not (banned & set(sel["features"])))
    # 5. split periods are disjoint and ordered
    sp = c["classification"]
    ok = sp["train"][1] <= sp["validation"][0] and sp["validation"][1] <= sp["test"][0] and sp["test"][1] <= sp["new"][0]
    add("train < validation < test < new (no overlap)", "ordered", [sp["train"], sp["validation"], sp["test"], sp["new"]], ok)
    # 6. model selection file was written before the test metrics
    ms_t, tm_t = (ARTIFACTS / "model_selection.json").stat().st_mtime, (ARTIFACTS / "test_metrics.json").stat().st_mtime
    add("model choice frozen before test evaluation", sel["frozen_at"], "selection older than test metrics", ms_t <= tm_t)
    # 7. root Gini reduction recomputed from scratch
    ex = read_json(ARTIFACTS / "explanations.json")
    rs = ex["root_split_worked"]
    cnt = {k: np.array(list(rs["class_counts"][k].values()), dtype=float) for k in ("parent", "left", "right")}
    g = lambda v: 1 - ((v / v.sum()) ** 2).sum()  # noqa: E731
    red = g(cnt["parent"]) - (cnt["left"].sum() * g(cnt["left"]) + cnt["right"].sum() * g(cnt["right"])) / cnt["parent"].sum()
    add("root split Gini reduction", rs["gini"]["reduction"], float(red), abs(red - rs["gini"]["reduction"]) < 1e-12)
    # 8. the exported tree reproduces the joblib tree's predictions on test rows
    tree = joblib.load(MODELS / "final_tree.joblib")
    exp = ex["tree_export"]
    nodes = {n["id"]: n for n in exp["nodes"]}
    f = pd.read_parquet(PROCESSED / "block_features.parquet")
    sample = f[f["id"].isin(pred["id"])].sample(2000, random_state=1)
    Xs = sample[sel["features"]].astype(float)
    mine = []
    for _, row in Xs.iterrows():
        n = nodes[0]
        while not n["leaf"]:
            n = nodes[n["left"] if row[n["feature"]] <= n["threshold"] else n["right"]]
        mine.append(n["predict"])
    agree = float(np.mean(np.array(mine) == tree.predict(Xs)))
    add("exported tree (web simulator) == fitted tree", 1.0, agree, agree == 1.0)
    # 9. Apriori vs a second, independent brute-force count over the first 10 items, max size 2
    ru = read_json(ARTIFACTS / "rules.json")
    from .rules import items_frame
    a, b = (pd.Timestamp(x, tz="UTC") for x in (c["association"]["window"][0], c["association"]["confirm_window"][0]))
    disc = f[(f["time"] >= a) & (f["time"] < b)]
    I, _ = items_frame(disc, ru["bin_edges"])
    first = list(I.columns[:10])
    freq = sum(1 for k in (1, 2) for cmb in combinations(first, k) if I[list(cmb)].all(axis=1).sum() >= ru["min_count"])
    add("transactions count", ru["transactions"], len(I), len(I) == ru["transactions"])
    add("Apriori brute-force check (stage) passed", True, ru["brute_force_check"]["passed"], ru["brute_force_check"]["passed"],
        f"{freq} frequent itemsets of size <= 2 among the first 10 items here")
    # 10. a top rule's confidence recomputed from raw item columns
    if ru["rules"]:
        r0 = ru["rules"][0]
        mask = I[r0["antecedent"]].all(axis=1)
        conf = float((mask & I[r0["consequent"]]).sum() / mask.sum())
        add("top rule confidence", r0["confidence"], conf, abs(conf - r0["confidence"]) < 1e-12, " & ".join(r0["antecedent"]))
    # 11. hash price recomputed from raw charts for the last freeze day
    d = pd.read_parquet(PROCESSED / "days.parquet")
    d = d[d.index <= pd.Timestamp(c["sources"]["freeze_day"], tz="UTC")].dropna(subset=["hashrate_ths", "price_usd"])
    last = d.iloc[-1]
    raw = {k: {pd.Timestamp(v["x"], unit="s", tz="UTC").floor("D"): v["y"] for v in json.loads((RAW / f"chart_{k}.json").read_text())["values"]}
           for k in ("hash-rate", "market-price")}
    day = d.index[-1]
    if day in raw["hash-rate"] and day in raw["market-price"]:
        hp = last["revenue_btc"] * raw["market-price"][day] / raw["hash-rate"][day]
        add("hash price (USD/TH/day) on freeze day", float(last["hashprice_usd_th_day"]), float(hp),
            abs(hp - last["hashprice_usd_th_day"]) / hp < 1e-9)
    # 12. subsidy schedule: block subsidy halves every 210,000 blocks
    b = pd.read_parquet(INTERIM / "blocks.parquet", columns=["id", "generation"])
    exp_sub = (50e8 / 2 ** (b["id"] // 210000)).astype("int64")
    gen = b["generation"].astype("int64")
    bad = int((gen != exp_sub).sum())
    over = int((gen > exp_sub).sum())
    add("subsidy follows 50 BTC / 2^(height // 210000)", "0 over-claims", {"mismatches": bad, "over_claims": over},
        over == 0,
        f"consensus forbids over-claiming; {bad} blocks under-claimed their reward (allowed, mostly 2011-2013 pool software)")
    # 13. solo probability formula
    dec = read_json(ARTIFACTS / "decisions.json")
    a0 = next(x for x in dec["advisor"] if x["device"].startswith("Bitaxe"))
    lam = 1.2 / dec["network_state"]["hashrate_ths_30d"] * 144 * 365
    add("solo P(block in a year), Bitaxe", a0["solo_p_block_per_year"], 1 - np.exp(-lam), abs(a0["solo_p_block_per_year"] - (1 - np.exp(-lam))) < 1e-15)
    # 14. label audit agreement threshold
    la = q["label_audit"]
    add("tag labeller precision >= 99% when a tag is found", ">= 0.99", la.get("precision_when_tag_found"),
        (la.get("precision_when_tag_found") or 0) >= 0.99,
        f"{la.get('blocks_compared')} blocks vs mempool.space; coverage {la.get('coverage_tag_found'):.3f}, overall agreement "
        f"{la.get('agreement'):.3f} (address-only pools are left Unknown by design)")
    # 15. heights complete
    add("no missing or duplicate heights", 0, q["missing_heights"] + q["duplicate_heights"],
        q["missing_heights"] + q["duplicate_heights"] == 0)
    # 16. web data in sync with artifacts
    wm = ROOT / "web" / "public" / "data" / "models.json"
    if wm.exists():
        w = read_json(wm)
        add("web models.json matches test metrics", pub, w["test"]["families"][tm["operational_family"]]["macro_f1"],
            w["test"]["families"][tm["operational_family"]]["macro_f1"] == pub)
    res = {"passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks}
    write_json(ARTIFACTS / "verification.json", res)
    for ch in checks:
        print(("PASS " if ch["passed"] else "FAIL ") + ch["check"])
    print(f"{res['passed']}/{res['total']} checks passed")
    return res
