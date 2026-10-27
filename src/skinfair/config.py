"""Single place for every constant the experiment depends on."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path

# HAM10000 diagnosis codes in a fixed order. Index == integer label everywhere
# in this package, so a model trained in one run stays interpretable in another.
CLASSES: tuple[str, ...] = ("akiec", "bcc", "bkl", "df", "mel", "nv", "vasc")

CLASS_FULL_NAMES: dict[str, str] = {
    "akiec": "Actinic keratosis / intraepithelial carcinoma",
    "bcc": "Basal cell carcinoma",
    "bkl": "Benign keratosis-like lesion",
    "df": "Dermatofibroma",
    "mel": "Melanoma",
    "nv": "Melanocytic nevus",
    "vasc": "Vascular lesion",
}

MALIGNANT: frozenset[str] = frozenset({"mel", "bcc", "akiec"})


@dataclass(frozen=True)
class DataConfig:
    """Paths and split policy.

    The split is grouped on lesion_id and happens BEFORE any resampling. 1,956
    of HAM10000's 7,470 lesions contribute more than one image (4,501 images in
    total), so an image-level split leaks near-duplicate views of the same
    lesion across train and test even without oversampling.
    """

    metadata_csv: Path = Path("data/HAM10000_metadata.csv")
    image_dirs: tuple[Path, ...] = (
        Path("data/HAM10000_images_part_1"),
        Path("data/HAM10000_images_part_2"),
    )
    val_fraction: float = 0.15
    test_fraction: float = 0.15
    seed: int = 42
    # Oversample the TRAIN split only, to this many rows per class. None disables
    # rebalancing and leaves the natural (58:1) distribution in place.
    train_samples_per_class: int | None = 5000
    # Mean greyscale intensity below this marks a row as the low-brightness
    # subgroup. A proxy for skin tone, and a poor one -- see subgroup_report().
    brightness_threshold: float = 110.0
    # Rows above this form the comparison subgroup.
    brightness_light_threshold: float = 140.0


@dataclass(frozen=True)
class ClassifierConfig:
    image_size: int = 224
    batch_size: int = 32
    max_epochs: int = 150
    early_stopping_patience: int = 5
    reduce_lr_patience: int = 3
    learning_rate: float = 1e-3
    dropout: float = 0.3
    # Stage 2 in the original notebook continued training stage 1's weights, so
    # the two arms differed in total epochs as well as in data. Every arm here
    # is trained from the same fresh initialisation instead.
    freeze_base: bool = True
    fine_tune_epochs: int = 0


@dataclass(frozen=True)
class GanConfig:
    image_size: int = 64
    noise_dim: int = 100
    epochs: int = 400
    batch_size: int = 32
    generator_lr: float = 1e-4
    discriminator_lr: float = 1e-4
    # The notebook trained one unconditional generator and then labelled its
    # output class_0..class_6 by filename, injecting 3,500 mislabelled images.
    # Conditioning is on by default so synthetic labels carry information.
    conditional: bool = True
    label_smoothing: float = 0.1


@dataclass(frozen=True)
class ExperimentConfig:
    data: DataConfig = field(default_factory=DataConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    gan: GanConfig = field(default_factory=GanConfig)
    # Several seeds, because a single split cannot separate a real effect from
    # split variance. The headline comparison is a mean with a spread.
    seeds: tuple[int, ...] = (0, 1, 2)
    synthetic_per_class: int = 500
    output_dir: Path = Path("results")

    def to_dict(self) -> dict:
        def _convert(value):
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, (tuple, list)):
                return [_convert(v) for v in value]
            if isinstance(value, dict):
                return {k: _convert(v) for k, v in value.items()}
            return value

        return {k: _convert(v) for k, v in asdict(self).items()}
