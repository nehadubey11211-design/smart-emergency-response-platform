# FILE: docs/api_docs.md
# Smart AI Emergency Response System — API Reference

**Base URL:** `http://localhost:8000/api`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)  
**ReDoc:** `http://localhost:8000/redoc`

---

## Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
```

Obtain a token via `/api/auth/login` or `/api/auth/register`.

---

## 🔐 Auth Endpoints

### POST `/api/auth/register`
Register a new operator account.

**Request body:**
```json
{
  "name": "Alice",
  "email": "alice@emergency.com",
  "password": "securepassword",
  "role": "operator"
}
```

**Response `201`:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Alice",
    "email": "alice@emergency.com",
    "role": "operator",
    "is_active": true,
    "created_at": "2024-04-20T10:00:00Z"
  }
}
```

**Errors:** `400` Email already registered

---

### POST `/api/auth/login`
Authenticate and receive a JWT.

**Request body:**
```json
{
  "email": "alice@emergency.com",
  "password": "securepassword"
}
```

**Response `200`:** Same structure as `/register`

**Errors:** `401` Invalid credentials | `403` Account deactivated

---

### GET `/api/auth/me?token=<jwt>`
Get the currently authenticated user's profile.

**Response `200`:** User object (no password field)

---

## 🚨 Accident Endpoints

### GET `/api/accidents/`
List accidents, newest first.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | — | Filter: `detected` \| `responding` \| `resolved` |
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Pagination limit (max 100) |

**Response `200`:**
```json
[
  {
    "id": 5,
    "location": "MG Road Junction, Pune",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "severity": "critical",
    "status": "detected",
    "confidence": 0.97,
    "camera_id": "CAM-001",
    "description": "Multi-vehicle collision",
    "detected_at": "2024-04-20T10:05:00Z",
    "resolved_at": null,
    "response_time_minutes": null
  }
]
```

---

### POST `/api/accidents/`
Report a new accident. Called by the AI module (`detect_accident.py`).

**Request body:**
```json
{
  "location": "MG Road Junction, Pune",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "severity": "high",
  "confidence": 0.92,
  "camera_id": "CAM-001",
  "description": "Auto-detected by AI at 10:05:00"
}
```

**Response `201`:** Full accident object

**Side effects on success:**
- Broadcasts `NEW_ACCIDENT` to all WebSocket clients
- Sends email alert if SMTP is configured
- Logs to console

---

### GET `/api/accidents/{id}`
Get a single accident by ID.

**Response `200`:** Accident object  
**Errors:** `404` Not found

---

### PATCH `/api/accidents/{id}`
Partial update — only include fields you want to change.

**Request body (all fields optional):**
```json
{
  "status": "resolved",
  "severity": "critical",
  "description": "Scene cleared at 11:30"
}
```

**Response `200`:** Updated accident object  
When `status` is set to `"resolved"`, `resolved_at` is auto-stamped.

---

### DELETE `/api/accidents/{id}`
Hard delete an accident record.

**Response `204`:** No content  
**Note:** Prefer soft-deletes in production — this endpoint is for dev cleanup only.

---

### WS `/api/accidents/ws`
WebSocket endpoint for real-time incident alerts.

**Connect (JavaScript):**
```javascript
const ws = new WebSocket("ws://localhost:8000/api/accidents/ws");
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  // msg.type === "NEW_ACCIDENT"
  // msg.data === { id, location, severity, confidence, detected_at }
};
```

**Message format:**
```json
{
  "type": "NEW_ACCIDENT",
  "data": {
    "id": 5,
    "location": "MG Road Junction",
    "severity": "critical",
    "confidence": 0.97,
    "detected_at": "2024-04-20T10:05:00Z"
  }
}
```

---

## 🚦 Traffic Signal Endpoints

### GET `/api/traffic/signals`
List all registered traffic signals.

**Response `200`:**
```json
[
  {
    "signal_id": "SIG-001",
    "location": "MG Road Junction",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "current_mode": "auto",
    "is_online": true,
    "last_update": "2024-04-20T10:00:00Z"
  }
]
```

---

### POST `/api/traffic/signals/{signal_id}/emergency`
Switch a signal to `EMERGENCY` mode (green corridor).

**Response `200`:**
```json
{
  "message": "Signal SIG-001 activated to EMERGENCY mode",
  "signal_id": "SIG-001",
  "new_mode": "emergency"
}
```

**Errors:** `404` Signal not found | `503` Signal offline

---

### POST `/api/traffic/signals/{signal_id}/reset`
Return a signal to normal `AUTO` mode.

**Response `200`:**
```json
{
  "message": "Signal SIG-001 reset to AUTO mode",
  "signal_id": "SIG-001",
  "new_mode": "auto"
}
```

---

### POST `/api/traffic/green-corridor?accident_id=1&hospital_id=HOSP-001`
Compute ambulance route and activate all signals along it.

**Query params:**
| Param | Type | Required | Description |
|---|---|---|---|
| `accident_id` | int | ✅ | ID of the accident to route from |
| `hospital_id` | string | ✅ | Target hospital identifier |

**Response `200`:**
```json
{
  "message": "Green corridor activated",
  "accident_id": 1,
  "hospital_id": "HOSP-001",
  "activated_signals": ["SIG-001", "SIG-002", "SIG-003"],
  "failed_signals": [],
  "auto_reset_in_s": 300
}
```

---

### POST `/api/traffic/reset-corridor`
Reset all signals currently in EMERGENCY mode back to AUTO.

**Response `200`:**
```json
{
  "message": "Reset 3 signals to AUTO mode",
  "reset_count": 3
}
```

---

## 📊 Analytics Endpoints

### GET `/api/analytics/summary`
Dashboard KPI summary.

**Response `200`:**
```json
{
  "total_today": 5,
  "active_incidents": 2,
  "resolved_today": 3,
  "avg_response_time_minutes": 14.2
}
```

---

### GET `/api/analytics/severity-breakdown`
Accident count grouped by severity (pie chart data).

**Response `200`:**
```json
[
  { "severity": "critical", "count": 2 },
  { "severity": "high",     "count": 5 },
  { "severity": "medium",   "count": 8 },
  { "severity": "low",      "count": 3 }
]
```

---

### GET `/api/analytics/trends?days=7`
Daily accident counts for the last N days (line chart data).

**Query params:** `days` (int, default `7`, max `365`)

**Response `200`:**
```json
[
  { "date": "2024-04-14", "count": 2 },
  { "date": "2024-04-15", "count": 5 },
  { "date": "2024-04-16", "count": 1 }
]
```

---

### GET `/api/analytics/status-breakdown`
Accident count grouped by status.

**Response `200`:**
```json
[
  { "status": "detected",   "count": 3 },
  { "status": "responding", "count": 1 },
  { "status": "resolved",   "count": 14 }
]
```

---

### GET `/api/analytics/hotspots?limit=10`
Top locations by accident frequency.

**Response `200`:**
```json
[
  { "location": "MG Road Junction, Pune", "total": 8 },
  { "location": "FC Road & Bhandarkar",   "total": 5 }
]
```

---

## 🩺 Health Endpoints

### GET `/`
Root endpoint — confirms server is running.

**Response `200`:**
```json
{
  "message": "Smart AI Emergency Response System is online 🚨",
  "docs": "/docs",
  "version": "1.0.0"
}
```

---

### GET `/health`
Health check for Docker, load balancers, and monitoring tools.

**Response `200`:**
```json
{ "status": "ok", "service": "emergency-response-api" }
```

---

## Error Response Format

All error responses follow this format:
```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Code | Meaning |
|---|---|
| `400` | Bad Request — invalid input data |
| `401` | Unauthorized — missing or invalid/expired JWT |
| `403` | Forbidden — valid token but insufficient permissions |
| `404` | Not Found — resource doesn't exist |
| `422` | Unprocessable Entity — Pydantic validation failed |
| `503` | Service Unavailable — e.g. signal controller offline |
