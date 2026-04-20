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

import os
import sys

print("=" * 55)
print("Generating minimal test model for accident detection")
print("=" * 55)

try:
    import tensorflow as tf
    print(f"✅ TensorFlow {tf.__version__} found")
except ImportError:
    print("❌ TensorFlow not installed.")
    print("   Install it with: pip install tensorflow==2.16.1")
    sys.exit(1)

from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import (
    Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
)
from tensorflow.keras.models import Model

MODEL_DIR  = os.path.join(os.path.dirname(__file__), "model")
MODEL_PATH = os.path.join(MODEL_DIR, "accident_model.h5")
os.makedirs(MODEL_DIR, exist_ok=True)

print("\n⏳ Building MobileNetV2 model (random weights, no ImageNet)...")

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

print(f"\n✅ Test model saved!")
print(f"   Path:          {MODEL_PATH}")
print(f"   File size:     {size_mb:.1f} MB")
print(f"   Input shape:   {model.input_shape}")
print(f"   Output shape:  {model.output_shape}")
print(f"   Parameters:    {model.count_params():,}")
print(f"\n⚠️  This model has RANDOM weights — predictions are meaningless.")
print(f"   Run train_model.py with real dataset images for actual detection.")
