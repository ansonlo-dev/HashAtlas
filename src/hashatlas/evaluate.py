"""Score the frozen model choices on the sealed 2025-04 to 2026-10 test period.

Each family is refitted on the declared train/validation sample and evaluated on
the same test rows. Outputs include class metrics, Solo ROC/PR curves, day-block
bootstrap intervals, monthly drift and predictions for newcomer pools."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (average_precision_score, classification_report, confusion_matrix,
                             precision_recall_curve, roc_auc_score, roc_curve)

from .config import ARTIFACTS, MODELS, cfg, read_json, write_json
from .train import families, family_scores, load_sets, macro_scores, sample_train, topk_accuracy


def _scores(model, X) -> np.ndarray:
    """Solo-class score: probability when available, otherwise the SVM decision value (not a probability)."""
    classes = list(model.classes_)
    k = classes.index("Solo")
    if hasattr(model, "predict_proba"):
        try:
            return model.predict_proba(X)[:, k]
        except AttributeError:
            pass
    d = model.decision_function(X)
    return d[:, k] if d.ndim == 2 else d


def _curve(y, s, n=60):
    fpr, tpr, _ = roc_curve(y, s)
    pr, rc, _ = precision_recall_curve(y, s)
    idx = np.unique(np.linspace(0, len(fpr) - 1, n).astype(int))
    idx2 = np.unique(np.linspace(0, len(pr) - 1, n).astype(int))
    return {"roc": [[float(fpr[i]), float(tpr[i])] for i in idx],
            "pr": [[float(rc[i]), float(pr[i])] for i in idx2]}


def bootstrap(te: pd.DataFrame, pred: np.ndarray, n: int, seed: int) -> dict:
    """Resample whole days (blocks on the same day share conditions), recompute macro-F1 and accuracy."""
    rs = np.random.RandomState(seed)
    day = te["time"].dt.floor("D").to_numpy()
    days = np.unique(day)
    by_day = {d: np.where(day == d)[0] for d in days}
    yt = te["y"].to_numpy()
    f1s, accs = [], []
    for _ in range(n):
        idx = np.concatenate([by_day[d] for d in rs.choice(days, len(days), replace=True)])
        s = macro_scores(yt[idx], pred[idx])
        f1s.append(s["macro_f1"])
        accs.append(s["accuracy"])
    q = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]  # noqa: E731
    return {"resamples": n, "unit": "day", "macro_f1_95ci": q(f1s), "accuracy_95ci": q(accs)}


def run() -> dict:
    c = cfg()
    seed = c["project"]["random_seed"]
    sel = read_json(ARTIFACTS / "model_selection.json")
    search = read_json(ARTIFACTS / "model_search.json")["families"]
    feats = sel["features"]
    sets, cmap = load_sets()
    tr = sample_train(sets["train"], c["classification"]["pool_negative_sample"], seed)
    va = sets["validation"][sets["validation"]["y"] != "Unknown"]
    rs = np.random.RandomState(seed)
    va_s = va.groupby("month", group_keys=False).sample(frac=min(1.0, 30000 / len(va)), random_state=seed)
    va_s = pd.concat([va_s, va[(va["y"] == "Solo") & ~va.index.isin(va_s.index)]])
    fit = pd.concat([tr, va_s])
    te = sets["test"][sets["test"]["y"] != "Unknown"].reset_index(drop=True)
    Xf, yf, Xt, yt = fit[feats].astype(float), fit["y"], te[feats].astype(float), te["y"]

    out, preds, curves = {}, {}, {}
    fams = families(seed)
    for name in ["tree", "knn", "svm_linear", "svm_rbf"]:
        est = clone(fams[name][0]).set_params(**search[name]["best_params"])
        Xs, ys = Xf, yf
        if name.startswith("svm"):
            n = min(len(fit), c["classification"]["svm_max_train_rows"])
            solo_i = np.where(yf == "Solo")[0]
            idx = np.sort(np.r_[solo_i, rs.choice(np.where(yf != "Solo")[0], n - len(solo_i), replace=False)])
            Xs, ys = Xf.iloc[idx], yf.iloc[idx]
        est.fit(Xs, ys)
        joblib.dump(est, MODELS / f"final_{name}.joblib", compress=3)
        p = est.predict(Xt)
        preds[name] = p
        s = _scores(est, Xt)
        ysolo = (yt == "Solo").to_numpy()
        out[name] = {**macro_scores(yt, p), **family_scores(yt, p, sel["template_families"]["map"]),
                     "top3_accuracy": topk_accuracy(est, Xt, yt),
                     "solo_roc_auc": float(roc_auc_score(ysolo, s)) if ysolo.any() else None,
                     "solo_average_precision": float(average_precision_score(ysolo, s)) if ysolo.any() else None,
                     "solo_base_rate": float(ysolo.mean()),
                     "score_type": "probability" if name in ("tree", "knn") else "decision value (not a probability)"}
        curves[name] = _curve(ysolo, s)
        print(f"test {name}: macro-F1 {out[name]['macro_f1']:.3f}  bal-acc {out[name]['balanced_accuracy']:.3f}  "
              f"solo AP {out[name]['solo_average_precision']:.3f}", flush=True)
    for b in ("majority", "stratified_random", "decision_stump"):
        m = joblib.load(MODELS / f"{b}_train.joblib")
        pb = m.predict(Xt)
        out[b] = {**macro_scores(yt, pb), **family_scores(yt, pb, sel["template_families"]["map"]), "baseline": True}

    chosen = sel["chosen_family"]
    p = preds[chosen]
    labels = cmap["classes"]
    cm = confusion_matrix(yt, p, labels=labels)
    rep = classification_report(yt, p, labels=labels, output_dict=True, zero_division=0)
    fam_map = sel["template_families"]["map"]
    fam_labels = sorted(set(fam_map.get(x, x) for x in labels))
    cm_fam = confusion_matrix(yt.map(lambda x: fam_map.get(x, x)), pd.Series(p).map(lambda x: fam_map.get(x, x)),
                              labels=fam_labels)
    # Solo operating threshold (frozen on validation) applied to the operational tree's Solo probability
    tree = joblib.load(MODELS / "final_tree.joblib")
    ps = _scores(tree, Xt)
    flag = ps >= sel["solo_threshold"]["value"]
    ysolo = (yt == "Solo").to_numpy()
    solo_op = {"threshold": sel["solo_threshold"]["value"], "flagged": int(flag.sum()), "solo_in_test": int(ysolo.sum()),
               "true_positives": int((flag & ysolo).sum()),
               "precision": float(ysolo[flag].mean()) if flag.any() else None,
               "recall": float(flag[ysolo].mean()) if ysolo.any() else None}
    # Monthly drift of the operational model
    te2 = te.assign(pred=p, ok=(p == yt.to_numpy()))
    monthly = te2.groupby("month").apply(lambda g: pd.Series(macro_scores(g["y"], g["pred"]))).reset_index()
    # Where do pools that did not exist (or were small) in training get mapped?  (template-sharing evidence)
    newcomers = []
    rest = pd.concat([sets["validation"], sets["test"]])
    rest = rest[(rest["y"] == "Other pools")]
    model_for_map = joblib.load(MODELS / f"final_{chosen}.joblib")
    for miner, g in rest.groupby("miner"):
        if len(g) < 150:
            continue
        pm = pd.Series(model_for_map.predict(g[feats].astype(float))).value_counts(normalize=True)
        newcomers.append({"miner": miner, "blocks": len(g), "predicted_share": pm.round(4).head(4).to_dict(),
                          "top_prediction": pm.index[0], "top_share": float(pm.iloc[0])})
    newcomers.sort(key=lambda r: -r["blocks"])
    res = {
        "operational_family": chosen, "test_blocks": len(te), "test_period": c["classification"]["test"],
        "families": out, "per_class": {k: rep[k] for k in labels},
        "confusion": {"labels": labels, "matrix": cm.tolist()},
        "family_confusion": {"labels": fam_labels, "matrix": cm_fam.tolist()},
        "bootstrap": bootstrap(te, p, c["bootstrap"]["n_resamples"] if "bootstrap" in c else 500, seed),
        "solo_operating_point": solo_op, "monthly": monthly.to_dict(orient="records"),
        "newcomer_pools": newcomers, "curves": curves,
    }
    write_json(ARTIFACTS / "test_metrics.json", res)
    te2[["id", "time", "miner", "y", "pred"]].assign(solo_score=ps).to_parquet(
        ARTIFACTS.parent / "data" / "processed" / "test_predictions.parquet", index=False)
    return res
