"""
FILE: ai-module/generate_test_model.py
============================================
Generate a Minimal Test Model (No Training Data Required)
============================================

This script creates a valid, loadable model directory with RANDOM WEIGHTS,
laid out exactly the way train_model.py lays out a real one:

    model/<TIMESTAMP>/
    ├── accident_model.keras     ← model file (random weights)
    ├── class_metadata.json      ← class mapping (required by detect_accident.py)
    └── model.sha256             ← checksum (required for integrity verification)

It is useful for:
  - Testing the inference pipeline shape and format
  - Running tests/test_ai_model.py without a trained model
  - CI/CD pipelines that need a model present but can't afford to train one

Note: detect_accident.py's _find_latest_model_dir() only recognises a model
directory if it contains class_metadata.json, so this script produces the
same layout train_model.py does.

The model predictions will be RANDOM (not meaningful).
For real accident detection, run train_model.py with actual dataset images.

Usage:
    cd ai-module
    python generate_test_model.py
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

logger.info("Generating minimal test model for accident detection")

try:
    import tensorflow as tf
    logger.info("TensorFlow %s found", tf.__version__)
except ImportError:
    logger.error("TensorFlow not installed.")
    logger.error("Install it with: pip install tensorflow==2.16.1")
    sys.exit(1)

from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import (
    Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
)
from tensorflow.keras.models import Model

# ── Layout matches train_model.py's output exactly ───────────────────────────
CLASS_LABELS = ["accident", "normal", "traffic_jam"]   # alphabetical, like
                                                        # image_dataset_from_directory
IMG_SIZE     = (224, 224)

MODEL_BASE   = os.path.join(os.path.dirname(__file__), "model")
TIMESTAMP    = datetime.now().strftime("%Y%m%d_%H%M%S")
MODEL_DIR    = os.path.join(MODEL_BASE, TIMESTAMP)
MODEL_PATH   = os.path.join(MODEL_DIR, "accident_model.keras")
META_PATH    = os.path.join(MODEL_DIR, "class_metadata.json")
CHECKSUM_PATH = os.path.join(MODEL_DIR, "model.sha256")

os.makedirs(MODEL_DIR, exist_ok=True)

logger.info("Building MobileNetV2 model (random weights, no ImageNet)...")

# Build the SAME architecture as train_model.py
# weights=None → random initialisation (no ImageNet download needed)
base = MobileNetV2(
    weights      = None,           # No pretrained weights — this is just for testing
    include_top  = False,
    input_shape  = (*IMG_SIZE, 3),
)
base.trainable = False

x   = GlobalAveragePooling2D()(base.output)
x   = BatchNormalization()(x)
x   = Dense(256, activation="relu")(x)
x   = Dropout(0.3)(x)
out = Dense(len(CLASS_LABELS), activation="softmax")(x)

model = Model(inputs=base.input, outputs=out)

model.compile(
    optimizer = "adam",
    loss      = "categorical_crossentropy",
    metrics   = ["accuracy"],
)

# ── Save the model ────────────────────────────────────────────────────────
model.save(MODEL_PATH)
size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)

# ── Save class_metadata.json (required by detect_accident.py's loader) ────
metadata = {
    "class_indices":      {name: idx for idx, name in enumerate(CLASS_LABELS)},
    "idx_to_class":        {str(idx): name for idx, name in enumerate(CLASS_LABELS)},
    "num_classes":         len(CLASS_LABELS),
    "img_size":            list(IMG_SIZE),
    "preprocessing":       "mobilenet_v2.preprocess_input — maps [0,255] to [-1,1]",
    "color_format":        "RGB",
    "train_samples":       0,
    "val_samples":         0,
    "tensorflow_version":  tf.__version__,
    "python_version":      sys.version.split()[0],
    "trained_at":          datetime.now().isoformat(),
    "note":                "TEST MODEL — random weights, not trained on real data.",
}
with open(META_PATH, "w") as fh:
    json.dump(metadata, fh, indent=2)

# ── Save SHA-256 checksum (required for verify_model_checksum) ────────────
sha256 = hashlib.sha256()
with open(MODEL_PATH, "rb") as fh:
    for chunk in iter(lambda: fh.read(65536), b""):
        sha256.update(chunk)
with open(CHECKSUM_PATH, "w") as fh:
    fh.write(sha256.hexdigest())

logger.info("Test model saved!")
logger.info("Model dir: %s", MODEL_DIR)
logger.info("File size: %.1f MB", size_mb)
logger.info("Input shape: %s", model.input_shape)
logger.info("Output shape: %s", model.output_shape)
logger.info("Parameters: %s", f"{model.count_params():,}")
logger.info("Class metadata: %s", META_PATH)
logger.info("Checksum: %s", CHECKSUM_PATH)
logger.warning("This model has RANDOM weights — predictions are meaningless.")
logger.warning("Run train_model.py with real dataset images for actual detection.")