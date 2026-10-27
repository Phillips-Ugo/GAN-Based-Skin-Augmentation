"""Tests for the subgroup metrics, including the undefined-rate cases."""

import numpy as np
import pytest

from skinfair import fairness
from skinfair.config import CLASSES

MEL = CLASSES.index("mel")
NV = CLASSES.index("nv")
BCC = CLASSES.index("bcc")
DF = CLASSES.index("df")


def test_to_binary_malignant_maps_the_three_malignant_classes():
    labels = np.array([MEL, NV, BCC, DF, CLASSES.index("akiec")])
    assert fairness.to_binary_malignant(labels).tolist() == [1, 0, 1, 0, 1]


def test_group_metrics_on_a_hand_checked_case():
    # 4 malignant (mel), 4 benign (nv). Predictions: 3 of 4 malignant caught,
    # 1 of 4 benign wrongly called malignant.
    y_true = np.array([MEL, MEL, MEL, MEL, NV, NV, NV, NV])
    y_pred = np.array([MEL, MEL, MEL, NV, NV, NV, NV, BCC])
    m = fairness.group_metrics(y_true, y_pred, "test")

    assert m.n == 8
    assert m.n_positive == 4
    assert m.tpr == pytest.approx(0.75)
    assert m.fpr == pytest.approx(0.25)
    assert m.accuracy == pytest.approx(6 / 8)


def test_tpr_is_none_when_a_group_has_no_positive_case():
    y_true = np.array([NV, NV, NV])
    m = fairness.group_metrics(y_true, np.array([NV, NV, MEL]))
    assert m.tpr is None
    assert m.fpr == pytest.approx(1 / 3)


def test_equalized_odds_takes_the_larger_gap():
    y_true = np.array([MEL, MEL, NV, NV] * 2)
    # group a: both malignant caught, no false positive -> tpr 1.0, fpr 0.0
    # group b: neither caught, both benign flagged  -> tpr 0.0, fpr 1.0
    y_pred = np.array([MEL, MEL, NV, NV, NV, NV, MEL, MEL])
    groups = np.array(["a"] * 4 + ["b"] * 4)

    result = fairness.equalized_odds_difference(y_true, y_pred, groups, "a", "b")
    assert result["tpr_gap"] == pytest.approx(1.0)
    assert result["fpr_gap"] == pytest.approx(1.0)
    assert result["eod"] == pytest.approx(1.0)
    assert result["min_group_n"] == 4
    assert result["undefined_rates"] == []


def test_equalized_odds_is_none_when_a_rate_is_undefined():
    y_true = np.array([MEL, MEL, NV, NV])
    y_pred = np.array([MEL, NV, NV, NV])
    groups = np.array(["a", "a", "b", "b"])  # group a all malignant, b all benign

    result = fairness.equalized_odds_difference(y_true, y_pred, groups, "a", "b")
    assert result["eod"] is None
    assert set(result["undefined_rates"]) == {"tpr_gap", "fpr_gap"}


def test_perfect_parity_gives_zero():
    y_true = np.array([MEL, NV] * 10)
    groups = np.array(["a"] * 10 + ["b"] * 10)
    result = fairness.equalized_odds_difference(y_true, y_true, groups, "a", "b")
    assert result["eod"] == pytest.approx(0.0)


def test_bootstrap_interval_brackets_the_point_estimate():
    rng = np.random.default_rng(0)
    # Each subgroup needs both classes, or TPR and FPR are undefined in it.
    y_true = np.array([MEL] * 30 + [NV] * 30 + [MEL] * 30 + [NV] * 30)
    y_pred = y_true.copy()
    flip = rng.choice(120, size=18, replace=False)
    y_pred[flip] = np.where(y_true[flip] == MEL, NV, MEL)
    groups = np.array(["low_brightness"] * 60 + ["high_brightness"] * 60)

    point = fairness.equalized_odds_difference(
        y_true, y_pred, groups, "low_brightness", "high_brightness"
    )["eod"]
    interval = fairness.bootstrap_interval(
        y_true, y_pred, groups, "low_brightness", "high_brightness", n_resamples=400, seed=1
    )
    low, high = interval["eod_ci"]
    assert low <= point <= high
    assert interval["n_valid_resamples"] > 0


def test_bootstrap_interval_is_wide_for_a_twelve_image_subgroup():
    """A subgroup of 12 cannot support a two-decimal fairness claim."""
    y_true = np.concatenate([np.array([MEL] * 6 + [NV] * 6), np.array([MEL] * 250 + [NV] * 250)])
    y_pred = y_true.copy()
    y_pred[0] = NV  # one missed melanoma in the small group
    groups = np.array(["low_brightness"] * 12 + ["high_brightness"] * 500)

    interval = fairness.bootstrap_interval(
        y_true, y_pred, groups, "low_brightness", "high_brightness", n_resamples=600, seed=2
    )
    low, high = interval["eod_ci"]
    assert high - low > 0.2


def test_mcnemar_exact_p_value_against_a_known_case():
    # 10 discordant pairs, all favouring model b: exact two-sided p = 2/2^10.
    y_true = np.array([MEL] * 10)
    pred_a = np.array([NV] * 10)
    pred_b = np.array([MEL] * 10)
    result = fairness.mcnemar_test(y_true, pred_a, pred_b)

    assert result["n_discordant"] == 10
    assert result["only_b_correct"] == 10
    assert result["p_value"] == pytest.approx(2 / 1024, rel=1e-6)


def test_mcnemar_reports_agreement():
    y_true = np.array([MEL, NV, MEL])
    result = fairness.mcnemar_test(y_true, y_true, y_true)
    assert result["n_discordant"] == 0
    assert result["p_value"] == 1.0


def test_mcnemar_is_symmetric():
    rng = np.random.default_rng(5)
    y_true = rng.integers(0, len(CLASSES), size=200)
    a = y_true.copy()
    b = y_true.copy()
    a[rng.choice(200, 30, replace=False)] = NV
    b[rng.choice(200, 40, replace=False)] = MEL
    forward = fairness.mcnemar_test(y_true, a, b)["p_value"]
    backward = fairness.mcnemar_test(y_true, b, a)["p_value"]
    assert forward == pytest.approx(backward)


def test_evaluate_returns_every_section():
    y_true = np.concatenate([np.full(20, MEL), np.full(20, NV)])
    y_pred = y_true.copy()
    y_pred[:3] = NV
    groups = np.array(["low_brightness"] * 20 + ["high_brightness"] * 20)

    report = fairness.evaluate(y_true, y_pred, groups)
    assert set(report) == {"overall", "per_group", "equalized_odds", "bootstrap", "caveat"}
    assert set(report["per_group"]) == {"low_brightness", "high_brightness"}
    assert report["overall"]["n"] == 40


def test_group_metrics_rejects_mismatched_shapes():
    with pytest.raises(ValueError, match="shape mismatch"):
        fairness.group_metrics(np.array([1, 2]), np.array([1]))
