"""
FILE: ai-module/train_model.py
=====================================
CNN Model Training — MobileNetV2 Transfer Learning
=====================================

TRANSFER LEARNING EXPLAINED:
  Training a CNN from scratch needs millions of images and weeks of compute.
  Transfer learning reuses a model pretrained on a large dataset (ImageNet,
  which has 1.2M images across 1000 classes).

  The pretrained model has already learned low-level features:
    Layer 1-10:  edges, corners, gradients
    Layer 11-50: textures, patterns
    Layer 51+:   high-level features (wheels, road markings, etc.)

  We:
    1. Keep all these pretrained layers (freeze them — don't update weights)
    2. Remove the original 1000-class head
    3. Add our own classification head (3 classes: accident/normal/traffic_jam)
    4. Train ONLY our new head (fast — only a few thousand parameters)
    5. Optionally "fine-tune" by unfreezing the top layers and training slowly

DATASET STRUCTURE:
  dataset/
    accident/      ← Images of road accidents
    normal/        ← Normal traffic images
    traffic_jam/   ← Traffic jam images (without accidents)

  Aim for at least 200+ images per class for reasonable accuracy.
  More is better — 1000+ per class for production quality.

WHY MOBILENETV2?
  - Designed for mobile/edge devices with limited compute
  - 3.4M parameters vs ResNet50's 25M
  - Still achieves ~72% top-1 accuracy on ImageNet
  - Runs inference in ~30ms on CPU — fast enough for real-time use

DATA AUGMENTATION:
  We artificially expand the training set by randomly transforming images:
    - Random rotation ±15°
    - Horizontal flip (a left-side crash is still a crash)
    - Width/height shift (simulate camera angle variation)
  This prevents overfitting to specific image compositions.

INTERVIEW TALKING POINT:
  "I used transfer learning with MobileNetV2 because collecting thousands
  of labelled accident images is expensive. By reusing ImageNet weights,
  I achieved good accuracy with only ~500 images per class.
  The two-phase training (frozen base → fine-tune) is standard practice."
"""

import os
import sys

import numpy as np

# Lazy import of TensorFlow — avoids slow startup if just checking args
try:
    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import (
        Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
    )
    from tensorflow.keras.models import Model
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import (
        ModelCheckpoint, EarlyStopping, ReduceLROnPlateau, TensorBoard
    )
except ImportError:
    print("❌ TensorFlow not found. Run: pip install tensorflow")
    sys.exit(1)


# ─── Configuration ────────────────────────────────────────────────────────────

DATASET_DIR   = os.path.join(os.path.dirname(__file__), "dataset")
MODEL_DIR     = os.path.join(os.path.dirname(__file__), "model")
MODEL_OUTPUT  = os.path.join(MODEL_DIR, "accident_model.h5")
LOG_DIR       = os.path.join(MODEL_DIR, "logs")     # TensorBoard logs

IMG_SIZE    = (224, 224)   # MobileNetV2's native input size
BATCH_SIZE  = 32           # Larger batches = faster but more GPU memory needed
EPOCHS_HEAD = 20           # Phase 1: train only the classification head
EPOCHS_FINE = 10           # Phase 2: fine-tune top layers
NUM_CLASSES = 3            # accident | normal | traffic_jam
SEED        = 42           # For reproducibility


# ─── Data Pipeline ────────────────────────────────────────────────────────────

def build_data_generators():
    """
    Create training and validation data generators.

    ImageDataGenerator handles:
      1. Loading images from disk in batches (memory-efficient)
      2. Resizing to IMG_SIZE automatically
      3. Applying random augmentations (training only)
      4. One-hot encoding labels for categorical_crossentropy

    validation_split=0.2 means 80% of images go to training,
    20% to validation (used to monitor generalisation, not for training).
    """
    # Augmentation parameters for training data
    # validation data gets ONLY rescaling — no augmentation (would corrupt evaluation)
    train_datagen = ImageDataGenerator(
        rescale           = 1.0 / 255,   # Normalise pixel values to [0, 1]
        rotation_range    = 15,           # Random rotation ±15°
        width_shift_range = 0.1,          # Shift image horizontally ±10%
        height_shift_range= 0.1,          # Shift image vertically ±10%
        horizontal_flip   = True,         # Random horizontal mirror
        zoom_range        = 0.1,          # Random zoom ±10%
        brightness_range  = [0.8, 1.2],   # Random brightness variation
        validation_split  = 0.2,
    )

    # Load training images from disk
    train_gen = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size  = IMG_SIZE,
        batch_size   = BATCH_SIZE,
        class_mode   = "categorical",    # One-hot encoded labels
        subset       = "training",
        seed         = SEED,
        shuffle      = True,
    )

    # Load validation images (no augmentation)
    val_gen = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size  = IMG_SIZE,
        batch_size   = BATCH_SIZE,
        class_mode   = "categorical",
        subset       = "validation",
        seed         = SEED,
        shuffle      = False,            # Keep order for consistent evaluation
    )

    return train_gen, val_gen


# ─── Model Architecture ───────────────────────────────────────────────────────

def build_model() -> Model:
    """
    Build the transfer learning model.

    Architecture:
      MobileNetV2 (frozen, pretrained on ImageNet)
        → GlobalAveragePooling2D  (reduce spatial dims: (7,7,1280) → (1280,))
        → BatchNormalization      (stabilise activations, speeds training)
        → Dense(256, ReLU)        (learn task-specific features)
        → Dropout(0.3)            (regularisation — prevent overfitting)
        → Dense(NUM_CLASSES, Softmax) (output: probability per class)

    GlobalAveragePooling2D vs Flatten:
      Flatten: (7,7,1280) → 62720 neurons → huge, prone to overfitting
      GAP:     (7,7,1280) → 1280 neurons  → smaller, more regularised
    """
    # Load MobileNetV2 pretrained on ImageNet.
    # include_top=False removes the original 1000-class classifier.
    # weights="imagenet" downloads pretrained weights on first run (~14MB).
    base_model = MobileNetV2(
        weights      = "imagenet",
        include_top  = False,
        input_shape  = (*IMG_SIZE, 3),   # (224, 224, 3)
    )

    # Freeze all base model layers — their weights won't change during Phase 1
    base_model.trainable = False
    print(f"📦 Base model: {base_model.name} | Layers: {len(base_model.layers)} (all frozen)")

    # Build our classification head on top
    x = base_model.output
    x = GlobalAveragePooling2D()(x)           # (None, 1280)
    x = BatchNormalization()(x)               # Normalise activations
    x = Dense(256, activation="relu")(x)      # Task-specific feature extractor
    x = Dropout(0.3)(x)                       # Regularisation: randomly zero 30%
    output = Dense(NUM_CLASSES, activation="softmax")(x)  # (None, 3)

    model = Model(inputs=base_model.input, outputs=output)

    trainable_params = sum(
        [tf.keras.backend.count_params(w) for w in model.trainable_weights]
    )
    print(f"🧠 Trainable parameters (Phase 1): {trainable_params:,}")

    return model,base_model


# ─── Training Callbacks ───────────────────────────────────────────────────────

def build_callbacks(phase: int) -> list:
    """
    Callbacks are functions called at specific training events (end of epoch, etc.)

    ModelCheckpoint: Save the model weights whenever validation accuracy improves.
      save_best_only=True means we ONLY save when it's better — not every epoch.
      This ensures the final saved model is the best one seen, even if later
      epochs overfit.

    EarlyStopping: Stop training if val_accuracy doesn't improve for N epochs.
      Prevents wasting time training after the model has peaked.
      restore_best_weights=True resets to the best epoch's weights on stop.

    ReduceLROnPlateau: Halve the learning rate if val_accuracy plateaus.
      Models often get "stuck" — reducing LR lets them escape local minima.

    TensorBoard: Log metrics for visualisation.
      Run: tensorboard --logdir ai-module/model/logs
    """
    return [
        ModelCheckpoint(
            filepath        = MODEL_OUTPUT,
            monitor         = "val_accuracy",
            save_best_only  = True,
            save_weights_only = False,  # Save full model (architecture + weights)
            verbose         = 1,
        ),
        EarlyStopping(
            monitor              = "val_accuracy",
            patience             = 5,               # Stop after 5 stagnant epochs
            restore_best_weights = True,
            verbose              = 1,
        ),
        ReduceLROnPlateau(
            monitor  = "val_loss",
            factor   = 0.5,    # Multiply LR by 0.5 (halve it)
            patience = 3,
            min_lr   = 1e-7,   # Don't go below this learning rate
            verbose  = 1,
        ),
        TensorBoard(
            log_dir           = os.path.join(LOG_DIR, f"phase{phase}"),
            histogram_freq    = 0,
            write_graph       = False,
        ),
    ]


# ─── Training Phases ──────────────────────────────────────────────────────────

def phase1_train_head(model, train_gen, val_gen) -> dict:
    """
    Phase 1: Train only the classification head.
    Base model layers are frozen — only head weights change.

    Higher learning rate (1e-3) is safe because we're only training the small head.
    """
    print("\n" + "═"*55)
    print("PHASE 1: Training classification head (base frozen)")
    print("═"*55)

    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"],
    )

    history = model.fit(
        train_gen,
        validation_data = val_gen,
        epochs          = EPOCHS_HEAD,
        callbacks       = build_callbacks(phase=1),
        verbose         = 1,
    )

    print(
        f"\n✅ Phase 1 complete. "
        f"Best val_accuracy: {max(history.history['val_accuracy']):.2%}"
    )
    return history.history


def phase2_fine_tune(model, base_model, train_gen, val_gen) -> dict:
    """
    Phase 2: Fine-tune the top layers of the base model.
    We unfreeze the last 30 layers and train with a very low learning rate.

    Why low LR (1e-5)?
      The pretrained weights are "good" — we want to gently nudge them
      toward our task, not overwrite them with random noise.
      Too high an LR here would destroy the pretrained features.
    """
    print("\n" + "═"*55)
    print("PHASE 2: Fine-tuning top layers of base model")
    print("═"*55)

   # base_model = model.layers[1]   # MobileNetV2 is the second layer (after Input)
    base_model.trainable = True
    print("DEBUG base_model type:", type(base_model))
    # Freeze everything EXCEPT the last 30 layers of the base model
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    fine_tune_params = sum(
        [tf.keras.backend.count_params(w) for w in model.trainable_weights]
    )
    print(f"🧠 Trainable parameters (Phase 2): {fine_tune_params:,}")

    # Recompile with a lower learning rate for fine-tuning
    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss      = "categorical_crossentropy",
        metrics   = ["accuracy"],
    )

    history = model.fit(
        train_gen,
        validation_data = val_gen,
        epochs          = EPOCHS_FINE,
        callbacks       = build_callbacks(phase=2),
        verbose         = 1,
    )

    print(
        f"\n✅ Phase 2 complete. "
        f"Best val_accuracy: {max(history.history['val_accuracy']):.2%}"
    )
    return history.history


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Starting model training pipeline")
    print(f"   Dataset:    {DATASET_DIR}")
    print(f"   Output:     {MODEL_OUTPUT}")
    print(f"   Image size: {IMG_SIZE}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   GPU available: {len(tf.config.list_physical_devices('GPU')) > 0}")

    # ── Validate dataset ─────────────────────────────────────────────────
    if not os.path.exists(DATASET_DIR):
        print(f"\n❌ Dataset directory not found: {DATASET_DIR}")
        print("   Create it and add image subdirectories:")
        for cls in ["accident", "normal", "traffic_jam"]:
            print(f"     dataset/{cls}/  ← add images here")
        sys.exit(1)

    classes_found = [
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ]
    print(f"\n📂 Found {len(classes_found)} class folders: {sorted(classes_found)}")

    if len(classes_found) < 2:
        print("❌ Need at least 2 class folders with images")
        sys.exit(1)

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(LOG_DIR,   exist_ok=True)

    # ── Build data generators ────────────────────────────────────────────
    train_gen, val_gen = build_data_generators()

    # Print label → index mapping (CRITICAL: save this for inference!)
    print(f"\n🏷  Class indices: {train_gen.class_indices}")
    print("   ⚠️  Make sure CLASS_LABELS in detect_accident.py matches this order!")

    # ── Build model ──────────────────────────────────────────────────────
    model, base_model = build_model()

    # ── Phase 1: Train head ──────────────────────────────────────────────
    phase1_train_head(model, train_gen, val_gen)

    # ── Phase 2: Fine-tune ───────────────────────────────────────────────
    phase2_fine_tune(model, base_model ,train_gen, val_gen)

    # ── Evaluate ─────────────────────────────────────────────────────────
    print("\n📊 Final evaluation on validation set:")
    loss, accuracy = model.evaluate(val_gen, verbose=0)
    print(f"   Loss:     {loss:.4f}")
    print(f"   Accuracy: {accuracy:.2%}")

    print(f"\n✅ Training complete. Model saved to: {MODEL_OUTPUT}")
    print("   Next steps:")
    print("   1. Run: python detect_accident.py")
    print("   2. Or: tensorboard --logdir model/logs  (visualise training)")


if __name__ == "__main__":
    main()
