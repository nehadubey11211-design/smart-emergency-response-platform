"""
FILE: backend/app/database/db.py
=======================================
Database Engine, Session Factory & Base Model
=======================================

SQLAlchemy is the most popular Python ORM (Object-Relational Mapper).
It maps Python classes (models) to database tables and Python objects to rows.

KEY CONCEPTS used here:
  - Engine    : The core interface to the database. Holds the connection pool.
  - Session   : A unit of work. All DB operations (SELECT, INSERT, etc.) go
                through a Session. Changes are committed or rolled back together.
  - Base      : The declarative base class. All model classes inherit from it.
                SQLAlchemy uses Base.metadata to track all registered table schemas.

NEON DATABASE MIGRATION CHANGES:
  When migrating from local PostgreSQL to Neon (serverless PostgreSQL),
  the following changes are required in this file:

  1. SSL ENFORCEMENT:
     Neon REQUIRES SSL on all connections. We pass SSL settings via
     connect_args when the DATABASE_URL points to Neon.
     Without this, you'll get:
       SSL connection required. Please use SSL.

  2. POOL CONFIGURATION:
     Neon suspends inactive compute after 5 minutes (free tier).
     pool_pre_ping=True ensures SQLAlchemy detects and recovers from
     stale/dropped connections after a Neon "cold start".

  3. AUTO-DETECTION:
     We check if "neon.tech" is in the DATABASE_URL to automatically
     apply Neon-specific settings. This way the same code works for
     both local development (SQLite/local PG) and Neon in production.

  4. POOL SIZE ADJUSTMENTS FOR NEON:
     Neon's free tier limits concurrent connections.
     We reduce pool_size to avoid hitting connection limits.
     Free tier: max 10 connections
     Pro tier:  max 100 connections

CONNECTION STRING DETECTION LOGIC:
  - Contains "neon.tech"     → Neon serverless PostgreSQL (SSL required)
  - Contains "postgresql"    → local PostgreSQL (SSL optional)
  - Contains "sqlite"        → SQLite for dev/testing (no SSL)

INTERVIEW TALKING POINT:
  "I used conditional engine configuration to support both Neon serverless
  PostgreSQL (which requires SSL) and local SQLite for development. The
  is_neon flag auto-detects the environment from the DATABASE_URL, so
  no manual configuration switching is needed between environments."
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import settings


# ─── Detect Database Type ─────────────────────────────────────────────────────
# Auto-detect whether we're connecting to Neon or a local database.
# This drives which engine configuration we use.

is_neon    = "neon.tech"      in settings.DATABASE_URL
is_sqlite  = "sqlite"         in settings.DATABASE_URL
is_local_pg = (
    "postgresql" in settings.DATABASE_URL and not is_neon
)

print(f"🗄️  Database type detected: "
      f"{'Neon serverless PostgreSQL' if is_neon else 'SQLite (local dev)' if is_sqlite else 'Local PostgreSQL'}")


# ─── Engine Configuration ─────────────────────────────────────────────────────
# Build the correct engine kwargs based on the detected database type.

def build_engine_kwargs() -> dict:
    """
    Returns the correct SQLAlchemy engine kwargs for the detected database.

    NEON SPECIFIC:
      connect_args={"sslmode": "require"}
        Forces SSL — Neon rejects non-SSL connections.

      pool_size=5
        Neon free tier allows max 10 connections.
        We use 5 to leave headroom for other services or workers.

      max_overflow=5
        Allow 5 extra connections under burst load (total max = 10).

      pool_timeout=30
        How long to wait for a connection from the pool before raising
        an error. Neon cold starts can take ~1-2s, so 30s is safe.

      pool_recycle=300
        Return connections to the pool after 5 minutes.
        Neon suspends compute after 5min of inactivity — recycling
        connections prevents using stale ones after a suspend/resume.

    SQLITE SPECIFIC:
      connect_args={"check_same_thread": False}
        Required for SQLite in multi-threaded FastAPI context.
        Without this, SQLite raises an error when used across threads.

    LOCAL POSTGRESQL:
      Standard pooling config — no SSL required for local connections.
    """
    if is_neon:
        return {
            # ── SSL Configuration (REQUIRED for Neon) ──────────────────────
            "connect_args": {
                "sslmode": "require",    # Neon mandates SSL
                # Optional: provide CA cert for stricter verification
                # "sslrootcert": "/path/to/ca-certificate.crt",
            },

            # ── Pool Configuration (tuned for Neon free tier) ──────────────
            # pool_pre_ping: sends "SELECT 1" before using a pooled connection
            # This is CRITICAL for Neon because the serverless compute can
            # suspend and connections become stale during suspension periods.
            "pool_pre_ping": True,

            # Neon free tier: max 10 connections
            # Keep pool_size + max_overflow <= 10 on free tier
            "pool_size":     5,
            "max_overflow":  5,

            # Wait 30s for a pool connection (handles Neon cold starts)
            "pool_timeout":  30,

            # Recycle connections every 5 minutes
            # Matches Neon's 5-minute inactivity suspend window
            "pool_recycle":  300,

            # Echo SQL for debugging — set to False in production
            "echo": settings.DEBUG,
        }

    elif is_sqlite:
        return {
            # SQLite needs this for FastAPI's async/threaded request handling
            "connect_args": {"check_same_thread": False},
            # SQLite doesn't support connection pooling the same way
            # StaticPool keeps one connection open (fine for dev/testing)
            "echo": settings.DEBUG,
        }

    else:
        # Local PostgreSQL — standard production config
        return {
            "pool_pre_ping": True,
            "pool_size":     10,
            "max_overflow":  20,
            "pool_recycle":  1800,   # 30 minutes
            "echo":          settings.DEBUG,
        }


# ─── Create Engine ────────────────────────────────────────────────────────────
# The engine is created once at module load time and shared across the app.
# It does NOT open a connection immediately — connections are lazy (on demand).

engine = create_engine(
    settings.DATABASE_URL,
    **build_engine_kwargs()
)


# ─── SQLite Specific: Enable Foreign Keys ─────────────────────────────────────
# SQLite disables foreign key enforcement by default.
# This event listener enables it for every new connection.
# (PostgreSQL and Neon enforce foreign keys automatically — no action needed.)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key enforcement in SQLite connections."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ─── Session Factory ──────────────────────────────────────────────────────────
# SessionLocal is a factory that produces Session objects.
# autocommit=False: we must explicitly call db.commit() — transactional control.
# autoflush=False: prevents SQLAlchemy from auto-sending SQL before queries.

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ─── Declarative Base ─────────────────────────────────────────────────────────
# All SQLAlchemy model classes inherit from this Base.
# Base.metadata holds the registry of all tables.

Base = declarative_base()


# ─── Dependency: get_db ───────────────────────────────────────────────────────
# FastAPI dependency used in route handlers via Depends(get_db).
#
# Pattern:
#   1. A new Session is created at the start of each HTTP request.
#   2. The `yield` passes the session to the route handler.
#   3. The `finally` block closes the session even if an exception is raised.

def get_db():
    """
    Yield a database session scoped to a single HTTP request.
    The session is automatically closed when the request finishes.

    For Neon: each request gets a connection from the pool.
    pool_pre_ping ensures stale connections (after Neon cold start) are
    detected and refreshed before being used.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Connection Health Check ──────────────────────────────────────────────────

def check_database_connection() -> bool:
    """
    Test the database connection at startup.
    Useful for the /health endpoint and startup validation.

    For Neon: the first connection may take 1-2s if compute was suspended.
    This function is called once at startup to "warm up" the connection.

    Returns True if connection succeeds, False otherwise.
    """
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection verified"
              f" ({'Neon' if is_neon else 'SQLite' if is_sqlite else 'PostgreSQL'})")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
