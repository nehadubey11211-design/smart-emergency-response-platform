"""
FILE: backend/app/database/db.py
=======================================
Database Engine, Session Factory & Base Model
=======================================

SQLAlchemy is the most popular Python ORM (Object-Relational Mapper).
It maps Python classes (models) to database tables and Python objects to rows.

KEY CONCEPTS used here:
  - Engine    : The core interface to the database.  Holds the connection pool.
  - Session   : A unit of work.  All DB operations (SELECT, INSERT, etc.) go
                through a Session.  Changes are committed or rolled back together.
  - Base      : The declarative base class.  All model classes inherit from it.
                SQLAlchemy uses Base.metadata to track all registered table schemas.

CONNECTION POOLING:
  pool_size=10 means SQLAlchemy keeps up to 10 open connections ready.
  max_overflow=20 allows up to 20 additional connections under high load.
  pool_pre_ping=True sends a lightweight "SELECT 1" before each connection
  is handed out, auto-recovering from stale/dropped connections.

INTERVIEW TALKING POINT:
  "I used SQLAlchemy's connection pool rather than creating a new connection
  per request.  Opening a DB connection is expensive (~10-50ms), so pooling
  reuses existing ones and improves throughput significantly under load."
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import settings


# ─── Engine ───────────────────────────────────────────────────────────────────
# The engine is created once at module load time and shared across the app.
# It does NOT open a connection immediately — connections are lazy (on demand).

engine = create_engine(
    settings.DATABASE_URL,

    # Ping the DB before handing out a pooled connection.
    # This prevents "connection lost" errors after idle periods.
    pool_pre_ping=True,

    # Keep up to 10 persistent connections open in the pool.
    pool_size=10,

    # Allow up to 20 extra connections when the pool is full (burst traffic).
    max_overflow=20,

    # Return connections to the pool after 30 minutes of inactivity.
    pool_recycle=1800,
)


# ─── Session Factory ──────────────────────────────────────────────────────────
# SessionLocal is a factory that produces Session objects.
# We set autocommit=False so we must explicitly call db.commit().
# This gives us transactional control: we can rollback on errors.
# autoflush=False prevents SQLAlchemy from auto-sending SQL before queries.

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ─── Declarative Base ─────────────────────────────────────────────────────────
# All SQLAlchemy model classes inherit from this Base.
# Base.metadata holds the registry of all tables — used by create_all() and Alembic.

Base = declarative_base()


# ─── Dependency: get_db ───────────────────────────────────────────────────────
# This is a FastAPI dependency used in route handlers via Depends(get_db).
#
# Pattern explanation:
#   1. A new Session is created at the start of each HTTP request.
#   2. The `yield` passes the session to the route handler.
#   3. The `finally` block ensures the session is closed even if an exception
#      is raised inside the route — preventing connection leaks.
#
# Usage in a route:
#   @router.get("/items")
#   def get_items(db: Session = Depends(get_db)):
#       return db.query(Item).all()

def get_db():
    """
    Yield a database session scoped to a single HTTP request.
    The session is automatically closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
