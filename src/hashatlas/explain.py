"""Stage 6 - explanations that open the models up (sections 7-8).

* Decision tree: exported structure (for the web simulator), a hand-checked Gini split at the root with
  weighted impurity reduction, Gini-vs-entropy and depth complexity curves, root-to-leaf traces of real blocks.
* Permutation importance on the test period (which fingerprints actually carry information).
* KNN: the actual neighbours, distances and vote for a real test block.
* Linear SVM: the largest coefficients for the Solo class (after scaling).
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from .config import ARTIFACTS, MODELS, cfg, read_json, write_json
from .train import load_sets, sample_train


def gini(counts: np.ndarray) -> float:
    p = counts / counts.sum()
    return float(1 - (p ** 2).sum())


def entropy(counts: np.ndarray) -> float:
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log2(p)).sum())


def export_tree(tree, feats, classes, max_nodes: int = 4000) -> dict:
    t = tree.tree_
    nodes = []
    for i in range(min(t.node_count, max_nodes)):
        v = t.value[i][0]
        v = v / v.sum() if v.sum() else v
        leaf = t.children_left[i] == -1
        nodes.append({"id": i, "leaf": bool(leaf),
                      "feature": None if leaf else feats[t.feature[i]],
                      "threshold": None if leaf else float(t.threshold[i]),
                      "left": int(t.children_left[i]), "right": int(t.children_right[i]),
                      "samples": int(t.n_node_samples[i]), "impurity": float(t.impurity[i]),
                      "dist": [round(float(x), 4) for x in v],
                      "predict": classes[int(np.argmax(v))]})
    return {"classes": list(classes), "features": feats, "depth": int(tree.get_depth()),
            "leaves": int(tree.get_n_leaves()), "criterion": tree.criterion, "nodes": nodes}


def worked_split(tree, X: pd.DataFrame, y: pd.Series, feats) -> dict:
    """Recompute the root split by hand on the tree's own training rows (unweighted counts)."""
    t = tree.tree_
    f, thr = feats[t.feature[0]], float(t.threshold[0])
    classes = list(tree.classes_)
    cnt = lambda s: np.array([(s == k).sum() for k in classes], dtype=float)  # noqa: E731
    left = X[f] <= thr
    parent, cl, cr = cnt(y), cnt(y[left]), cnt(y[~left])
    nl, nr, n = cl.sum(), cr.sum(), parent.sum()
    g_p, g_l, g_r = gini(parent), gini(cl), gini(cr)
    e_p, e_l, e_r = entropy(parent), entropy(cl), entropy(cr)
    return {
        "feature": f, "threshold": thr, "n": int(n), "n_left": int(nl), "n_right": int(nr),
        "class_counts": {"parent": dict(zip(classes, parent.astype(int).tolist())),
                         "left": dict(zip(classes, cl.astype(int).tolist())),
                         "right": dict(zip(classes, cr.astype(int).tolist()))},
        "gini": {"parent": g_p, "left": g_l, "right": g_r,
                 "weighted_children": (nl * g_l + nr * g_r) / n, "reduction": g_p - (nl * g_l + nr * g_r) / n},
        "entropy": {"parent": e_p, "left": e_l, "right": e_r,
                    "information_gain": e_p - (nl * e_l + nr * e_r) / n},
        "note": "computed on unweighted training counts; the fitted tree may use class weights, so its stored "
                "impurity can differ from the unweighted value shown here",
        "sklearn_root_impurity": float(t.impurity[0]),
    }


def trace(tree, x: pd.Series, feats) -> list[dict]:
    t = tree.tree_
    i, path = 0, []
    while t.children_left[i] != -1:
        f, thr = feats[t.feature[i]], float(t.threshold[i])
        go_left = float(x[f]) <= thr
        path.append({"node": i, "feature": f, "threshold": thr, "value": float(x[f]),
                     "goes": "left (<=)" if go_left else "right (>)"})
        i = t.children_left[i] if go_left else t.children_right[i]
    v = t.value[i][0]
    v = v / v.sum()
    path.append({"leaf": i, "distribution": {k: round(float(p), 4) for k, p in zip(tree.classes_, v) if p > 0.005}})
    return path


def complexity(search: dict) -> dict:
    grid = pd.DataFrame([{**g["params"], "cv": g["cv"], "train": g["train"]} for g in search["tree"]["grid"]])
    grid["max_depth"] = grid["max_depth"].fillna(99).astype(int)
    by_depth = grid.groupby("max_depth")[["cv", "train"]].max().reset_index()
    by_crit = grid.groupby("criterion")["cv"].max().to_dict()
    return {"by_depth": by_depth.to_dict(orient="records"), "best_cv_by_criterion": by_crit,
            "note": "depth 99 = unlimited; values are the best over the other hyper-parameters at that depth"}


def run() -> dict:
    c = cfg()
    seed = c["project"]["random_seed"]
    sel = read_json(ARTIFACTS / "model_selection.json")
    search = read_json(ARTIFACTS / "model_search.json")["families"]
    feats = sel["features"]
    sets, cmap = load_sets()
    tr = sample_train(sets["train"], c["classification"]["pool_negative_sample"], seed)
    te = sets["test"][sets["test"]["y"] != "Unknown"].reset_index(drop=True)
    tree_tr = joblib.load(MODELS / "tree_train.joblib")
    tree = joblib.load(MODELS / "final_tree.joblib")
    out = {"tree_export": export_tree(tree, feats, list(tree.classes_)),
           "root_split_worked": worked_split(tree_tr, tr[feats].astype(float), tr["y"], feats),
           "complexity": complexity(search)}
    # Traces for real blocks: the most recent test Solo block and one block of the two largest classes
    examples = []
    for cls in ["Solo"] + [k for k in te["y"].value_counts().index if k != "Solo"][:2]:
        g = te[te["y"] == cls]
        if len(g):
            row = g.iloc[-1]
            examples.append({"height": int(row["id"]), "time": str(row["time"]), "true": cls, "miner": row["miner"],
                             "path": trace(tree, row[feats].astype(float), feats)})
    out["traces"] = examples
    # Permutation importance (test period, operational tree), on a stratified sample for cost
    samp = te.groupby("y", group_keys=False).apply(lambda g: g.sample(min(len(g), 3000), random_state=seed))
    pi = permutation_importance(tree, samp[feats].astype(float), samp["y"], scoring="f1_macro", n_repeats=5,
                                random_state=seed, n_jobs=-1)
    imp = pd.DataFrame({"feature": feats, "mean": pi.importances_mean, "sd": pi.importances_std})
    out["permutation_importance"] = imp.sort_values("mean", ascending=False).round(5).to_dict(orient="records")
    out["tree_impurity_importance"] = (pd.Series(tree.feature_importances_, index=feats)
                                       .sort_values(ascending=False).round(5).head(20).to_dict())
    # KNN neighbours for the latest test Solo block
    knn = joblib.load(MODELS / "final_knn.joblib")
    solo = te[te["y"] == "Solo"]
    if len(solo):
        q = solo.iloc[[-1]][feats].astype(float)
        scaler, model = knn.named_steps["scale"], knn.named_steps["model"]
        dist, idx = model.kneighbors(scaler.transform(q), n_neighbors=model.n_neighbors)
        lab = np.asarray(model._y)
        classes = model.classes_
        votes = pd.Series([classes[lab[i]] for i in idx[0]]).value_counts().to_dict()
        out["knn_example"] = {"height": int(solo.iloc[-1]["id"]), "true": "Solo", "metric": model.metric,
                              "k": int(model.n_neighbors), "weights": model.weights,
                              "neighbours": [{"rank": r + 1, "distance": float(d), "class": classes[lab[i]]}
                                             for r, (d, i) in enumerate(zip(dist[0], idx[0]))][:15],
                              "votes": votes, "prediction": knn.predict(q)[0]}
    # Linear SVM coefficients for the Solo class
    lin = joblib.load(MODELS / "final_svm_linear.joblib")
    m = lin.named_steps["model"]
    k = list(m.classes_).index("Solo")
    coef = pd.Series(m.coef_[k], index=feats).sort_values()
    out["svm_linear_solo_coefficients"] = {"most_negative": coef.head(8).round(4).to_dict(),
                                           "most_positive": coef.tail(8).round(4).to_dict()}
    write_json(ARTIFACTS / "explanations.json", out)
    print("root split:", out["root_split_worked"]["feature"], round(out["root_split_worked"]["gini"]["reduction"], 4))
    return out
