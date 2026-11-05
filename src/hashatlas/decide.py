"""Stage 9 - decisions on new examples (section 11).

1. Attribution of "Unknown" blocks with the frozen classifier, and its effect on the measured concentration
   (Nakamoto coefficient = smallest number of entities controlling > 50% of blocks).
2. Genuinely new blocks mined after the analysis freeze (1-11 Nov 2026): predicted miner vs the label revealed
   afterwards.
3. The miner advisor: for each device and country electricity price, expected pool income, electricity cost,
   solo-mining odds, and a recommendation (pool / solo as a lottery / do not mine).
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from .config import ARTIFACTS, MODELS, PROCESSED, RAW, cfg, read_json, write_json
from .train import load_sets

COUNTRY_ALIASES = {"United States": "USA", "United Kingdom": "UK", "United Arab Emirates": "UAE"}


def nakamoto(counts: pd.Series) -> int:
    s = counts.sort_values(ascending=False) / counts.sum()
    return int((s.cumsum() < 0.5).sum() + 1)


def electricity() -> pd.DataFrame:
    e = pd.DataFrame(read_json(RAW / "electricity_prices.json")["rows"])
    want = cfg()["decision"]["countries"]
    rows = []
    for c in want:
        key = COUNTRY_ALIASES.get(c, c)
        hit = e[e["country"].str.lower() == key.lower()]
        if len(hit):
            r = hit.iloc[0]
            rows.append({"country": c, "household_usd_kwh": r["household_usd_kwh"],
                         "business_usd_kwh": r["business_usd_kwh"], "available": True,
                         "asia": c in cfg()["decision"]["asia"]})
        else:
            rows.append({"country": c, "household_usd_kwh": None, "business_usd_kwh": None, "available": False,
                         "asia": c in cfg()["decision"]["asia"]})
    return pd.DataFrame(rows)


def advise(ths: float, watts: float, price_kwh: float, hashrate_ths: float, hashprice_usd: float,
           pool_fee: float) -> dict:
    """Economics of one device. Pool income = hash price x TH/s x (1 - fee); electricity = kW x 24 x price.
    Solo: blocks found follow a Poisson process with rate (ths / network) x 144 per day."""
    income = hashprice_usd * ths * (1 - pool_fee)
    cost = watts / 1000 * 24 * price_kwh
    lam_day = ths / hashrate_ths * 144
    p_year = 1 - np.exp(-lam_day * 365)
    rec = ("pool mining (profitable)" if income > cost else
           "do not mine for profit; solo only as a lottery ticket" if ths < 50 else "do not mine (unprofitable)")
    return {"pool_income_usd_day": income, "electricity_usd_day": cost, "profit_usd_day": income - cost,
            "breakeven_usd_kwh": income / (watts / 1000 * 24), "solo_p_block_per_year": p_year,
            "solo_expected_years_to_block": (1 / lam_day / 365) if lam_day > 0 else None,
            "recommendation": rec}


def run() -> dict:
    c = cfg()
    sel = read_json(ARTIFACTS / "model_selection.json")
    feats = sel["features"]
    model = joblib.load(MODELS / f"final_{sel['chosen_family']}.joblib")
    tree = joblib.load(MODELS / "final_tree.joblib")
    sets, cmap = load_sets()
    out = {}
    # 1. Unknown attribution over the last 12 months before the freeze
    hist = pd.concat([sets["train"], sets["validation"], sets["test"]])
    last = hist[hist["time"] >= hist["time"].max() - pd.Timedelta(days=365)]
    unk = last[last["y"] == "Unknown"]
    known = last[last["y"] != "Unknown"]
    pred = pd.Series(model.predict(unk[feats].astype(float)), index=unk.index) if len(unk) else pd.Series(dtype=str)
    prob = tree.predict_proba(unk[feats].astype(float)).max(axis=1) if len(unk) else np.array([])
    by_miner = known["miner"].value_counts()
    fams = read_json(ARTIFACTS / "clusters.json")["pool_families"]["families"]
    fam_of = {p: " + ".join(f) for f in fams for p in f if len(f) > 1}
    by_family = known["miner"].map(lambda m: fam_of.get(m, m)).value_counts()
    out["unknown_attribution"] = {
        "window": [str(last["time"].min().date()), str(last["time"].max().date())],
        "blocks": len(last), "unknown_blocks": len(unk), "unknown_share": len(unk) / len(last),
        "predicted_classes": pred.value_counts().to_dict(),
        "high_confidence_share": float((prob >= 0.6).mean()) if len(prob) else None,
        "nakamoto_by_pool_name": nakamoto(by_miner),
        "nakamoto_after_family_merge": nakamoto(by_family),
        "top5_pool_share": float(by_miner.head(5).sum() / by_miner.sum()),
        "top_families": by_family.head(6).to_dict(),
        "caution": "family merges come from fingerprint similarity (section 9), which suggests but does not prove "
                   "common control; shared templates can also come from shared software or proxy arrangements",
    }
    # 2. New blocks after the freeze: predictions first, labels revealed afterwards
    new = sets["new"]
    nl = new[new["y"] != "Unknown"]
    pn = model.predict(nl[feats].astype(float)) if len(nl) else np.array([])
    out["new_blocks"] = {
        "period": c["classification"]["new"], "blocks": len(new), "labelled": len(nl),
        "accuracy": float(np.mean(pn == nl["y"].to_numpy())) if len(nl) else None,
        "examples": [{"height": int(r.id), "time": str(r.time), "predicted": p, "revealed_label": r.y,
                      "correct": p == r.y} for r, p in list(zip(nl.itertuples(), pn))[-12:]],
        "solo_in_new": int((new["y"] == "Solo").sum()),
    }
    # 3. Miner advisor at the latest observed network state
    d = pd.read_parquet(PROCESSED / "days.parquet")
    freeze = pd.Timestamp(c["sources"]["freeze_day"], tz="UTC")
    d = d[d.index <= freeze].dropna(subset=["hashrate_ths", "price_usd"])
    now = d.iloc[-30:]
    state = {"date": str(now.index[-1].date()), "hashrate_ths_30d": float(now["hashrate_ths"].mean()),
             "price_usd_30d": float(now["price_usd"].mean()),
             "hashprice_usd_th_day_30d": float(now["hashprice_usd_th_day"].mean()),
             "fee_share_30d": float(now["fee_share"].mean())}
    elec = electricity()
    table = []
    for dev in c["decision"]["default_devices"]:
        for _, r in elec[elec["available"]].iterrows():
            for tariff in ("household_usd_kwh", "business_usd_kwh"):
                if pd.isna(r[tariff]):
                    continue
                a = advise(dev["ths"], dev["watts"], float(r[tariff]), state["hashrate_ths_30d"],
                           state["hashprice_usd_th_day_30d"], c["decision"]["pool_fee"])
                table.append({"device": dev["name"], "country": r["country"], "asia": bool(r["asia"]),
                              "tariff": tariff.split("_")[0], "price_usd_kwh": float(r[tariff]), **a})
    out["network_state"] = state
    out["electricity"] = elec.to_dict(orient="records")
    out["electricity_source"] = read_json(RAW / "electricity_prices.json")["source"]
    out["advisor"] = table
    out["devices"] = c["decision"]["default_devices"]
    write_json(ARTIFACTS / "decisions.json", out)
    ua = out["unknown_attribution"]
    print("unknown share", round(ua["unknown_share"], 4), "nakamoto", ua["nakamoto_by_pool_name"], "->",
          ua["nakamoto_after_family_merge"], "| new-block accuracy", out["new_blocks"]["accuracy"])
    return out
