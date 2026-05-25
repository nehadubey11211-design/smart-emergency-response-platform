"""
FILE: ai-module/detect_accident.py
================================================================================
Real-time Accident Detection — AI Inference Loop (Deployment-Ready)
================================================================================

PROCESS OVERVIEW:
  1.  Environment variables are read (see CONFIG section below for full list).
  2.  TensorFlow is imported and GPU memory growth is enabled if a GPU is found.
  3.  The latest timestamped model directory under ai-module/model/ is located
      automatically; it must contain class_metadata.json produced by train_model.py.
  4.  The Keras model is loaded, checksum-verified, and compiled into a @tf.function
      for fast inference.
  5.  The video source (webcam / RTSP stream / file) is opened via OpenCV.
  6.  The main loop reads frames; every Nth frame (determined by TARGET_IPS) is
      preprocessed and passed through the model.
  7.  Raw predictions are averaged over a rolling TEMPORAL_WINDOW to reduce
      false positives caused by single-frame noise.
  8.  When class == "accident" and smoothed confidence >= CONFIDENCE_THRESHOLD,
      an alert is dispatched to the FastAPI backend in a background thread via
      a bounded ThreadPoolExecutor (max 2 workers).
  9.  A per-camera cooldown (ALERT_COOLDOWN_SECONDS) prevents duplicate alerts.
      The cooldown timestamp is set IMMEDIATELY in the main thread the moment
      an alert is dispatched — not after the POST completes. This prevents
      duplicate alerts when the backend is slow (e.g. Neon cold-start ~5s).
      If the POST fails, the failure is logged with the full payload for audit.
  10. If the backend returns HTTP 401, the cached auth token is cleared and a
      single re-authentication attempt is made before giving up on that alert.
      A retry cooldown prevents hammering the login endpoint on repeated failures.
  11. Evidence frames (JPEG snapshots) are saved locally with automatic cleanup:
      files older than EVIDENCE_RETENTION_DAYS are deleted on each startup.
  12. On RTSP/webcam disconnection the loop retries with exponential back-off
      (up to MAX_RECONNECT_ATTEMPTS); on file-source EOF the process exits cleanly.
  13. In headless mode (HEADLESS=1) all cv2.imshow / cv2.waitKey calls are
      skipped, making the script safe for Docker / cloud VM deployment.

FILE PATH:
  smart-emergency-response-platform/
  └── ai-module/
      ├── detect_accident.py          ← this file
      ├── train_model.py
      └── model/
          └── <timestamp>/
              ├── accident_model.keras   (or .h5 / phase checkpoints)
              ├── class_metadata.json
              └── model.sha256

ENVIRONMENT VARIABLES (all optional — defaults shown):
  BACKEND_URL                 http://localhost:8000
  CONFIDENCE_THRESHOLD        0.75
  ALERT_COOLDOWN_SECONDS      60
  TARGET_IPS                  1.0          (inferences per second)
  TEMPORAL_WINDOW             5            (frames to average)
  CAMERA_ID                   CAM-001
  CAMERA_LAT                  0.0
  CAMERA_LON                  0.0
  CAMERA_LOCATION_DESC        <CAMERA_ID> Zone
  AI_MODULE_EMAIL             (empty → unauthenticated requests)
  AI_MODULE_PASSWORD          (empty → unauthenticated requests)
  VIDEO_SOURCE                0            (0 = default webcam)
  HEADLESS                    0            (1 = disable cv2.imshow)
  EVIDENCE_RETENTION_DAYS     7
  MAX_RECONNECT_ATTEMPTS      10

QUICK START:
  pip install tensorflow opencv-python requests
  python detect_accident.py

HEADLESS / DOCKER:
  HEADLESS=1 CAMERA_ID=CAM-002 BACKEND_URL=http://api:8000 python detect_accident.py

"""

# ── Standard library ──────────────────────────────────────────────────────────
import hashlib
import json
import logging
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

# ── Third-party ───────────────────────────────────────────────────────────────
import cv2
import numpy as np
import requests

# ── Logging (configure before any other module logs) ─────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── TensorFlow import (fail fast with a clear message) ───────────────────────
try:
    import tensorflow as tf
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
except ImportError:
    logger.error("TensorFlow not found. Run: pip install tensorflow")
    sys.exit(1)

# Enable GPU memory growth to avoid OOM on shared-GPU hosts
for _gpu in tf.config.list_physical_devices("GPU"):
    tf.config.experimental.set_memory_growth(_gpu, True)

# ── Configuration (all tunable via environment variables) ─────────────────────
BACKEND_BASE_URL          = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_ACCIDENTS_URL     = f"{BACKEND_BASE_URL}/api/accidents"
BACKEND_LOGIN_URL         = f"{BACKEND_BASE_URL}/api/v1/auth/login"

MODEL_BASE_DIR            = Path(__file__).parent / "model"

CONFIDENCE_THRESHOLD      = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
ALERT_COOLDOWN_SECONDS    = int(os.getenv("ALERT_COOLDOWN_SECONDS", "60"))
TARGET_IPS                = float(os.getenv("TARGET_IPS", "1.0"))
TEMPORAL_WINDOW           = int(os.getenv("TEMPORAL_WINDOW", "5"))
EVIDENCE_RETENTION_DAYS   = int(os.getenv("EVIDENCE_RETENTION_DAYS", "7"))
MAX_RECONNECT_ATTEMPTS    = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10"))

CAMERA_ID                 = os.getenv("CAMERA_ID", "CAM-001")
CAMERA_LAT                = float(os.getenv("CAMERA_LAT", "0.0"))
CAMERA_LON                = float(os.getenv("CAMERA_LON", "0.0"))
CAMERA_LOCATION_DESC      = os.getenv("CAMERA_LOCATION_DESC", f"{CAMERA_ID} Zone")

AI_MODULE_EMAIL           = os.getenv("AI_MODULE_EMAIL", "")
AI_MODULE_PASSWORD        = os.getenv("AI_MODULE_PASSWORD", "")

HEADLESS                  = os.getenv("HEADLESS", "0") == "1"

_raw_source = os.getenv("VIDEO_SOURCE", "0")
VIDEO_SOURCE: int | str = int(_raw_source) if _raw_source.isdigit() else _raw_source

AUTH_RETRY_COOLDOWN       = 30  # seconds between re-auth attempts on failure

# ── Auth token state (protected by a lock for thread safety) ──────────────────
_auth_token: str | None = None
_auth_token_last_fail: float = 0.0
_auth_lock = threading.Lock()

# ── Background alert executor (bounded to prevent thread pile-up) ─────────────
_alert_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="alert")


# ── Model discovery ───────────────────────────────────────────────────────────

def _find_latest_model_dir(base_dir: Path) -> Path:
    """
    Return the most recently timestamped subdirectory of base_dir that
    contains class_metadata.json.  Raises FileNotFoundError with a clear
    message if none is found.
    """
    valid = sorted(
        [
            d for d in base_dir.iterdir()
            if d.is_dir() and (d / "class_metadata.json").exists()
        ],
        reverse=True,
    )
    if not valid:
        raise FileNotFoundError(
            f"No valid model directories found in {base_dir}.\n"
            "Each directory must contain class_metadata.json.\n"
            "Run train_model.py first."
        )
    logger.info("Found %d model dir(s). Using: %s", len(valid), valid[0])
    return valid[0]


def load_class_metadata(model_dir: Path) -> dict:
    """Load class_metadata.json and normalise idx_to_class keys to int."""
    path = model_dir / "class_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"class_metadata.json not found at {path}.")
    with path.open() as fh:
        meta = json.load(fh)
    meta["idx_to_class"] = {int(k): v for k, v in meta["idx_to_class"].items()}
    logger.info("Class mapping: %s", meta["idx_to_class"])
    return meta


def verify_model_checksum(model_dir: Path, model_path: Path) -> None:
    """
    Verify the SHA-256 checksum of the model file against model.sha256.
    Logs a warning if the checksum file is absent.
    Raises RuntimeError if the checksum does not match (corrupted model).
    Only applicable to single-file .keras / .h5 models; skipped for directories.
    """
    if model_path.is_dir():
        logger.warning("SavedModel directory — skipping checksum verification.")
        return

    checksum_file = model_dir / "model.sha256"
    if not checksum_file.exists():
        logger.warning("No model.sha256 found — skipping integrity check.")
        return

    expected = checksum_file.read_text().strip()
    sha = hashlib.sha256()
    with model_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha.update(chunk)

    actual = sha.hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Model checksum mismatch for {model_path}.\n"
            f"  Expected : {expected}\n"
            f"  Actual   : {actual}\n"
            "The model file may be corrupted. Re-run train_model.py."
        )
    logger.info("Model checksum verified: %s", actual)


def load_model_from_dir(model_dir: Path):
    """
    Try to load a Keras model from the given directory.
    Checks for saved-model files in priority order and verifies the checksum
    when a model.sha256 file is present.
    """
    candidates = [
        "accident_model.keras",
        "accident_model.h5",
        "phase2_best.keras",
        "phase1_best.keras",
        "phase2_best",
        "phase1_best",
    ]
    for name in candidates:
        path = model_dir / name
        if path.exists():
            logger.info("Loading model from %s", path)
            verify_model_checksum(model_dir, path)
            model = tf.keras.models.load_model(str(path))
            logger.info("Model loaded. Input shape: %s", model.input_shape)
            return model
    raise FileNotFoundError(f"No model file found in {model_dir}")


# ── Frame preprocessing ───────────────────────────────────────────────────────

def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """
    BGR OpenCV frame → float32 batch tensor ready for MobileNetV2.

    Steps:
      resize to (224, 224)
      BGR → RGB  (OpenCV default is BGR; MobileNetV2 was trained on RGB)
      cast to float32
      add batch dimension → shape (1, 224, 224, 3)
      apply MobileNetV2 preprocess_input → scales to [-1, 1]
    """
    img = cv2.resize(frame, (224, 224))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = np.expand_dims(img, axis=0)
    img = preprocess_input(img)
    return img


# ── Severity mapping ──────────────────────────────────────────────────────────

def confidence_to_severity(confidence: float) -> str:
    if confidence >= 0.95:
        return "critical"
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.75:
        return "medium"
    return "low"


# ── Authentication (thread-safe) ──────────────────────────────────────────────

def _fetch_new_token() -> str | None:
    """
    POST credentials to the backend login endpoint and return the access token.
    Returns None on any failure.  Must be called with _auth_lock held.
    """
    if not AI_MODULE_EMAIL or not AI_MODULE_PASSWORD:
        return None
    try:
        resp = requests.post(
            BACKEND_LOGIN_URL,
            json={"email": AI_MODULE_EMAIL, "password": AI_MODULE_PASSWORD},
            timeout=10,
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            logger.info("Authentication successful.")
            return token
        logger.warning("Auth failed: HTTP %d — %s", resp.status_code, resp.text[:80])
        return None
    except Exception as exc:
        logger.warning("Auth request error: %s", exc)
        return None


def get_auth_token(force_refresh: bool = False) -> str | None:
    """
    Return a valid auth token, refreshing if needed.
    Thread-safe: uses _auth_lock so concurrent threads don't trigger
    multiple simultaneous login requests.

    A retry cooldown (AUTH_RETRY_COOLDOWN) prevents hammering the login
    endpoint when the backend is down or returning errors repeatedly.
    """
    global _auth_token, _auth_token_last_fail
    with _auth_lock:
        if not force_refresh and _auth_token:
            return _auth_token
        if not force_refresh and (time.time() - _auth_token_last_fail < AUTH_RETRY_COOLDOWN):
            logger.debug("Auth retry cooldown active — skipping login attempt.")
            return None
        _auth_token = _fetch_new_token()
        if not _auth_token:
            _auth_token_last_fail = time.time()
        return _auth_token


# ── Evidence storage with automatic cleanup ───────────────────────────────────

def _cleanup_old_evidence(evidence_dir: Path) -> None:
    """Delete JPEG evidence frames older than EVIDENCE_RETENTION_DAYS."""
    cutoff = datetime.now() - timedelta(days=EVIDENCE_RETENTION_DAYS)
    removed = 0
    for f in evidence_dir.glob("*.jpg"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            pass
    if removed:
        logger.info("Evidence cleanup: removed %d old frame(s) from %s", removed, evidence_dir)


def save_evidence_frame(frame: np.ndarray) -> str | None:
    """
    Save the accident frame as a JPEG for audit purposes.
    Returns the file path string on success, None on failure.
    """
    try:
        evidence_dir = Path(__file__).parent / "evidence" / CAMERA_ID
        evidence_dir.mkdir(parents=True, exist_ok=True)
        _cleanup_old_evidence(evidence_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = evidence_dir / f"accident_{timestamp}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logger.info("Evidence frame saved: %s", path)
        return str(path)
    except Exception as exc:
        logger.warning("Failed to save evidence frame: %s", exc)
        return None


# ── Backend alert (runs in thread pool) ──────────────────────────────────────

def _post_alert(frame: np.ndarray, confidence: float) -> bool:
    """
    Save the evidence frame and POST an accident record to the backend.

    Auth flow:
      1. Use the cached token (if any).
      2. On HTTP 401, force-refresh the token and retry ONCE.
      3. If the retry also fails or there is no token, return False.

    Returns True on HTTP 201, False on any error.
    """
    evidence_path = save_evidence_frame(frame)
    severity = confidence_to_severity(confidence)

    payload = {
        "location":    CAMERA_LOCATION_DESC,
        "severity":    severity,
        "confidence":  round(confidence, 4),
        "camera_id":   CAMERA_ID,
        "latitude":    CAMERA_LAT,
        "longitude":   CAMERA_LON,
        "image_path":  evidence_path,
        "description": (
            f"Auto-detected by AI module at "
            f"{datetime.now().strftime('%H:%M:%S')} "
            f"[confidence: {confidence:.1%}]"
        ),
    }

    def _do_post(token: str | None) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return requests.post(
            BACKEND_ACCIDENTS_URL,
            json=payload,
            headers=headers,
            timeout=8,
        )

    try:
        resp = _do_post(get_auth_token())

        # ── Token expired: refresh once and retry ─────────────────────────
        if resp.status_code == 401:
            logger.warning("Auth token expired — refreshing and retrying once.")
            new_token = get_auth_token(force_refresh=True)
            if not new_token:
                logger.error("Re-authentication failed. Alert dropped.")
                return False
            resp = _do_post(new_token)

        if resp.status_code == 201:
            accident_id = resp.json().get("id", "?")
            logger.info("Alert sent → Accident #%s created.", accident_id)
            return True

        logger.warning("Backend HTTP %d: %s", resp.status_code, resp.text[:120])
        logger.error(
            "Alert DROPPED (HTTP %d) — payload: location=%s confidence=%.1f%% camera=%s",
            resp.status_code, CAMERA_LOCATION_DESC, confidence * 100, CAMERA_ID,
        )
        return False

    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach backend at %s", BACKEND_ACCIDENTS_URL)
        logger.error(
            "Alert DROPPED (connection error) — payload: location=%s confidence=%.1f%% camera=%s time=%s",
            CAMERA_LOCATION_DESC, confidence * 100, CAMERA_ID,
            datetime.now().strftime("%H:%M:%S"),
        )
    except requests.exceptions.Timeout:
        logger.warning("Backend timed out after 8s.")
        logger.error(
            "Alert DROPPED (timeout) — payload: location=%s confidence=%.1f%% camera=%s time=%s",
            CAMERA_LOCATION_DESC, confidence * 100, CAMERA_ID,
            datetime.now().strftime("%H:%M:%S"),
        )
    except Exception as exc:
        logger.error("Unexpected alert error: %s", exc)
    return False


def dispatch_alert(
    frame: np.ndarray,
    confidence: float,
    last_alert_ref: list,     # mutable single-element list used as a ref
) -> None:
    """
    Set the cooldown timestamp IMMEDIATELY (main thread), then submit the
    POST to the thread pool.

    The cooldown blocks immediately on dispatch. If the POST fails the
    failure is logged with the full payload so nothing is silently lost.
    """
    last_alert_ref[0] = time.time()

    frame_copy = frame.copy()
    detected_at = datetime.now().strftime("%H:%M:%S")

    def _task():
        success = _post_alert(frame_copy, confidence)
        if not success:
            logger.error(
                "Alert DROPPED — manual review needed: "
                "camera=%s confidence=%.1f%% detected_at=%s location=%s",
                CAMERA_ID, confidence * 100, detected_at, CAMERA_LOCATION_DESC,
            )

    _alert_executor.submit(_task)


# ── Video capture with reconnection ──────────────────────────────────────────

def open_capture(source: int | str) -> cv2.VideoCapture:
    """
    Open a cv2.VideoCapture with exponential back-off retries.
    Raises RuntimeError after MAX_RECONNECT_ATTEMPTS failures.
    """
    delay = 1.0
    for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            return cap
        logger.warning(
            "Cannot open video source (attempt %d/%d). Retrying in %.0fs…",
            attempt, MAX_RECONNECT_ATTEMPTS, delay,
        )
        time.sleep(delay)
        delay = min(delay * 2, 30.0)
    raise RuntimeError(f"Failed to open video source after {MAX_RECONNECT_ATTEMPTS} attempts: {source}")


# ── Main detection loop ───────────────────────────────────────────────────────

def run_detection() -> None:
    """
    Entry point for the real-time detection loop.
    All configuration is read from environment variables at module load time.
    """

    # ── Coordinate warning ────────────────────────────────────────────────
    if CAMERA_LAT == 0.0 and CAMERA_LON == 0.0:
        logger.warning(
            "CAMERA_LAT / CAMERA_LON not set — alerts will have no GPS coordinates. "
            "Set them via environment variables."
        )

    # ── Load model ────────────────────────────────────────────────────────
    model_dir    = _find_latest_model_dir(MODEL_BASE_DIR)
    meta         = load_class_metadata(model_dir)
    idx_to_class: dict[int, str] = meta["idx_to_class"]
    model        = load_model_from_dir(model_dir)

    # Compile into a tf.function for faster repeated inference
    @tf.function(
        input_signature=[tf.TensorSpec(shape=(None, 224, 224, 3), dtype=tf.float32)]
    )
    def infer(x: tf.Tensor) -> tf.Tensor:
        return model(x, training=False)

    # ── Open video source ─────────────────────────────────────────────────
    logger.info("Opening video source: %s", VIDEO_SOURCE)
    cap = open_capture(VIDEO_SOURCE)

    fps        = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_skip = max(1, int(fps / TARGET_IPS))

    logger.info("FPS: %.0f | Analyzing every %d frame(s) (%.1f inference/s)",
                fps, frame_skip, TARGET_IPS)
    logger.info("Threshold: %.0f%% | Cooldown: %ds | Camera: %s — %s",
                CONFIDENCE_THRESHOLD * 100, ALERT_COOLDOWN_SECONDS,
                CAMERA_ID, CAMERA_LOCATION_DESC)
    if HEADLESS:
        logger.info("HEADLESS mode — display disabled.")
    else:
        logger.info("Press 'q' in the preview window to quit.")

    pred_buffer  = deque(maxlen=TEMPORAL_WINDOW)
    frame_count  = 0
    last_alert   = [0.0]

    severity_colours = {
        "accident":    (0,   0,   255),
        "traffic_jam": (0,   165, 255),
        "normal":      (0,   255, 0),
    }

    reconnect_attempts = 0

    try:
        while True:
            ret, frame = cap.read()

            # ── Handle disconnection ──────────────────────────────────────
            if not ret:
                if isinstance(VIDEO_SOURCE, str) and not VIDEO_SOURCE.startswith("rtsp"):
                    logger.info("End of video file. Exiting.")
                    break

                reconnect_attempts += 1
                if reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                    logger.error("Exceeded max reconnect attempts. Exiting.")
                    break

                delay = min(2 ** reconnect_attempts, 30.0)
                logger.warning(
                    "Stream disconnected (attempt %d/%d). Retrying in %.0fs…",
                    reconnect_attempts, MAX_RECONNECT_ATTEMPTS, delay,
                )
                cap.release()
                time.sleep(delay)
                cap = open_capture(VIDEO_SOURCE)
                pred_buffer.clear()
                logger.info("Reconnected to video source.")
                reconnect_attempts = 0
                continue

            reconnect_attempts = 0
            frame_count += 1

            # ── Skip non-analysis frames ──────────────────────────────────
            if frame_count % frame_skip != 0:
                continue

            # ── Inference ─────────────────────────────────────────────────
            processed  = preprocess_frame(frame)
            raw_preds  = infer(tf.constant(processed)).numpy()[0]
            pred_buffer.append(raw_preds)

            smoothed   = np.mean(pred_buffer, axis=0)
            class_idx  = int(np.argmax(smoothed))
            confidence = float(smoothed[class_idx])
            label      = idx_to_class[class_idx]

            logger.info(
                "[Frame %06d] %-12s %.1f%%",
                frame_count, label, confidence * 100,
            )

            # ── Alert trigger ─────────────────────────────────────────────
            if label == "accident" and confidence >= CONFIDENCE_THRESHOLD:
                elapsed = time.time() - last_alert[0]

                if elapsed < ALERT_COOLDOWN_SECONDS:
                    logger.info(
                        "Cooldown active — next alert in %.0fs.",
                        ALERT_COOLDOWN_SECONDS - elapsed,
                    )
                else:
                    logger.warning(
                        "ACCIDENT DETECTED! Confidence: %.1f%% | Camera: %s",
                        confidence * 100, CAMERA_ID,
                    )
                    dispatch_alert(frame, confidence, last_alert)

            # ── Optional live preview (skipped in HEADLESS mode) ──────────
            if not HEADLESS:
                colour = severity_colours.get(label, (255, 255, 255))
                cv2.putText(
                    frame,
                    f"{label.upper()} {confidence:.0%}",
                    (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    colour,
                    2,
                )
                cv2.putText(
                    frame,
                    f"Cam: {CAMERA_ID} | Frame: {frame_count}",
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                )
                cv2.imshow("Emergency Detection Feed — press Q to quit", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Detection stopped by user.")
                    break

    except KeyboardInterrupt:
        logger.info("Detection stopped (Ctrl+C).")
    finally:
        cap.release()
        if not HEADLESS:
            cv2.destroyAllWindows()
        _alert_executor.shutdown(wait=True)
        logger.info("Camera released. Alert executor shut down. Detection ended.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_detection()
