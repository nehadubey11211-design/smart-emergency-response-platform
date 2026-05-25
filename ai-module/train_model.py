"""
FILE: ai-module/train_model.py
================================================================================
CNN Model Training — MobileNetV2 Transfer Learning (Deployment-Ready)
================================================================================

PROCESS OVERVIEW:
  This script trains a 3-class image classifier (accident / normal / traffic_jam)
  using MobileNetV2 as a frozen feature extractor, then fine-tunes the top layers.

  PHASE 1 — Head training (base frozen):
    Only the custom classification head is trained. The MobileNetV2 base is
    completely frozen. A higher learning rate (1e-3) is used because only
    new weights are being learned. Runs for up to EPOCHS_HEAD epochs with
    early stopping on val_accuracy.

  PHASE 2 — Fine-tuning (top base layers unfrozen):
    Layers from FINE_TUNE_AT onwards in the base model are unfrozen.
    A much lower learning rate (1e-5) is used to avoid destroying the
    pre-trained ImageNet features. BatchNormalization layers are always
    kept frozen (inference mode) to preserve normalisation statistics.
    Runs for up to EPOCHS_FINE epochs with early stopping.

  OUTPUT:
    model/<TIMESTAMP>/
    ├── accident_model.keras     ← final trained model (Keras v3 format)
    ├── class_metadata.json      ← class mapping, img size, training stats
    ├── model.sha256             ← SHA-256 checksum of the .keras file
    └── logs/
        ├── phase1/              ← TensorBoard logs for phase 1
        └── phase2/              ← TensorBoard logs for phase 2

FILE PATH:
  smart-emergency-response-platform/
  └── ai-module/
      ├── train_model.py           ← this file
      ├── detect_accident.py
      └── dataset/
          ├── accident/            ← images of accidents
          ├── normal/              ← images of normal traffic
          └── traffic_jam/         ← images of traffic jams

DATASET REQUIREMENTS:
  - Each class must have its own subdirectory under dataset/
  - Minimum MIN_SAMPLES_PER_CLASS images per class (default: 50)
  - Images can be any size — they are resized to 224×224 at load time
  - Supported formats: .jpg, .jpeg, .png, .bmp

QUICK START:
  pip install tensorflow scikit-learn
  python train_model.py

TENSORBOARD (run in a separate terminal after training starts):
  tensorboard --logdir ai-module/model/<TIMESTAMP>/logs

WHY MOBILENETV2?
  MobileNetV2 was designed for mobile/edge deployment. At ~3.4M parameters
  it is much smaller than VGG16 (138M) or ResNet50 (25M), runs comfortably
  on CPU in real-time, and achieves strong accuracy on image classification
  tasks via ImageNet pre-training.

REPRODUCIBILITY:
  Seeds are set for Python, NumPy, and TensorFlow. TF_DETERMINISTIC_OPS=1
  enforces deterministic GPU ops (may slow training slightly on GPU).

"""

# ── Determinism — must be set before any other imports ───────────────────────
import os
os.environ["PYTHONHASHSEED"]        = "42"
os.environ["TF_DETERMINISTIC_OPS"]  = "1"

# ── Standard library ──────────────────────────────────────────────────────────
import hashlib
import json
import logging
import platform
import random
import sys
from datetime import datetime
from pathlib import Path

# ── Seed everything before numpy / tf import ──────────────────────────────────
random.seed(42)

import numpy as np
np.random.seed(42)

# ── Logging (configured before TF import so TF logs obey the level) ──────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── TensorFlow ────────────────────────────────────────────────────────────────
try:
    import tensorflow as tf
    tf.random.set_seed(42)

    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
    from tensorflow.keras.layers import (
        BatchNormalization, Dense, Dropout, GlobalAveragePooling2D,
    )
    from tensorflow.keras.models import Model
    from tensorflow.keras.regularizers import l2
    from tensorflow.keras.callbacks import (
        EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard,
    )
    from sklearn.utils.class_weight import compute_class_weight

except ImportError as exc:
    # Use print here — logging may not be fully initialised yet
    print(f"[ERROR] Missing dependency: {exc}")
    print("Run: pip install tensorflow scikit-learn")
    sys.exit(1)

# ── GPU memory growth (prevents OOM on shared-GPU hosts) ─────────────────────
for _gpu in tf.config.list_physical_devices("GPU"):
    tf.config.experimental.set_memory_growth(_gpu, True)

# ── Paths (resolved relative to this file — safe regardless of cwd) ──────────
_HERE        = Path(__file__).parent
DATASET_DIR  = _HERE / "dataset"
MODEL_BASE   = _HERE / "model"

# ── Hyperparameters ───────────────────────────────────────────────────────────
IMG_SIZE              = (224, 224)
BATCH_SIZE            = 32
EPOCHS_HEAD           = 20          # Phase 1: head-only training
EPOCHS_FINE           = 10          # Phase 2: fine-tuning
SEED                  = 42
FINE_TUNE_AT          = 100         # Unfreeze base layers from this index onward
VALIDATION_SPLIT      = 0.15        # 15 % of data held out for validation
MIN_SAMPLES_PER_CLASS = 50          # Training aborts if any class is below this
L2_REG                = 1e-4        # L2 regularisation on Dense layers
DROPOUT_RATE          = 0.5
DENSE_UNITS           = 256


# ══════════════════════════════════════════════════════════════════════════════
# Data pipeline
# ══════════════════════════════════════════════════════════════════════════════

def _validate_dataset(dataset_dir: Path, num_classes: int) -> None:
    """
    Abort early if the dataset is missing, has too few classes, or any class
    has fewer than MIN_SAMPLES_PER_CLASS images.  A clear error here is far
    better than a cryptic crash deep inside model.fit().
    """
    if not dataset_dir.exists():
        logger.error("Dataset directory not found: %s", dataset_dir)
        sys.exit(1)

    class_dirs = sorted([d for d in dataset_dir.iterdir() if d.is_dir()])
    logger.info("Found %d class folder(s): %s", len(class_dirs), [d.name for d in class_dirs])

    if len(class_dirs) < 2:
        logger.error("Need at least 2 class folders with images. Found: %d", len(class_dirs))
        sys.exit(1)

    low_classes = []
    for cls_dir in class_dirs:
        count = sum(
            1 for f in cls_dir.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        )
        logger.info("  Class %-20s → %d image(s)", cls_dir.name, count)
        if count < MIN_SAMPLES_PER_CLASS:
            low_classes.append((cls_dir.name, count))

    if low_classes:
        for name, count in low_classes:
            logger.error(
                "Class '%s' has only %d images (minimum: %d). "
                "Add more images or lower MIN_SAMPLES_PER_CLASS.",
                name, count, MIN_SAMPLES_PER_CLASS,
            )
        sys.exit(1)


def build_tf_datasets(dataset_dir: Path, model_dir: Path):
    """
    Build train and validation tf.data.Dataset pipelines using the modern
    tf.keras.utils.image_dataset_from_directory API (replaces the deprecated
    ImageDataGenerator).

    Augmentation is applied only to the training set using a Sequential
    augmentation model, which runs on the GPU when available — faster than
    CPU-based augmentation in ImageDataGenerator.

    Returns (train_ds, val_ds, class_names, metadata_dict).
    """
    logger.info("Building tf.data pipelines from: %s", dataset_dir)

    # ── Load raw datasets ─────────────────────────────────────────────────
    train_ds_raw = tf.keras.utils.image_dataset_from_directory(
        str(dataset_dir),
        validation_split=VALIDATION_SPLIT,
        subset="training",
        seed=SEED,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="categorical",
        shuffle=True,
    )

    val_ds_raw = tf.keras.utils.image_dataset_from_directory(
        str(dataset_dir),
        validation_split=VALIDATION_SPLIT,
        subset="validation",
        seed=SEED,
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        label_mode="categorical",
        shuffle=False,   # never shuffle validation
    )

    class_names = train_ds_raw.class_names
    logger.info("Class names (alphabetical order): %s", class_names)
    logger.info("Train batches: %d | Val batches: %d",
                len(train_ds_raw), len(val_ds_raw))

    # ── Augmentation layer (GPU-accelerated, training-only) ───────────────
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.05),
        tf.keras.layers.RandomZoom(0.1),
        tf.keras.layers.RandomTranslation(0.1, 0.1),
        tf.keras.layers.RandomBrightness(0.3),
        tf.keras.layers.RandomContrast(0.2),
    ], name="augmentation")

    # ── Preprocessing: MobileNetV2 expects [-1, 1] ────────────────────────
    def preprocess_train(images, labels):
        images = augmentation(images, training=True)
        images = preprocess_input(images)
        return images, labels

    def preprocess_val(images, labels):
        images = preprocess_input(images)
        return images, labels

    # ── Build optimised pipelines ─────────────────────────────────────────
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = (
        train_ds_raw
        .map(preprocess_train, num_parallel_calls=AUTOTUNE)
        .prefetch(AUTOTUNE)
    )
    val_ds = (
        val_ds_raw
        .map(preprocess_val, num_parallel_calls=AUTOTUNE)
        .cache()           # cache validation set — it never changes
        .prefetch(AUTOTUNE)
    )

    # ── Count samples for metadata ────────────────────────────────────────
    train_count = sum(1 for _ in train_ds_raw.unbatch())
    val_count   = sum(1 for _ in val_ds_raw.unbatch())
    logger.info("Train samples: %d | Val samples: %d", train_count, val_count)

    # ── Build and save metadata ───────────────────────────────────────────
    class_indices  = {name: idx for idx, name in enumerate(class_names)}
    idx_to_class   = {idx: name for idx, name in enumerate(class_names)}

    metadata = {
        "class_indices":    class_indices,
        "idx_to_class":     {str(k): v for k, v in idx_to_class.items()},
        "num_classes":      len(class_names),
        "img_size":         list(IMG_SIZE),
        "preprocessing":    "mobilenet_v2.preprocess_input — maps [0,255] to [-1,1]",
        "color_format":     "RGB",
        "train_samples":    train_count,
        "val_samples":      val_count,
        "tensorflow_version": tf.__version__,
        "python_version":   platform.python_version(),
        "trained_at":       datetime.now().isoformat(),
    }

    meta_path = model_dir / "class_metadata.json"
    with meta_path.open("w") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info("Class metadata saved: %s", meta_path)

    return train_ds, val_ds, class_names, metadata


# ══════════════════════════════════════════════════════════════════════════════
# Class weights
# ══════════════════════════════════════════════════════════════════════════════

def compute_weights(dataset_dir: Path, class_names: list) -> dict:
    """
    Compute per-class weights to correct for class imbalance.
    Reads label counts directly from directory file counts — avoids
    iterating the full tf.data pipeline (which can be slow).
    """
    counts = []
    for name in class_names:
        cls_dir = dataset_dir / name
        n = sum(
            1 for f in cls_dir.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        )
        counts.append(n)

    total    = sum(counts)
    all_y    = np.concatenate([
        np.full(count, idx) for idx, count in enumerate(counts)
    ])
    weights  = compute_class_weight("balanced", classes=np.arange(len(class_names)), y=all_y)
    cw       = {int(i): float(w) for i, w in enumerate(weights)}

    logger.info("Class weights (imbalance correction):")
    for idx, name in enumerate(class_names):
        logger.info("  [%d] %-20s count=%-5d weight=%.4f", idx, name, counts[idx], cw[idx])

    return cw


# ══════════════════════════════════════════════════════════════════════════════
# Model architecture
# ══════════════════════════════════════════════════════════════════════════════

def build_model(num_classes: int) -> tuple[Model, Model]:
    """
    Construct the transfer-learning model.

    Architecture:
      MobileNetV2 (ImageNet, frozen)
        → GlobalAveragePooling2D
        → BatchNormalization
        → Dense(256, relu, L2)
        → Dropout(0.5)
        → Dense(num_classes, softmax, L2)

    BatchNormalization after GAP stabilises training when the dense head
    is being trained on top of frozen features.

    Returns (full_model, base_model_reference) — base_model is needed
    separately so phase 2 can selectively unfreeze its layers.
    """
    base_model = MobileNetV2(
        weights="imagenet",
        include_top=False,
        input_shape=(*IMG_SIZE, 3),
    )
    base_model.trainable = False
    logger.info("Base: %s | Layers: %d | All frozen for Phase 1",
                base_model.name, len(base_model.layers))

    x      = base_model.output
    x      = GlobalAveragePooling2D()(x)
    x      = BatchNormalization()(x)
    x      = Dense(DENSE_UNITS, activation="relu", kernel_regularizer=l2(L2_REG))(x)
    x      = Dropout(DROPOUT_RATE)(x)
    output = Dense(num_classes, activation="softmax", kernel_regularizer=l2(L2_REG))(x)

    model = Model(inputs=base_model.input, outputs=output)

    total     = model.count_params()
    trainable = sum(int(np.prod(w.shape)) for w in model.trainable_weights)
    logger.info("Total params: %d | Trainable (Phase 1): %d", total, trainable)

    return model, base_model


# ══════════════════════════════════════════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════════════════════════════════════════

def build_callbacks(phase: int, model_dir: Path) -> list:
    """
    Build the callback list for a training phase.

    Both EarlyStopping and ReduceLROnPlateau monitor val_loss for consistency:
    - val_accuracy can plateau while val_loss still improves slightly
    - Monitoring the same metric avoids both callbacks firing simultaneously
      in confusing / counterproductive ways

    TensorBoard histogram_freq is set to 0 (disabled) — writing weight
    histograms every N epochs adds significant I/O overhead on CPU-only hosts.
    Enable manually for deep debugging: set histogram_freq=5.
    """
    checkpoint_path = str(model_dir / f"phase{phase}_best.keras")
    log_path        = str(model_dir / "logs" / f"phase{phase}")

    return [
        ModelCheckpoint(
            filepath=checkpoint_path,
            monitor="val_loss",       # save the epoch with lowest val_loss
            save_best_only=True,
            save_format="keras",
            verbose=1,
        ),
        EarlyStopping(
            monitor="val_loss",       # consistent with ModelCheckpoint
            patience=8,
            restore_best_weights=True,
            min_delta=1e-4,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",       # consistent with EarlyStopping
            factor=0.5,
            patience=3,
            min_lr=1e-7,
            verbose=1,
        ),
        TensorBoard(
            log_dir=log_path,
            histogram_freq=0,         # disabled by default — expensive on CPU
            write_graph=True,
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Training phases
# ══════════════════════════════════════════════════════════════════════════════

def phase1_train_head(
    model: Model,
    train_ds,
    val_ds,
    class_weights: dict,
    model_dir: Path,
) -> dict:
    """
    Phase 1: Train only the classification head while the MobileNetV2 base
    is completely frozen.  A higher learning rate is safe here because only
    the randomly-initialised head weights are being updated.
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: Training classification head (base frozen)")
    logger.info("  LR: 1e-3 | Max epochs: %d | Early stopping patience: 8", EPOCHS_HEAD)
    logger.info("=" * 60)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS_HEAD,
        callbacks=build_callbacks(phase=1, model_dir=model_dir),
        class_weight=class_weights,
        verbose=1,
    )

    best_val_loss = min(history.history["val_loss"])
    best_val_acc  = max(history.history["val_accuracy"])
    logger.info("Phase 1 complete | Best val_loss: %.4f | Best val_accuracy: %.2f%%",
                best_val_loss, best_val_acc * 100)
    return history.history


def phase2_fine_tune(
    model: Model,
    base_model: Model,
    train_ds,
    val_ds,
    class_weights: dict,
    model_dir: Path,
) -> dict:
    """
    Phase 2: Unfreeze the top layers of the MobileNetV2 base (from
    FINE_TUNE_AT onwards) and fine-tune with a much lower learning rate.

    BatchNormalization layers are ALWAYS kept frozen (trainable=False)
    regardless of their position in the network.  Unfreezing BN layers
    during fine-tuning corrupts the running mean/variance statistics that
    were accumulated on ImageNet, which destabilises training.

    IMPORTANT: model.compile() must be called AFTER changing layer
    trainability — otherwise TensorFlow does not recompute the gradient tape.
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: Fine-tuning top layers (from layer %d onward)", FINE_TUNE_AT)
    logger.info("  LR: 1e-5 | Max epochs: %d | Early stopping patience: 8", EPOCHS_FINE)
    logger.info("=" * 60)

    base_model.trainable = True
    frozen_count = 0
    for layer in base_model.layers:
        if base_model.layers.index(layer) < FINE_TUNE_AT:
            layer.trainable = False
            frozen_count += 1
        if isinstance(layer, BatchNormalization):
            layer.trainable = False    # always freeze BN regardless of position

    trainable = sum(int(np.prod(w.shape)) for w in model.trainable_weights)
    logger.info("Layers frozen: %d | Trainable params (Phase 2): %d",
                frozen_count, trainable)

    # compile AFTER changing trainability
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss="categorical_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS_FINE,
        callbacks=build_callbacks(phase=2, model_dir=model_dir),
        class_weight=class_weights,
        verbose=1,
    )

    best_val_loss = min(history.history["val_loss"])
    best_val_acc  = max(history.history["val_accuracy"])
    logger.info("Phase 2 complete | Best val_loss: %.4f | Best val_accuracy: %.2f%%",
                best_val_loss, best_val_acc * 100)
    return history.history


# ══════════════════════════════════════════════════════════════════════════════
# Checksum
# ══════════════════════════════════════════════════════════════════════════════

def save_checksum(model_path: Path, model_dir: Path) -> None:
    """
    Write a SHA-256 checksum of the saved .keras file for integrity
    verification on deployment.

    Note: This only works for single-file .keras format.  SavedModel
    format is a directory — checksum generation is skipped for directories.
    """
    if model_path.is_dir():
        logger.warning(
            "Model was saved as SavedModel directory — skipping SHA-256 checksum. "
            "Use .keras format for checksumming."
        )
        return

    if not model_path.exists():
        logger.error("Model file not found for checksumming: %s", model_path)
        return

    sha256 = hashlib.sha256()
    with model_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha256.update(chunk)

    checksum     = sha256.hexdigest()
    checksum_path = model_dir / "model.sha256"
    checksum_path.write_text(checksum)
    logger.info("SHA-256 checksum: %s", checksum)
    logger.info("Checksum saved:   %s", checksum_path)


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Full training pipeline:
      validate dataset → build data pipelines → build model →
      phase 1 head training → phase 2 fine-tuning →
      final evaluation → save model → save checksum
    """

    # ── Timestamp is created here (not at import time) ────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = MODEL_BASE / timestamp
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "logs").mkdir(parents=True, exist_ok=True)
    model_output = model_dir / "accident_model.keras"

    # ── Startup info ──────────────────────────────────────────────────────
    gpu_count = len(tf.config.list_physical_devices("GPU"))
    logger.info("=" * 60)
    logger.info("Smart Emergency Response — Model Training")
    logger.info("  TensorFlow : %s", tf.__version__)
    logger.info("  Python     : %s", platform.python_version())
    logger.info("  GPU(s)     : %d", gpu_count)
    logger.info("  Dataset    : %s", DATASET_DIR)
    logger.info("  Output     : %s", model_dir)
    logger.info("  Image size : %s", IMG_SIZE)
    logger.info("  Batch size : %d", BATCH_SIZE)
    logger.info("  Seed       : %d", SEED)
    logger.info("=" * 60)

    if gpu_count == 0:
        logger.warning(
            "No GPU detected — training on CPU. "
            "Phase 1 will take significantly longer."
        )

    # ── Validate dataset before doing any heavy work ──────────────────────
    _validate_dataset(DATASET_DIR, num_classes=None)

    # ── Build data pipelines ──────────────────────────────────────────────
    train_ds, val_ds, class_names, metadata = build_tf_datasets(DATASET_DIR, model_dir)
    num_classes = len(class_names)

    if num_classes < 2:
        logger.error("Need at least 2 classes. Found: %d", num_classes)
        sys.exit(1)

    logger.info("Training with %d class(es): %s", num_classes, class_names)

    # ── Build model ───────────────────────────────────────────────────────
    model, base_model = build_model(num_classes=num_classes)

    # Log model summary via logger (not print) so it appears in log files
    summary_lines: list[str] = []
    model.summary(print_fn=lambda line: summary_lines.append(line))
    for line in summary_lines:
        logger.info(line)

    # ── Class weights ─────────────────────────────────────────────────────
    class_weights = compute_weights(DATASET_DIR, class_names)

    # ── Phase 1 ───────────────────────────────────────────────────────────
    phase1_train_head(model, train_ds, val_ds, class_weights, model_dir)

    # ── Phase 2 ───────────────────────────────────────────────────────────
    phase2_fine_tune(model, base_model, train_ds, val_ds, class_weights, model_dir)

    # ── Final evaluation (fresh val_ds pass — no generator state issues) ──
    logger.info("Final evaluation on validation set:")
    results = model.evaluate(val_ds, verbose=1)
    for name, value in zip(model.metrics_names, results):
        logger.info("  %-20s %.4f", name, value)

    # ── Save model ────────────────────────────────────────────────────────
    model.save(str(model_output))
    logger.info("Model saved: %s", model_output)

    # ── Checksum ──────────────────────────────────────────────────────────
    save_checksum(model_output, model_dir)

    # ── Done ──────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Training complete.")
    logger.info("Next steps:")
    logger.info("  Run detector : python detect_accident.py")
    logger.info("  TensorBoard  : tensorboard --logdir %s", model_dir / "logs")
    logger.info("  Model dir    : %s", model_dir)
    logger.info("=" * 60)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
