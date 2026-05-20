"""
FILE: database/migrations/env.py
========================================
Alembic Migration Environment Configuration
========================================

WHAT IS ALEMBIC?
  Alembic is the database migration tool for SQLAlchemy.
  It handles schema changes in a version-controlled, reversible way.

NEON MIGRATION CHANGES IN THIS FILE:
  The key change for Neon is ensuring that the SQLAlchemy engine
  created by Alembic uses SSL when connecting to Neon.

  In online mode (run_migrations_online), we now pass connect_args
  with sslmode="require" when the DATABASE_URL points to Neon.

  This is necessary because Alembic creates its own engine separately
  from the app's engine in db.py. Without the SSL config here,
  Alembic migrations would fail with:
    "SSL connection required. Please use SSL."

RUNNING MIGRATIONS AGAINST NEON:
  1. Make sure DATABASE_URL is set in your environment or .env file:
       export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require"
     OR add it to backend/.env

  2. Navigate to the backend directory:
       cd backend

  3. Run migrations:
       alembic upgrade head       # Apply all pending migrations
       alembic downgrade -1       # Rollback the last migration
       alembic history            # View migration history
       alembic current            # Check current DB version

  4. Generate a new migration after changing a model:
       alembic revision --autogenerate -m "add phone to users"
       # Review the generated file in database/migrations/versions/
       alembic upgrade head

IMPORTANT NOTE ABOUT NEON AND ALEMBIC:
  Neon supports all standard PostgreSQL DDL commands that Alembic generates.
  No special handling is needed for CREATE TABLE, ALTER TABLE, ADD COLUMN, etc.
  The only difference is the SSL connection requirement handled below.

INTERVIEW TALKING POINT:
  "Alembic works identically with Neon as with local PostgreSQL. The only
  change was passing sslmode=require in the connect_args when Neon is detected.
  The migration files themselves are 100% compatible."
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# ── Path Setup ────────────────────────────────────────────────────────────────
# Add the backend directory to sys.path so we can import our app modules.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)

# Import the SQLAlchemy Base and all models.
# The models MUST be imported here so Alembic can detect their tables.
from app.database.db import Base                         # noqa: E402
from app.models import (                                 # noqa: E402, F401
    user_model,
    accident_model,
    traffic_model,
)
from app.config.settings import settings                 # noqa: E402

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ── Override DATABASE_URL from settings ───────────────────────────────────────
# This ensures Alembic uses the same DATABASE_URL as the FastAPI app.
# For Neon, this will include the ?sslmode=require parameter.
# If the environment contains an async URL, convert it back to sync for Alembic.

def make_sync_url(url: str) -> str:
    """
    Convert async SQLAlchemy URLs into a sync-only URL for Alembic.
    """
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url

config.set_main_option("sqlalchemy.url", make_sync_url(settings.DATABASE_URL))


# ── Neon Detection ────────────────────────────────────────────────────────────
# Check if we're connecting to Neon so we can apply SSL settings.
# The same logic as in db.py — centralised detection by DATABASE_URL content.

is_neon = "neon.tech" in settings.DATABASE_URL


def get_connect_args() -> dict:
    """
    Returns the correct connect_args for the detected database type.

    For Neon: SSL is required.
    For SQLite/local PostgreSQL: no special args needed.
    """
    if is_neon:
        return {"sslmode": "require"}
    return {}


# ── Offline Mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in "offline" mode — generates SQL scripts without
    connecting to the database.

    NEON USAGE:
      This mode generates SQL that you can review and run manually
      via the Neon SQL Editor or psql.

      Usage:
        alembic upgrade head --sql > migration.sql
        # Then paste migration.sql into Neon's SQL Editor
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online Mode ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in "online" mode — connects to the database and applies
    changes directly.

    NEON CHANGES:
      - Added connect_args={"sslmode": "require"} for Neon connections
      - This is the ONLY change needed compared to the original file

    Usage (the normal way):
      alembic upgrade head
    """
    # ── Build engine config ───────────────────────────────────────────────
    # Get the raw config section from alembic.ini
    configuration = config.get_section(config.config_ini_section, {})

    # NEON CHANGE:
    # We create the engine manually (instead of using engine_from_config)
    # so we can pass connect_args for SSL.
    #
    # For Neon: connect_args={"sslmode": "require"} is required.
    # For local PG/SQLite: connect_args={} (empty — no SSL needed).

    connectable = create_engine(
        make_sync_url(settings.DATABASE_URL),

        # NEON: pass SSL connect_args
        connect_args=get_connect_args(),

        # NullPool: don't pool connections for migrations
        # (migrations are one-off operations, not long-running servers)
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Dispatch ──────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
