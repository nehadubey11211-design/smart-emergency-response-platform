# FILE: docs/architecture.md
# Smart AI Emergency Response System — Architecture

---

## System Overview

A three-tier architecture that connects live CCTV feeds to an operator dashboard through an AI detection engine and a real-time API server.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CCTV / Webcam Feed                          │
│                    (OpenCV VideoCapture — RTSP / USB)               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │  1 frame/second (every 30th frame)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        AI MODULE  (ai-module/)                      │
│                                                                     │
│   Frame  →  Preprocess  →  MobileNetV2 CNN  →  Softmax Output      │
│   (any)     224×224 RGB     (TensorFlow)        [normal|accident    │
│             float32 /255                         |traffic_jam]      │
│                                                                     │
│   If class == "accident" AND confidence >= 0.75:                   │
│       POST /api/accidents/   →  FastAPI Backend                     │
└─────────────────────────┬───────────────────────────────────────────┘
                          │  HTTP POST (JSON payload)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FASTAPI BACKEND  (backend/)                   │
│                                                                     │
│   Routes:   /api/auth      /api/accidents    /api/traffic           │
│             /api/analytics /api/accidents/ws (WebSocket)            │
│                                                                     │
│   Services: AlertService        → email notifications               │
│             TrafficService      → green corridor + IoT commands     │
│             NotificationService → SMS / Slack stubs                 │
│                                                                     │
│   ORM:  SQLAlchemy  →  PostgreSQL                                   │
│   Auth: JWT (PyJWT) + bcrypt                                        │
└──────┬──────────────────────────────────┬───────────────────────────┘
       │  SQL queries (SQLAlchemy ORM)    │  WebSocket broadcast
       ▼                                  ▼
┌──────────────────┐          ┌────────────────────────────────────┐
│   PostgreSQL DB  │          │      REACT DASHBOARD  (frontend/)  │
│                  │          │                                     │
│  Tables:         │          │  Pages: Home | Login | Dashboard    │
│  · users         │◄─────────│         Analytics | History        │
│  · accidents     │  REST API│                                     │
│  · traffic_      │  (axios) │  Real-time: WebSocket client       │
│    signals       │          │  Charts: Recharts                  │
└──────────────────┘          │  Styling: Tailwind CSS             │
                              └────────────────────────────────────┘
```

---

## Component Breakdown

### AI Module (`ai-module/`)

| File | Purpose |
|---|---|
| `train_model.py` | Two-phase transfer learning pipeline — trains MobileNetV2 on accident dataset |
| `detect_accident.py` | Real-time inference loop — reads frames, runs CNN, POSTs alerts |

**Model Architecture:**
```
MobileNetV2 (pretrained ImageNet, frozen)
    → GlobalAveragePooling2D   (1280,)
    → BatchNormalization
    → Dense(256, relu)
    → Dropout(0.3)
    → Dense(3, softmax)         [accident | normal | traffic_jam]
```

**Why MobileNetV2?**
- 3.4M parameters vs ResNet50's 25M — runs in real-time on CPU
- Pretrained on 1.2M ImageNet images — strong feature extraction out-of-box
- `include_top=False` lets us attach our own 3-class head

---

### Backend (`backend/app/`)

**Layered architecture — each layer has one responsibility:**

```
HTTP Request
    ↓
routes/        ← Thin handlers: validate input, call service, return response
    ↓
services/      ← Business logic: alert dispatch, green corridor, notifications
    ↓
models/        ← SQLAlchemy ORM: table definitions, relationships
    ↓
database/      ← Engine, session factory, connection pool
    ↓
PostgreSQL
```

**Key patterns used:**
- **Dependency Injection** (`Depends(get_db)`) — session scoped per request
- **Pydantic schemas** — separate validation from DB models (never leak passwords)
- **WebSocket ConnectionManager** — Observer pattern for live incident broadcast
- **Service layer** — business logic outside route handlers (testable in isolation)

---

### Frontend (`frontend/src/`)

```
pages/         ← Container components: own data fetching via custom hooks
    ↓ props
components/    ← Presentational components: receive data, emit callbacks
    ↑
hooks/         ← Custom hooks: encapsulate stateful data-fetching logic
services/      ← api.js (axios + interceptors) + socket.js (WebSocket client)
utils/         ← Pure helpers, constants, formatters
```

**State management:** Local `useState` + custom hooks — no Redux needed.  
React's unidirectional data flow: data flows down as props, changes bubble up as callbacks.

---

## Data Flow — Accident Detection to Dashboard

```
1.  Camera frame captured by OpenCV (1fps)
2.  Frame preprocessed: resize 224×224, normalise to [0,1]
3.  MobileNetV2 inference: output = [0.02, 0.97, 0.01]
4.  argmax → class "accident", confidence 0.97 > threshold 0.75
5.  POST /api/accidents/  { location, severity, confidence, camera_id }
6.  FastAPI saves accident to PostgreSQL
7.  FastAPI broadcasts via WebSocket:
      { type: "NEW_ACCIDENT", data: { id, location, severity } }
8.  All connected dashboards receive message < 100ms
9.  Dashboard shows red flash banner + adds card to feed
10. AlertService sends email to operator
11. Operator clicks "Green Corridor" button
12. TrafficService sets all signals along ambulance route to EMERGENCY mode
13. IoT command sent to each physical signal controller
14. After 5 minutes: auto-reset all signals to AUTO mode
```

---

## Database Schema

```
users
  id, name, email (unique), password (bcrypt), role, is_active, created_at

accidents
  id, location, latitude, longitude
  severity ENUM(low|medium|high|critical)
  status   ENUM(detected|responding|resolved)
  confidence, camera_id, image_path, description
  detected_at (indexed), resolved_at

traffic_signals
  id, signal_id (unique), location, latitude, longitude
  current_mode ENUM(auto|emergency|manual)
  is_online, last_update
```

**Indexes:** `accidents.status`, `accidents.detected_at DESC`, `accidents.severity`, `accidents.camera_id`

---

## Technology Decisions

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI | Native async, WebSocket support, auto Swagger docs, Pydantic validation |
| Database | PostgreSQL | ENUM types, TIMESTAMPTZ, ACID, great for geospatial (PostGIS extension) |
| ORM | SQLAlchemy | Pythonic, works with Alembic migrations, DB-agnostic for testing |
| Auth | JWT + bcrypt | Stateless (horizontally scalable), bcrypt's cost factor resists brute force |
| AI | TensorFlow + MobileNetV2 | Runs on CPU in real-time, transfer learning with minimal data |
| Video | OpenCV | Industry standard for video capture and frame processing |
| Frontend | React 18 | Component model, hooks, large ecosystem |
| Styling | Tailwind CSS | Utility-first, consistent spacing scale, tiny prod bundle via purge |
| Charts | Recharts | React-native, composable, dark theme friendly |
| Real-time | Native WebSocket | No Socket.IO overhead — we only need server→client push |
| Build | Vite | 10× faster HMR than Webpack/CRA, native ES modules |
| Deploy | Docker Compose | One-command startup, environment parity, portable |

---

## Scalability Considerations

| Concern | Current (Demo) | Production Upgrade |
|---|---|---|
| WebSocket connections | In-memory list | Redis Pub/Sub (share connections across servers) |
| Signal commands | Mock print() | MQTT broker (Eclipse Mosquitto) |
| Route computation | All signals activated | Google Maps Directions API + PostGIS ST_DWithin() |
| Background tasks | asyncio.create_task | Celery + Redis (survives server restarts) |
| DB migrations | create_all() | Alembic versioned migrations |
| Model serving | In-process TF | TensorFlow Serving / TorchServe microservice |
| Auth tokens | No revocation | Redis token blacklist or short TTL + refresh tokens |
