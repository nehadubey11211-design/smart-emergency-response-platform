"""
FILE: ai-module/generate_test_model.py
============================================
Generate a Minimal Test Model (No Training Data Required)
============================================

This script creates a valid accident_model.h5 file with RANDOM WEIGHTS.
It is useful for:
  - Testing the inference pipeline shape and format
  - Running test_ai_model.py without a trained model
  - CI/CD pipelines that need a model file present

The model predictions will be RANDOM (not meaningful).
For real accident detection, run train_model.py with actual dataset images.

Usage:
    cd ai-module
    python generate_test_model.py
"""

import logging
import os
import sys

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

MODEL_DIR  = os.path.join(os.path.dirname(__file__), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "accident_model.h5")
os.makedirs(MODEL_DIR, exist_ok=True)

logger.info("Building MobileNetV2 model (random weights, no ImageNet)...")

# Build the SAME architecture as train_model.py
# weights=None → random initialisation (no ImageNet download needed)
base = MobileNetV2(
    weights      = None,           # No pretrained weights — this is just for testing
    include_top  = False,
    input_shape  = (224, 224, 3),
)
base.trainable = False

x   = GlobalAveragePooling2D()(base.output)
x   = BatchNormalization()(x)
x   = Dense(256, activation="relu")(x)
x   = Dropout(0.3)(x)
out = Dense(3, activation="softmax")(x)    # 3 classes: accident|normal|traffic_jam

model = Model(inputs=base.input, outputs=out)

model.compile(
    optimizer = "adam",
    loss      = "categorical_crossentropy",
    metrics   = ["accuracy"],
)

# Save the model
model.save(MODEL_PATH)
size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)

logger.info("Test model saved!")
logger.info("Path: %s", MODEL_PATH)
logger.info("File size: %.1f MB", size_mb)
logger.info("Input shape: %s", model.input_shape)
logger.info("Output shape: %s", model.output_shape)
logger.info("Parameters: %s", f"{model.count_params():,}")
logger.warning("This model has RANDOM weights — predictions are meaningless.")
logger.warning("Run train_model.py with real dataset images for actual detection.")
