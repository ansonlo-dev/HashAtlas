"""`hashatlas predict`: apply the frozen models to new examples.

* `--heights H1 H2 ...`: fingerprint any downloaded block (e.g. blocks mined after the freeze) and print the
  predicted miner class, the tree's class probabilities and the root-to-leaf path. The true label is printed
  separately as "revealed_label" so the prediction can be checked afterwards.
* `--ths T --watts W [--country C] [--price P]`: miner advice for a device at a country's electricity price.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from .config import ARTIFACTS, INTERIM, MODELS, read_json
from .decide import advise, electricity
from .explain import trace
from .features import block_features
from .train import to_class


def run(args) -> dict:
    out = {}
    sel = read_json(ARTIFACTS / "model_selection.json")
    if args.heights:
        feats = sel["features"]
        b = pd.read_parquet(INTERIM / "blocks.parquet")
        need = set(args.heights)
        lo = min(need) - 2
        sub = b[(b["id"] >= lo) & (b["id"] <= max(need))].reset_index(drop=True)
        # day-relative features need the whole day: include every block of the days involved
        days = sub["time"].dt.floor("D").unique()
        sub = b[b["time"].dt.floor("D").isin(days) | b["id"].between(lo, max(need))].sort_values("id").reset_index(drop=True)
        f = block_features(sub)
        model = joblib.load(MODELS / f"final_{sel['chosen_family']}.joblib")
        tree = joblib.load(MODELS / "final_tree.joblib")
        cmap = read_json(ARTIFACTS / "class_map.json")
        rows = []
        for h in args.heights:
            i = sub.index[sub["id"] == h]
            if not len(i):
                rows.append({"height": h, "status": "block not in data/interim/blocks.parquet; rerun acquire + clean"})
                continue
            x = f.loc[i, feats].astype(float)
            proba = tree.predict_proba(x)[0]
            rows.append({"height": h, "time": str(sub.loc[i[0], "time"]),
                         "predicted_class": model.predict(x)[0],
                         "tree_probabilities": {k: round(float(p), 4) for k, p in zip(tree.classes_, proba) if p > 0.01},
                         "tree_path": trace(tree, x.iloc[0], feats),
                         "revealed_label": to_class(pd.Series([sub.loc[i[0], "miner"]]), cmap).iloc[0],
                         "revealed_miner": sub.loc[i[0], "miner"]})
        out["blocks"] = rows
    if args.ths:
        dec = read_json(ARTIFACTS / "decisions.json")
        st = dec["network_state"]
        price_mult = (args.price / st["price_usd_30d"]) if args.price else 1.0
        e = electricity()
        r = e[e["country"].str.lower() == args.country.lower()]
        if not len(r):
            raise SystemExit(f"unknown country {args.country!r}; choose from {e['country'].tolist()}")
        r = r.iloc[0]
        kwh = r["business_usd_kwh"] if pd.notna(r["business_usd_kwh"]) else r["household_usd_kwh"]
        a = advise(args.ths, args.watts or args.ths * 17.5, float(kwh), st["hashrate_ths_30d"],
                   st["hashprice_usd_th_day_30d"] * price_mult, 0.02)
        out["advice"] = {"country": r["country"], "usd_kwh": float(kwh), "network_state": st,
                         "price_multiplier": price_mult, **{k: (float(v) if isinstance(v, (float, np.floating)) else v)
                                                            for k, v in a.items()}}
    return out
