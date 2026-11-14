"""Select fingerprints and tune model families without opening the sealed test.

Month-grouped CV uses 2019-2023 training data. The 2024-01 to 2025-03 validation
period selects the model family and Solo threshold. evaluate.py later applies
the frozen choices to 2025-04 to 2026-10. Unknown blocks are excluded from fitting."""
from __future__ import annotations

import time

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.dummy import DummyClassifier
from sklearn.feature_selection import mutual_info_classif
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, LinearSVC
from sklearn.tree import DecisionTreeClassifier

from .acquire import SOLO_POOLS
from .config import ARTIFACTS, MODELS, PROCESSED, cfg, ensure_dirs, write_json
from .features import BLOCK_FEATURES_BASE

MIN_CLASS_SHARE = 0.02   # a pool gets its own class if it mined >= 2% of training-period blocks

GROUPS = {
    "version bits": [f for f in BLOCK_FEATURES_BASE if f.startswith("ver_")],
    "nonce bits": [f for f in BLOCK_FEATURES_BASE if f.startswith("nonce_")],
    "timestamps": ["ts_minus_median_s", "interval_prev_s"],
    "body composition": ["log_tx_count", "is_empty", "fullness", "witness_tx_share", "witness_byte_share",
                         "io_ratio", "avg_tx_vbytes", "log_fee_total", "log_fee_per_kwu", "fee_share", "log_min_fee"],
    "day-relative policy": ["rel_fee_rate", "rel_min_fee", "rel_median_fee", "rel_tx_count", "rel_fullness"],
    "fee ladder (percentiles)": ["rel_fee_p10", "rel_fee_p25", "rel_fee_p75", "rel_fee_p90", "fee_spread"],
    "hour of day (control)": ["hour_sin", "hour_cos"],
}


def period(df: pd.DataFrame, span) -> pd.DataFrame:
    a, b = (pd.Timestamp(x, tz="UTC") for x in span)
    return df[(df["time"] >= a) & (df["time"] < b)]


def class_map(train: pd.DataFrame) -> dict:
    known = train[train["miner"] != "Unknown"]
    share = known["miner"].value_counts(normalize=True)
    big = [m for m, s in share.items() if s >= MIN_CLASS_SHARE and m not in SOLO_POOLS]
    return {"classes": sorted(big) + ["Other pools", "Solo"], "big_pools": sorted(big),
            "train_share": share.round(5).to_dict()}


def to_class(miner: pd.Series, cmap: dict) -> pd.Series:
    big = set(cmap["big_pools"])
    return miner.map(lambda m: "Solo" if m in SOLO_POOLS else (m if m in big else "Other pools"))


def load_sets():
    c = cfg()["classification"]
    df = pd.read_parquet(PROCESSED / "block_features.parquet")
    df["month"] = df["time"].dt.strftime("%Y-%m")
    sets = {k: period(df, c[k]) for k in ("train", "validation", "test", "new")}
    cmap = class_map(sets["train"])
    for k in sets:
        s = sets[k].copy()
        s["y"] = to_class(s["miner"], cmap)
        s.loc[s["miner"] == "Unknown", "y"] = "Unknown"
        sets[k] = s
    return sets, cmap


def sample_train(train: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Keep every Solo block; sample the rest in proportion within each month (representative sampling)."""
    lab = train[train["y"] != "Unknown"]
    solo = lab[lab["y"] == "Solo"]
    rest = lab[lab["y"] != "Solo"]
    frac = min(1.0, (n - len(solo)) / len(rest))
    rest = rest.groupby("month", group_keys=False).sample(frac=frac, random_state=seed)
    return pd.concat([rest, solo]).sort_values("time")


# Feature selection (training data only)
def select_features(tr: pd.DataFrame, seed: int) -> dict:
    X = tr[BLOCK_FEATURES_BASE].astype(float)
    y = tr["y"]
    log = {"candidates": len(BLOCK_FEATURES_BASE)}
    # (a) variance filter on [0, 1]-scaled values
    rng_ = (X.max() - X.min()).replace(0, 1)
    var = ((X - X.min()) / rng_).var()
    low_var = var[var < 1e-4].index.tolist()
    log["removed_low_variance"] = low_var
    keep = [f for f in BLOCK_FEATURES_BASE if f not in low_var]
    # (b) mutual information filter against a noise-probe baseline (random features with no relation to y)
    rs = np.random.RandomState(seed)
    probe = pd.DataFrame({f"probe_{i}": rs.permutation(X[keep[i % len(keep)]].to_numpy()) for i in range(10)},
                         index=X.index)
    mi = mutual_info_classif(pd.concat([X[keep], probe], axis=1), y, random_state=seed,
                             discrete_features=[X[f].nunique() <= 2 for f in keep] + [X[keep[i % len(keep)]].nunique() <= 2
                                                                                      for i in range(10)])
    mi = pd.Series(mi, index=keep + list(probe.columns))
    cutoff = float(mi[probe.columns].max())
    log["mi_noise_cutoff"] = cutoff
    log["mutual_information"] = mi[keep].sort_values(ascending=False).round(5).to_dict()
    weak = [f for f in keep if mi[f] <= cutoff]
    log["removed_mi_below_noise"] = weak
    keep = [f for f in keep if f not in weak]
    # (c) redundancy: |Spearman rho| > threshold -> drop the feature with lower MI
    rho = spearmanr(X[keep].to_numpy()).statistic
    rho = pd.DataFrame(np.atleast_2d(rho), index=keep, columns=keep)
    dropped, pairs = set(), []
    for i, a in enumerate(keep):
        for b in keep[i + 1:]:
            if a in dropped or b in dropped:
                continue
            if abs(rho.loc[a, b]) > 0.90:
                loser = a if mi[a] < mi[b] else b
                dropped.add(loser)
                pairs.append({"a": a, "b": b, "rho": round(float(rho.loc[a, b]), 3), "dropped": loser})
    log["removed_redundant"] = pairs
    keep = [f for f in keep if f not in dropped]
    # (d) wrapper: drop-one-group ablation with a fixed shallow tree, month-grouped CV, macro-F1
    groups = tr["month"]
    base_tree = DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, class_weight="balanced", random_state=seed)
    cv = GroupKFold(n_splits=5)
    full = cross_val_score(base_tree, X[keep], y, groups=groups, cv=cv, scoring="f1_macro", n_jobs=-1).mean()
    abl = {}
    for g, cols in GROUPS.items():
        rest = [f for f in keep if f not in cols]
        if len(rest) == len(keep):
            continue
        s = cross_val_score(base_tree, X[rest], y, groups=groups, cv=cv, scoring="f1_macro", n_jobs=-1).mean()
        abl[g] = {"macro_f1_without": round(float(s), 4), "change": round(float(s - full), 4),
                  "features_in_group": len([f for f in keep if f in cols])}
    log["group_ablation"] = {"macro_f1_all_selected": round(float(full), 4), "groups": abl}
    removed_groups = [g for g, a in abl.items() if a["change"] >= 0.0]
    for g in removed_groups:
        keep = [f for f in keep if f not in GROUPS[g]]
    log["removed_groups_no_gain"] = removed_groups
    log["selected"] = keep
    log["n_selected"] = len(keep)
    return log


# Model families
def families(seed: int) -> dict:
    c = cfg()["classification"]
    scaled = lambda est: Pipeline([("scale", StandardScaler()), ("model", est)])  # noqa: E731
    return {
        "tree": (DecisionTreeClassifier(random_state=seed),
                 {"criterion": c["tree"]["criterion"], "max_depth": c["tree"]["max_depth"],
                  "min_samples_leaf": c["tree"]["min_samples_leaf"], "class_weight": c["tree"]["class_weight"]}),
        "knn": (scaled(KNeighborsClassifier(algorithm="brute", n_jobs=1)),
                {"model__n_neighbors": c["knn"]["n_neighbors"], "model__weights": c["knn"]["weights"],
                 "model__metric": c["knn"]["metric"]}),
        "svm_linear": (scaled(LinearSVC(class_weight="balanced", dual=False, max_iter=5000, random_state=seed)),
                       {"model__C": c["svm_linear"]["C"]}),
        "svm_rbf": (scaled(SVC(kernel="rbf", class_weight="balanced", cache_size=2000, random_state=seed)),
                    {"model__C": c["svm_rbf"]["C"], "model__gamma": c["svm_rbf"]["gamma"]}),
    }


def macro_scores(y_true, y_pred) -> dict:
    """Macro-F1 over the classes that actually occur in y_true. Predicting a pool that no longer exists is still
    an error (a false negative for the true class), but an absent class does not add an artificial zero."""
    present = sorted(set(np.asarray(y_true)))
    return {"macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=present)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
            "accuracy": float(np.mean(np.asarray(y_true) == np.asarray(y_pred))),
            "solo_f1": float(f1_score(np.asarray(y_true) == "Solo", np.asarray(y_pred) == "Solo", zero_division=0))}


def template_families(tr: pd.DataFrame, feats: list[str]) -> dict:
    """Group the classes whose *training-period* fingerprint profiles are nearly identical (average linkage on
    standardised class means; cut at the 35th percentile of merge heights). Frozen before validation/testing and
    used to report family-level accuracy: two pools building blocks from the same template cannot be told apart."""
    prof = tr.groupby("y")[feats].mean()
    Z = ((prof - prof.mean()) / prof.std(ddof=0).replace(0, 1)).to_numpy()
    L = linkage(Z, method="average")
    cut = float(np.quantile(L[:, 2], 0.35))
    lab = fcluster(L, cut, criterion="distance")
    groups: dict[int, list[str]] = {}
    for cls, g in zip(prof.index, lab):
        groups.setdefault(int(g), []).append(cls)
    fam = {}
    for members in groups.values():
        name = members[0] if len(members) == 1 else "Family: " + " + ".join(sorted(members))
        for m in members:
            fam[m] = name
    return {"map": fam, "cut_height": cut, "groups": sorted(groups.values(), key=len, reverse=True),
            "merge_heights": L[:, 2].round(4).tolist()}


def topk_accuracy(model, X, y, k: int = 3) -> float | None:
    if hasattr(model, "predict_proba"):
        try:
            s = model.predict_proba(X)
        except AttributeError:
            s = model.decision_function(X)
    else:
        s = model.decision_function(X)
    if s.ndim != 2:
        return None
    top = np.asarray(model.classes_)[np.argsort(-s, axis=1)[:, :k]]
    return float(np.mean([t in row for t, row in zip(np.asarray(y), top)]))


def family_scores(y_true, y_pred, fam: dict) -> dict:
    yt = pd.Series(np.asarray(y_true)).map(lambda c: fam.get(c, c))
    yp = pd.Series(np.asarray(y_pred)).map(lambda c: fam.get(c, c))
    s = macro_scores(yt, yp)
    return {"family_macro_f1": s["macro_f1"], "family_accuracy": s["accuracy"]}


def run() -> dict:
    ensure_dirs()
    c = cfg()["classification"]
    seed = cfg()["project"]["random_seed"]
    sets, cmap = load_sets()
    write_json(ARTIFACTS / "class_map.json", cmap)
    tr = sample_train(sets["train"], c["pool_negative_sample"], seed)
    split_manifest = {k: {"rows": int(len(v)), "labelled": int((v["y"] != "Unknown").sum()),
                          "solo": int((v["y"] == "Solo").sum()), "unknown": int((v["y"] == "Unknown").sum()),
                          "first": str(v["time"].min()), "last": str(v["time"].max()),
                          "class_counts": v["y"].value_counts().to_dict()} for k, v in sets.items()}
    split_manifest["train_sample"] = {"rows": len(tr), "solo": int((tr["y"] == "Solo").sum()),
                                      "rule": "all Solo blocks + month-stratified proportional sample of the rest"}
    write_json(ARTIFACTS / "split_manifest.json", split_manifest)

    t0 = time.time()
    fs = select_features(tr, seed)
    fs["seconds"] = round(time.time() - t0, 1)
    write_json(ARTIFACTS / "feature_selection.json", fs)
    feats = fs["selected"]
    print(f"selected {len(feats)} features in {fs['seconds']}s", flush=True)

    X, y, groups = tr[feats].astype(float), tr["y"], tr["month"]
    va = sets["validation"][sets["validation"]["y"] != "Unknown"]
    Xv, yv = va[feats].astype(float), va["y"]
    cv = GroupKFold(n_splits=c["cv_folds"])
    results, fitted = {}, {}
    rs = np.random.RandomState(seed)
    for name, (est, grid) in families(seed).items():
        t0 = time.time()
        if name.startswith("svm"):
            n = min(len(tr), c["svm_max_train_rows"])
            idx = np.sort(np.r_[np.where(y == "Solo")[0],
                                rs.choice(np.where(y != "Solo")[0], n - int((y == "Solo").sum()), replace=False)])
            Xs, ys, gs = X.iloc[idx], y.iloc[idx], groups.iloc[idx]
        else:
            Xs, ys, gs = X, y, groups
        gsv = GridSearchCV(est, grid, scoring="f1_macro", cv=cv, n_jobs=-1, refit=True, return_train_score=True)
        gsv.fit(Xs, ys, groups=gs)
        pred_v = gsv.predict(Xv)
        cvres = pd.DataFrame(gsv.cv_results_)
        best = gsv.best_index_
        results[name] = {
            "best_params": gsv.best_params_, "train_rows": len(Xs),
            "cv_macro_f1_mean": float(cvres.loc[best, "mean_test_score"]),
            "cv_macro_f1_se": float(cvres.loc[best, "std_test_score"] / np.sqrt(c["cv_folds"])),
            "cv_train_macro_f1": float(cvres.loc[best, "mean_train_score"]),
            "validation": {**macro_scores(yv, pred_v), "top3_accuracy": topk_accuracy(gsv.best_estimator_, Xv, yv)},
            "search_seconds": round(time.time() - t0, 1), "configs": len(cvres),
            "grid": [{"params": p, "cv": float(m), "train": float(t)} for p, m, t in
                     zip(cvres["params"], cvres["mean_test_score"], cvres["mean_train_score"])],
        }
        fitted[name] = gsv.best_estimator_
        print(f"{name}: cv {results[name]['cv_macro_f1_mean']:.3f} val {results[name]['validation']['macro_f1']:.3f} "
              f"({results[name]['search_seconds']}s)", flush=True)

    fams = template_families(tr, feats)
    for name in results:
        results[name]["validation"].update(family_scores(yv, fitted[name].predict(Xv), fams["map"]))
    # Baselines
    for bname, est in (("majority", DummyClassifier(strategy="most_frequent")),
                       ("stratified_random", DummyClassifier(strategy="stratified", random_state=seed)),
                       ("decision_stump", DecisionTreeClassifier(max_depth=1, random_state=seed))):
        est.fit(X, y)
        pv = est.predict(Xv)
        results[bname] = {"validation": {**macro_scores(yv, pv), **family_scores(yv, pv, fams["map"])}, "baseline": True}
        fitted[bname] = est

    # Nested CV (outer 5 x inner 3, month groups) for the tree: an unbiased estimate of the *tuning procedure*
    t0 = time.time()
    est, grid = families(seed)["tree"]
    inner = GridSearchCV(est, grid, scoring="f1_macro", cv=GroupKFold(c["nested_inner_folds"]), n_jobs=-1)
    outer_scores = []
    for k, (a, b) in enumerate(GroupKFold(c["nested_outer_folds"]).split(X, y, groups)):
        inner.fit(X.iloc[a], y.iloc[a], groups=groups.iloc[a])
        outer_scores.append({"fold": k, "macro_f1": macro_scores(y.iloc[b], inner.predict(X.iloc[b]))["macro_f1"],
                             "chosen": inner.best_params_})
    nested = {"outer": outer_scores, "mean": float(np.mean([o["macro_f1"] for o in outer_scores])),
              "sd": float(np.std([o["macro_f1"] for o in outer_scores], ddof=1)), "seconds": round(time.time() - t0, 1)}

    # Model choice on the out-of-time validation period: best macro-F1; the tree wins ties within 0.01
    fam = ["tree", "knn", "svm_linear", "svm_rbf"]
    best = max(fam, key=lambda f: results[f]["validation"]["macro_f1"])
    chosen = "tree" if results["tree"]["validation"]["macro_f1"] >= results[best]["validation"]["macro_f1"] - 0.01 else best
    # Solo operating threshold on validation (tree probability of the Solo class): highest recall at precision >= p
    tree = fitted["tree"]
    solo_col = list(tree.classes_).index("Solo")
    ps = tree.predict_proba(Xv)[:, solo_col]
    is_solo = (yv == "Solo").to_numpy()
    best_t, best_r = 0.5, -1.0
    for t in np.unique(np.r_[ps, 0.5]):
        flag = ps >= t
        if flag.sum() == 0:
            continue
        prec, rec = is_solo[flag].mean(), flag[is_solo].mean() if is_solo.any() else 0.0
        if prec >= c["min_precision_for_threshold"] and rec > best_r:
            best_t, best_r = float(t), float(rec)
    selection = {
        "rule": "highest validation macro-F1; the decision tree is preferred if within 0.01 (interpretability)",
        "chosen_family": chosen, "best_by_score": best, "chosen_params": results[chosen]["best_params"],
        "features": feats, "classes": cmap["classes"], "template_families": fams,
        "solo_threshold": {"value": best_t, "validation_recall": best_r,
                           "rule": f"highest recall with precision >= {c['min_precision_for_threshold']} on validation"},
        "final_refit": "chosen configuration refitted on train-sample + validation before the sealed test",
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_json(ARTIFACTS / "model_search.json", {"families": results, "nested_cv_tree": nested})
    write_json(ARTIFACTS / "model_selection.json", selection)
    for k, m in fitted.items():
        joblib.dump(m, MODELS / f"{k}_train.joblib", compress=3)
    print("chosen:", chosen, "| solo threshold", best_t, flush=True)
    return selection
