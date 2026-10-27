#!/usr/bin/env python3
"""Run the rebalancing / synthetic-augmentation comparison end to end.

This script is the controlled version of the two-stage experiment in
notebooks/exploratory_model.ipynb. The differences that matter:

  1. the train/val/test split is grouped on lesion_id and happens before any
     resampling, so no image or lesion crosses a split boundary;
  2. rebalancing touches the training split only;
  3. all arms are scored on one shared, never-resampled test set;
  4. each arm is trained from a fresh initialisation, over several seeds;
  5. the generator is class-conditional, so synthetic labels carry information;
  6. subgroup metrics ship with bootstrap intervals, a McNemar test, and the
     diagnosis mix of each subgroup.

Nothing here has been executed yet: it needs the HAM10000 image archives and a
GPU. Results land in results/ as JSON. Until that happens, no number produced
by this script appears in the README or the manuscript.

Usage:
    python scripts/run_experiment.py --arms resampling_only synthetic_augmented
    python scripts/run_experiment.py --seeds 0 1 2 --samples-per-class 5000
    python scripts/run_experiment.py --dry-run      # split + subgroup audit only
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skinfair import __version__, classifier, data, fairness, gan  # noqa: E402
from skinfair.config import (  # noqa: E402
    ClassifierConfig,
    DataConfig,
    ExperimentConfig,
    GanConfig,
)

log = logging.getLogger("run_experiment")

ARMS = ("imbalanced", "resampling_only", "synthetic_augmented")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--metadata", type=Path, default=DataConfig.metadata_csv)
    parser.add_argument(
        "--image-dir",
        type=Path,
        action="append",
        dest="image_dirs",
        help="directory of HAM10000 .jpg files; repeatable",
    )
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--samples-per-class", type=int, default=5000)
    parser.add_argument("--synthetic-per-class", type=int, default=500)
    parser.add_argument("--gan-epochs", type=int, default=GanConfig.epochs)
    parser.add_argument("--max-epochs", type=int, default=ClassifierConfig.max_epochs)
    parser.add_argument("--batch-size", type=int, default=ClassifierConfig.batch_size)
    parser.add_argument("--unconditional-gan", action="store_true", help="reproduce the notebook's label noise")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="split the data and audit the subgroups, then stop before training",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help=(
            "audit the split from metadata alone, without the image files and "
            "without brightness. Implies --dry-run."
        ),
    )
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> ExperimentConfig:
    data_config = DataConfig(
        metadata_csv=args.metadata,
        image_dirs=tuple(args.image_dirs) if args.image_dirs else DataConfig.image_dirs,
        train_samples_per_class=args.samples_per_class,
    )
    return ExperimentConfig(
        data=data_config,
        classifier=ClassifierConfig(max_epochs=args.max_epochs, batch_size=args.batch_size),
        gan=GanConfig(epochs=args.gan_epochs, conditional=not args.unconditional_gan),
        seeds=tuple(args.seeds),
        synthetic_per_class=args.synthetic_per_class,
        output_dir=args.output_dir,
    )


def prepare_splits(
    config: ExperimentConfig, *, require_images: bool = True, with_brightness: bool = True
) -> tuple[pd.DataFrame, ...]:
    df = data.load_metadata(config.data, require_images=require_images)
    log.info("loaded %d rows covering %d lesions", len(df), df["lesion_id"].nunique())

    train, val, test = data.grouped_split(df, config.data)
    log.info("split: train=%d val=%d test=%d (lesion-grouped)", len(train), len(val), len(test))

    if not with_brightness:
        log.warning("skipping brightness; every row is assigned subgroup 'unknown'")
        for frame in (train, val, test):
            frame["brightness"] = float("nan")
            frame["subgroup"] = "unknown"
        return train, val, test

    cache = config.output_dir / "brightness_cache.csv"
    out = []
    for name, frame in (("train", train), ("val", val), ("test", test)):
        log.info("computing brightness for %s (%d rows)", name, len(frame))
        out.append(data.assign_subgroup(data.attach_brightness(frame, cache), config.data))
    return tuple(out)


def arm_training_frame(
    arm: str,
    train: pd.DataFrame,
    config: ExperimentConfig,
    seed: int,
    synthetic_rows: list[dict] | None,
) -> pd.DataFrame:
    """Training rows for one arm. Only this function differs between arms."""
    if arm == "imbalanced":
        frame = data.rebalance(train, None, seed)
    else:
        frame = data.rebalance(train, config.data.train_samples_per_class, seed)

    if arm == "synthetic_augmented":
        if not synthetic_rows:
            raise RuntimeError("synthetic_augmented arm requested but no synthetic rows were generated")
        frame = pd.concat([frame, pd.DataFrame(synthetic_rows)], ignore_index=True)

    frame["is_synthetic"] = frame.get("is_synthetic", False)
    frame["is_synthetic"] = frame["is_synthetic"].fillna(False)
    return frame.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def train_generator(train: pd.DataFrame, config: ExperimentConfig, seed: int) -> list[dict]:
    """Train the DCGAN on the low-brightness training rows and sample from it."""
    import cv2

    dark = train[train["subgroup"] == "low_brightness"].drop_duplicates(subset="image_id")
    log.info(
        "GAN training set: %d distinct low-brightness training images, diagnosis mix %s",
        len(dark),
        dark["dx"].value_counts().to_dict(),
    )
    if dark.empty:
        raise RuntimeError("no low-brightness training images; cannot train the generator")

    size = config.gan.image_size
    images = []
    for path in dark["image_path"]:
        image = cv2.imread(str(path))
        if image is None:
            continue
        image = cv2.cvtColor(cv2.resize(image, (size, size)), cv2.COLOR_BGR2RGB)
        images.append((image / 127.5) - 1.0)
    real = np.asarray(images, dtype="float32")
    labels = dark["label"].to_numpy()[: len(real)]

    generator, losses = gan.train(real, labels, config.gan, seed=seed)
    synthetic_images, synthetic_labels = gan.generate(
        generator, config.synthetic_per_class, config.gan, seed=seed
    )
    rows = gan.save_synthetic(
        synthetic_images, synthetic_labels, config.output_dir / f"synthetic_seed{seed}"
    )

    memorisation = gan.nearest_neighbour_distances(synthetic_images, real)
    write_json(
        config.output_dir / f"gan_seed{seed}.json",
        {
            "n_distinct_training_images": int(len(dark)),
            "training_dx_counts": dark["dx"].value_counts().to_dict(),
            "conditional": config.gan.conditional,
            "final_generator_loss": losses["generator"][-1],
            "final_discriminator_loss": losses["discriminator"][-1],
            "losses": losses,
            "memorisation_check": memorisation,
        },
    )
    return rows


def write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))
    log.info("wrote %s", path)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    config = build_config(args)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    metadata_only = args.metadata_only
    train, val, test = prepare_splits(
        config,
        require_images=not metadata_only,
        with_brightness=not metadata_only,
    )

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skinfair_version": __version__,
        "python": platform.python_version(),
        "config": config.to_dict(),
        "metadata_only": metadata_only,
        "split_sizes": {"train": len(train), "val": len(val), "test": len(test)},
        "lesion_overlap": {
            "train_val": len(set(train["lesion_id"]) & set(val["lesion_id"])),
            "train_test": len(set(train["lesion_id"]) & set(test["lesion_id"])),
            "val_test": len(set(val["lesion_id"]) & set(test["lesion_id"])),
        },
        "test_class_counts": test["dx"].value_counts().to_dict(),
        "subgroups": {
            "train": data.subgroup_report(train),
            "test": data.subgroup_report(test),
        },
    }
    write_json(config.output_dir / "split_audit.json", audit)

    if args.dry_run or metadata_only:
        log.info("dry run complete; see %s", config.output_dir / "split_audit.json")
        return 0

    y_true = test["label"].to_numpy()
    groups = test["subgroup"].to_numpy()
    predictions: dict[str, dict[int, np.ndarray]] = {}
    results: dict[str, dict] = {}

    for seed in config.seeds:
        synthetic_rows = (
            train_generator(train, config, seed)
            if "synthetic_augmented" in args.arms
            else None
        )
        for arm in args.arms:
            log.info("training arm=%s seed=%d", arm, seed)
            frame = arm_training_frame(arm, train, config, seed, synthetic_rows)
            # Synthetic rows carry unique lesion ids, so this still catches a
            # real image leaking from train into test.
            data.assert_no_leakage(frame, val, test)

            model, history = classifier.train(frame, val, config.classifier, seed)
            y_pred = classifier.predict(model, test, config.classifier)
            predictions.setdefault(arm, {})[seed] = y_pred

            classifier.save(model, config.output_dir / f"model_{arm}_seed{seed}.keras")
            results.setdefault(arm, {})[str(seed)] = {
                "n_train_rows": int(len(frame)),
                "n_synthetic_rows": int(frame["is_synthetic"].sum()),
                "epochs_run": len(history.get("loss", [])),
                "best_val_accuracy": max(history.get("val_accuracy", [float("nan")])),
                "test": fairness.evaluate(y_true, y_pred, groups, seed=seed),
            }
            write_json(config.output_dir / "arm_results.json", results)

    summary = {"per_arm": {}, "paired_tests": {}}
    for arm, by_seed in results.items():
        accuracies = [r["test"]["overall"]["accuracy"] for r in by_seed.values()]
        eods = [r["test"]["equalized_odds"]["eod"] for r in by_seed.values()]
        defined = [e for e in eods if e is not None]
        summary["per_arm"][arm] = {
            "n_seeds": len(accuracies),
            "accuracy_mean": round(float(np.mean(accuracies)), 4),
            "accuracy_std": round(float(np.std(accuracies, ddof=1)), 4) if len(accuracies) > 1 else None,
            "accuracy_per_seed": accuracies,
            "eod_mean": round(float(np.mean(defined)), 4) if defined else None,
            "eod_per_seed": eods,
        }

    if {"resampling_only", "synthetic_augmented"} <= set(predictions):
        for seed in config.seeds:
            a = predictions["resampling_only"].get(seed)
            b = predictions["synthetic_augmented"].get(seed)
            if a is not None and b is not None:
                summary["paired_tests"][f"seed{seed}"] = fairness.mcnemar_test(y_true, a, b)

    summary["interpretation_notes"] = [
        "Both arms are scored on the same test set, which is never resampled.",
        "Each arm is trained from a fresh initialisation; no arm continues another's weights.",
        "Brightness subgroups are a proxy for skin tone, not a validated label.",
        "Read min_group_n and the bootstrap interval before any equalized-odds point estimate.",
    ]
    write_json(config.output_dir / "summary.json", summary)
    log.info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
