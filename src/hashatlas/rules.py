"""Mine discretised block properties with Apriori and check counts by brute force.

Bin edges use the discovery window. Candidate generation, subset pruning and
support counts are recorded at each level. Rules are remeasured on a later
window; within-pool and Solo contrasts retain signatures below global support."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from .acquire import SOLO_POOLS
from .config import ARTIFACTS, PROCESSED, cfg, read_json, write_json


def items_frame(f: pd.DataFrame, edges: dict | None = None) -> tuple[pd.DataFrame, dict]:
    if edges is None:
        edges = {"ts_q90": float(f["ts_minus_median_s"].quantile(0.90)),
                 "wit_q75": float(f["witness_byte_share"].quantile(0.75)),
                 "io_q25": float(f["io_ratio"].quantile(0.25)), "io_q75": float(f["io_ratio"].quantile(0.75))}
    # miner item = the actual pool for pools with >= 1% of the discovery window, otherwise "small pools"
    if "pools" not in edges:
        share = f.loc[f["miner"] != "Unknown", "miner"].value_counts(normalize=True)
        edges["pools"] = sorted(m for m, v in share.items() if v >= 0.01 and m not in SOLO_POOLS)
    big = set(edges["pools"])
    miner = f["miner"].map(lambda m: "Solo" if m in SOLO_POOLS else ("Unknown" if m == "Unknown" else
                                                                       (m if m in big else "small pools")))
    I = pd.DataFrame(index=f.index)
    I["block=empty"] = f["is_empty"] == 1
    I["fullness=full(>=98%)"] = f["fullness"] >= 0.98
    I["fullness=light(<50%)"] = (f["fullness"] < 0.5) & (f["is_empty"] == 0)
    I["version=no-rolling"] = f["ver_rolled"] == 0
    pc = f["ver_roll_popcount"]
    I["version=rolls 1-4 bits"] = pc.between(1, 4)
    I["version=rolls 5-8 bits"] = pc.between(5, 8)
    I["version=rolls 9-12 bits"] = pc.between(9, 12)
    I["version=rolls 13-16 bits"] = pc >= 13
    I["version=signal bits set"] = f["ver_signal_bits"] > 0
    I["time=far-ahead-of-median"] = f["ts_minus_median_s"] > edges["ts_q90"]
    I["interval=fast(<60s)"] = f["interval_prev_s"] < 60
    I["interval=slow(>30min)"] = f["interval_prev_s"] > 1800
    I["fees=below-day-median"] = f["rel_fee_rate"] < -0.05
    I["fees=above-day-median"] = f["rel_fee_rate"] > 0.05
    I["txcount=below-day-median"] = f["rel_tx_count"] < -0.05
    I["content=witness-heavy"] = f["witness_byte_share"] > edges["wit_q75"]
    I["shape=consolidating"] = f["io_ratio"] < edges["io_q25"]
    I["shape=fan-out"] = f["io_ratio"] > edges["io_q75"]
    for m in sorted(miner.unique()):
        I[f"miner={m}"] = miner == m
    return I.astype(bool), edges


def apriori(M: np.ndarray, names: list[str], min_count: int, max_len: int) -> tuple[dict, list[dict]]:
    n_items = M.shape[1]
    support = {}
    trace = []
    cnt1 = M.sum(axis=0)
    level = [(i,) for i in range(n_items) if cnt1[i] >= min_count]
    for (i,) in level:
        support[(i,)] = int(cnt1[i])
    trace.append({"k": 1, "candidates": n_items, "pruned_by_subset": 0, "counted": n_items, "frequent": len(level)})
    k = 2
    while level and k <= max_len:
        prev = set(level)
        cands = set()
        for a, b in combinations(sorted(level), 2):
            if a[:-1] == b[:-1]:
                cands.add(tuple(sorted(set(a) | set(b))))
        joined = len(cands)
        survivors = [c for c in cands if all(s in prev for s in combinations(c, k - 1))]
        freq = []
        for c in survivors:
            n = int(np.logical_and.reduce(M[:, list(c)], axis=1).sum())
            if n >= min_count:
                support[c] = n
                freq.append(c)
        trace.append({"k": k, "candidates": joined, "pruned_by_subset": joined - len(survivors),
                      "counted": len(survivors), "frequent": len(freq)})
        level = freq
        k += 1
    return support, trace


def brute_force_check(M: np.ndarray, support: dict, min_count: int, max_items: int = 12, max_len: int = 3) -> dict:
    """Enumerate every itemset over the first `max_items` items and compare with Apriori's output."""
    found, missing, wrong = 0, 0, 0
    for k in range(1, max_len + 1):
        for c in combinations(range(min(max_items, M.shape[1])), k):
            n = int(np.logical_and.reduce(M[:, list(c)], axis=1).sum())
            if n >= min_count:
                found += 1
                if c not in support:
                    missing += 1
                elif support[c] != n:
                    wrong += 1
    return {"items_checked": min(max_items, M.shape[1]), "max_len": max_len, "frequent_by_brute_force": found,
            "missing_from_apriori": missing, "wrong_counts": wrong, "passed": missing == 0 and wrong == 0}


def rules_from(support: dict, names: list[str], n: int, min_conf: float, consequent_prefix: str = "miner=") -> list:
    out = []
    for iset, cnt in support.items():
        if len(iset) < 2:
            continue
        for j in iset:
            if not names[j].startswith(consequent_prefix):
                continue
            ante = tuple(x for x in iset if x != j)
            if any(names[x].startswith(consequent_prefix) for x in ante):
                continue
            conf = cnt / support[ante]
            if conf < min_conf:
                continue
            base = support[(j,)] / n
            out.append({"antecedent": [names[x] for x in ante], "consequent": names[j], "count": cnt,
                        "support": cnt / n, "confidence": conf, "lift": conf / base, "consequent_base_rate": base,
                        "reverse_confidence": cnt / support[(j,)]})
    out.sort(key=lambda r: (-r["lift"], -r["support"]))
    return out


def confirm(rules: list, I2: pd.DataFrame) -> list:
    n = len(I2)
    for r in rules:
        a = I2[r["antecedent"]].all(axis=1) if all(x in I2 for x in r["antecedent"]) else pd.Series(False, index=I2.index)
        cons = I2[r["consequent"]] if r["consequent"] in I2 else pd.Series(False, index=I2.index)
        na, nab = int(a.sum()), int((a & cons).sum())
        r["confirm_support"] = nab / n if n else None
        r["confirm_confidence"] = nab / na if na else None
        r["confirm_lift"] = (nab / na) / cons.mean() if na and cons.mean() > 0 else None
        r["confirmed"] = bool(na and nab / na >= 0.8 * r["confidence"] and (r["confirm_lift"] or 0) > 1.2)
    return rules


def contrast(Mfeat: np.ndarray, names: list[str], inside: np.ndarray, outside: np.ndarray, min_share: float,
             max_len: int = 3) -> list[dict]:
    """Frequent itemsets inside one group (Apriori on that group's blocks) compared with their support outside."""
    Mi, Mo = Mfeat[inside], Mfeat[outside]
    sup, _ = apriori(Mi, names, max(5, int(np.ceil(min_share * len(Mi)))), max_len)
    out = []
    for iset, cnt in sup.items():
        so = float(np.logical_and.reduce(Mo[:, list(iset)], axis=1).mean())
        si = cnt / len(Mi)
        out.append({"itemset": [names[x] for x in iset], "support_inside": si, "support_outside": so,
                    "ratio": si / so if so > 0 else None, "blocks": int(cnt)})
    out.sort(key=lambda r: -(r["ratio"] if r["ratio"] is not None else 1e9))
    return out


def run() -> dict:
    c = cfg()["association"]
    f = pd.read_parquet(PROCESSED / "block_features.parquet")
    a, b = (pd.Timestamp(x, tz="UTC") for x in c["window"])
    ca, cb = (pd.Timestamp(x, tz="UTC") for x in c["confirm_window"])
    disc = f[(f["time"] >= a) & (f["time"] < ca)]
    conf_ = f[(f["time"] >= ca) & (f["time"] < cb)]
    I, edges = items_frame(disc)
    I2, _ = items_frame(conf_, edges)
    names = list(I.columns)
    M = I.to_numpy()
    n = len(M)
    min_count = int(np.ceil(c["min_support"] * n))
    support, trace = apriori(M, names, min_count, c["max_len"])
    check = brute_force_check(M, support, min_count)
    rules = confirm(rules_from(support, names, n, c["min_confidence"]), I2)
    # Solo contrast: frequent itemsets inside Solo blocks (2019+ for enough rows) vs their support in pool blocks
    s_all = f[(f["time"] < cb)]
    Is, _ = items_frame(s_all, edges)
    feat_cols = [x for x in Is.columns if not x.startswith("miner=")]
    solo_mask = s_all["is_solo"].to_numpy()
    pool_mask = (~solo_mask) & (s_all["miner"] != "Unknown").to_numpy()
    Ms = Is[feat_cols].to_numpy()[solo_mask]
    sup_s, _ = apriori(Ms, feat_cols, max(5, int(0.25 * len(Ms))), 3)
    Mp = Is[feat_cols].to_numpy()[pool_mask]
    contrast_solo = []
    for iset, cnt in sup_s.items():
        sp = float(np.logical_and.reduce(Mp[:, list(iset)], axis=1).mean())
        ss = cnt / len(Ms)
        contrast_solo.append({"itemset": [feat_cols[x] for x in iset], "support_in_solo": ss, "support_in_pools": sp,
                              "ratio": ss / sp if sp > 0 else None, "solo_blocks": int(cnt)})
    contrast_solo.sort(key=lambda r: -(r["ratio"] or 0))
    # Pool signatures: for every pool with >= 1% of discovery blocks, its most over-represented frequent itemsets
    Md = I[feat_cols].to_numpy()
    sigs = []
    for p in edges["pools"]:
        inside = (I[f"miner={p}"]).to_numpy()
        outside = ~inside & ~I.get("miner=Unknown", pd.Series(False, index=I.index)).to_numpy()
        c_ = [r for r in contrast(Md, feat_cols, inside, outside, 0.30) if (r["ratio"] or 0) > 1.2]
        sigs.append({"pool": p, "blocks": int(inside.sum()), "top": c_[:4]})
    sigs.sort(key=lambda r: -((r["top"][0]["ratio"] or 0) if r["top"] else 0))
    res = {"discovery_window": [c["window"][0], c["confirm_window"][0]], "confirm_window": c["confirm_window"],
           "transactions": n, "confirm_transactions": len(I2), "items": names, "bin_edges": edges,
           "item_support": {k: float(v) for k, v in I.mean().items()},
           "min_support": c["min_support"], "min_count": min_count, "min_confidence": c["min_confidence"],
           "apriori_trace": trace, "frequent_itemsets": len(support), "brute_force_check": check,
           "rules": rules[:150], "n_rules": len(rules),
           "solo_contrast": {"solo_blocks": int(solo_mask.sum()), "pool_blocks": int(pool_mask.sum()),
                             "min_support_in_solo": 0.25, "itemsets": contrast_solo[:40]},
           "pool_signatures": sigs}
    write_json(ARTIFACTS / "rules.json", res)
    print(f"apriori: {len(support)} frequent itemsets, {len(rules)} rules, brute force passed={check['passed']}")
    return res
