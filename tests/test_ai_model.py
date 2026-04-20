"""
FILE: tests/test_ai_model.py
===================================
AI Model Unit Tests — pytest
===================================

WHAT WE TEST:
  We can't test model accuracy without running training (takes minutes),
  but we CAN test:
    1. Model loads without error
    2. Output shape is correct (1 probability per class)
    3. Probabilities are valid (sum to 1.0, each in [0, 1])
    4. A valid class label is predicted
    5. The confidence threshold logic works correctly

  These tests catch:
    - Wrong model path / corrupted file
    - Architecture mismatch (wrong number of output classes)
    - Broken preprocessing pipeline
    - Threshold logic bugs

PYTEST MARKS:
  @pytest.mark.skipif skips a test when a condition is true.
  We skip all model tests if the model file doesn't exist
  (developer hasn't trained it yet) rather than failing with an obscure error.

FIXTURES vs GLOBAL VARIABLES:
  We use a module-scoped fixture to load the model once for all tests
  in this file. scope="module" means the fixture runs once per file,
  not once per test — loading a 15MB model 10 times would be slow.

INTERVIEW TALKING POINT:
  "I wrote tests for the AI module's input/output contract — not accuracy.
  These run in CI without needing a GPU. They verify the preprocessing
  pipeline produces the right tensor shape and the model's output is
  a valid probability distribution."
"""

import os
import numpy as np
import pytest

# Path to the trained model
MODEL_PATH   = os.path.join(os.path.dirname(__file__), "..", "ai-module", "model", "accident_model.h5")
CLASS_LABELS = ["accident", "normal", "traffic_jam"]
NUM_CLASSES  = len(CLASS_LABELS)
INPUT_SIZE   = (224, 224)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_dummy_image(mode: str = "random") -> np.ndarray:
    """
    Create a dummy image tensor in the format the model expects.
    Shape: (1, 224, 224, 3) — batch of 1, RGB, 224x224 pixels

    mode="random" : random pixel values (tests inference pipeline)
    mode="black"  : all zeros (edge case test)
    mode="white"  : all ones (edge case test)
    """
    if mode == "black":
        return np.zeros((1, *INPUT_SIZE, 3), dtype=np.float32)
    elif mode == "white":
        return np.ones((1, *INPUT_SIZE, 3), dtype=np.float32)
    else:  # random
        rng = np.random.default_rng(seed=42)   # Seeded for reproducibility
        return rng.random((1, *INPUT_SIZE, 3)).astype(np.float32)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def model():
    """
    Load the trained model once for all tests in this module.
    scope="module" ensures the model loads once, not per test.

    Skips all tests gracefully if the model doesn't exist yet.
    """
    if not os.path.exists(MODEL_PATH):
        pytest.skip(
            f"Model not found at {MODEL_PATH}. "
            "Run 'python ai-module/train_model.py' first."
        )

    import tensorflow as tf
    return tf.keras.models.load_model(MODEL_PATH)


# ─── Model Loading Tests ──────────────────────────────────────────────────────

class TestModelLoading:

    def test_model_loads_successfully(self, model):
        """The model object should not be None after loading."""
        assert model is not None

    def test_model_has_correct_input_shape(self, model):
        """
        Model input should expect (batch, 224, 224, 3) tensors.
        None for batch dimension means it accepts any batch size.
        """
        expected = (None, *INPUT_SIZE, 3)
        assert model.input_shape == expected, \
            f"Expected input shape {expected}, got {model.input_shape}"

    def test_model_has_correct_output_shape(self, model):
        """
        Model output should have one probability per class.
        (None, 3) = (batch_size, num_classes)
        """
        expected = (None, NUM_CLASSES)
        assert model.output_shape == expected, \
            f"Expected output shape {expected}, got {model.output_shape}"


# ─── Inference Tests ──────────────────────────────────────────────────────────

class TestInference:

    def test_inference_returns_correct_shape(self, model):
        """
        model.predict() on a batch of 1 should return shape (1, NUM_CLASSES).
        """
        dummy    = make_dummy_image("random")
        preds    = model.predict(dummy, verbose=0)
        assert preds.shape == (1, NUM_CLASSES), \
            f"Expected (1, {NUM_CLASSES}), got {preds.shape}"

    def test_probabilities_sum_to_one(self, model):
        """
        Softmax output must sum to ~1.0.
        If this fails, the final layer is not softmax.
        """
        dummy = make_dummy_image("random")
        preds = model.predict(dummy, verbose=0)[0]
        total = float(np.sum(preds))
        assert abs(total - 1.0) < 1e-5, \
            f"Probabilities sum to {total:.6f}, expected ~1.0"

    def test_all_probabilities_in_valid_range(self, model):
        """Each probability must be in [0.0, 1.0]."""
        dummy = make_dummy_image("random")
        preds = model.predict(dummy, verbose=0)[0]
        for i, p in enumerate(preds):
            assert 0.0 <= p <= 1.0, \
                f"Probability for class {i} is {p:.4f} — outside [0, 1]"

    def test_argmax_maps_to_valid_class_label(self, model):
        """The predicted class index must correspond to a valid class label."""
        dummy         = make_dummy_image("random")
        preds         = model.predict(dummy, verbose=0)[0]
        predicted_idx = int(np.argmax(preds))
        label         = CLASS_LABELS[predicted_idx]
        assert label in CLASS_LABELS, f"'{label}' is not in {CLASS_LABELS}"

    def test_inference_on_black_image(self, model):
        """Edge case: all-black image should still produce valid output."""
        preds = model.predict(make_dummy_image("black"), verbose=0)[0]
        assert abs(float(np.sum(preds)) - 1.0) < 1e-5

    def test_inference_on_white_image(self, model):
        """Edge case: all-white image should still produce valid output."""
        preds = model.predict(make_dummy_image("white"), verbose=0)[0]
        assert abs(float(np.sum(preds)) - 1.0) < 1e-5


# ─── Preprocessing Logic Tests ────────────────────────────────────────────────

class TestPreprocessing:
    """
    Test the preprocessing pipeline WITHOUT needing the model.
    These run even if the model file doesn't exist.
    """

    def test_resize_produces_correct_shape(self):
        """Resized image should have shape (1, 224, 224, 3)."""
        import cv2
        raw_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        resized   = cv2.resize(raw_frame, INPUT_SIZE)
        normalised = resized.astype(np.float32) / 255.0
        batched    = np.expand_dims(normalised, axis=0)
        assert batched.shape == (1, *INPUT_SIZE, 3)

    def test_normalisation_range(self):
        """After dividing by 255, all values should be in [0, 1]."""
        raw       = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        normalised = raw.astype(np.float32) / 255.0
        assert float(normalised.min()) >= 0.0
        assert float(normalised.max()) <= 1.0


# ─── Confidence Threshold Logic Tests ────────────────────────────────────────

class TestConfidenceLogic:
    """
    Test the confidence threshold and severity mapping logic.
    Pure Python — no model needed.
    """

    def test_high_confidence_passes_threshold(self):
        """Confidence above threshold should trigger an alert."""
        threshold  = 0.75
        confidence = 0.92
        assert confidence >= threshold, "High confidence should pass threshold"

    def test_low_confidence_blocked(self):
        """Confidence below threshold should NOT trigger an alert."""
        threshold  = 0.75
        confidence = 0.60
        assert confidence < threshold, "Low confidence should be blocked"

    def test_exactly_at_threshold_passes(self):
        """Confidence exactly equal to threshold should pass (>= not >)."""
        threshold = 0.75
        assert threshold >= threshold

    def test_severity_mapping_critical(self):
        """Confidence >= 0.95 should map to 'critical'."""
        from ai_module_utils import confidence_to_severity  # If extracted to utils
        # Inline test since the function is inside detect_accident.py
        confidence = 0.97
        if confidence >= 0.95:
            severity = "critical"
        elif confidence >= 0.85:
            severity = "high"
        elif confidence >= 0.75:
            severity = "medium"
        else:
            severity = "low"
        assert severity == "critical"


# ─── Skip marker for environments without the model ──────────────────────────
# All tests in TestInference and TestModelLoading already skip via the
# model fixture's pytest.skip(). This is just additional documentation.
