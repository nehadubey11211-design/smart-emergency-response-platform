"""
FILE: ai-module/detect_accident.py
=========================================
Real-time Accident Detection — AI Inference Loop
=========================================

HOW IT WORKS:
  1. OpenCV opens the video source (webcam / RTSP stream / file)
  2. Every 30th frame is extracted and preprocessed to 224×224
  3. The trained MobileNetV2 model classifies it into 3 classes:
       normal | accident | traffic_jam
  4. If class == "accident" and confidence > threshold → POST to backend API
  5. A 60-second cooldown prevents duplicate alerts for the same incident

OPENCV VIDEO CAPTURE:
  cv2.VideoCapture(0)             — webcam index 0
  cv2.VideoCapture("video.mp4")   — local file
  cv2.VideoCapture("rtsp://...")  — IP camera stream

FRAME PREPROCESSING PIPELINE:
  Raw frame (any resolution, BGR)
    → Resize to (224, 224)          — CNN input size
    → Convert to float32            — for normalization
    → Divide by 255.0               — normalize to [0, 1]
    → Add batch dimension           — shape: (1, 224, 224, 3)
    → Pass to model.predict()       — shape: (1, 3)

WHY SKIP FRAMES?
  A 30fps stream has 30 frames/second. Analyzing every frame would require
  30 inference calls/second — too slow on CPU.
  Analyzing every 30th frame gives ~1 inference/second — fast enough.

INTERVIEW TALKING POINT:
  "I used MobileNetV2 because it was designed for mobile/edge deployment.
  At ~3.4M parameters it's much smaller than VGG16 (138M) or ResNet50 (25M),
  but achieves comparable accuracy on image classification tasks.
  It runs comfortably in real-time on a CPU."
"""

import logging
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np
import requests

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
# Centralise all tunable values at the top — easier to change without
# hunting through the code.

# Backend API endpoint for reporting accidents
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/accidents")

# Path to the trained Keras model (relative to this script's location)
MODEL_PATH  = os.path.join(os.path.dirname(__file__), "model", "accident_model.h5")

# Confidence threshold: 0.75 = only alert if model is ≥75% confident
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))

# Analyze every Nth frame (1 per second at 30fps → N=30)
FRAME_INTERVAL = 10

# Minimum seconds between alerts for the SAME camera (avoids duplicates)
ALERT_COOLDOWN_SECONDS = 60

# Camera identifier — sent to the backend so operators know which camera
CAMERA_ID = os.getenv("CAMERA_ID", "CAM-001")

# Video source: 0 = default webcam, or a path/URL
VIDEO_SOURCE = int(os.getenv("VIDEO_SOURCE", "0")) \
    if os.getenv("VIDEO_SOURCE", "0").isdigit() \
    else os.getenv("VIDEO_SOURCE", "0")

#Class labels — ORDER MUST MATCH the training data directory order
#(Keras sorts class names alphabetically by default)
CLASS_LABELS = ["accident", "normal", "traffic_jam"]

# Default coordinates (example: Pune)
DEFAULT_LAT = 18.483243
DEFAULT_LON = 73.809709
# ─── Model Loading ────────────────────────────────────────────────────────────

def load_model():
    """
    Load the trained Keras model from disk.

    model.h5 format saves both the architecture AND the weights in one file.
    Loading is slow (~2-5s on CPU) so we do it once at startup.

    Returns None if the model file doesn't exist — caller handles the error.
    """
    try:
        # Import TensorFlow here (not at top level) so the script starts faster
        # when called with --help or when checking args.
        import tensorflow as tf

        if not os.path.exists(MODEL_PATH):
            logger.error("Model not found at: %s", MODEL_PATH)
            logger.error("Run python train_model.py first to train and save the model.")
            return None

        logger.info("Loading model from %s", MODEL_PATH)
        model = tf.keras.models.load_model(MODEL_PATH)
        logger.info("Model loaded. Input shape: %s", model.input_shape)
        return model

    except Exception as e:
        logger.error("Failed to load model: %s", e)
        return None


# ─── Frame Preprocessing ──────────────────────────────────────────────────────

def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """
    Transform a raw OpenCV frame into the format expected by the CNN.

    OpenCV reads frames in BGR order (not RGB) and as uint8 (0-255).
    The CNN expects RGB float32 in range [0, 1] with a batch dimension.

    Steps:
      1. cv2.resize    → (224, 224, 3)  — match CNN input size
      2. astype(float32)→ (224, 224, 3) — needed for division
      3. / 255.0       → values in [0.0, 1.0]
      4. expand_dims   → (1, 224, 224, 3) — batch of 1

    Note: MobileNetV2 was trained on RGB images, but OpenCV reads BGR.
    For production accuracy, convert: cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    """
    img = cv2.resize(frame, (224, 224))                  # Resize
    img = img.astype(np.float32) / 255.0                 # Normalise
    img = np.expand_dims(img, axis=0)                    # Add batch dim
    return img


# ─── Confidence → Severity Mapping ───────────────────────────────────────────

def confidence_to_severity(confidence: float) -> str:
    """
    Map the AI confidence score to a severity level string.

    Higher confidence = more certain = treated as more severe.
    This is a heuristic — in production, severity would also factor in:
      - Number of vehicles involved (from object detection)
      - Whether the road is blocked (from segmentation)
      - Time of day (peak hours = higher impact)
    """
    if confidence >= 0.95: return "critical"
    if confidence >= 0.85: return "high"
    if confidence >= 0.75: return "medium"
    return "low"


# ─── Backend API Communication ────────────────────────────────────────────────

def send_alert_to_backend(
    location: str,
    confidence: float,
    severity: str ,
    lat: float,
    lon: float
) -> bool:
    """
    POST a new accident record to the FastAPI backend.

    The backend will:
      1. Save to PostgreSQL
      2. Broadcast via WebSocket to all dashboard clients
      3. Send email notifications

    Returns True on success, False on failure.
    """
    payload = {
        "location":    location,
        "severity":    severity,
        "confidence":  round(confidence, 4),
        "camera_id":   CAMERA_ID,
        "latitude": lat,
        "longitude": lon,
        "description": (
            f"Auto-detected by AI module at "
            f"{datetime.now().strftime('%H:%M:%S')} "
            f"[confidence: {confidence:.1%}]"
        ),
    }

    try:
        response = requests.post(
            BACKEND_URL,
            json=payload,
            timeout=5,   # Don't block the detection loop for more than 5s
        )

        if response.status_code == 201:
            accident_id = response.json().get("id", "?")
            logger.info("Alert sent -> Accident #%s created in database", accident_id)
            return True
        else:
            logger.warning(
                "Backend returned HTTP %s: %s",
                response.status_code,
                response.text[:100],
            )
            return False

    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach backend — is FastAPI running on localhost:8000?")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Backend timed out after 5s")
        return False
    except Exception as e:
        logger.error("Unexpected error sending alert: %s", e)
        return False


# ─── Main Detection Loop ──────────────────────────────────────────────────────

def run_detection():
    """
    Main entry point for the real-time detection loop.

    Workflow:
      1. Load model
      2. Open video source
      3. For each frame:
         a. Skip if not on the analysis interval
         b. Preprocess and run inference
         c. If accident detected with sufficient confidence → send alert
         d. Optionally display the frame with overlay
    """
    # Step 1: Load model
    model = load_model()
    if model is None:
        sys.exit(1)

    # Step 2: Open video source
    logger.info("Opening video source: %s", VIDEO_SOURCE)
    cap = cv2.VideoCapture(VIDEO_SOURCE)

    if not cap.isOpened():
        logger.error("Cannot open video source: %s", VIDEO_SOURCE)
        logger.error("Ensure your webcam is connected or the file path is correct.")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    logger.info("Video source opened | FPS: %.0f | Camera: %s", fps, CAMERA_ID)
    logger.info(
        "Analyzing every %s frames (%.1f inferences/s)",
        FRAME_INTERVAL,
        fps / FRAME_INTERVAL,
    )
    logger.info("Confidence threshold: %.0f%%", CONFIDENCE_THRESHOLD * 100)
    logger.info("Press 'q' to quit")

    frame_count      = 0
    last_alert_time  = 0

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                logger.info("End of video stream or camera disconnected")
                break

            frame_count += 1

            # ── Skip non-analysis frames ─────────────────────────────────
            if frame_count % FRAME_INTERVAL != 0:
                continue

            # ── Run inference ────────────────────────────────────────────
            processed    = preprocess_frame(frame)
            # model.predict returns a 2D array [[p_class0, p_class1, p_class2]]
            predictions  = model.predict(processed, verbose=0)[0]
            class_idx    = int(np.argmax(predictions))
            confidence   = float(predictions[class_idx])
            label        = CLASS_LABELS[class_idx]

            logger.info(
                "[Frame %06d] %s confidence: %.1f%%",
                frame_count,
                label,
                confidence * 100,
            )

            # ── Trigger alert if accident detected ───────────────────────
            if label == "accident" and confidence >= CONFIDENCE_THRESHOLD:
                current_time = time.time()
                seconds_since_last = current_time - last_alert_time

                if seconds_since_last < ALERT_COOLDOWN_SECONDS:
                    remaining = ALERT_COOLDOWN_SECONDS - seconds_since_last
                    logger.info("Cooldown active — next alert in %.0fs", remaining)
                else:
                    logger.warning(
                        "ACCIDENT DETECTED! Confidence: %.1f%% | Camera: %s",
                        confidence * 100,
                        CAMERA_ID,
                    )
                    severity = confidence_to_severity(confidence)
                    success  = send_alert_to_backend(
                        location   = f"{CAMERA_ID} Zone",
                        confidence = confidence,
                        severity   = severity,
                         # Coordinates
                        lat = DEFAULT_LAT,
                        lon = DEFAULT_LON,
                    )
                    if success:
                        last_alert_time = current_time

            # ── Optional live preview ─────────────────────────────────────
            # Comment out the lines below for headless server deployment
            severity_colours = {
                "accident":    (0,   0,   255),  # Red   (BGR)
                "traffic_jam": (0,   165, 255),  # Orange
                "normal":      (0,   255, 0),    # Green
            }
            text_colour = severity_colours.get(label, (255, 255, 255))

            cv2.putText(
                frame,
                f"{label.upper()} {confidence:.0%}",
                (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                text_colour,
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

            # 'q' key exits the loop
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Detection stopped by user")
                break

    except KeyboardInterrupt:
        logger.info("Detection stopped (Ctrl+C)")
    finally:
        # Always release the camera and close windows — even on error
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Camera released. Detection ended.")


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_detection()
