"""Stage 10 - Future Lab: scenario projections, not predictions (section 12).

What is known for certain is the protocol schedule: the subsidy halves at height 1,050,000. Everything else is
uncertain, so we (1) simulate network hash-rate paths by block-bootstrapping 30-day blocks of historical daily
log-growth from the industrial-ASIC era, (2) convert each path into block timing (difficulty lags hash rate by
about a week, so blocks arrive faster while hash rate grows) and hence a halving-date distribution, (3) treat the
BTC price and the fee share as user-chosen scenarios instead of forecasting them, and (4) backtest the same
projection method from four historical origins to report how wrong it would have been.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ARTIFACTS, PROCESSED, cfg, write_json

DEVICES_FUTURE = [{"name": "Bitaxe-class home miner", "ths": 1.2, "watts": 18},
                  {"name": "Antminer S21", "ths": 200, "watts": 3500},
                  {"name": "Antminer S21 XP Hyd", "ths": 473, "watts": 5676}]


def series() -> pd.Series:
    d = pd.read_parquet(PROCESSED / "days.parquet")
    d = d[d.index <= pd.Timestamp(cfg()["sources"]["freeze_day"], tz="UTC")]
    return np.log(d["hashrate_ths"].dropna()).rolling(7, min_periods=3).mean().dropna()


def simulate(logh: pd.Series, origin: pd.Timestamp, start: str, horizon: int, n_paths: int, seed: int,
             block: int = 30) -> np.ndarray:
    """Return an (n_paths, horizon+1) array of log hash rate, starting at the origin value."""
    hist = logh[(logh.index >= pd.Timestamp(start, tz="UTC")) & (logh.index <= origin)]
    inc = hist.diff().dropna().to_numpy()
    rs = np.random.RandomState(seed)
    n_blocks = int(np.ceil(horizon / block))
    starts = rs.randint(0, len(inc) - block, size=(n_paths, n_blocks))
    steps = np.stack([inc[s:s + block] for s in starts.ravel()]).reshape(n_paths, n_blocks * block)[:, :horizon]
    return logh.loc[:origin].iloc[-1] + np.c_[np.zeros(n_paths), np.cumsum(steps, axis=1)]


METHODS = {"since-2017": lambda origin: min(pd.Timestamp(cfg()["future"]["growth_window_start"], tz="UTC"),
                                            origin - pd.Timedelta(days=730)),
           "last-3-years": lambda origin: origin - pd.Timedelta(days=1095)}


def backtest(logh: pd.Series, seed: int, method: str) -> dict:
    c = cfg()["future"]
    rows = []
    for o in c["backtest_origins"]:
        origin = logh.index[logh.index.get_indexer([pd.Timestamp(o, tz="UTC")], method="nearest")[0]]
        start = METHODS[method](origin)
        paths = simulate(logh, origin, str(start.date()), c["backtest_horizon_days"], 2000, seed)
        # simple comparators: persistence (no growth) and trailing 1-year trend extrapolation
        trend = (logh.loc[:origin].iloc[-1] - logh.loc[:origin - pd.Timedelta(days=365)].iloc[-1]) / 365
        for h in (90, 180, 360, 540):
            t = origin + pd.Timedelta(days=h)
            if t > logh.index[-1]:
                continue
            real = float(logh.loc[:t].iloc[-1])
            q10, q50, q90 = np.percentile(paths[:, h], [10, 50, 90])
            rows.append({"origin": str(origin.date()), "horizon_days": h, "realised_log": real,
                         "p10": float(q10), "p50": float(q50), "p90": float(q90),
                         "inside_80pct_band": bool(q10 <= real <= q90),
                         "median_error_pct": float(np.exp(q50 - real) - 1) * 100,
                         "persistence_error_pct": float(np.exp(logh.loc[:origin].iloc[-1] - real) - 1) * 100,
                         "trend_error_pct": float(np.exp(logh.loc[:origin].iloc[-1] + trend * h - real) - 1) * 100})
    df = pd.DataFrame(rows)
    summ = {"cases": len(df), "coverage_80pct_band": float(df["inside_80pct_band"].mean()),
            "mae_pct": {k: float(df[f"{k}_error_pct"].abs().mean()) for k in ("median", "persistence", "trend")}}
    return {"method": method, "rows": rows, "summary": summ}


def run() -> dict:
    c = cfg()
    fc = c["future"]
    seed = c["project"]["random_seed"]
    logh = series()
    origin = logh.index[-1]
    # Declared rule: the resampling window with the lower backtest mean |error| of the median path drives the
    # main scenario; the other window is kept as a sensitivity line.
    bts = {m: backtest(logh, seed, m) for m in METHODS}
    main = min(bts, key=lambda m: bts[m]["summary"]["mae_pct"]["median"])
    other = next(m for m in METHODS if m != main)
    paths = simulate(logh, origin, str(METHODS[main](origin).date()), fc["horizon_days"], fc["n_paths"], seed)
    recent = simulate(logh, origin, str(METHODS[other](origin).date()), fc["horizon_days"], fc["n_paths"], seed + 1)
    days = pd.date_range(origin, periods=fc["horizon_days"] + 1, freq="D")
    d = pd.read_parquet(PROCESSED / "days.parquet")
    d = d[d.index <= origin]
    height0 = int(d["height_last"].dropna().iloc[-1])
    last30 = d.iloc[-30:]
    price0 = float(last30["price_usd"].mean())
    fee0 = float(last30["fee_share"].mean())
    # block timing: blocks/day ~ 144 * H(t) / H(t - 7d) (difficulty retargets with roughly a one-week lag)
    lag = np.c_[np.repeat(paths[:, :1], 7, axis=1), paths[:, :-7]][:, : paths.shape[1]]
    bpd = 144 * np.exp(paths - lag)
    heights = height0 + np.cumsum(bpd, axis=1)
    hidx = (heights >= fc["halving_height"]).argmax(axis=1)
    halving_dates = days[hidx]
    subsidy = np.where(heights < fc["halving_height"], fc["subsidy_now_btc"], fc["subsidy_now_btc"] / 2)
    H = np.exp(paths)
    out = {"origin": str(origin.date()), "height_at_origin": height0, "price_usd_last30": price0,
           "fee_share_last30": fee0, "n_paths": fc["n_paths"],
           "growth_resampling": f"30-day blocks of daily log-growth, window '{main}' (lower backtest error than "
                                f"'{other}', which is shown as a sensitivity line)",
           "main_method": main, "sensitivity_method": other,
           "halving": {"height": fc["halving_height"],
                       "date_p10": str(pd.Series(halving_dates).quantile(0.1).date()),
                       "date_p50": str(pd.Series(halving_dates).quantile(0.5).date()),
                       "date_p90": str(pd.Series(halving_dates).quantile(0.9).date())}}
    monthly = np.arange(0, fc["horizon_days"] + 1, 30)
    out["hashrate_eh"] = [{"date": str(days[i].date()),
                           **{f"p{q}": float(np.percentile(H[:, i], q) / 1e6) for q in (10, 25, 50, 75, 90)},
                           "sensitivity_p50": float(np.percentile(np.exp(recent[:, i]), 50) / 1e6)} for i in monthly]
    # hash price under price x fee scenarios (USD per TH/s per day), median path
    scen = []
    for pm in (0.5, 1.0, 2.0):
        for fs in fc["fee_share_scenarios"]:
            rev_btc = subsidy * bpd / (1 - fs)        # fees make up a share fs of total block reward
            hp = rev_btc * price0 * pm / H
            scen.append({"price_multiplier": pm, "price_usd": price0 * pm, "fee_share": fs,
                         "hashprice_p50": [float(np.percentile(hp[:, i], 50)) for i in monthly],
                         "hashprice_p10": [float(np.percentile(hp[:, i], 10)) for i in monthly],
                         "hashprice_p90": [float(np.percentile(hp[:, i], 90)) for i in monthly]})
    out["months"] = [str(days[i].date()) for i in monthly]
    # arrays the web Future Lab needs to recompute hash price for any price / fee the user chooses
    out["client"] = {
        "h_ths": {f"p{q}": [float(np.percentile(H[:, i], q)) for i in monthly] for q in (10, 50, 90)},
        "subsidy_btc_per_day_p50": [float(np.percentile(subsidy[:, i] * bpd[:, i], 50)) for i in monthly],
        "post_halving_share": [float((heights[:, i] >= fc["halving_height"]).mean()) for i in monthly],
    }
    out["hashprice_scenarios"] = scen
    # devices at three checkpoints: break-even electricity price and solo odds (median path, price flat, fee=5%)
    checkpoints = {"2027-01-01": None, "one month after halving": None, "2029-01-01": None}
    p50_half = pd.Timestamp(out["halving"]["date_p50"], tz="UTC")
    for k in checkpoints:
        t = p50_half + pd.Timedelta(days=30) if k.startswith("one") else pd.Timestamp(k, tz="UTC")
        checkpoints[k] = int(min(max((t - origin).days, 0), fc["horizon_days"]))
    devs = []
    for dev in DEVICES_FUTURE:
        for k, i in checkpoints.items():
            Hi = H[:, i]
            rev_btc = subsidy[:, i] * bpd[:, i] / (1 - 0.05)
            hp = rev_btc * price0 / Hi
            be = hp * dev["ths"] * (1 - c["decision"]["pool_fee"]) / (dev["watts"] / 1000 * 24)
            p_solo = 1 - np.exp(-dev["ths"] / Hi * 144 * 365)
            devs.append({"device": dev["name"], "checkpoint": k, "date": str(days[i].date()),
                         "breakeven_usd_kwh_p10": float(np.percentile(be, 10)),
                         "breakeven_usd_kwh_p50": float(np.percentile(be, 50)),
                         "breakeven_usd_kwh_p90": float(np.percentile(be, 90)),
                         "solo_p_year_p50": float(np.percentile(p_solo, 50))})
    out["devices"] = devs
    out["backtest"] = bts[main]
    out["backtest_comparison"] = {m: b["summary"] for m, b in bts.items()}
    out["scope_statement"] = ("Scenario projections conditional on resampled historical growth, a fixed price "
                              "multiplier and a fixed fee share. They are not price forecasts and not investment "
                              "advice; the backtest shows the size of the error to expect.")
    write_json(ARTIFACTS / "future.json", out)
    print("halving p50:", out["halving"]["date_p50"], "| backtest coverage",
          round(out["backtest"]["summary"]["coverage_80pct_band"], 2), out["backtest"]["summary"]["mae_pct"])
    return out
