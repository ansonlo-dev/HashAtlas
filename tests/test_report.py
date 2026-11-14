"""Keep report comparisons consistent with the reported macro-F1 values."""
from hashatlas.report import _baseline_comparison


def metrics(linear=0.077):
    return {
        "majority": {"macro_f1": 0.031},
        "stratified_random": {"macro_f1": 0.081},
        "decision_stump": {"macro_f1": 0.063},
        "knn": {"macro_f1": 0.105},
        "svm_linear": {"macro_f1": linear},
        "svm_rbf": {"macro_f1": 0.099},
    }


def test_beating_the_stump_does_not_imply_beating_every_baseline():
    sentence = _baseline_comparison(metrics())
    assert "matches or exceeds Linear SVM" in sentence
    assert "KNN and both SVMs also exceed" not in sentence


def test_a_tie_is_not_described_as_beating_the_baseline():
    assert "matches or exceeds Linear SVM" in _baseline_comparison(metrics(linear=0.081))


def test_all_models_above_the_strongest_baseline():
    assert "KNN and both SVMs also exceed the strongest baseline" in _baseline_comparison(metrics(linear=0.09))
