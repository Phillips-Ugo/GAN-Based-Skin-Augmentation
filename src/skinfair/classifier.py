"""EfficientNetB0 classifier: dataset construction, model, training, prediction.

Differences from the original notebook, all deliberate:
  * every arm is built from a fresh initialisation under a fixed seed, so two
    arms differ only in their training data;
  * the test set is never resampled and never shuffled, so predictions line up
    row for row with the test frame and can be compared across arms;
  * light augmentation is applied in-graph to the training split only, and is
    reported, rather than being claimed in the write-up and absent from the code.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CLASSES, ClassifierConfig

log = logging.getLogger(__name__)


def set_seeds(seed: int) -> None:
    """Seed Python, NumPy and TensorFlow so a run can be repeated."""
    import random

    import tensorflow as tf

    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    tf.keras.utils.set_random_seed(seed)


def build_dataset(
    df: pd.DataFrame,
    config: ClassifierConfig,
    *,
    training: bool,
    augment: bool = False,
):
    """Build a tf.data pipeline from a frame with `image_path` and `label`.

    `training=False` disables shuffling, which is what keeps prediction order
    aligned with the frame.
    """
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet import preprocess_input

    size = config.image_size

    def load(path, label):
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=3)
        image = tf.image.resize(image, [size, size])
        image = tf.cast(image, tf.float32)
        return preprocess_input(image), label

    dataset = tf.data.Dataset.from_tensor_slices(
        (df["image_path"].to_numpy(), df["label"].to_numpy())
    )
    dataset = dataset.map(load, num_parallel_calls=tf.data.AUTOTUNE)

    if augment:
        layers = tf.keras.Sequential(
            [
                tf.keras.layers.RandomFlip("horizontal"),
                tf.keras.layers.RandomRotation(0.04),
                tf.keras.layers.RandomZoom(0.1),
            ],
            name="augmentation",
        )
        dataset = dataset.map(
            lambda x, y: (layers(x, training=True), y),
            num_parallel_calls=tf.data.AUTOTUNE,
        )

    if training:
        dataset = dataset.shuffle(buffer_size=min(len(df), 10_000), seed=0)
    return dataset.batch(config.batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(config: ClassifierConfig, seed: int):
    """EfficientNetB0 with a frozen base and a fresh classification head."""
    import tensorflow as tf
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import EfficientNetB0

    set_seeds(seed)
    base = EfficientNetB0(
        include_top=False,
        input_shape=(config.image_size, config.image_size, 3),
        weights="imagenet",
    )
    base.trainable = not config.freeze_base

    model = models.Sequential(
        [
            base,
            layers.GlobalAveragePooling2D(),
            layers.Dropout(config.dropout),
            layers.Dense(len(CLASSES), activation="softmax"),
        ],
        name="skinfair_classifier",
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    config: ClassifierConfig,
    seed: int,
    *,
    augment: bool = True,
    class_weight: dict[int, float] | None = None,
):
    """Train one arm from scratch. Returns (model, history dict)."""
    import tensorflow as tf

    model = build_model(config, seed)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=config.early_stopping_patience,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=config.reduce_lr_patience,
            min_lr=1e-6,
        ),
    ]
    history = model.fit(
        build_dataset(train_df, config, training=True, augment=augment),
        validation_data=build_dataset(val_df, config, training=False),
        epochs=config.max_epochs,
        callbacks=callbacks,
        class_weight=class_weight,
        verbose=2,
    )
    return model, {k: [float(x) for x in v] for k, v in history.history.items()}


def predict(model, df: pd.DataFrame, config: ClassifierConfig) -> np.ndarray:
    """Predicted class indices, in the row order of `df`."""
    probabilities = model.predict(
        build_dataset(df, config, training=False), verbose=0
    )
    return np.argmax(probabilities, axis=1)


def save(model, path: Path) -> None:
    """Save in the native Keras format.

    The original notebook pickled a Keras object, which is why app.py needs a
    fallback loader: a pickled model cannot be read by a different TensorFlow
    version. `.keras` is portable across versions.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix != ".keras":
        path = path.with_suffix(".keras")
    model.save(path)
    log.info("saved model to %s", path)
