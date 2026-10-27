"""Metadata loading, leakage-free splitting, and the brightness subgroup proxy.

The one rule this module enforces: no lesion may appear in more than one split,
and resampling happens strictly after the split, on the training rows only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CLASSES, DataConfig

log = logging.getLogger(__name__)

LABEL_TO_INDEX: dict[str, int] = {name: i for i, name in enumerate(CLASSES)}
INDEX_TO_LABEL: dict[int, str] = {i: name for name, i in LABEL_TO_INDEX.items()}


class LeakageError(AssertionError):
    """Raised when splits share a lesion, an image, or a resampled row."""


def load_metadata(config: DataConfig, require_images: bool = True) -> pd.DataFrame:
    """Read HAM10000 metadata and attach integer labels and image paths.

    Missing ages are filled with the column mean, matching the original
    notebook. Rows whose image file cannot be found are dropped with a warning
    rather than silently kept, because a missing path becomes a decode error
    thousands of steps into training. Pass ``require_images=False`` to keep
    those rows, which lets the split policy be audited from metadata alone,
    before the 5GB of images have been downloaded.
    """
    df = pd.read_csv(config.metadata_csv)

    required = {"lesion_id", "image_id", "dx"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{config.metadata_csv} is missing columns: {sorted(missing)}")

    if "age" in df.columns:
        df["age"] = df["age"].fillna(df["age"].mean())

    unknown = set(df["dx"].unique()) - set(CLASSES)
    if unknown:
        raise ValueError(f"unexpected diagnosis codes in metadata: {sorted(unknown)}")

    df["label"] = df["dx"].map(LABEL_TO_INDEX).astype(int)
    df["image_path"] = [_resolve_image(image_id, config.image_dirs) for image_id in df["image_id"]]

    absent = df["image_path"].isna()
    if absent.any() and not require_images:
        log.warning(
            "%d of %d image files were not found; keeping the rows because "
            "require_images=False. Metadata-only mode: do not train on this.",
            int(absent.sum()),
            len(df),
        )
        return df.reset_index(drop=True)
    if absent.any():
        log.warning(
            "dropping %d of %d rows whose image file was not found under %s",
            int(absent.sum()),
            len(df),
            [str(d) for d in config.image_dirs],
        )
        df = df.loc[~absent].reset_index(drop=True)

    if df.empty:
        raise FileNotFoundError(
            "no HAM10000 images were found. Download the image archives into "
            f"{[str(d) for d in config.image_dirs]} -- see README.md."
        )
    return df


def _resolve_image(image_id: str, image_dirs: tuple[Path, ...]) -> str | None:
    for directory in image_dirs:
        candidate = Path(directory) / f"{image_id}.jpg"
        if candidate.exists():
            return str(candidate)
    return None


def grouped_split(
    df: pd.DataFrame, config: DataConfig
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split into train/val/test with every image of a lesion in one split.

    Lesions are assigned greedily, rarest diagnosis first, so that the 115-image
    `df` class and the 142-image `vasc` class are represented in all three
    splits. Stratification is approximate by construction: a lesion is an
    indivisible unit and carries a single diagnosis, so exact per-class
    proportions are not attainable at lesion granularity.
    """
    rng = np.random.default_rng(config.seed)
    holdout = config.val_fraction + config.test_fraction
    if not 0 < holdout < 1:
        raise ValueError("val_fraction + test_fraction must lie in (0, 1)")

    lesions = (
        df.groupby("lesion_id")
        .agg(dx=("dx", "first"), n_images=("image_id", "size"))
        .reset_index()
    )

    assignment: dict[str, str] = {}
    # Rarest class first: its lesion count is the binding constraint.
    class_order = sorted(CLASSES, key=lambda c: int((lesions["dx"] == c).sum()))
    for dx in class_order:
        group = lesions.loc[lesions["dx"] == dx, "lesion_id"].to_numpy()
        rng.shuffle(group)
        n = len(group)
        n_test = int(round(n * config.test_fraction))
        n_val = int(round(n * config.val_fraction))
        # Guarantee at least one lesion per split once a class has >= 3 lesions,
        # otherwise a rare class can vanish from the test set entirely.
        if n >= 3:
            n_test = max(1, n_test)
            n_val = max(1, n_val)
        if n_test + n_val >= n:
            n_test = min(n_test, max(0, n - 1))
            n_val = min(n_val, max(0, n - 1 - n_test))
        for lesion_id in group[:n_test]:
            assignment[lesion_id] = "test"
        for lesion_id in group[n_test : n_test + n_val]:
            assignment[lesion_id] = "val"
        for lesion_id in group[n_test + n_val :]:
            assignment[lesion_id] = "train"

    df = df.copy()
    df["split"] = df["lesion_id"].map(assignment)
    if df["split"].isna().any():
        raise LeakageError("some lesions were never assigned to a split")

    train = df[df["split"] == "train"].reset_index(drop=True)
    val = df[df["split"] == "val"].reset_index(drop=True)
    test = df[df["split"] == "test"].reset_index(drop=True)
    assert_no_leakage(train, val, test)
    return train, val, test


def assert_no_leakage(*splits: pd.DataFrame) -> None:
    """Fail loudly if any lesion or image is shared between two splits.

    Called after every split and again after resampling. The defect this guards
    against is the one that inflated the original 85% figure.
    """
    for key in ("lesion_id", "image_id"):
        seen: dict[object, int] = {}
        for index, split in enumerate(splits):
            if key not in split.columns:
                continue
            for value in split[key].unique():
                previous = seen.get(value)
                if previous is not None and previous != index:
                    raise LeakageError(
                        f"{key}={value!r} appears in split {previous} and split {index}"
                    )
                seen[value] = index


def rebalance(df: pd.DataFrame, samples_per_class: int | None, seed: int) -> pd.DataFrame:
    """Oversample each class with replacement, to be applied to TRAIN only.

    Classes already at or above the target are downsampled without replacement.
    The returned frame keeps an `is_duplicate` column so that any later
    evaluation can be checked for resampled rows.
    """
    if samples_per_class is None:
        out = df.copy()
        out["is_duplicate"] = False
        return out

    rng = np.random.default_rng(seed)
    parts = []
    for label in range(len(CLASSES)):
        group = df[df["label"] == label]
        if group.empty:
            log.warning("class %s has no training rows; skipping", INDEX_TO_LABEL[label])
            continue
        replace = len(group) < samples_per_class
        picks = rng.choice(len(group), size=samples_per_class, replace=replace)
        sampled = group.iloc[picks].copy()
        sampled["is_duplicate"] = sampled.duplicated(subset="image_id", keep="first")
        parts.append(sampled)
    out = pd.concat(parts, ignore_index=True)
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def compute_brightness(paths: list[str], image_size: int = 64) -> list[float | None]:
    """Mean greyscale intensity per image, the proxy used for the subgroup split.

    Imported lazily so that split and metric code stays usable without OpenCV.
    """
    import cv2

    values: list[float | None] = []
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            values.append(None)
            continue
        image = cv2.resize(image, (image_size, image_size))
        values.append(float(np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))))
    return values


def attach_brightness(df: pd.DataFrame, cache: Path | None = None) -> pd.DataFrame:
    """Add a `brightness` column, reading from and writing to an optional cache."""
    df = df.copy()
    if cache is not None and Path(cache).exists():
        known = pd.read_csv(cache).set_index("image_id")["brightness"].to_dict()
    else:
        known = {}

    todo = [p for i, p in zip(df["image_id"], df["image_path"]) if i not in known]
    if todo:
        ids = [i for i in df["image_id"] if i not in known]
        for image_id, value in zip(ids, compute_brightness(todo)):
            known[image_id] = value
        if cache is not None:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                {"image_id": list(known), "brightness": list(known.values())}
            ).to_csv(cache, index=False)

    df["brightness"] = df["image_id"].map(known)
    return df


def assign_subgroup(df: pd.DataFrame, config: DataConfig) -> pd.DataFrame:
    """Label rows `low_brightness`, `high_brightness`, or `mid` from brightness.

    This is a proxy for skin tone and a weak one. HAM10000 ships no Fitzpatrick
    annotation, and dark lesions on light skin depress mean intensity just as
    dark skin does. subgroup_report() quantifies the resulting confound.
    """
    if "brightness" not in df.columns:
        raise ValueError("call attach_brightness() before assign_subgroup()")

    def classify(value: float | None) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "unknown"
        if value < config.brightness_threshold:
            return "low_brightness"
        if value > config.brightness_light_threshold:
            return "high_brightness"
        return "mid"

    out = df.copy()
    out["subgroup"] = out["brightness"].map(classify)
    return out


def subgroup_report(df: pd.DataFrame) -> dict:
    """Describe the brightness subgroups, including the diagnosis confound.

    In the original notebook's 40 low-brightness rows, 24 were melanoma and 9
    were nevi, against a 11% melanoma base rate in HAM10000. A model that looks
    fairer on that subgroup may only be predicting melanoma more often, so the
    per-subgroup diagnosis mix belongs in any fairness claim built on it.
    """
    report: dict = {"overall_dx_distribution": df["dx"].value_counts(normalize=True).round(4).to_dict()}
    for name, group in df.groupby("subgroup"):
        report[str(name)] = {
            "n_rows": int(len(group)),
            "n_unique_images": int(group["image_id"].nunique()),
            "n_unique_lesions": int(group["lesion_id"].nunique()),
            "dx_counts": group["dx"].value_counts().to_dict(),
            "dx_distribution": group["dx"].value_counts(normalize=True).round(4).to_dict(),
            "mean_brightness": round(float(group["brightness"].mean()), 2),
        }
    return report
