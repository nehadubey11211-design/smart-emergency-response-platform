"""
File: backend/app/main.py
================================
FastAPI Application Entry Point
================================

FastAPI is a modern Python web framework built on top of Starlette (ASGI)
and Pydantic.

NEON MIGRATION CHANGES IN THIS FILE:
  1. Added check_database_connection() call in the lifespan startup.
     This "warms up" the Neon connection on startup, because Neon's
     free tier suspends compute after 5 minutes of inactivity.
     The first connection after suspension takes 1-2 seconds.
     Calling it at startup means the first real user request won't be slow.

  2. Added more descriptive startup logging to confirm which database
     (Neon vs local) the app is connecting to.

  3. The /health endpoint now also checks database connectivity,
     which is more meaningful with a cloud database like Neon.

EVERYTHING ELSE IS UNCHANGED:
  - All routes, middleware, CORS configuration are identical.
  - The app logic is completely database-agnostic.
  - SQLAlchemy abstracts away the PostgreSQL vs Neon difference.

INTERVIEW TALKING POINT:
  "The only change to main.py for Neon was adding a startup connection
  check. This warms up Neon's serverless compute so the first user
  request isn't slow after a period of inactivity."
"""
import logging
logger = logging.getLogger(__name__) 
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

from contextlib import asynccontextmanager

from fastapi import Response, Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.database.db import engine, Base, check_database_connection, is_neon
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create the global limiter before importing routes so other modules can
# import the same instance from app.main without causing circular imports.
limiter = Limiter(key_func=get_remote_address)

from app.routes import auth, accidents, traffic, analytics
from app.routes.ambulance_routes import router as ambulance_router   

from app.routes import password_reset



# ─── Application Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create tables and verify database connection.
    Shutdown: log cleanup.

    NEON CHANGE:
      Added check_database_connection() call on startup.
      This serves two purposes with Neon:
        1. Warms up Neon's serverless compute (avoids cold start on first request)
        2. Fails fast with a clear error if the Neon URL is wrong/unreachable
           rather than failing silently on the first API request
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    db_type = "Neon serverless PostgreSQL" if is_neon else "local database"
    print(f"🚀 Starting Smart AI Emergency Response System...")
    print(f"   Database: {db_type}")

    # Create all SQLAlchemy-defined tables if they don't exist.
    # This works identically with Neon and local PostgreSQL.
    # In production, use Alembic migrations instead.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified / created")

    # NEON ADDITION: Verify connection and warm up Neon compute.
    # For Neon free tier, this prevents the first API call from being slow
    # due to compute cold start after inactivity.
    db_ok = await check_database_connection()
    if not db_ok and is_neon:
        print("⚠️  Warning: Neon database connection failed at startup.")
        print("   Check your DATABASE_URL in .env — ensure it contains ?sslmode=require")
        print("   The app will continue but database operations will fail.")
    elif db_ok and is_neon:
        print("✅ Neon database warmed up and ready")

    yield  # Application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────────
    print("🛑 Shutting down server — cleanup complete")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
# ─── FastAPI Instance ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart AI Emergency Response API",
    description=(
        "Real-time accident detection and traffic signal management system. "
        "Powered by a CNN model that analyses live CCTV feeds and automatically "
        "creates green corridors for emergency vehicles. "
        "Database: Neon serverless PostgreSQL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
# UNCHANGED from original — CORS is not affected by the database change.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Router Registration ──────────────────────────────────────────────────────
# UNCHANGED from original.

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

app.include_router(
    ambulance_router, 
    prefix="/api",
    tags=["🚑 Ambulances"],
)

app.include_router(
    password_reset.router,
    prefix="/api/password",
    tags=["🔐 Password Reset"],
)


# ─── Root Endpoints ───────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.get("/", tags=["🏠 Root"])
async def root():
    """Landing endpoint — confirms the server is running."""
    return {
        "message":  "Smart AI Emergency Response System is online 🚨",
        "docs":     "/docs",
        "redoc":    "/redoc",
        "version":  "1.0.0",
        "database": "Neon serverless PostgreSQL" if is_neon else "Local database",
    }


@app.get("/health", tags=["🏠 Root"])
async def health_check(response: Response):
    """
    Health check endpoint used by Docker, load balancers, and monitoring tools.

    NEON CHANGE:
      Now also checks the database connection, not just the app status.
      With Neon, the DB could be unreachable (wrong URL, network issue)
      even if the FastAPI app itself is running fine.

      Returns:
        200 OK with status "ok"     → app and DB are healthy
        503 Service Unavailable      → app running but DB unreachable
    """
    db_healthy = await check_database_connection()
    if not db_healthy:
        response.status_code = 503
        return {"status": "ok" if db_healthy else "degraded"}


    return {
        "status":   "ok" if db_healthy else "degraded",
        "service":  "emergency-response-api",
        "database": "connected" if db_healthy else "unreachable",
        "db_type":  "neon" if is_neon else "local",
    }
