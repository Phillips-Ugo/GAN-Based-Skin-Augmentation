#!/usr/bin/env python3
"""Quantify how much the original split protocol inflates test accuracy.

The audit in docs/RESULTS_PROVENANCE.md argues that oversampling before the
train/test split makes the 85% figure optimistic. This script measures the size
of that effect instead of asserting it.

Re-running the real experiment needs the HAM10000 images and a GPU. So this is a
controlled simulation of the *mechanism*, not a rerun: a synthetic dataset built
to match HAM10000's two relevant structural features, then the same classifier
trained under both split protocols.

  * HAM10000's class imbalance, 67% nevi down to 1.15% dermatofibroma, which is
    what motivates oversampling to 5,000 rows per class in the first place.
  * Multiple images per lesion: 1,956 of 7,470 lesions contribute more than one
    image. Repeat images of one lesion are near-duplicates, so they leak even
    when no row is literally duplicated.

Two protocols, identical in every other respect:

  A (the notebook's): oversample the whole dataset to N per class with
    replacement, then split at random. Duplicated rows straddle the split.
  B (corrected): split on lesion id first, then oversample the training rows
    only. The test set contains no row and no lesion seen in training.

The gap between A's and B's test accuracy is the inflation. A reports on its own
contaminated test set, as the notebook did; B reports on a clean one.

Two learner capacities are run, because capacity governs how much a model can
exploit a duplicated row:

  * `logreg`, a multinomial linear head on fixed features. This is the faithful
    analogue of the real setup, where EfficientNetB0's base was frozen and only
    8,967 parameters were trained.
  * `rf`, a random forest, which can memorise individual rows. It shows the
    mechanism's upper bound.

The task difficulty is swept, because inflation depends on how much there is to
memorise relative to what can be learned. Reporting a single number here would
be picking a point on that curve.

Run: python scripts/leakage_demo.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skinfair.data import rebalance  # noqa: E402

# HAM10000 class proportions, in the order of skinfair.config.CLASSES.
HAM10000_PROPORTIONS = np.array(
    [327, 514, 1099, 115, 1113, 6705, 142], dtype=float
)
HAM10000_PROPORTIONS /= HAM10000_PROPORTIONS.sum()

N_CLASSES = 7


def make_dataset(
    n_lesions: int,
    n_features: int,
    within_lesion_noise: float,
    class_separation: float,
    rng: np.random.Generator,
):
    """Synthetic lesions whose repeat images are near-duplicates of each other.

    Each lesion gets one latent feature vector drawn around its class centroid.
    Its images are that vector plus small noise, which is what makes two images
    of one lesion far more similar to each other than to anything else.
    """
    centroids = rng.normal(0, class_separation, size=(N_CLASSES, n_features))

    # Match the real repeat-image distribution: 1,956 of 7,470 lesions have >1
    # image, 4,501 of 10,015 images belong to such a lesion.
    images_per_lesion = rng.choice([1, 2, 3], size=n_lesions, p=[0.738, 0.200, 0.062])

    rows, labels, lesion_ids = [], [], []
    for lesion in range(n_lesions):
        label = rng.choice(N_CLASSES, p=HAM10000_PROPORTIONS)
        latent = centroids[label] + rng.normal(0, 1.0, size=n_features)
        for _ in range(images_per_lesion[lesion]):
            rows.append(latent + rng.normal(0, within_lesion_noise, size=n_features))
            labels.append(label)
            lesion_ids.append(lesion)

    return (
        np.asarray(rows),
        np.asarray(labels),
        np.asarray(lesion_ids),
    )


def _build_model(kind: str, seed: int):
    if kind == "rf":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            n_estimators=120, max_depth=None, random_state=seed, n_jobs=-1
        )
    if kind == "logreg":
        from sklearn.linear_model import LogisticRegression

        # Low capacity, like the frozen-base head in the real experiment.
        # scikit-learn >= 1.7 dropped `multi_class`; multinomial is the default.
        return LogisticRegression(max_iter=2000, C=1.0)
    raise ValueError(f"unknown model kind: {kind}")


def _fit_and_score(X_train, y_train, X_test, y_test, seed: int, model_kind: str = "rf"):
    from sklearn.metrics import accuracy_score, f1_score

    model = _build_model(model_kind, seed)
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    return {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
        "macro_f1": round(float(f1_score(y_test, predicted, average="macro")), 4),
    }


def protocol_a(
    X, y, lesions, samples_per_class: int, test_fraction: float, seed: int,
    model_kind: str = "rf",
):
    """Oversample everything, then split at random. The notebook's order."""
    import pandas as pd

    frame = pd.DataFrame({"label": y, "row": np.arange(len(y)), "image_id": np.arange(len(y))})
    pool = rebalance(frame, samples_per_class, seed)

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(pool))
    cut = int(len(pool) * (1.0 - test_fraction))
    train_rows = pool.iloc[order[:cut]]["row"].to_numpy()
    test_rows = pool.iloc[order[cut:]]["row"].to_numpy()

    shared = len(set(train_rows) & set(test_rows))
    result = _fit_and_score(
        X[train_rows], y[train_rows], X[test_rows], y[test_rows], seed, model_kind
    )
    result.update(
        {
            "protocol": "A: oversample then split (the notebook's order)",
            "n_train": int(len(train_rows)),
            "n_test": int(len(test_rows)),
            "distinct_images_in_both_splits": int(shared),
            "fraction_of_test_seen_in_training": round(
                float(len(set(test_rows) & set(train_rows)) / len(set(test_rows))), 4
            ),
        }
    )
    return result


def protocol_b(
    X, y, lesions, samples_per_class: int, test_fraction: float, seed: int,
    model_kind: str = "rf",
):
    """Split on lesion, then oversample the training rows only."""
    import pandas as pd

    rng = np.random.default_rng(seed)
    unique = np.unique(lesions)
    rng.shuffle(unique)
    n_test = int(len(unique) * test_fraction)
    test_lesions = set(unique[:n_test].tolist())

    is_test = np.array([lesion in test_lesions for lesion in lesions])
    test_rows = np.flatnonzero(is_test)
    train_pool = np.flatnonzero(~is_test)

    frame = pd.DataFrame(
        {
            "label": y[train_pool],
            "row": train_pool,
            "image_id": train_pool,
        }
    )
    oversampled = rebalance(frame, samples_per_class, seed)
    train_rows = oversampled["row"].to_numpy()

    shared = len(set(train_rows) & set(test_rows))
    assert shared == 0, "protocol B must not share a row between splits"
    assert not (set(lesions[train_rows].tolist()) & set(lesions[test_rows].tolist()))

    result = _fit_and_score(
        X[train_rows], y[train_rows], X[test_rows], y[test_rows], seed, model_kind
    )
    result.update(
        {
            "protocol": "B: lesion-grouped split, then oversample train only",
            "n_train": int(len(train_rows)),
            "n_test": int(len(test_rows)),
            "distinct_images_in_both_splits": 0,
            "fraction_of_test_seen_in_training": 0.0,
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--n-lesions", type=int, default=7470, help="matches HAM10000")
    parser.add_argument("--n-features", type=int, default=24)
    parser.add_argument(
        "--samples-per-class", type=int, default=5000, help="the notebook's target"
    )
    parser.add_argument("--within-lesion-noise", type=float, default=0.15)
    parser.add_argument(
        "--class-separation",
        nargs="+",
        type=float,
        default=[0.15, 0.25, 0.35, 0.5, 0.7],
        help="difficulty sweep: smaller means a harder task",
    )
    parser.add_argument("--models", nargs="+", choices=["logreg", "rf"], default=["logreg", "rf"])
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--output", type=Path, default=Path("results/leakage_demo.json"))
    args = parser.parse_args(argv)

    cells = []
    for model_kind in args.models:
        for separation in args.class_separation:
            a_scores, b_scores, overlaps = [], [], []
            a_f1, b_f1 = [], []
            for seed in args.seeds:
                rng = np.random.default_rng(seed)
                X, y, lesions = make_dataset(
                    args.n_lesions,
                    args.n_features,
                    args.within_lesion_noise,
                    separation,
                    rng,
                )
                a = protocol_a(
                    X, y, lesions, args.samples_per_class, args.test_fraction, seed, model_kind
                )
                b = protocol_b(
                    X, y, lesions, args.samples_per_class, args.test_fraction, seed, model_kind
                )
                a_scores.append(a["accuracy"])
                b_scores.append(b["accuracy"])
                a_f1.append(a["macro_f1"])
                b_f1.append(b["macro_f1"])
                overlaps.append(a["fraction_of_test_seen_in_training"])

            a_mean = float(np.mean(a_scores))
            b_mean = float(np.mean(b_scores))
            a_f1_mean = float(np.mean(a_f1))
            b_f1_mean = float(np.mean(b_f1))
            cells.append(
                {
                    "model": model_kind,
                    "class_separation": separation,
                    "protocol_a_accuracy": round(a_mean, 4),
                    "protocol_b_accuracy": round(b_mean, 4),
                    "protocol_a_macro_f1": round(a_f1_mean, 4),
                    "protocol_b_macro_f1": round(b_f1_mean, 4),
                    "macro_f1_inflation": round(a_f1_mean - b_f1_mean, 4),
                    "inflation": round(a_mean - b_mean, 4),
                    "inflation_per_seed": [
                        round(float(a - b), 4) for a, b in zip(a_scores, b_scores)
                    ],
                    "test_overlap_fraction": round(float(np.mean(overlaps)), 4),
                }
            )
            print(
                f"{model_kind:6} sep={separation:<5} "
                f"acc A={a_mean:.4f} B={b_mean:.4f} ({a_mean - b_mean:+.4f})   "
                f"macroF1 A={a_f1_mean:.4f} B={b_f1_mean:.4f} ({a_f1_mean - b_f1_mean:+.4f})"
            )

    overlap = float(np.mean([c["test_overlap_fraction"] for c in cells]))
    summary = {
        "what_this_is": (
            "A controlled simulation of the split-protocol defect, not a rerun of "
            "the HAM10000 experiment. It measures the mechanism's effect size on "
            "synthetic data matched to HAM10000's class imbalance and repeat-image "
            "structure. Absolute accuracies are artefacts of the simulation; the "
            "gap between protocols at a given difficulty is the quantity of interest."
        ),
        "headline": (
            "Oversampling to {n} rows per class before splitting leaves {pct:.0%} of "
            "the test set also present in training. Protocol A's reported accuracy "
            "is then close to 1.0 almost regardless of how hard the task is, so it "
            "carries little information about generalisation."
        ).format(n=args.samples_per_class, pct=overlap),
        "simulation_confound": (
            "Protocol A's test set is drawn from the oversampled pool, so it is "
            "class-balanced, while protocol B's is the natural imbalanced "
            "distribution. Accuracy is therefore not strictly comparable between "
            "the two columns; macro-F1 is the more robust comparison, and both "
            "are reported. This mirrors the flaw in the original experiment, "
            "where the two arms were also scored on differently distributed sets."
        ),
        "caveat": (
            "The real experiment trained a frozen-base linear head (8,967 "
            "parameters), so the logreg rows are the faithful analogue and the rf "
            "rows are an upper bound on the mechanism. Neither predicts the exact "
            "inflation in the original 85% figure, which can only be settled by "
            "rerunning scripts/run_experiment.py on the real images."
        ),
        "n_seeds": len(args.seeds),
        "mean_fraction_of_test_set_also_in_training": round(overlap, 4),
        "config": {
            "n_lesions": args.n_lesions,
            "n_features": args.n_features,
            "samples_per_class": args.samples_per_class,
            "within_lesion_noise": args.within_lesion_noise,
            "test_fraction": args.test_fraction,
            "seeds": args.seeds,
        },
        "sweep": cells,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2))

    print()
    print(f"share of protocol A's test set also present in its training set: {overlap:.1%}")
    print()
    print("| model | separation | acc A | acc B | acc inflation | macro-F1 A | macro-F1 B | F1 inflation |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in cells:
        print(
            f"| {cell['model']} | {cell['class_separation']} | "
            f"{cell['protocol_a_accuracy']:.4f} | {cell['protocol_b_accuracy']:.4f} | "
            f"{cell['inflation']:+.4f} | {cell['protocol_a_macro_f1']:.4f} | "
            f"{cell['protocol_b_macro_f1']:.4f} | {cell['macro_f1_inflation']:+.4f} |"
        )
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
