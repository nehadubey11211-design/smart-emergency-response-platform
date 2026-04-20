"""
File: backend/app/main.py
================================
FastAPI Application Entry Point
================================

FastAPI is a modern Python web framework built on top of Starlette (ASGI) and
Pydantic.  Key advantages over Flask/Django:
  - Native async/await support (non-blocking I/O)
  - Automatic OpenAPI (Swagger) and ReDoc documentation generation
  - Built-in request/response validation via Pydantic schemas
  - WebSocket support out of the box

INTERVIEW TALKING POINT:
  "I used FastAPI because it auto-generates interactive API docs from type hints,
  which made it easy for the team to understand and test endpoints. The native
  async support also lets us handle WebSocket connections and DB queries without
  blocking the event loop."
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal imports — using absolute paths relative to the 'app' package
from app.config.settings import settings
from app.database.db import engine, Base
from app.routes import auth, accidents, traffic, analytics


# ─── Application Lifespan ─────────────────────────────────────────────────────
# The lifespan context manager runs startup/shutdown logic.
# Using @asynccontextmanager is the modern FastAPI pattern (replaces @app.on_event).
# Everything BEFORE `yield` runs on startup; everything AFTER runs on shutdown.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create all database tables if they don't exist.
    In production you'd use Alembic migrations instead of create_all(),
    but create_all() is fine for development and demos.

    Shutdown: log a clean shutdown message (extend with cleanup tasks here,
    e.g. closing DB connection pools, flushing cache, etc.)
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    print("🚀 Starting Smart AI Emergency Response System...")
    # SQLAlchemy reads all imported models (via their Base.metadata) and creates
    # tables that don't yet exist.  It does NOT drop/alter existing tables.
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified / created")

    yield  # Application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────────
    print("🛑 Shutting down server — cleanup complete")


# ─── FastAPI Instance ─────────────────────────────────────────────────────────
# All metadata here (title, description, version) is exposed in the
# auto-generated Swagger UI at /docs and ReDoc at /redoc.

app = FastAPI(
    title="Smart AI Emergency Response API",
    description=(
        "Real-time accident detection and traffic signal management system. "
        "Powered by a CNN model that analyses live CCTV feeds and automatically "
        "creates green corridors for emergency vehicles."
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Disable default /docs if you want to protect them in production:
    # docs_url=None, redoc_url=None
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows the React app running on
# localhost:5173 to make requests to the API on localhost:8000.
# Without this, browsers block cross-origin requests by default.
#
# INTERVIEW TALKING POINT:
#   "In production I'd restrict allow_origins to the specific frontend domain
#    rather than using a wildcard, to prevent CSRF and data leakage."

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,   # List of permitted origins
    allow_credentials=True,                    # Allow cookies/auth headers
    allow_methods=["*"],                       # GET, POST, PATCH, DELETE, etc.
    allow_headers=["*"],                       # Authorization, Content-Type, etc.
)


# ─── Router Registration ──────────────────────────────────────────────────────
# Each router is defined in its own module following the Single Responsibility
# Principle.  The prefix groups all routes under a common URL namespace and
# tags group them in the Swagger UI.

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["🔐 Authentication"],
)

app.include_router(
    accidents.router,
    prefix="/api/accidents",
    tags=["🚨 Accidents"],
)

app.include_router(
    traffic.router,
    prefix="/api/traffic",
    tags=["🚦 Traffic Signals"],
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["📊 Analytics"],
)


# ─── Root Endpoints ───────────────────────────────────────────────────────────

@app.get("/", tags=["🏠 Root"])
async def root():
    """Landing endpoint — confirms the server is running."""
    return {
        "message": "Smart AI Emergency Response System is online 🚨",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "1.0.0",
    }


@app.get("/health", tags=["🏠 Root"])
async def health_check():
    """
    Health check endpoint — used by Docker, load balancers, and monitoring tools
    (e.g. AWS ELB, Kubernetes liveness probes) to determine if the app is alive.

    Returns 200 OK when healthy.  In production, extend this to check DB
    connectivity, cache availability, etc.
    """
    return {"status": "ok", "service": "emergency-response-api"}
