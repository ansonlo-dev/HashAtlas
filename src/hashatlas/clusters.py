"""Stage 7 - clustering (section 9).

A. Mining eras from the data itself: one row per calendar week, 2009-2026 (~930 weeks), describing how blocks
   were produced (hash-rate level and growth, empty blocks, block fullness, fee share, unattributed share,
   pool concentration). K-means (elbow/SSE + silhouette, 25 initialisations, a hand-checked assignment/update
   iteration), four hierarchical linkages (cophenetic correlation) and DBSCAN (k-distance eps, MinPts grid)
   run on the *same* standardised weekly rows. Hardware eras are used only afterwards, to check (ARI) whether
   the unsupervised groups rediscover CPU -> GPU -> ASIC -> industrial ASIC.
B. Pool families: one profile per pool (2024-2026, >= 300 blocks) built from fingerprint features; hierarchical
   clustering shows which pools build blocks the same way (shared templates / common operators).
C. Anomalous blocks: DBSCAN noise on a recent block sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from .acquire import SOLO_POOLS
from .config import ARTIFACTS, INTERIM, PROCESSED, cfg, read_json, write_json

WEEK_FEATURES = ["log_hashrate", "hashrate_growth_30d", "empty_share", "log_tx_per_block", "fullness", "fee_share",
                 "unknown_share", "hhi", "log_hashprice_btc"]


def weekly() -> pd.DataFrame:
    d = pd.read_parquet(PROCESSED / "days.parquet")
    freeze = pd.Timestamp(cfg()["sources"]["freeze_day"], tz="UTC")
    d = d[d.index <= freeze]
    w = d.resample("W-MON", label="left", closed="left").agg({
        "log_hashrate": "mean", "hashrate_growth_30d": "mean", "empty_share": "mean", "tx_per_block": "mean",
        "fullness": "mean", "fee_share": "mean", "unknown_share": "mean", "hhi": "mean",
        "hashprice_btc_th_day": "mean", "era": "last", "solo_blocks": "sum", "blocks": "sum"})
    w["log_tx_per_block"] = np.log10(w["tx_per_block"])
    w["log_hashprice_btc"] = np.log10(w["hashprice_btc_th_day"])
    w = w.dropna(subset=WEEK_FEATURES)
    return w


def kmeans_trace(Z: np.ndarray, k: int, seed: int) -> dict:
    """One assignment + update step by hand from fixed initial centroids, compared with scikit-learn."""
    rs = np.random.RandomState(seed)
    init = Z[rs.choice(len(Z), k, replace=False)]
    d2 = ((Z[:, None, :] - init[None, :, :]) ** 2).sum(axis=2)
    assign = d2.argmin(axis=1)
    sse0 = float(d2[np.arange(len(Z)), assign].sum())
    new = np.vstack([Z[assign == j].mean(axis=0) if (assign == j).any() else init[j] for j in range(k)])
    d2b = ((Z[:, None, :] - new[None, :, :]) ** 2).sum(axis=2)
    sse1 = float(d2b[np.arange(len(Z)), d2b.argmin(axis=1)].sum())
    km = KMeans(n_clusters=k, init=init, n_init=1, max_iter=1, random_state=seed).fit(Z)
    return {"k": k, "sse_initial_assignment": sse0, "sse_after_update": sse1,
            "sse_decreased": sse1 <= sse0 + 1e-9,
            "sizes_after_first_assignment": np.bincount(assign, minlength=k).tolist(),
            "max_abs_diff_vs_sklearn_centroids": float(np.abs(km.cluster_centers_ - new).max()),
            "note": "SSE = sum of squared Euclidean distances to the assigned centroid (lecture definition)"}


def eras(seed: int) -> tuple[dict, pd.DataFrame]:
    c = cfg()["clustering"]
    w = weekly()
    Z = StandardScaler().fit_transform(w[WEEK_FEATURES])
    k_lo, k_hi = c["day_k_range"]
    elbow = []
    for k in range(k_lo, k_hi + 1):
        km = KMeans(n_clusters=k, n_init=c["n_init"], random_state=seed).fit(Z)
        elbow.append({"k": k, "sse": float(km.inertia_), "silhouette": float(silhouette_score(Z, km.labels_))})
    # choose K: largest silhouette among K >= 3 (K=2 trivially splits "early" vs "late")
    best = max([e for e in elbow if e["k"] >= 3], key=lambda e: e["silhouette"])
    k = best["k"]
    km = KMeans(n_clusters=k, n_init=c["n_init"], random_state=seed).fit(Z)
    # stability across seeds
    stab = [adjusted_rand_score(km.labels_, KMeans(n_clusters=k, n_init=1, random_state=s).fit(Z).labels_)
            for s in range(10)]
    # relabel clusters in chronological order of their median week
    order = pd.Series(np.arange(len(w)), index=km.labels_).groupby(level=0).median().sort_values().index
    remap = {old: new for new, old in enumerate(order)}
    w["kmeans"] = [remap[x] for x in km.labels_]
    cent = pd.DataFrame(StandardScaler().fit(w[WEEK_FEATURES]).inverse_transform(km.cluster_centers_),
                        columns=WEEK_FEATURES).rename(index=remap).sort_index()
    era_codes = w["era"].astype("category").cat.codes
    res = {"k_selected": k, "rule": "max silhouette for K >= 3", "elbow": elbow,
           "seed_stability_ari_mean": float(np.mean(stab)), "ari_vs_hardware_eras": {},
           "kmeans_trace": kmeans_trace(Z, k, seed), "features": WEEK_FEATURES, "weeks": len(w)}
    res["ari_vs_hardware_eras"]["kmeans"] = float(adjusted_rand_score(era_codes, w["kmeans"]))
    prof = []
    for j in range(k):
        g = w[w["kmeans"] == j]
        prof.append({"cluster": j, "weeks": len(g), "first_week": str(g.index.min().date()),
                     "last_week": str(g.index.max().date()),
                     "contiguous_runs": int((w["kmeans"].ne(w["kmeans"].shift()) & (w["kmeans"] == j)).sum()),
                     "dominant_hardware_era": g["era"].mode().iloc[0],
                     "centroid": cent.loc[j].round(4).to_dict()})
    res["profiles"] = prof
    res["contingency_vs_hardware_era"] = pd.crosstab(w["kmeans"], w["era"]).to_dict()
    # hierarchical: all four linkages on the same rows
    hier = {}
    dist = pdist(Z)
    for meth in ("single", "complete", "average", "ward"):
        L = linkage(Z, method=meth)
        lab = fcluster(L, k, criterion="maxclust")
        coph = float(cophenet(L, dist)[0])
        sizes = np.bincount(lab)[1:]
        hier[meth] = {"cophenetic_correlation": coph, "cluster_sizes": sorted(sizes.tolist(), reverse=True),
                      "ari_vs_kmeans": float(adjusted_rand_score(w["kmeans"], lab)),
                      "ari_vs_hardware_eras": float(adjusted_rand_score(era_codes, lab)),
                      "last_merge_heights": [float(x) for x in L[-6:, 2]]}
        w[f"hier_{meth}"] = lab
    res["hierarchical"] = hier
    Lw = linkage(Z, method="ward")
    dn = dendrogram(Lw, truncate_mode="lastp", p=24, no_plot=True)
    res["ward_dendrogram_truncated"] = {"icoord": dn["icoord"], "dcoord": dn["dcoord"], "ivl": dn["ivl"]}
    # DBSCAN on the same rows: eps from the k-distance curve quantiles, MinPts grid (MinPts counts the point itself)
    dbs = []
    for mp in c["dbscan_min_samples"]:
        nn = NearestNeighbors(n_neighbors=mp).fit(Z)
        kd = np.sort(nn.kneighbors(Z)[0][:, -1])
        for q in c["dbscan_eps_quantiles"]:
            eps = float(np.quantile(kd, q))
            lab = DBSCAN(eps=eps, min_samples=mp).fit(Z).labels_
            core = DBSCAN(eps=eps, min_samples=mp).fit(Z).core_sample_indices_
            n_cl = len(set(lab)) - (1 if -1 in lab else 0)
            dbs.append({"min_samples": mp, "eps_quantile": q, "eps": eps, "clusters": n_cl,
                        "noise_share": float((lab == -1).mean()), "core_points": len(core),
                        "ari_vs_hardware_eras": float(adjusted_rand_score(era_codes, lab))})
    res["dbscan"] = dbs
    pick = max(dbs, key=lambda r: (r["clusters"] >= 2, -abs(r["noise_share"] - 0.05)))
    lab = DBSCAN(eps=pick["eps"], min_samples=pick["min_samples"]).fit(Z).labels_
    w["dbscan"] = lab
    res["dbscan_selected"] = pick
    res["dbscan_noise_weeks"] = [str(x.date()) for x in w.index[lab == -1]][:60]
    nn = NearestNeighbors(n_neighbors=pick["min_samples"]).fit(Z)
    res["k_distance_curve"] = np.sort(nn.kneighbors(Z)[0][:, -1])[::max(1, len(Z) // 200)].round(4).tolist()
    # PCA-free 2-D view for plotting: two most interpretable axes
    return res, w


POOL_PROFILE = ["ver_rolled", "ver_roll_popcount", "ver_bip9", "ver_signal_bits", "is_empty", "fullness",
                "witness_byte_share", "rel_fee_rate", "rel_tx_count", "rel_fullness", "ts_minus_median_s",
                "io_ratio", "avg_tx_vbytes"]


def pool_families(seed: int) -> dict:
    c = cfg()["clustering"]
    f = pd.read_parquet(PROCESSED / "block_features.parquet")
    a, b = (pd.Timestamp(x, tz="UTC") for x in c["pool_window"])
    f = f[(f["time"] >= a) & (f["time"] < b) & (f["miner"] != "Unknown")]
    f["group"] = f["miner"].where(~f["miner"].isin(SOLO_POOLS), "Solo (all services)")
    counts = f["group"].value_counts()
    keep = counts[counts >= c["min_pool_blocks"]].index.tolist()
    if "Solo (all services)" not in keep and "Solo (all services)" in counts:
        keep.append("Solo (all services)")   # kept despite its size, flagged as thin
    f = f[f["group"].isin(keep)]
    bits = [f"ver_b{i}" for i in range(13, 29)]
    prof = f.groupby("group")[POOL_PROFILE + bits].mean()
    prof["ts_minus_median_s"] = f.groupby("group")["ts_minus_median_s"].median()
    Z = StandardScaler().fit_transform(prof)
    out = {"pools": prof.index.tolist(), "blocks": counts[prof.index].astype(int).to_dict(),
           "profile_features": POOL_PROFILE + bits, "window": c["pool_window"], "linkages": {}}
    dist = pdist(Z)
    for meth in ("single", "complete", "average", "ward"):
        L = linkage(Z, method=meth)
        out["linkages"][meth] = {"cophenetic_correlation": float(cophenet(L, dist)[0])}
    L = linkage(Z, method="average")
    dn = dendrogram(L, labels=prof.index.tolist(), no_plot=True)
    out["average_dendrogram"] = {"icoord": dn["icoord"], "dcoord": dn["dcoord"], "ivl": dn["ivl"]}
    # family cut: distance below the 35th percentile of merge heights = "same way of building blocks"
    cut = float(np.quantile(L[:, 2], 0.35))
    fam = fcluster(L, cut, criterion="distance")
    fams = {}
    for p, k in zip(prof.index, fam):
        fams.setdefault(int(k), []).append(p)
    out["family_cut_height"] = cut
    out["families"] = sorted([v for v in fams.values()], key=lambda v: -sum(counts[x] for x in v))
    out["pairwise_closest"] = []
    D = pd.DataFrame(np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(axis=2)), index=prof.index,
                     columns=prof.index)
    for p in prof.index:
        q = D.loc[p].drop(p).idxmin()
        out["pairwise_closest"].append({"pool": p, "closest": q, "distance": float(D.loc[p, q])})
    out["profiles"] = prof.round(4).reset_index().to_dict(orient="records")
    return out


def anomalies(seed: int) -> dict:
    f = pd.read_parquet(PROCESSED / "block_features.parquet")
    f = f[f["time"] >= pd.Timestamp("2025-04-01", tz="UTC")]
    f = f[f["time"] < pd.Timestamp(cfg()["classification"]["test"][1], tz="UTC")]
    samp = f.sample(min(len(f), cfg()["clustering"]["reference_rows"] * 4), random_state=seed)
    cols = ["log_tx_count", "fullness", "witness_byte_share", "rel_fee_rate", "ts_minus_median_s",
            "interval_prev_s", "io_ratio", "avg_tx_vbytes"]
    Z = StandardScaler().fit_transform(samp[cols])
    mp = 10
    kd = np.sort(NearestNeighbors(n_neighbors=mp).fit(Z).kneighbors(Z)[0][:, -1])
    eps = float(np.quantile(kd, 0.97))
    lab = DBSCAN(eps=eps, min_samples=mp).fit(Z).labels_
    noise = samp[lab == -1]
    return {"rows": len(samp), "eps": eps, "min_samples": mp, "noise_share": float((lab == -1).mean()),
            "clusters": int(len(set(lab)) - (1 if -1 in lab else 0)),
            "noise_profile_vs_all": (noise[cols].median() - samp[cols].median()).round(3).to_dict(),
            "noise_empty_share": float(noise["is_empty"].mean()), "all_empty_share": float(samp["is_empty"].mean()),
            "noise_solo_share": float(noise["is_solo"].mean()), "all_solo_share": float(samp["is_solo"].mean()),
            "noise_miners": noise["miner"].value_counts().head(8).to_dict()}


def run() -> dict:
    seed = cfg()["project"]["random_seed"]
    res, w = eras(seed)
    res["pool_families"] = pool_families(seed)
    res["anomalies"] = anomalies(seed)
    write_json(ARTIFACTS / "clusters.json", res)
    w.reset_index().rename(columns={"index": "week"}).to_parquet(PROCESSED / "weeks.parquet", index=False)
    print("eras k =", res["k_selected"], "ARI vs hardware eras", round(res["ari_vs_hardware_eras"]["kmeans"], 3),
          "| families:", res["pool_families"]["families"][:4])
    return res
