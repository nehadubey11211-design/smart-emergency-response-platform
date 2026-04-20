# FILE: docs/project_report.md
# Smart AI Emergency Response System — Project Report

---

## 1. Problem Statement

Every minute counts in a road accident. Two core problems slow emergency response in Indian cities:

**Problem 1 — Delayed Detection**  
Accidents are reported by passersby or witnesses — often 3–10 minutes after they happen. This delay directly increases injury severity and fatality rates.

**Problem 2 — Traffic Signal Inefficiency**  
Ambulances face the same red lights as other traffic. A study by the Indian Journal of Critical Care Medicine found that ambulance response times in metro cities average 18–22 minutes — far above the international golden standard of 8 minutes.

**This system solves both problems:**
- AI detects accidents automatically from existing CCTV infrastructure in under 1 second
- Traffic signals along the ambulance route switch to green automatically within seconds of dispatch

---

## 2. Objectives

| Objective | Implementation | Status |
|---|---|---|
| Real-time accident detection | MobileNetV2 CNN on live video frames | ✅ |
| Sub-second operator alerts | WebSocket push notifications | ✅ |
| Automated green corridor | Traffic signal IoT control API | ✅ |
| Operator dashboard | React SPA with live data | ✅ |
| Historical analytics | PostgreSQL aggregation + Recharts | ✅ |
| Secure multi-user access | JWT + bcrypt + role-based access | ✅ |
| One-command deployment | Docker Compose | ✅ |
| Automated testing | pytest + SQL + manual checklist | ✅ |

---

## 3. System Architecture

See [architecture.md](architecture.md) for the full diagram.

**Summary:** Three-tier architecture:
- **Presentation tier:** React 18 SPA with Tailwind CSS, Recharts, WebSocket client
- **Application tier:** FastAPI async server — REST endpoints + WebSocket broadcast
- **Data tier:** PostgreSQL with SQLAlchemy ORM, ENUM constraints, indexed queries

---

## 4. AI/ML Component

### Model Choice: MobileNetV2

MobileNetV2 was chosen over alternatives for these reasons:

| Model | Parameters | ImageNet Accuracy | Inference (CPU) |
|---|---|---|---|
| VGG16 | 138M | 71.5% | ~500ms |
| ResNet50 | 25M | 74.9% | ~150ms |
| **MobileNetV2** | **3.4M** | **71.8%** | **~30ms** ✅ |
| EfficientNetB0 | 5.3M | 77.1% | ~45ms |

MobileNetV2 offers near-best accuracy at a fraction of the compute cost — critical for real-time inference on CPU hardware typically found in traffic management centres.

### Transfer Learning Strategy

**Phase 1 — Head Training (20 epochs):**
- Base MobileNetV2 layers frozen
- Only the custom 3-class head trained
- Learning rate: 1e-3 (safe, only small head)
- Purpose: Quickly adapt to accident domain

**Phase 2 — Fine-tuning (10 epochs):**
- Last 30 layers of base unfrozen
- Learning rate: 1e-5 (gentle nudge)
- Purpose: Adapt high-level features to accident-specific patterns

**Data Augmentation:** Random rotation (±15°), horizontal flip, brightness variation, zoom — artificially expands training set and prevents overfitting to specific camera angles.

### Inference Pipeline

```
Raw frame (640×480, BGR, uint8)
  → cv2.resize(224, 224)
  → float32 / 255.0          (normalise to [0, 1])
  → expand_dims(axis=0)      (add batch dimension)
  → model.predict()          (shape: [1, 3])
  → argmax()                 → class label
  → confidence >= 0.75?      → trigger alert
```

---

## 5. Backend Architecture

### Why FastAPI over Django/Flask?

| Feature | FastAPI | Flask | Django |
|---|---|---|---|
| Async support | Native | Plugin | Plugin |
| WebSocket | Built-in | Flask-SocketIO | Django Channels |
| Auto Swagger docs | ✅ | ❌ | ❌ |
| Pydantic validation | ✅ | ❌ | ❌ |
| Performance | Very high | Medium | Medium |

### Key Design Patterns

**Service Layer Pattern:**  
Route handlers are thin — they validate input, call a service function, and return a response. All business logic (email sending, route computation, IoT commands) lives in `services/`. This makes services independently testable without HTTP context.

**Repository Pattern (via SQLAlchemy):**  
DB queries are in the route/service layer rather than a separate repository class (simplified for project scope). In production, a dedicated repository layer would further isolate DB logic.

**Observer Pattern (WebSocket):**  
`ConnectionManager` maintains a list of subscribers. When `POST /accidents/` is called, it broadcasts to all subscribers. The AI module is the publisher; dashboard clients are subscribers.

---

## 6. Frontend Architecture

### Component Hierarchy

```
App (router)
├── Home (public landing page)
├── Login (public auth page)
└── ProtectedRoute (auth guard)
    ├── Navbar (sidebar navigation)
    └── Pages:
        ├── Dashboard
        │   ├── StatusPanel (WebSocket status)
        │   ├── AnalyticsCard × 4 (KPI summary)
        │   ├── AlertCard × N (incident cards)
        │   └── TrafficPanel (signal control)
        ├── Analytics
        │   ├── AnalyticsCard × 4
        │   ├── AreaChart (trend)
        │   └── PieChart (severity)
        └── History
            └── Table (paginated incident log)
```

### State Management

No Redux or Zustand — React's built-in state is sufficient:
- **Server state:** Custom hooks (`useAccidents`, `useAnalytics`) with `useEffect` + `useState`
- **UI state:** Local `useState` in each component (filters, loading, errors)
- **Real-time state:** WebSocket events via `socketService.on()` trigger `refetch()`

---

## 7. Database Design

### Why PostgreSQL ENUM Types?

```sql
CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high', 'critical');
```

Inserting an invalid value (`'extreme'`) throws an error at the database level — even if someone bypasses the API and writes directly to the DB. This is a stronger guarantee than application-level validation alone.

### Index Strategy

```sql
CREATE INDEX idx_accidents_status      ON accidents(status);
CREATE INDEX idx_accidents_detected_at ON accidents(detected_at DESC);
```

Without these, `WHERE status = 'detected'` and `ORDER BY detected_at DESC` would require full table scans. With indexes, these are O(log n) lookups — critical for a dashboard that queries these on every page load.

---

## 8. Security Measures

| Threat | Mitigation |
|---|---|
| Password theft | bcrypt with 12 rounds — brute force takes years |
| JWT forgery | HMAC-SHA256 signature with secret key |
| User enumeration | Same 401 response for "user not found" and "wrong password" |
| Timing attacks | `bcrypt.checkpw()` uses constant-time comparison |
| SQL injection | SQLAlchemy parameterised queries — never raw SQL strings |
| CORS | Explicit allowed origins list in settings |
| Secret leakage | All secrets in `.env` file (gitignored) |
| Docker privilege | Non-root user in Dockerfile |

---

## 9. Testing Strategy

| Layer | Tool | Type | What's Tested |
|---|---|---|---|
| Backend | pytest + FastAPI TestClient | Unit/Integration | Auth flow, CRUD, analytics queries |
| Database | PostgreSQL DO blocks | Integration | ENUM constraints, NOT NULL, indexes |
| AI Module | pytest | Unit | Output shape, probability validity, threshold logic |
| Frontend | Manual checklist | E2E | All user flows, WebSocket, responsive layout |

**Test isolation:** Backend tests use an in-memory SQLite database via FastAPI's dependency override system — no real PostgreSQL needed to run tests.

---

## 10. Future Enhancements

| Feature | Description | Complexity |
|---|---|---|
| GPS ambulance tracking | Show live ambulance position on map using Leaflet.js | Medium |
| Route computation | Integrate Google Maps Directions API for real corridor routing | Medium |
| Multi-camera dashboard | Live feeds from multiple cameras in a grid view | High |
| YOLOv8 detection | Upgrade from classification to object detection — bounding boxes + vehicle count | High |
| Mobile app | React Native app for field operators with push notifications | High |
| ANPR integration | Automatic Number Plate Recognition for stolen vehicle alerts | High |
| PostGIS spatial queries | ST_DWithin() to find signals within 50m of ambulance route polyline | Medium |
| Celery task queue | Replace asyncio.create_task() with Celery + Redis for reliable background jobs | Medium |
| Redis Pub/Sub | Replace in-memory WebSocket list with Redis for multi-server deployments | Medium |

---

## 11. Limitations

1. **AI model requires training data** — The model's accuracy depends entirely on the quality and quantity of labelled training images. Without a proper dataset, the model won't generalise well.

2. **Green corridor uses mock routing** — The current implementation activates ALL signals rather than only those along the optimal route. Production requires Google Maps Directions API + PostGIS.

3. **WebSocket not authenticated** — The `/ws` endpoint accepts any connection. In production, pass the JWT in the WebSocket handshake URL or `Sec-WebSocket-Protocol` header.

4. **Single-server WebSocket** — The in-memory `ConnectionManager` only works on a single server process. Horizontal scaling requires Redis Pub/Sub.

5. **IoT commands are simulated** — `send_signal_command()` prints to console. Real deployment requires MQTT broker + physical signal controllers.
