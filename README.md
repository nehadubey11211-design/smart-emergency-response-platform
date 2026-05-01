
# 🚨 Smart AI Emergency Response System

> **A full-stack, production-grade system that uses Computer Vision to detect road
> accidents in real-time and automatically manages traffic signals to create
> green corridors for ambulances.**

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16-FF6F00)](https://tensorflow.org)
[![Neon PostgreSQL](https://img.shields.io/badge/Neon%20PostgreSQL-15-336791)](https://neon.tech)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](https://docker.com)

---

## 📌 Project Summary  *(Read this before interviews)*

This project demonstrates a range of skills interviewers look for:

| Skill Area | What This Project Shows |
|---|---|
| **Full-Stack Development** | React SPA + FastAPI REST server + Neon PostgreSQL |
| **Machine Learning** | Transfer learning (MobileNetV2) for real-time video classification |
| **Real-Time Systems** | WebSocket-based live incident broadcasting |
| **System Design** | Clean 3-tier layered architecture with separation of concerns |
| **API Design** | RESTful routes, Pydantic validation, auto-generated Swagger docs |
| **Authentication** | JWT-based stateless auth with bcrypt password hashing |
| **DevOps** | Multi-container Docker Compose with health checks |
| **Testing** | pytest unit tests, SQL integrity checks, frontend checklist |
| **Software Engineering** | DB migrations, error handling, environment configs, logging |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│   CCTV / Webcam                                                 │
│        ↓  OpenCV reads frames at 1fps                           │
│   ┌─────────────────────────────────┐                           │
│   │  AI Module  (ai-module/)        │                           │
│   │  MobileNetV2 CNN classifier     │                           │
│   │  Classes: normal|accident|jam   │                           │
│   └──────────────┬──────────────────┘                           │
│                  │  POST /api/accidents/  (confidence > 75%)    │
│   ┌──────────────▼──────────────────┐                           │
│   │  FastAPI Backend  (backend/)    │◄──── React Dashboard      │
│   │  Routes / Services / Models     │      (WebSocket + REST)   │
│   └──────────────┬──────────────────┘                           │
│                  │  SQLAlchemy ORM                              │
│   ┌──────────────▼──────────────────┐                           │
│   │  Neon PostgreSQL Database       │                           │
│   │  users | accidents | signals    │                           │
│   └─────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Docker (one command)
```bash
git clone <repo-url>
cd smart-ai-emergency-response-system/deployment
docker-compose up --build
```

### Manual setup
```bash
# 1. Setup Neon Database
- Create project at https://neon.tech
- Copy DATABASE_URL

# 2. Run migrations
psql $DATABASE_URL -f database/schema.sql
psql $DATABASE_URL -f database/seed.sql
# 2. Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev

# 4. AI Detection (after training)
cd ai-module && python train_model.py   # one-time
python detect_accident.py              # start detection
```

---

## 🌐 URLs

| URL | Description |
|---|---|
| http://localhost:5173 | React Dashboard |
| http://localhost:8000/docs | Swagger API Docs |
| http://localhost:8000/redoc | ReDoc API Docs |

**Default login:** `admin@emergency.com` / `admin123`

---

## 📁 Folder Structure

```
smart-ai-emergency-response-system/
├── frontend/           React 18 + Tailwind + Recharts + WebSocket
│   └── src/
│       ├── components/ Reusable UI (AlertCard, TrafficPanel, etc.)
│       ├── pages/      Route-level views (Dashboard, Analytics, etc.)
│       ├── services/   API calls (axios) + WebSocket client
│       ├── hooks/      Custom React hooks (useAccidents, useAnalytics)
│       └── utils/      Shared helpers and constants
│
├── backend/            FastAPI + SQLAlchemy + JWT
│   └── app/
│       ├── routes/     HTTP + WebSocket endpoint handlers
│       ├── services/   Business logic layer
│       ├── models/     SQLAlchemy DB models
│       ├── schemas/    Pydantic request/response validators
│       ├── database/   DB engine + session factory
│       └── config/     Environment-based settings
│
├── ai-module/          TensorFlow/Keras CNN
│   ├── train_model.py  MobileNetV2 transfer learning pipeline
│   └── detect_accident.py  Real-time OpenCV + inference loop
│
├── database/           Neon PostgreSQL
│   ├── schema.sql      Table definitions + ENUM types
│   ├── seed.sql        Development data
│   └── migrations/     Alembic migration environment
│
├── deployment/         Docker
│   ├── Dockerfile      Multi-stage backend image
│   └── docker-compose.yml  Full stack orchestration
│
├── tests/              Test suite
└── docs/               Architecture, API reference, project report
```

---

## 🧪 Tests

```bash
cd backend
pytest ../tests/test_backend.py -v          # API + auth + DB tests
pytest ../tests/test_ai_model.py -v         # Model output shape + logic tests
psql -U postgres -d emergency_db -f ../tests/test_database.sql
```

---

## 🔑 Key Design Decisions

| Decision | Rationale |
|---|---|
| FastAPI over Django/Flask | Native async/await, auto Swagger docs, Pydantic schema validation |
| MobileNetV2 transfer learning | Runs on CPU in real-time, good accuracy with limited data |
| WebSocket over polling | Sub-second push for life-critical alerts; polling adds 5-30s delay |
| JWT stateless auth | No session storage on server — horizontally scalable |
| Neon PostgreSQL ENUM types | Validity enforced at DB level, not just application level |
| Pydantic schemas | Separate request/response validation from DB models |
| Service layer pattern | Keeps route handlers thin and business logic testable |
| Docker Compose | Reproducible dev environment; works on any machine |

---

## 📄 Documentation
- [System Architecture](docs/architecture.md)
- [API Reference](docs/api_docs.md)
- [Deployment Guide](docs/deployment_guide.md)
- [Project Report](docs/project_report.md)
