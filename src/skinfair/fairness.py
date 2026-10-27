"""Subgroup performance, equalized-odds difference, and paired significance tests.

Nothing in the original notebook computed any of this; the fairness numbers in
the manuscript have no code behind them. See docs/RESULTS_PROVENANCE.md.

Every function takes plain integer label arrays so it can be tested without
TensorFlow or image data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import CLASSES, MALIGNANT

LABEL_TO_INDEX = {name: i for i, name in enumerate(CLASSES)}
MALIGNANT_INDICES = frozenset(LABEL_TO_INDEX[name] for name in MALIGNANT)


@dataclass(frozen=True)
class GroupMetrics:
    """Binary screening metrics for one subgroup, malignant vs benign."""

    group: str
    n: int
    n_positive: int
    accuracy: float
    tpr: float | None
    fpr: float | None

    def to_dict(self) -> dict:
        return {
            "group": self.group,
            "n": self.n,
            "n_positive": self.n_positive,
            "accuracy": _round(self.accuracy),
            "tpr": _round(self.tpr),
            "fpr": _round(self.fpr),
        }


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(float(value), digits)


def to_binary_malignant(labels: np.ndarray) -> np.ndarray:
    """Collapse the 7 classes to malignant (1) vs benign (0).

    Equalized odds is defined for a binary outcome. Malignant here is melanoma,
    basal cell carcinoma, and actinic keratosis, the three classes where a
    missed case carries clinical cost.
    """
    labels = np.asarray(labels)
    return np.isin(labels, list(MALIGNANT_INDICES)).astype(int)


def group_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, group: str = "all"
) -> GroupMetrics:
    """Accuracy, TPR and FPR for one subgroup.

    TPR is None when the subgroup contains no positive case, and FPR is None
    when it contains no negative case. Returning None rather than 0.0 keeps an
    undefined rate from silently entering an equalized-odds difference.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_pred.shape}")
    if y_true.size == 0:
        return GroupMetrics(group, 0, 0, float("nan"), None, None)

    binary_true = to_binary_malignant(y_true)
    binary_pred = to_binary_malignant(y_pred)

    positives = binary_true == 1
    negatives = ~positives
    tpr = float(binary_pred[positives].mean()) if positives.any() else None
    fpr = float(binary_pred[negatives].mean()) if negatives.any() else None

    return GroupMetrics(
        group=group,
        n=int(y_true.size),
        n_positive=int(positives.sum()),
        accuracy=float((y_true == y_pred).mean()),
        tpr=tpr,
        fpr=fpr,
    )


def equalized_odds_difference(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
    group_a: str,
    group_b: str,
) -> dict:
    """max(|TPR gap|, |FPR gap|) between two subgroups, with both gaps reported.

    Returns `eod: None` when either rate is undefined in either group, which is
    the usual outcome for a subgroup of a dozen images. A reported 0.07 computed
    over 12 images moves by more than its own magnitude when one image changes
    label, so `n` travels with the number and `min_group_n` is the figure to
    read first.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    groups = np.asarray(groups)

    mask_a = groups == group_a
    mask_b = groups == group_b
    metrics_a = group_metrics(y_true[mask_a], y_pred[mask_a], group_a)
    metrics_b = group_metrics(y_true[mask_b], y_pred[mask_b], group_b)

    tpr_gap = (
        abs(metrics_a.tpr - metrics_b.tpr)
        if metrics_a.tpr is not None and metrics_b.tpr is not None
        else None
    )
    fpr_gap = (
        abs(metrics_a.fpr - metrics_b.fpr)
        if metrics_a.fpr is not None and metrics_b.fpr is not None
        else None
    )
    defined = [gap for gap in (tpr_gap, fpr_gap) if gap is not None]

    return {
        "group_a": metrics_a.to_dict(),
        "group_b": metrics_b.to_dict(),
        "tpr_gap": _round(tpr_gap),
        "fpr_gap": _round(fpr_gap),
        "eod": _round(max(defined)) if defined else None,
        "min_group_n": int(min(metrics_a.n, metrics_b.n)),
        "undefined_rates": [
            name
            for name, gap in (("tpr_gap", tpr_gap), ("fpr_gap", fpr_gap))
            if gap is None
        ],
    }


def bootstrap_interval(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
    group_a: str,
    group_b: str,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 0,
) -> dict:
    """Percentile bootstrap interval for the equalized-odds difference.

    Resampling is stratified within each subgroup, so group sizes stay fixed and
    the interval reflects uncertainty in the rates rather than in the subgroup
    composition. With a subgroup of 12 the interval is wide, which is the point:
    it is what makes a 0.13 to 0.07 change interpretable.
    """
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    groups = np.asarray(groups)

    index_a = np.flatnonzero(groups == group_a)
    index_b = np.flatnonzero(groups == group_b)
    if index_a.size == 0 or index_b.size == 0:
        return {"eod_ci": None, "reason": "a subgroup is empty"}

    samples: list[float] = []
    for _ in range(n_resamples):
        pick = np.concatenate(
            [
                rng.choice(index_a, size=index_a.size, replace=True),
                rng.choice(index_b, size=index_b.size, replace=True),
            ]
        )
        result = equalized_odds_difference(
            y_true[pick], y_pred[pick], groups[pick], group_a, group_b
        )
        if result["eod"] is not None:
            samples.append(result["eod"])

    if not samples:
        return {"eod_ci": None, "reason": "every resample left a rate undefined"}

    alpha = (1.0 - confidence) / 2.0
    low, high = np.quantile(samples, [alpha, 1.0 - alpha])
    return {
        "eod_ci": [_round(low), _round(high)],
        "confidence": confidence,
        "n_valid_resamples": len(samples),
        "n_requested": n_resamples,
    }


def mcnemar_test(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict:
    """Exact McNemar test on two models' predictions over the same test set.

    This is the correct test for the 85% vs 80% comparison, and it requires what
    the original experiment did not have: both arms scored on one shared test
    set. Uses the exact binomial p-value, since the discordant count is small
    whenever the subgroup is.
    """
    y_true = np.asarray(y_true)
    pred_a = np.asarray(pred_a)
    pred_b = np.asarray(pred_b)
    if not (y_true.shape == pred_a.shape == pred_b.shape):
        raise ValueError("y_true, pred_a and pred_b must have the same shape")

    correct_a = y_true == pred_a
    correct_b = y_true == pred_b
    only_a = int(np.sum(correct_a & ~correct_b))
    only_b = int(np.sum(~correct_a & correct_b))
    n = only_a + only_b

    if n == 0:
        return {
            "n_discordant": 0,
            "only_a_correct": 0,
            "only_b_correct": 0,
            "p_value": 1.0,
            "note": "the two models agree on every test image",
        }

    from math import comb

    k = min(only_a, only_b)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2.0**n)
    p_value = min(1.0, 2.0 * tail)

    return {
        "n_discordant": n,
        "only_a_correct": only_a,
        "only_b_correct": only_b,
        "p_value": _round(p_value, 10),
        "accuracy_a": _round(float(correct_a.mean())),
        "accuracy_b": _round(float(correct_b.mean())),
    }


def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    groups: np.ndarray,
    group_a: str = "low_brightness",
    group_b: str = "high_brightness",
    seed: int = 0,
) -> dict:
    """Full subgroup report for one model: overall, per-group, EOD, interval."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    groups = np.asarray(groups)

    per_group = {
        str(name): group_metrics(y_true[groups == name], y_pred[groups == name], str(name)).to_dict()
        for name in np.unique(groups)
    }
    eod = equalized_odds_difference(y_true, y_pred, groups, group_a, group_b)
    interval = bootstrap_interval(y_true, y_pred, groups, group_a, group_b, seed=seed)

    return {
        "overall": group_metrics(y_true, y_pred, "all").to_dict(),
        "per_group": per_group,
        "equalized_odds": eod,
        "bootstrap": interval,
        "caveat": (
            "Brightness is a proxy for skin tone, not a validated label. "
            "HAM10000 provides no Fitzpatrick annotation. Read min_group_n and "
            "the bootstrap interval before the point estimate."
        ),
    }
