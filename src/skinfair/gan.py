"""DCGAN for low-brightness lesion images, with an optional class condition.

The notebook's generator was unconditional, and its 3,500 outputs were then
labelled class_0..class_6 by filename. Those labels were independent of the
image content, so 12.5% of the augmented training set was label noise. Setting
`GanConfig.conditional = True` (the default) makes the label an input to both
networks, so a synthetic image labelled `mel` was at least generated from the
melanoma condition.

This does not make 29 distinct training images sufficient. It removes one
confound so that the remaining question -- whether synthetic data helps at this
sample size -- can actually be asked.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .config import CLASSES, GanConfig

log = logging.getLogger(__name__)


def build_generator(config: GanConfig):
    import tensorflow as tf
    from tensorflow.keras import layers

    noise = layers.Input(shape=(config.noise_dim,), name="noise")
    inputs = [noise]
    x = noise

    if config.conditional:
        label = layers.Input(shape=(1,), dtype="int32", name="label")
        inputs.append(label)
        embedded = layers.Embedding(len(CLASSES), config.noise_dim)(label)
        embedded = layers.Flatten()(embedded)
        x = layers.Multiply()([noise, embedded])

    x = layers.Dense(8 * 8 * 256, use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(0.2)(x)
    x = layers.Reshape((8, 8, 256))(x)

    for filters in (128, 64):
        x = layers.Conv2DTranspose(filters, 5, strides=2, padding="same", use_bias=False)(x)
        x = layers.BatchNormalization()(x)
        x = layers.LeakyReLU(0.2)(x)

    output = layers.Conv2DTranspose(
        3, 5, strides=2, padding="same", use_bias=False, activation="tanh"
    )(x)
    return tf.keras.Model(inputs, output, name="generator")


def build_discriminator(config: GanConfig):
    import tensorflow as tf
    from tensorflow.keras import layers

    image = layers.Input(shape=(config.image_size, config.image_size, 3), name="image")
    inputs = [image]
    x = image

    if config.conditional:
        label = layers.Input(shape=(1,), dtype="int32", name="label")
        inputs.append(label)
        plane = layers.Embedding(len(CLASSES), config.image_size**2)(label)
        plane = layers.Reshape((config.image_size, config.image_size, 1))(plane)
        x = layers.Concatenate()([image, plane])

    for filters in (64, 128):
        x = layers.Conv2D(filters, 5, strides=2, padding="same")(x)
        x = layers.LeakyReLU(0.2)(x)
        x = layers.Dropout(0.3)(x)

    x = layers.Flatten()(x)
    logit = layers.Dense(1)(x)
    return tf.keras.Model(inputs, logit, name="discriminator")


def train(
    images: np.ndarray,
    labels: np.ndarray | None,
    config: GanConfig,
    seed: int = 0,
    log_every: int = 50,
) -> tuple[object, dict]:
    """Train the DCGAN on images scaled to [-1, 1]. Returns (generator, losses)."""
    import tensorflow as tf

    if images.ndim != 4 or images.shape[1:3] != (config.image_size, config.image_size):
        raise ValueError(
            f"expected images of shape (n, {config.image_size}, {config.image_size}, 3), "
            f"got {images.shape}"
        )
    if config.conditional and labels is None:
        raise ValueError("conditional=True requires labels")
    if len(images) < config.batch_size:
        log.warning(
            "only %d training images for a batch size of %d; the discriminator "
            "will see every image in nearly every batch",
            len(images),
            config.batch_size,
        )

    tf.keras.utils.set_random_seed(seed)
    generator = build_generator(config)
    discriminator = build_discriminator(config)
    g_optimizer = tf.keras.optimizers.Adam(config.generator_lr, beta_1=0.5)
    d_optimizer = tf.keras.optimizers.Adam(config.discriminator_lr, beta_1=0.5)
    loss_fn = tf.keras.losses.BinaryCrossentropy(from_logits=True)

    if labels is None:
        labels = np.zeros(len(images), dtype="int32")
    dataset = (
        tf.data.Dataset.from_tensor_slices(
            (images.astype("float32"), labels.astype("int32"))
        )
        .shuffle(len(images), seed=seed)
        .batch(config.batch_size, drop_remainder=False)
        .prefetch(tf.data.AUTOTUNE)
    )

    @tf.function
    def step(real_images, real_labels):
        batch = tf.shape(real_images)[0]
        noise = tf.random.normal([batch, config.noise_dim])
        fake_labels = (
            real_labels
            if config.conditional
            else tf.zeros([batch], dtype=tf.int32)
        )
        g_inputs = [noise, tf.expand_dims(fake_labels, -1)] if config.conditional else noise

        with tf.GradientTape() as g_tape, tf.GradientTape() as d_tape:
            fake_images = generator(g_inputs, training=True)
            d_real_in = (
                [real_images, tf.expand_dims(real_labels, -1)]
                if config.conditional
                else real_images
            )
            d_fake_in = (
                [fake_images, tf.expand_dims(fake_labels, -1)]
                if config.conditional
                else fake_images
            )
            real_logits = discriminator(d_real_in, training=True)
            fake_logits = discriminator(d_fake_in, training=True)

            # One-sided label smoothing on the real target only: it slows the
            # discriminator's win over a 29-image training set.
            real_target = tf.ones_like(real_logits) * (1.0 - config.label_smoothing)
            d_loss = loss_fn(real_target, real_logits) + loss_fn(
                tf.zeros_like(fake_logits), fake_logits
            )
            g_loss = loss_fn(tf.ones_like(fake_logits), fake_logits)

        g_optimizer.apply_gradients(
            zip(g_tape.gradient(g_loss, generator.trainable_variables), generator.trainable_variables)
        )
        d_optimizer.apply_gradients(
            zip(
                d_tape.gradient(d_loss, discriminator.trainable_variables),
                discriminator.trainable_variables,
            )
        )
        return g_loss, d_loss

    losses: dict[str, list[float]] = {"generator": [], "discriminator": []}
    for epoch in range(config.epochs):
        g_total, d_total, batches = 0.0, 0.0, 0
        for real_images, real_labels in dataset:
            g_loss, d_loss = step(real_images, real_labels)
            g_total += float(g_loss)
            d_total += float(d_loss)
            batches += 1
        losses["generator"].append(g_total / max(batches, 1))
        losses["discriminator"].append(d_total / max(batches, 1))
        if (epoch + 1) % log_every == 0:
            log.info(
                "epoch %d/%d  g_loss=%.4f  d_loss=%.4f",
                epoch + 1,
                config.epochs,
                losses["generator"][-1],
                losses["discriminator"][-1],
            )

    return generator, losses


def generate(
    generator, n_per_class: int, config: GanConfig, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Sample synthetic images in [0, 1] with their conditioning labels."""
    import tensorflow as tf

    tf.random.set_seed(seed)
    images, labels = [], []
    for label in range(len(CLASSES)):
        noise = tf.random.normal([n_per_class, config.noise_dim])
        if config.conditional:
            condition = tf.fill([n_per_class, 1], label)
            batch = generator([noise, condition], training=False)
        else:
            batch = generator(noise, training=False)
        images.append((batch.numpy() + 1.0) / 2.0)
        labels.append(np.full(n_per_class, label, dtype=int))
    return np.concatenate(images), np.concatenate(labels)


def save_synthetic(
    images: np.ndarray, labels: np.ndarray, out_dir: Path
) -> list[dict]:
    """Write synthetic images to disk and return rows for the training frame.

    Filenames carry the conditioning label, and each row is marked
    `is_synthetic` so synthetic data can never silently enter a test split.
    """
    from PIL import Image

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, (image, label) in enumerate(zip(images, labels)):
        name = f"synthetic_{CLASSES[int(label)]}_{index:05d}.jpg"
        path = out_dir / name
        Image.fromarray((np.clip(image, 0.0, 1.0) * 255).astype("uint8")).save(path)
        rows.append(
            {
                "image_id": name.removesuffix(".jpg"),
                # A synthetic image belongs to no real lesion. Giving it a unique
                # lesion_id keeps the leakage check meaningful.
                "lesion_id": f"SYNTH_{index:05d}",
                "dx": CLASSES[int(label)],
                "label": int(label),
                "image_path": str(path),
                "split": "train",
                "is_synthetic": True,
            }
        )
    log.info("wrote %d synthetic images to %s", len(rows), out_dir)
    return rows


def nearest_neighbour_distances(
    synthetic: np.ndarray, real: np.ndarray
) -> dict:
    """Distance from each synthetic image to its closest real training image.

    A memorising generator trained on 29 images produces near copies, which
    would make synthetic augmentation a slow form of duplication rather than new
    data. Reported in place of FID, which is not meaningful at this sample size.
    """
    flat_synthetic = synthetic.reshape(len(synthetic), -1)
    flat_real = real.reshape(len(real), -1)
    # Rescale real images from [-1, 1] to [0, 1] to match generate()'s output.
    if flat_real.min() < 0:
        flat_real = (flat_real + 1.0) / 2.0

    minimums = []
    for i in range(0, len(flat_synthetic), 256):
        chunk = flat_synthetic[i : i + 256]
        distances = np.linalg.norm(chunk[:, None, :] - flat_real[None, :, :], axis=2)
        minimums.append(distances.min(axis=1))
    minimums = np.concatenate(minimums)

    return {
        "n_synthetic": int(len(synthetic)),
        "n_real": int(len(real)),
        "mean_nn_distance": round(float(minimums.mean()), 4),
        "min_nn_distance": round(float(minimums.min()), 4),
        "p05_nn_distance": round(float(np.quantile(minimums, 0.05)), 4),
        "note": (
            "L2 distance in pixel space, images in [0, 1]. Small values mean the "
            "generator is reproducing its training images."
        ),
    }
