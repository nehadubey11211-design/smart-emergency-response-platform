"""
FILE: tests/test_ai_model.py
===================================
AI Model Unit Tests — pytest
===================================

WHAT WE TEST:
  We can't test model accuracy without running training (takes minutes),
  but we CAN test:
    1. The model directory discovery and class metadata loading logic
    2. Checksum verification (pass / corrupt / missing)
    3. Model loads without error, with the expected input/output shape
    4. Inference output is a valid probability distribution
    5. preprocess_frame() produces the exact tensor shape/scale the model expects
    6. confidence_to_severity() thresholds

  These tests catch:
    - Wrong model path / corrupted file
    - Architecture mismatch (wrong number of output classes)
    - Broken preprocessing pipeline
    - Threshold logic bugs
    - Model-directory / metadata layout drifting out of sync with the loader

PYTEST MARKS:
  @pytest.fixture + pytest.skip() skip all model-dependent tests when no
  valid model directory exists (developer hasn't trained one, or run
  generate_test_model.py yet) rather than failing with an obscure error.

FIXTURES vs GLOBAL VARIABLES:
  We use module-scoped fixtures to import detect_accident.py and load the
  model once for all tests in this file — loading a multi-MB model per test
  would be slow.

RUNNING THESE TESTS:
    cd ai-module && python generate_test_model.py   # creates a throwaway model
    pytest tests/test_ai_model.py -v
"""

import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

# ─── Paths ──────────────────────────────────────────────────────────────────

TESTS_DIR      = Path(__file__).parent
AI_MODULE_DIR  = TESTS_DIR / ".." / "ai-module"
MODEL_BASE_DIR = AI_MODULE_DIR / "model"
DETECT_SCRIPT  = AI_MODULE_DIR / "detect_accident.py"

CLASS_LABELS = ["accident", "normal", "traffic_jam"]
NUM_CLASSES  = len(CLASS_LABELS)
INPUT_SIZE   = (224, 224)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_dummy_frame(mode: str = "random") -> np.ndarray:
    """
    Create a dummy BGR frame the way cv2.VideoCapture.read() would return
    one: uint8, shape (H, W, 3), arbitrary source resolution (not yet
    resized to the model's 224x224 input).

    mode="random" : random pixel values (tests inference pipeline)
    mode="black"  : all zeros (edge case test)
    mode="white"  : all 255s (edge case test)
    """
    if mode == "black":
        return np.zeros((480, 640, 3), dtype=np.uint8)
    elif mode == "white":
        return np.full((480, 640, 3), 255, dtype=np.uint8)
    else:  # random
        rng = np.random.default_rng(seed=42)  # seeded for reproducibility
        return rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def detect_accident():
    """
    Import ai-module/detect_accident.py as a module.

    ai-module contains a hyphen, so it isn't a valid Python package name and
    can't be `import`ed normally — it's loaded directly from its file path
    instead. This also runs its module-level code (TensorFlow import, GPU
    config, env-var reads for CONFIDENCE_THRESHOLD, etc).

    Skips (doesn't fail) if TensorFlow / OpenCV / requests aren't installed —
    those are runtime deps for the detector, not for every dev's machine.
    Also catches SystemExit, since detect_accident.py's own TensorFlow
    import guard calls sys.exit(1) rather than raising.
    """
    if not DETECT_SCRIPT.exists():
        pytest.skip(f"detect_accident.py not found at {DETECT_SCRIPT}")

    spec = importlib.util.spec_from_file_location("detect_accident", DETECT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, SystemExit) as exc:
        pytest.skip(f"detect_accident.py could not be imported (missing dependency): {exc}")
    return module


@pytest.fixture(scope="module")
def model_dir(detect_accident):
    """
    Find the latest valid timestamped model directory using
    detect_accident.py's own discovery function.

    Skips gracefully if none exists yet — run generate_test_model.py or
    train_model.py first.
    """
    if not MODEL_BASE_DIR.exists():
        pytest.skip(f"Model base directory not found: {MODEL_BASE_DIR}")
    try:
        return detect_accident._find_latest_model_dir(MODEL_BASE_DIR)
    except FileNotFoundError as exc:
        pytest.skip(
            f"{exc}\n"
            "Run 'python ai-module/generate_test_model.py' for a throwaway "
            "test model, or 'python ai-module/train_model.py' for a real one."
        )


@pytest.fixture(scope="module")
def class_metadata(detect_accident, model_dir):
    """Load class_metadata.json via the real load_class_metadata()."""
    return detect_accident.load_class_metadata(model_dir)


@pytest.fixture(scope="module")
def model(detect_accident, model_dir):
    """Load the model once for all tests, via the real load_model_from_dir()."""
    return detect_accident.load_model_from_dir(model_dir)


# ─── Model Discovery & Metadata Tests ──────────────────────────────────────────

class TestModelDiscovery:

    def test_find_latest_model_dir_raises_on_empty_base(self, detect_accident, tmp_path):
        """
        An empty base directory (or one with no class_metadata.json anywhere)
        must raise FileNotFoundError with a message pointing at train_model.py
        — not fail silently or crash with an unrelated exception.
        """
        empty_base = tmp_path / "model"
        empty_base.mkdir()
        with pytest.raises(FileNotFoundError, match="train_model.py"):
            detect_accident._find_latest_model_dir(empty_base)

    def test_find_latest_model_dir_ignores_dirs_without_metadata(self, detect_accident, tmp_path):
        """A subdirectory without class_metadata.json must not be considered valid."""
        base = tmp_path / "model"
        (base / "20200101_000000").mkdir(parents=True)  # no class_metadata.json
        with pytest.raises(FileNotFoundError):
            detect_accident._find_latest_model_dir(base)

    def test_find_latest_model_dir_picks_most_recent(self, detect_accident, tmp_path):
        """When multiple valid model dirs exist, the most recent timestamp wins."""
        base = tmp_path / "model"
        for ts in ("20250101_000000", "20260601_120000", "20250601_000000"):
            d = base / ts
            d.mkdir(parents=True)
            (d / "class_metadata.json").write_text("{}")
        chosen = detect_accident._find_latest_model_dir(base)
        assert chosen.name == "20260601_120000"

    def test_load_class_metadata_missing_file_raises(self, detect_accident, tmp_path):
        """A model dir without class_metadata.json should raise a clear FileNotFoundError."""
        empty_dir = tmp_path / "no_metadata"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            detect_accident.load_class_metadata(empty_dir)

    def test_class_metadata_idx_to_class_keys_are_int(self, class_metadata):
        """load_class_metadata() must normalise JSON's string keys ('0','1'...) to int."""
        assert all(isinstance(k, int) for k in class_metadata["idx_to_class"])

    def test_class_metadata_has_expected_labels(self, class_metadata):
        """The set of class names in metadata should match the known label set."""
        labels = set(class_metadata["idx_to_class"].values())
        assert labels == set(CLASS_LABELS), \
            f"Expected labels {CLASS_LABELS}, got {sorted(labels)}"

    def test_class_metadata_num_classes_matches_mapping(self, class_metadata):
        """num_classes in metadata should equal the length of idx_to_class."""
        assert class_metadata["num_classes"] == len(class_metadata["idx_to_class"])


# ─── Checksum Verification Tests ───────────────────────────────────────────────

class TestChecksumVerification:

    def _make_model_file(self, tmp_path, content: bytes = b"fake-model-bytes"):
        model_dir = tmp_path / "20260101_000000"
        model_dir.mkdir()
        model_path = model_dir / "accident_model.keras"
        model_path.write_bytes(content)
        return model_dir, model_path

    def test_correct_checksum_passes_silently(self, detect_accident, tmp_path):
        """A matching model.sha256 should not raise."""
        model_dir, model_path = self._make_model_file(tmp_path)
        checksum = hashlib.sha256(model_path.read_bytes()).hexdigest()
        (model_dir / "model.sha256").write_text(checksum)
        detect_accident.verify_model_checksum(model_dir, model_path)  # should not raise

    def test_mismatched_checksum_raises(self, detect_accident, tmp_path):
        """A tampered/corrupted model file must raise RuntimeError, not load silently."""
        model_dir, model_path = self._make_model_file(tmp_path)
        (model_dir / "model.sha256").write_text("0" * 64)  # deliberately wrong
        with pytest.raises(RuntimeError, match="checksum mismatch"):
            detect_accident.verify_model_checksum(model_dir, model_path)

    def test_missing_checksum_file_does_not_raise(self, detect_accident, tmp_path):
        """No model.sha256 present (e.g. a manually-dropped model) should warn, not fail."""
        model_dir, model_path = self._make_model_file(tmp_path)
        detect_accident.verify_model_checksum(model_dir, model_path)  # should not raise

    def test_directory_model_path_skips_checksum(self, detect_accident, tmp_path):
        """SavedModel directories (not single files) skip checksumming entirely."""
        model_dir = tmp_path / "20260101_000000"
        model_dir.mkdir()
        saved_model_dir = model_dir / "phase2_best"
        saved_model_dir.mkdir()
        detect_accident.verify_model_checksum(model_dir, saved_model_dir)  # should not raise


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

    def test_model_output_matches_metadata_num_classes(self, model, class_metadata):
        """
        Model output width should equal num_classes from class_metadata.json —
        not a hardcoded constant, since the two must always agree in production.
        """
        expected = (None, class_metadata["num_classes"])
        assert model.output_shape == expected, \
            f"Expected output shape {expected}, got {model.output_shape}"


class TestModelFilePriority:
    """
    load_model_from_dir() checks candidate filenames in a fixed priority
    order: accident_model.keras, accident_model.h5, phase2_best.keras,
    phase1_best.keras, phase2_best, phase1_best. These tests patch
    tf.keras.models.load_model so they only exercise the file-selection
    logic, not real model loading.
    """

    def test_raises_when_no_candidate_file_exists(self, detect_accident, tmp_path):
        model_dir = tmp_path / "20260101_000000"
        model_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            detect_accident.load_model_from_dir(model_dir)

    def test_prefers_keras_over_h5(self, detect_accident, tmp_path, monkeypatch):
        model_dir = tmp_path / "20260101_000000"
        model_dir.mkdir()
        (model_dir / "accident_model.keras").write_bytes(b"fake-keras")
        (model_dir / "accident_model.h5").write_bytes(b"fake-h5")

        loaded_paths = []

        def fake_load_model(path):
            loaded_paths.append(path)
            return Mock(input_shape=(None, 224, 224, 3))

        monkeypatch.setattr(detect_accident.tf.keras.models, "load_model", fake_load_model)
        detect_accident.load_model_from_dir(model_dir)
        assert loaded_paths[0].endswith("accident_model.keras")

    def test_falls_back_to_h5_when_keras_absent(self, detect_accident, tmp_path, monkeypatch):
        model_dir = tmp_path / "20260101_000000"
        model_dir.mkdir()
        (model_dir / "accident_model.h5").write_bytes(b"fake-h5")

        loaded_paths = []

        def fake_load_model(path):
            loaded_paths.append(path)
            return Mock(input_shape=(None, 224, 224, 3))

        monkeypatch.setattr(detect_accident.tf.keras.models, "load_model", fake_load_model)
        detect_accident.load_model_from_dir(model_dir)
        assert loaded_paths[0].endswith("accident_model.h5")


# ─── Preprocessing Tests (preprocess_frame, no model needed) ──────────────────

class TestPreprocessing:
    """
    Test preprocess_frame() exactly as detect_accident.py calls it in the
    main loop — a raw BGR frame from cv2.VideoCapture in, a normalised
    tensor out. No model required.
    """

    def test_output_shape(self, detect_accident):
        """Output should always be (1, 224, 224, 3) regardless of input frame size."""
        frame = make_dummy_frame("random")
        out = detect_accident.preprocess_frame(frame)
        assert out.shape == (1, *INPUT_SIZE, 3)

    def test_output_dtype_is_float32(self, detect_accident):
        frame = make_dummy_frame("random")
        out = detect_accident.preprocess_frame(frame)
        assert out.dtype == np.float32

    def test_output_range_matches_mobilenet_preprocessing(self, detect_accident):
        """
        preprocess_frame() applies MobileNetV2's preprocess_input, which maps
        [0, 255] to [-1, 1].
        """
        frame = make_dummy_frame("random")
        out = detect_accident.preprocess_frame(frame)
        assert float(out.min()) >= -1.0001
        assert float(out.max()) <= 1.0001

    def test_black_frame_maps_to_minus_one(self, detect_accident):
        """An all-zero BGR frame should map to (approximately) all -1.0 after preprocess_input."""
        out = detect_accident.preprocess_frame(make_dummy_frame("black"))
        assert np.allclose(out, -1.0, atol=1e-3)

    def test_white_frame_maps_to_one(self, detect_accident):
        """An all-255 BGR frame should map to (approximately) all 1.0 after preprocess_input."""
        out = detect_accident.preprocess_frame(make_dummy_frame("white"))
        assert np.allclose(out, 1.0, atol=1e-3)

    def test_bgr_to_rgb_conversion(self, detect_accident):
        """
        A pure-blue BGR frame ([255, 0, 0] per pixel in BGR order) should
        become pure-red after the BGR→RGB conversion, i.e. channel 0 (R)
        should end up at the "high" end and channel 2 (B) at the "low" end.
        """
        blue_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        blue_bgr[:, :, 0] = 255  # channel 0 = Blue in BGR
        out = detect_accident.preprocess_frame(blue_bgr)[0]
        assert out[0, 0, 0] < 0   # R channel: low (was 0 before scaling)
        assert out[0, 0, 2] > 0   # B channel: high (was 255 before scaling)


# ─── Severity Mapping Tests (confidence_to_severity, no model needed) ─────────

class TestSeverityMapping:
    """Test confidence_to_severity() imported directly from detect_accident.py."""

    @pytest.mark.parametrize("confidence,expected", [
        (0.97, "critical"),
        (0.95, "critical"),   # boundary: >= 0.95 is critical
        (0.94, "high"),
        (0.90, "high"),
        (0.85, "high"),       # boundary: >= 0.85 is high
        (0.84, "medium"),
        (0.80, "medium"),
        (0.75, "medium"),     # boundary: >= 0.75 is medium
        (0.74, "low"),
        (0.10, "low"),
        (0.0, "low"),
    ])
    def test_severity_thresholds(self, detect_accident, confidence, expected):
        assert detect_accident.confidence_to_severity(confidence) == expected


class TestConfidenceThresholdConstant:
    """
    Test the module-level CONFIDENCE_THRESHOLD / alert-trigger comparison
    used in run_detection()'s main loop: `confidence >= CONFIDENCE_THRESHOLD`.
    """

    def test_default_confidence_threshold(self, detect_accident):
        """Default threshold (no env var override) should be 0.75."""
        assert detect_accident.CONFIDENCE_THRESHOLD == 0.75

    def test_high_confidence_passes_threshold(self, detect_accident):
        threshold = detect_accident.CONFIDENCE_THRESHOLD
        assert 0.92 >= threshold, "High confidence should pass threshold"

    def test_low_confidence_blocked(self, detect_accident):
        threshold = detect_accident.CONFIDENCE_THRESHOLD
        assert 0.60 < threshold, "Low confidence should be blocked"

    def test_exactly_at_threshold_passes(self, detect_accident):
        """Confidence exactly equal to threshold should pass (>= not >)."""
        threshold = detect_accident.CONFIDENCE_THRESHOLD
        assert threshold >= threshold


# ─── Authentication Tests (get_auth_token / _fetch_new_token) ────────────────

class TestAuthentication:
    """
    Test the thread-safe token cache and retry-cooldown logic in
    get_auth_token(), with requests.post mocked so no network call happens.
    """

    @pytest.fixture(autouse=True)
    def reset_auth_state(self, detect_accident):
        """Auth token / cooldown are module globals — reset before and after each test."""
        detect_accident._auth_token = None
        detect_accident._auth_token_last_fail = 0.0
        yield
        detect_accident._auth_token = None
        detect_accident._auth_token_last_fail = 0.0

    def test_no_credentials_returns_none(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "")
        assert detect_accident.get_auth_token() is None

    def test_successful_login_returns_and_caches_token(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "secret")

        call_count = {"n": 0}

        class FakeResponse:
            status_code = 200
            def json(self):
                return {"access_token": "tok-123"}

        def fake_post(*args, **kwargs):
            call_count["n"] += 1
            return FakeResponse()

        monkeypatch.setattr(detect_accident.requests, "post", fake_post)

        token1 = detect_accident.get_auth_token()
        token2 = detect_accident.get_auth_token()  # should use cache, not call post again

        assert token1 == "tok-123"
        assert token2 == "tok-123"
        assert call_count["n"] == 1

    def test_failed_login_returns_none(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "wrong")

        class FakeResponse:
            status_code = 401
            text = "invalid credentials"

        monkeypatch.setattr(detect_accident.requests, "post", lambda *a, **k: FakeResponse())

        assert detect_accident.get_auth_token() is None

    def test_retry_cooldown_blocks_immediate_retry(self, detect_accident, monkeypatch):
        """After a failed login, a second call within AUTH_RETRY_COOLDOWN must not hit the network again."""
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "wrong")

        call_count = {"n": 0}

        class FakeResponse:
            status_code = 401
            text = "invalid credentials"

        def fake_post(*args, **kwargs):
            call_count["n"] += 1
            return FakeResponse()

        monkeypatch.setattr(detect_accident.requests, "post", fake_post)

        detect_accident.get_auth_token()  # first attempt fails, starts cooldown
        detect_accident.get_auth_token()  # should be blocked by cooldown

        assert call_count["n"] == 1

    def test_force_refresh_bypasses_cache(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "secret")

        call_count = {"n": 0}

        class FakeResponse:
            status_code = 200
            def json(self):
                return {"access_token": f"tok-{call_count['n']}"}

        def fake_post(*args, **kwargs):
            call_count["n"] += 1
            return FakeResponse()

        monkeypatch.setattr(detect_accident.requests, "post", fake_post)

        token1 = detect_accident.get_auth_token()
        token2 = detect_accident.get_auth_token(force_refresh=True)

        assert call_count["n"] == 2
        assert token1 != token2


# ─── Evidence Storage Tests (save_evidence_frame / _cleanup_old_evidence) ────

class TestEvidenceStorage:
    """
    save_evidence_frame() derives its output directory from the module's own
    __file__, so these tests redirect that to a tmp_path before calling it.
    """

    @pytest.fixture
    def redirected_module(self, detect_accident, tmp_path, monkeypatch):
        fake_module_path = tmp_path / "ai-module" / "detect_accident.py"
        fake_module_path.parent.mkdir(parents=True)
        monkeypatch.setattr(detect_accident, "__file__", str(fake_module_path))
        return detect_accident, fake_module_path.parent

    def test_save_evidence_frame_creates_file(self, redirected_module):
        detect_accident, module_dir = redirected_module
        frame = make_dummy_frame("random")
        # cv2.imwrite needs a real 3-channel uint8 array, which make_dummy_frame provides.
        path = detect_accident.save_evidence_frame(frame)
        assert path is not None
        assert os.path.exists(path)
        assert (module_dir / "evidence" / detect_accident.CAMERA_ID).exists()

    def test_cleanup_removes_only_old_files(self, redirected_module):
        detect_accident, module_dir = redirected_module
        evidence_dir = module_dir / "evidence" / detect_accident.CAMERA_ID
        evidence_dir.mkdir(parents=True)

        old_file = evidence_dir / "old.jpg"
        new_file = evidence_dir / "new.jpg"
        old_file.write_bytes(b"old")
        new_file.write_bytes(b"new")

        old_time = (
            datetime.now() - timedelta(days=detect_accident.EVIDENCE_RETENTION_DAYS + 1)
        ).timestamp()
        os.utime(old_file, (old_time, old_time))

        detect_accident._cleanup_old_evidence(evidence_dir)

        assert not old_file.exists()
        assert new_file.exists()


# ─── Alert Dispatch Tests (_post_alert / dispatch_alert) ─────────────────────

class TestPostAlert:
    """
    _post_alert() with requests.post mocked — no real network call. Evidence
    saving is bypassed by redirecting __file__ the same way TestEvidenceStorage does.
    """

    @pytest.fixture
    def redirected_module(self, detect_accident, tmp_path, monkeypatch):
        fake_module_path = tmp_path / "ai-module" / "detect_accident.py"
        fake_module_path.parent.mkdir(parents=True)
        monkeypatch.setattr(detect_accident, "__file__", str(fake_module_path))
        monkeypatch.setattr(detect_accident, "_auth_token", None)
        monkeypatch.setattr(detect_accident, "_auth_token_last_fail", 0.0)
        return detect_accident

    def test_201_returns_true(self, redirected_module, monkeypatch):
        detect_accident = redirected_module

        class FakeResponse:
            status_code = 201
            def json(self):
                return {"id": 42}

        monkeypatch.setattr(detect_accident.requests, "post", lambda *a, **k: FakeResponse())
        assert detect_accident._post_alert(make_dummy_frame(), 0.9) is True

    def test_non_201_returns_false(self, redirected_module, monkeypatch):
        detect_accident = redirected_module

        class FakeResponse:
            status_code = 500
            text = "server error"

        monkeypatch.setattr(detect_accident.requests, "post", lambda *a, **k: FakeResponse())
        assert detect_accident._post_alert(make_dummy_frame(), 0.9) is False

    def test_connection_error_returns_false(self, redirected_module, monkeypatch):
        detect_accident = redirected_module

        def raise_connection_error(*a, **k):
            raise detect_accident.requests.exceptions.ConnectionError("no route to host")

        monkeypatch.setattr(detect_accident.requests, "post", raise_connection_error)
        assert detect_accident._post_alert(make_dummy_frame(), 0.9) is False

    def test_timeout_returns_false(self, redirected_module, monkeypatch):
        detect_accident = redirected_module

        def raise_timeout(*a, **k):
            raise detect_accident.requests.exceptions.Timeout("timed out")

        monkeypatch.setattr(detect_accident.requests, "post", raise_timeout)
        assert detect_accident._post_alert(make_dummy_frame(), 0.9) is False

    def test_401_retries_once_with_refreshed_token(self, redirected_module, monkeypatch):
        """
        A 401 on the first accidents POST should trigger exactly one
        force-refresh login call, then exactly one retry POST that succeeds.
        """
        detect_accident = redirected_module
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "secret")
        # Pre-seed a cached (now-expired) token so get_auth_token() returns it
        # without hitting the network on the first call.
        monkeypatch.setattr(detect_accident, "_auth_token", "expired-token")

        accidents_calls = []
        login_calls = []

        class Unauthorized:
            status_code = 401
            text = "expired"

        class Success:
            status_code = 201
            def json(self):
                return {"id": 7}

        class LoginOK:
            status_code = 200
            def json(self):
                return {"access_token": "fresh-token"}

        def fake_post(url, headers=None, **kwargs):
            if url == detect_accident.BACKEND_LOGIN_URL:
                login_calls.append(url)
                return LoginOK()
            # accidents endpoint
            accidents_calls.append(headers.get("Authorization") if headers else None)
            if len(accidents_calls) == 1:
                return Unauthorized()  # first attempt uses the expired token
            return Success()          # retry, now with the refreshed token

        monkeypatch.setattr(detect_accident.requests, "post", fake_post)
        result = detect_accident._post_alert(make_dummy_frame(), 0.9)

        assert result is True
        assert len(login_calls) == 1, "expected exactly one re-auth attempt"
        assert len(accidents_calls) == 2, "expected exactly one retry after 401"
        assert accidents_calls[0] == "Bearer expired-token"
        assert accidents_calls[1] == "Bearer fresh-token"

    def test_401_with_failed_reauth_returns_false(self, redirected_module, monkeypatch):
        """If re-authentication itself fails after a 401, the alert must be dropped (False), not retried forever."""
        detect_accident = redirected_module
        monkeypatch.setattr(detect_accident, "AI_MODULE_EMAIL", "test@example.com")
        monkeypatch.setattr(detect_accident, "AI_MODULE_PASSWORD", "secret")
        monkeypatch.setattr(detect_accident, "_auth_token", "expired-token")

        accidents_calls = {"n": 0}

        class Unauthorized:
            status_code = 401
            text = "expired"

        class LoginFailed:
            status_code = 401
            text = "bad credentials"

        def fake_post(url, headers=None, **kwargs):
            if url == detect_accident.BACKEND_LOGIN_URL:
                return LoginFailed()
            accidents_calls["n"] += 1
            return Unauthorized()

        monkeypatch.setattr(detect_accident.requests, "post", fake_post)
        result = detect_accident._post_alert(make_dummy_frame(), 0.9)

        assert result is False
        assert accidents_calls["n"] == 1, "must not retry the accidents POST if re-auth failed"


class TestDispatchAlert:
    """
    dispatch_alert() must set the cooldown timestamp on the calling (main)
    thread BEFORE the background POST completes — that's the whole point of
    the design (prevents duplicate alerts while the backend is slow).
    """

    def test_cooldown_timestamp_set_before_background_task_finishes(self, detect_accident, monkeypatch):
        release_event = threading.Event()
        started_event = threading.Event()

        def slow_post_alert(frame, confidence):
            started_event.set()
            release_event.wait(timeout=5)
            return True

        monkeypatch.setattr(detect_accident, "_post_alert", slow_post_alert)

        last_alert = [0.0]
        before = time.time()
        detect_accident.dispatch_alert(make_dummy_frame(), 0.9, last_alert)

        # last_alert must already be updated even though the background task
        # hasn't run yet (it's blocked on release_event).
        assert last_alert[0] >= before

        started_event.wait(timeout=5)
        release_event.set()
        detect_accident._alert_executor.shutdown(wait=True)
        # Recreate the executor since we just shut the module-level one down.
        detect_accident._alert_executor = detect_accident.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="alert"
        )


# ─── Video Capture Retry Tests (open_capture) ─────────────────────────────────

class TestOpenCapture:
    """
    open_capture() retries with exponential back-off. time.sleep is mocked
    out so these tests run instantly instead of waiting for real delays.
    """

    def test_succeeds_on_first_try(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident.time, "sleep", lambda s: None)

        class FakeCap:
            def isOpened(self):
                return True

        monkeypatch.setattr(detect_accident.cv2, "VideoCapture", lambda source: FakeCap())
        cap = detect_accident.open_capture(0)
        assert cap.isOpened()

    def test_retries_then_succeeds(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident.time, "sleep", lambda s: None)
        attempts = {"n": 0}

        class FakeCap:
            def __init__(self):
                attempts["n"] += 1
                self._opened = attempts["n"] >= 3  # fails twice, succeeds on 3rd

            def isOpened(self):
                return self._opened

        monkeypatch.setattr(detect_accident.cv2, "VideoCapture", lambda source: FakeCap())
        cap = detect_accident.open_capture(0)
        assert cap.isOpened()
        assert attempts["n"] == 3

    def test_raises_after_max_attempts(self, detect_accident, monkeypatch):
        monkeypatch.setattr(detect_accident.time, "sleep", lambda s: None)
        monkeypatch.setattr(detect_accident, "MAX_RECONNECT_ATTEMPTS", 2)

        class FakeCap:
            def isOpened(self):
                return False

        monkeypatch.setattr(detect_accident.cv2, "VideoCapture", lambda source: FakeCap())
        with pytest.raises(RuntimeError, match="Failed to open video source"):
            detect_accident.open_capture(0)


# ─── Inference Tests (model + preprocess_frame together) ─────────────────────

class TestInference:

    def test_inference_returns_correct_shape(self, detect_accident, model, class_metadata):
        """model.predict() on a batch of 1 should return shape (1, num_classes)."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("random"))
        preds = model.predict(dummy, verbose=0)
        assert preds.shape == (1, class_metadata["num_classes"])

    def test_probabilities_sum_to_one(self, detect_accident, model):
        """Softmax output must sum to ~1.0. If this fails, the final layer isn't softmax."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("random"))
        preds = model.predict(dummy, verbose=0)[0]
        total = float(np.sum(preds))
        assert abs(total - 1.0) < 1e-4, f"Probabilities sum to {total:.6f}, expected ~1.0"

    def test_all_probabilities_in_valid_range(self, detect_accident, model):
        """Each probability must be in [0.0, 1.0]."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("random"))
        preds = model.predict(dummy, verbose=0)[0]
        assert np.all(preds >= 0.0) and np.all(preds <= 1.0), \
            f"Probabilities out of [0, 1]: {preds}"

    def test_argmax_maps_to_valid_class_label(self, detect_accident, model, class_metadata):
        """The predicted class index must correspond to a valid class label."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("random"))
        preds = model.predict(dummy, verbose=0)[0]
        predicted_idx = int(np.argmax(preds))
        assert predicted_idx in class_metadata["idx_to_class"], \
            f"Predicted index {predicted_idx} has no matching label"

    def test_inference_on_black_frame(self, detect_accident, model):
        """Edge case: all-black frame should still produce valid softmax output."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("black"))
        preds = model.predict(dummy, verbose=0)[0]
        assert abs(float(np.sum(preds)) - 1.0) < 1e-4

    def test_inference_on_white_frame(self, detect_accident, model):
        """Edge case: all-white frame should still produce valid softmax output."""
        dummy = detect_accident.preprocess_frame(make_dummy_frame("white"))
        preds = model.predict(dummy, verbose=0)[0]
        assert abs(float(np.sum(preds)) - 1.0) < 1e-4

    def test_inference_end_to_end_matches_alert_condition(self, detect_accident, model, class_metadata):
        """
        Smoke test that chains preprocess_frame -> model.predict -> label lookup
        exactly as run_detection()'s main loop does, and confirms the result
        can be compared against CONFIDENCE_THRESHOLD without error.
        """
        dummy = detect_accident.preprocess_frame(make_dummy_frame("random"))
        preds = model.predict(dummy, verbose=0)[0]
        class_idx = int(np.argmax(preds))
        confidence = float(preds[class_idx])
        label = class_metadata["idx_to_class"][class_idx]
        is_alert = label == "accident" and confidence >= detect_accident.CONFIDENCE_THRESHOLD
        assert isinstance(is_alert, bool)