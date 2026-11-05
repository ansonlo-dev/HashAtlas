"""Stage 11 - static figures for the report and slides (matplotlib, one consistent palette).

Every figure is drawn from artifacts/ or data/processed/, so a rerun regenerates the same pictures.
"""
from __future__ import annotations

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy.cluster.hierarchy import dendrogram, linkage  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from .config import ARTIFACTS, FIGURES, INTERIM, MODELS, PROCESSED, cfg, read_json  # noqa: E402

INK, MUTED, GRID = "#0B1530", "#5B6478", "#E3E7EF"
BTC, VIOLET, CYAN, PINK, GREEN, BLUE, AMBER, RED = ("#F7931A", "#7C3AED", "#06B6D4", "#EC4899", "#10B981",
                                                    "#3B82F6", "#F59E0B", "#EF4444")
CYCLE = [BTC, VIOLET, CYAN, PINK, GREEN, BLUE, AMBER, RED, "#14B8A6", "#A855F7", "#64748B", "#84CC16"]
ERA_COL = {"CPU": "#94A3B8", "GPU": CYAN, "FPGA/early ASIC": GREEN, "ASIC": VIOLET, "Industrial ASIC": BTC}
HALVINGS = ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-20"]
NEON = LinearSegmentedColormap.from_list("neon", ["#FFFFFF", "#C4B5FD", VIOLET, "#4C1D95"])


def style():
    plt.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 200, "font.size": 9.5, "font.family": "DejaVu Sans",
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlecolor": INK, "axes.titleweight": "bold",
        "axes.titlesize": 11, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": MUTED,
        "legend.frameon": False, "axes.prop_cycle": matplotlib.cycler(color=CYCLE)})


def save(fig, name: str):
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def days():
    d = pd.read_parquet(PROCESSED / "days.parquet")
    return d[d.index <= pd.Timestamp(cfg()["sources"]["freeze_day"], tz="UTC")]


def era_shading(ax, d):
    eras = cfg()["eras"]
    ends = [pd.Timestamp(e["start"], tz="UTC") for e in eras[1:]] + [d.index.max()]
    for e, end in zip(eras, ends):
        ax.axvspan(pd.Timestamp(e["start"], tz="UTC"), end, color=ERA_COL[e["name"]], alpha=0.10, lw=0)
        ax.text(pd.Timestamp(e["start"], tz="UTC") + pd.Timedelta(days=20), 0.97, e["name"], transform=ax.get_xaxis_transform(),
                fontsize=7.5, color=ERA_COL[e["name"]], va="top", fontweight="bold")
    for h in HALVINGS:
        ax.axvline(pd.Timestamp(h, tz="UTC"), color=MUTED, ls=":", lw=0.9)


def fig_hashrate(d):
    fig, ax = plt.subplots(figsize=(9, 3.6))
    era_shading(ax, d)
    ax.semilogy(d.index, d["hashrate_ths"].rolling(7).mean() * 1e12, color=VIOLET, lw=1.6, label="Network hash rate (H/s, 7-day mean)")
    ax.set_ylabel("hashes per second (log)")
    ax2 = ax.twinx()
    ax2.semilogy(d.index, d["frontier_j_per_th"], color=BTC, lw=1.4, drawstyle="steps-post", label="Best hardware (J/TH)")
    ax2.set_ylabel("joules per terahash (log)", color=BTC)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_title("From CPUs to industrial ASICs: hash rate grew ~10^23-fold while energy per hash fell ~10^6-fold")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=8)
    save(fig, "f01_hashrate_eras")


def fig_who_mines():
    b = pd.read_parquet(INTERIM / "blocks.parquet", columns=["time", "miner", "is_solo"])
    b = b[b["time"] <= pd.Timestamp(cfg()["sources"]["freeze_day"], tz="UTC") + pd.Timedelta(days=1)]
    q = b["time"].dt.to_period("Q").dt.start_time
    grp = np.where(b["is_solo"], "Solo services", np.where(b["miner"] == "Unknown", "Unattributed (mostly solo / early)", "Pools"))
    top = b.loc[(b["miner"] != "Unknown") & ~b["is_solo"] & (b["time"] >= pd.Timestamp("2016-01-01", tz="UTC")), "miner"].value_counts().head(5).index
    grp = np.where(np.isin(b["miner"], top), b["miner"], grp)
    t = pd.crosstab(q, grp, normalize="index")
    order = ["Unattributed (mostly solo / early)", "Solo services", "Pools", *top]
    t = t[[c for c in order if c in t]]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    cols = ["#CBD5E1", PINK, "#94A3B8", BTC, VIOLET, CYAN, GREEN, BLUE]
    ax.stackplot(t.index, t.T.to_numpy(), labels=t.columns, colors=cols[:len(t.columns)], alpha=0.95)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of blocks per quarter")
    ax.set_title("Who wins blocks: unattributed individual miners gave way to pools by 2013-2014")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5)
    save(fig, "f02_who_mines")


def fig_solo(d):
    b = pd.read_parquet(INTERIM / "blocks.parquet", columns=["time", "is_solo", "miner"])
    yr = b[b["is_solo"]].groupby(b["time"].dt.year).size()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.4), gridspec_kw={"width_ratios": [1.5, 1]})
    ax.semilogy(d.index, d["solo_p_year_bitaxe"].rolling(7).mean(), color=PINK, lw=1.6)
    for p, lab in ((1e-2, "1 in 100"), (1e-4, "1 in 10,000")):
        ax.axhline(p, color=MUTED, ls="--", lw=0.8)
        ax.text(d.index[40], p * 1.3, lab, fontsize=7.5, color=MUTED)
    ax.set_ylim(1e-6, 1.05)
    ax.set_title("Chance a 1.2 TH/s home miner wins >= 1 block in a year")
    ax.set_ylabel("probability (log)")
    ax2.bar(yr.index, yr.to_numpy(), color=VIOLET)
    ax2.set_title("Blocks won by solo-mining services")
    ax2.set_xlabel("year")
    save(fig, "f03_solo_odds")


def fig_quality():
    q = read_json(ARTIFACTS / "quality_report.json")
    u = pd.Series(q["unknown_miner_share_by_year"]).astype(float)
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.1))
    ax[0].bar(u.index.astype(str), u.to_numpy(), color=[CYAN if int(y) >= 2019 else "#94A3B8" for y in u.index])
    ax[0].set_title("Unattributed (Unknown) share of blocks by year")
    ax[0].tick_params(axis="x", rotation=90, labelsize=7)
    src = pd.Series(q["labels"]["by_source"])
    ax[1].barh(src.index, src.to_numpy(), color=[VIOLET, BTC, CYAN, PINK][:len(src)])
    ax[1].set_title("Label source of every block")
    ax[1].set_xscale("log")
    save(fig, "f04_label_quality")


def fig_selection():
    fs = read_json(ARTIFACTS / "feature_selection.json")
    mi = pd.Series(fs["mutual_information"]).sort_values(ascending=True).tail(30)
    sel = set(fs["selected"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 5.2), gridspec_kw={"width_ratios": [1.3, 1]})
    ax[0].barh(mi.index, mi.to_numpy(), color=[VIOLET if f in sel else "#CBD5E1" for f in mi.index])
    ax[0].axvline(fs["mi_noise_cutoff"], color=RED, ls="--", lw=1)
    ax[0].text(fs["mi_noise_cutoff"], 0, " noise-probe cutoff", color=RED, fontsize=7.5)
    ax[0].set_title("Mutual information with the miner class (top 30)")
    ax[0].tick_params(axis="y", labelsize=7)
    ab = fs["group_ablation"]["groups"]
    g = pd.Series({k: v["change"] for k, v in ab.items()}).sort_values()
    ax[1].barh(g.index, g.to_numpy(), color=[RED if v < 0 else GREEN for v in g.to_numpy()])
    ax[1].axvline(0, color=INK, lw=0.8)
    ax[1].set_title("Group ablation: change in CV macro-F1\nwhen the group is removed")
    save(fig, "f05_feature_selection")


def fig_complexity():
    ex = read_json(ARTIFACTS / "explanations.json")
    cx = pd.DataFrame(ex["complexity"]["by_depth"])
    lab = cx["max_depth"].astype(str).replace("99", "none")
    fig, ax = plt.subplots(figsize=(5.2, 3.3))
    ax.plot(lab, cx["train"], marker="o", color=BTC, label="training folds")
    ax.plot(lab, cx["cv"], marker="o", color=VIOLET, label="held-out folds (CV)")
    ax.set_xlabel("max_depth")
    ax.set_ylabel("macro-F1")
    ax.set_title("Tree complexity: training keeps rising, CV peaks")
    ax.legend()
    save(fig, "f06_tree_complexity")


def fig_models():
    t = read_json(ARTIFACTS / "test_metrics.json")
    s = read_json(ARTIFACTS / "model_search.json")["families"]
    names = ["tree", "knn", "svm_linear", "svm_rbf", "decision_stump", "stratified_random", "majority"]
    lab = ["Decision tree", "KNN", "Linear SVM", "RBF SVM", "Stump (depth 1)", "Random (stratified)", "Majority"]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    cv = [s[n].get("cv_macro_f1_mean", np.nan) for n in names]
    val = [s[n]["validation"]["macro_f1"] for n in names]
    te = [t["families"][n]["macro_f1"] for n in names]
    ax.bar(x - 0.27, cv, 0.27, label="CV (train 2019-23)", color="#C4B5FD")
    ax.bar(x, val, 0.27, label="validation (2024-25Q1)", color=VIOLET)
    ax.bar(x + 0.27, te, 0.27, label="sealed test (2025Q2-26)", color=BTC)
    ci = t["bootstrap"]["macro_f1_95ci"]
    k = names.index(t["operational_family"])
    ax.errorbar(k + 0.27, te[k], yerr=[[te[k] - ci[0]], [ci[1] - te[k]]], color=INK, capsize=4, lw=1.2)
    ax.set_xticks(x, lab, fontsize=8)
    ax.set_ylabel("macro-F1")
    ax.set_title("Model comparison on identical blocks (higher is better)")
    ax.legend(fontsize=8)
    save(fig, "f07_model_comparison")


def fig_confusion():
    t = read_json(ARTIFACTS / "test_metrics.json")
    labels = t["confusion"]["labels"]
    m = np.array(t["confusion"]["matrix"], dtype=float)
    r = m / m.sum(axis=1, keepdims=True).clip(min=1)
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    im = ax.imshow(r, cmap=NEON, vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=55, ha="right", fontsize=7.5)
    ax.set_yticks(range(len(labels)), labels, fontsize=7.5)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if r[i, j] >= 0.05:
                ax.text(j, i, f"{r[i, j]:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if r[i, j] > 0.5 else INK)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true (row-normalised = recall)")
    ax.set_title("Who looks like whom: test-period confusion matrix")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.04)
    save(fig, "f08_confusion")


def fig_curves():
    t = read_json(ARTIFACTS / "test_metrics.json")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    names = {"tree": "Decision tree", "knn": "KNN", "svm_linear": "Linear SVM", "svm_rbf": "RBF SVM"}
    for (k, lab), col in zip(names.items(), [VIOLET, CYAN, GREEN, BTC]):
        cv = t["curves"][k]
        f = t["families"][k]
        ax[0].plot(*np.array(cv["roc"]).T, color=col, label=f"{lab} (AUC {f['solo_roc_auc']:.2f})")
        ax[1].plot(*np.array(cv["pr"]).T, color=col, label=f"{lab} (AP {f['solo_average_precision']:.2f})")
    ax[0].plot([0, 1], [0, 1], color=MUTED, ls=":")
    ax[0].set(xlabel="false positive rate", ylabel="true positive rate", title="Solo vs rest: ROC")
    base = t["families"]["tree"]["solo_base_rate"]
    ax[1].axhline(base, color=MUTED, ls=":")
    ax[1].set(xlabel="recall", ylabel="precision", title=f"Solo vs rest: precision-recall (base rate {base:.4f})")
    for a in ax:
        a.legend(fontsize=7.5)
    save(fig, "f09_solo_roc_pr")


def fig_importance():
    ex = read_json(ARTIFACTS / "explanations.json")
    pi = pd.DataFrame(ex["permutation_importance"]).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    ax.barh(pi["feature"], pi["mean"], xerr=pi["sd"], color=CYAN, ecolor=MUTED)
    ax.set_title("Permutation importance on the test period\n(drop in macro-F1 when the feature is shuffled)")
    save(fig, "f10_permutation_importance")


def fig_tree():
    from sklearn.tree import plot_tree
    sel = read_json(ARTIFACTS / "model_selection.json")
    tree = joblib.load(MODELS / "final_tree.joblib")
    fig, ax = plt.subplots(figsize=(13, 5.6))
    plot_tree(tree, max_depth=2, feature_names=sel["features"], class_names=list(tree.classes_), filled=False,
              impurity=True, proportion=True, fontsize=7, ax=ax, precision=2)
    ax.set_title("Top three levels of the fitted decision tree (proportions per node)")
    save(fig, "f11_tree_top")


def fig_clusters():
    cl = read_json(ARTIFACTS / "clusters.json")
    el = pd.DataFrame(cl["elbow"])
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    ax[0].plot(el["k"], el["sse"], marker="o", color=VIOLET)
    ax[0].set(xlabel="K", ylabel="SSE", title="K-means elbow (weekly rows)")
    ax0 = ax[0].twinx()
    ax0.plot(el["k"], el["silhouette"], marker="s", color=BTC)
    ax0.set_ylabel("silhouette", color=BTC)
    ax0.grid(False)
    ax0.axvline(cl["k_selected"], color=PINK, ls="--")
    kd = cl["k_distance_curve"]
    ax[1].plot(np.linspace(0, 1, len(kd)), kd, color=CYAN)
    ax[1].axhline(cl["dbscan_selected"]["eps"], color=PINK, ls="--", label=f"eps = {cl['dbscan_selected']['eps']:.2f}")
    ax[1].set(xlabel="weeks (sorted)", ylabel=f"distance to {cl['dbscan_selected']['min_samples']}-th neighbour",
              title="DBSCAN k-distance curve")
    ax[1].legend()
    save(fig, "f12_kmeans_dbscan")
    w = pd.read_parquet(PROCESSED / "weeks.parquet")
    tcol = w.columns[0]
    fig, ax = plt.subplots(figsize=(9, 2.9))
    rows = [("hardware era", w["era"].map({e: i for i, e in enumerate(ERA_COL)}), list(ERA_COL.values())),
            ("K-means", w["kmeans"], CYCLE), ("Ward", w["hier_ward"] - 1, CYCLE), ("DBSCAN", w["dbscan"], CYCLE)]
    for i, (name, lab, cols) in enumerate(rows):
        c = ["#111827" if v < 0 else cols[int(v) % len(cols)] for v in lab]
        ax.scatter(w[tcol], np.full(len(w), i), c=c, marker="|", s=260, lw=2.2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title(f"Unsupervised eras vs hardware eras (ARI K-means = {cl['ari_vs_hardware_eras']['kmeans']:.2f}; black = DBSCAN noise)")
    ax.grid(False)
    save(fig, "f13_eras_timeline")
    pf = cl["pool_families"]
    prof = pd.DataFrame(pf["profiles"]).set_index("group")
    Z = StandardScaler().fit_transform(prof[pf["profile_features"]])
    L = linkage(Z, method="average")
    fig, ax = plt.subplots(figsize=(9, 4.4))
    dendrogram(L, labels=prof.index.tolist(), leaf_rotation=60, leaf_font_size=7.5, ax=ax,
               color_threshold=pf["family_cut_height"], above_threshold_color="#94A3B8")
    ax.axhline(pf["family_cut_height"], color=PINK, ls="--", lw=1)
    ax.set_title("Pool families: average-linkage dendrogram of block-building fingerprints (2024-2026)")
    ax.set_ylabel("Euclidean distance (standardised profiles)")
    ax.grid(False)
    save(fig, "f14_pool_dendrogram")


def fig_rules():
    r = read_json(ARTIFACTS / "rules.json")
    df = pd.DataFrame(r["rules"])
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    if len(df):
        sc = ax.scatter(df["support"], df["confidence"], c=df["lift"], s=18 + 10 * df["antecedent"].map(len),
                        cmap="plasma", alpha=0.85, edgecolor="white", lw=0.4)
        fig.colorbar(sc, ax=ax, label="lift")
    ax.set(xlabel="support", ylabel="confidence", title=f"{r['n_rules']} rules 'block properties -> miner'")
    save(fig, "f15_rules")


def fig_advisor():
    dc = read_json(ARTIFACTS / "decisions.json")
    a = pd.DataFrame(dc["advisor"])
    s = a[(a["device"] == "Antminer S21") & (a["tariff"] == "business")].sort_values("price_usd_kwh")
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(s["country"], s["price_usd_kwh"], color=[CYAN if x else "#CBD5E1" for x in s["asia"]])
    be = float(s["breakeven_usd_kwh"].iloc[0])
    ax.axhline(be, color=BTC, lw=2)
    ax.text(0, be * 1.05, f"S21 break-even {be:.3f} USD/kWh", color=BTC, fontsize=8, fontweight="bold")
    ax.tick_params(axis="x", rotation=65, labelsize=7.5)
    ax.set_ylabel("business electricity (USD/kWh)")
    ax.set_title("Where does an Antminer S21 pay for its electricity? (cyan = Asia)")
    save(fig, "f16_advisor")


def fig_future():
    fu = read_json(ARTIFACTS / "future.json")
    d = days()
    h = pd.DataFrame(fu["hashrate_eh"])
    h["date"] = pd.to_datetime(h["date"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    hist = d.loc["2021":, "hashrate_ths"].rolling(7).mean() / 1e6
    ax[0].plot(hist.index.tz_localize(None), hist, color=INK, lw=1.2, label="observed")
    ax[0].fill_between(h["date"], h["p10"], h["p90"], color=VIOLET, alpha=0.18, label="10-90% of paths")
    ax[0].fill_between(h["date"], h["p25"], h["p75"], color=VIOLET, alpha=0.30)
    ax[0].plot(h["date"], h["p50"], color=VIOLET, lw=1.6, label="median path")
    ax[0].plot(h["date"], h["recent_p50"], color=PINK, ls="--", lw=1.2, label="median (last-3-years growth)")
    hv = pd.Timestamp(fu["halving"]["date_p50"])
    ax[0].axvline(hv, color=BTC, ls=":")
    ax[0].text(hv, ax[0].get_ylim()[1] * 0.95, " 2028 halving (median)", color=BTC, fontsize=7.5, va="top")
    ax[0].set(ylabel="EH/s", title="Hash-rate scenarios (block bootstrap)")
    ax[0].legend(fontsize=7)
    bt = pd.DataFrame(fu["backtest"]["rows"])
    for i, (o, g) in enumerate(bt.groupby("origin")):
        ax[1].errorbar(g["horizon_days"] + i * 8, np.exp(g["p50"] - g["realised_log"]) * 100 - 100,
                       yerr=[np.exp(g["p50"] - g["realised_log"]) * 100 - np.exp(g["p10"] - g["realised_log"]) * 100,
                             np.exp(g["p90"] - g["realised_log"]) * 100 - np.exp(g["p50"] - g["realised_log"]) * 100],
                       fmt="o", capsize=3, color=CYCLE[i], label=f"origin {o}")
    ax[1].axhline(0, color=INK, lw=0.8)
    ax[1].set(xlabel="horizon (days)", ylabel="projection error vs realised (%)",
              title=f"Backtest: 80% band covered {fu['backtest']['summary']['coverage_80pct_band']:.0%} of cases")
    ax[1].legend(fontsize=7)
    save(fig, "f17_future")


def fig_concentration(d):
    fig, ax = plt.subplots(figsize=(9, 3))
    s = d.loc["2013":]
    ax.plot(s.index, s["nakamoto"].rolling(30).mean(), color=VIOLET, label="Nakamoto coefficient (30-day mean)")
    ax.set_ylabel("entities for > 50% of blocks")
    ax2 = ax.twinx()
    ax2.plot(s.index, s["top1_share"].rolling(30).mean(), color=BTC, label="largest pool share")
    ax2.set_ylabel("largest pool share", color=BTC)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_title("Concentration of block production by labelled pool name")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    save(fig, "f18_concentration")


def run() -> None:
    style()
    FIGURES.mkdir(parents=True, exist_ok=True)
    d = days()
    for f in (lambda: fig_hashrate(d), fig_who_mines, lambda: fig_solo(d), fig_quality, fig_selection,
              fig_complexity, fig_models, fig_confusion, fig_curves, fig_importance, fig_tree, fig_clusters,
              fig_rules, fig_advisor, fig_future, lambda: fig_concentration(d)):
        f()
    print("figures:", len(list(FIGURES.glob("*.png"))))
