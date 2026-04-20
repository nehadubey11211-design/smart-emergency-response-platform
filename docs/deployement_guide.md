# FILE: docs/deployment_guide.md
# Deployment Guide

---

## Option A — Docker Compose (Recommended)

One command starts the entire stack: PostgreSQL + FastAPI + React.

```bash
# Clone the repository
git clone <your-repo-url>
cd smart-ai-emergency-response-system

# Start all services
cd deployment
docker-compose up --build

# To run in background (detached mode)
docker-compose up --build -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Stop everything
docker-compose down

# Stop and delete database data (full reset)
docker-compose down -v
```

**Access points after startup:**

| Service | URL |
|---|---|
| React Dashboard | http://localhost:5173 |
| FastAPI REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PostgreSQL | localhost:5432 |

---

## Option B — Manual (Development)

### Step 1: PostgreSQL

```bash
# Install PostgreSQL 15 (Ubuntu/Debian)
sudo apt install postgresql-15

# Or macOS with Homebrew
brew install postgresql@15

# Create the database
createdb emergency_db

# Apply schema and seed data
psql -U postgres -d emergency_db -f database/schema.sql
psql -U postgres -d emergency_db -f database/seed.sql
```

---

### Step 2: Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
# or: venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env.local             # Edit DATABASE_URL if needed

# Start the server
uvicorn app.main:app --reload --port 8000
```

The `--reload` flag watches for file changes and restarts automatically (dev only).

---

### Step 3: Frontend

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8000` automatically (configured in `vite.config.js`).

---

### Step 4: AI Module

```bash
cd ai-module

# 1. Collect training images:
#    Put accident images in:  dataset/accident/
#    Put normal images in:    dataset/normal/
#    Put traffic jam images:  dataset/traffic_jam/
#    Aim for 200+ images per class

# 2. Train the model (one-time, ~10-30 minutes on CPU)
python train_model.py

# 3. Start real-time detection
python detect_accident.py

# Optional: watch training progress
tensorboard --logdir model/logs
```

---

## Environment Variables Reference

### `backend/.env`

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/emergency_db` | PostgreSQL connection string |
| `SECRET_KEY` | `dev-only-secret...` | JWT signing key — **CHANGE IN PRODUCTION** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token expiry (24 hours) |
| `DEBUG` | `true` | Enables hot-reload and verbose errors |
| `CONFIDENCE_THRESHOLD` | `0.75` | Minimum AI confidence to trigger alert |
| `SMTP_USER` | *(empty)* | Gmail address for email alerts |
| `SMTP_PASSWORD` | *(empty)* | Gmail app password |

### `frontend/.env`

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | Backend REST API base URL |
| `VITE_WS_URL` | `ws://localhost:8000/api/accidents/ws` | WebSocket URL |

---

## Running Tests

```bash
# Backend unit tests (no external services needed — uses SQLite)
cd backend
pytest ../tests/test_backend.py -v

# AI model tests (requires trained model)
pytest ../tests/test_ai_model.py -v

# Database integrity tests
psql -U postgres -d emergency_db -f tests/test_database.sql

# Frontend manual QA
# Open tests/test_frontend.md and check each item
```

---

## Production Checklist

Before going to production, complete ALL of these:

### Security
- [ ] Change `SECRET_KEY` to a long random string: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set `DEBUG=false` in backend environment
- [ ] Use a strong PostgreSQL password (not `postgres`)
- [ ] Set `ALLOWED_ORIGINS` to your specific frontend domain only
- [ ] Run the backend as a non-root user (Dockerfile already does this)
- [ ] Enable HTTPS — use nginx + Let's Encrypt (Certbot)

### Infrastructure
- [ ] Set `uvicorn` workers to CPU count: `--workers $(nproc)`
- [ ] Configure PostgreSQL connection pool size to match worker count
- [ ] Set up daily database backups (pg_dump to S3)
- [ ] Configure Docker restart policies (`restart: always`)
- [ ] Set up health monitoring (UptimeRobot, Datadog, or Prometheus)

### AI Module
- [ ] Replace webcam (`VIDEO_SOURCE=0`) with real RTSP camera streams
- [ ] Deploy detect_accident.py as a systemd service for auto-restart
- [ ] Set `CAMERA_ID` per camera to identify alerts by location

### Notifications
- [ ] Configure `SMTP_USER` and `SMTP_PASSWORD` for real email alerts
- [ ] Optionally enable Twilio SMS (see `notification_service.py`)
- [ ] Optionally enable Slack webhooks (see `notification_service.py`)

---

## Useful Commands

```bash
# Reset database (drop all data, re-apply schema + seed)
psql -U postgres -c "DROP DATABASE IF EXISTS emergency_db;"
psql -U postgres -c "CREATE DATABASE emergency_db;"
psql -U postgres -d emergency_db -f database/schema.sql
psql -U postgres -d emergency_db -f database/seed.sql

# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Run Alembic migration (after changing a model)
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head

# Build production frontend bundle
cd frontend && npm run build
# Output is in frontend/dist/ — serve with nginx or any static file server

# Test the WebSocket manually
curl -X POST http://localhost:8000/api/accidents/ \
  -H "Content-Type: application/json" \
  -d '{"location":"Test Junction","severity":"critical","confidence":0.97,"camera_id":"CAM-TEST"}'
# Watch the dashboard for the real-time alert banner
```
