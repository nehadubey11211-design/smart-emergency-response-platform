# 🚨 Smart AI Emergency Response System

## AI Module Report (Accident Detection & Training)

---

## 📌 1. Introduction

The AI Module is a core component of the Smart AI Emergency Response System. Its purpose is to **analyze real-time video streams** and automatically detect:

* Road accidents
* Traffic congestion
* Normal traffic conditions

Once an accident is detected, the system sends an alert to the backend, enabling emergency response actions such as traffic signal control and ambulance routing.

---

## 🎯 2. Objectives

* Detect accidents in real-time using computer vision
* Classify traffic into three categories:

  * **Accident**
  * **Normal**
  * **Traffic Jam**
* Ensure fast inference on CPU (real-time capable)
* Integrate seamlessly with backend API

---

## 🧠 3. Model Architecture

The system uses **MobileNetV2 (Transfer Learning)**:

### Why MobileNetV2?

* Lightweight (~3.4M parameters)
* Fast inference (~30ms on CPU)
* Pretrained on ImageNet (1.2M images)

### Architecture Flow:

```
Input Image (224x224)
        ↓
MobileNetV2 (Pretrained Base)
        ↓
GlobalAveragePooling
        ↓
BatchNormalization
        ↓
Dense Layer (ReLU)
        ↓
Dropout (0.3)
        ↓
Output Layer (Softmax - 3 classes)
```

---

## 📂 4. Dataset Structure

```
dataset/
  accident/
  normal/
  traffic_jam/
```

### Data Sources:

* Kaggle datasets
* Roboflow datasets
* Extracted frames from dashcam videos
* Manually collected images

### Dataset Strategy:

* Minimum 300+ images per class
* Data augmentation applied to increase diversity

---

## 🔄 5. Data Preprocessing

Each image undergoes:

* Resize → 224x224
* Normalization → pixel values [0,1]
* Augmentation:

  * Rotation
  * Horizontal flip
  * Zoom
  * Brightness adjustment

---

## 🏋️ 6. Training Process

### Phase 1: Feature Extraction

* Base model frozen
* Only classification head trained
* Learning rate: 0.001

### Phase 2: Fine-Tuning

* Top 30 layers unfrozen
* Learning rate: 0.00001
* Improves accuracy by adapting pretrained features

### Callbacks Used:

* ModelCheckpoint (save best model)
* EarlyStopping (avoid overfitting)
* ReduceLROnPlateau (dynamic learning rate)
* TensorBoard (visualization)

---

## 📊 7. Model Output

The model predicts probabilities:

```
[accident, normal, traffic_jam]
```

Example:

```
[0.82, 0.10, 0.08] → Accident detected (82%)
```

---

## 🎥 8. Real-Time Detection Module

### Workflow:

1. Open video source (webcam/video/RTSP)
2. Process every Nth frame (performance optimization)
3. Preprocess frame
4. Run model prediction
5. If accident detected:

   * Check confidence threshold (≥ 75%)
   * Apply cooldown (60 sec)
   * Send alert to backend API

---

## 🌐 9. Backend Integration

When an accident is detected:

* API Request sent to:

  ```
  POST /api/accidents
  ```

### Payload:

```json
{
  "location": "CAM-001 Zone",
  "severity": "high",
  "confidence": 0.87,
  "camera_id": "CAM-001"
}
```

### Backend Actions:

* Store in PostgreSQL (Neon DB)
* Broadcast via WebSocket
* Notify dashboard users

---

## ⚙️ 10. Key Features

* Real-time detection (1 inference/sec)
* Lightweight model (CPU compatible)
* Automatic alert system
* Cooldown to avoid duplicate alerts
* Scalable architecture

---

## ⚠️ 11. Challenges Faced

| Issue              | Solution                                 |
| ------------------ | ---------------------------------------- |
| OpenCV GUI error   | Replaced headless version                |
| SciPy import error | Installed in correct virtual environment |
| Dataset imbalance  | Used augmentation & multiple sources     |
| Wrong layer access | Fixed base_model reference               |
| Dashcam variation  | Added preprocessing improvements         |

---

## 🚀 12. Improvements Implemented

* Added RGB conversion for better accuracy
* Reduced frame processing load
* Improved confidence threshold tuning
* Structured dataset for better training
* Fixed fine-tuning layer issue

---

## 📈 13. Limitations

* Performance depends on dataset quality
* Less accurate in:

  * Low light
  * Motion blur
  * Extreme camera angles
* Cannot detect accident severity beyond confidence score

---

## 🔮 14. Future Enhancements

* Use object detection (YOLO) for better accuracy
* Multi-camera tracking system
* Accident severity estimation using scene understanding
* Integration with live CCTV feeds
* Edge deployment (Raspberry Pi / Jetson Nano)

---

## 🏁 15. Conclusion

The AI Module successfully demonstrates a **real-time accident detection system** using deep learning and computer vision.

It is:

* Efficient
* Scalable
* Practical for real-world deployment

This module plays a critical role in enabling **smart emergency response systems** and improving road safety.

---

## 👨‍💻 Developed By

* **Neha Dubey** – AI & ML Developer
* **Yash Agrawal** – AI & ML Developer**Neha Dubey** – AI & ML Developer
* **Abhishek Taur** – Full Stack AI Developer

---
