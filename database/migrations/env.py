"""
FILE: database/migrations/env.py
========================================
Alembic Migration Environment Configuration
========================================

WHAT IS ALEMBIC?
  Alembic is the database migration tool for SQLAlchemy.
  While SQLAlchemy's create_all() creates tables, it can't:
    - Safely alter existing columns
    - Add new columns to populated tables
    - Track what changes have been applied

  Alembic adds:
    - Version-controlled schema changes (like git for your database)
    - Auto-generated migrations from model diffs (--autogenerate)
    - Upgrade/downgrade commands (alembic upgrade head / alembic downgrade -1)
    - Migration history table (alembic_version in the DB)

TYPICAL WORKFLOW:
  1. Change a SQLAlchemy model (e.g. add a column)
  2. Generate migration: alembic revision --autogenerate -m "add phone to users"
  3. Review the generated file in database/migrations/versions/
  4. Apply it: alembic upgrade head
  5. Rollback if needed: alembic downgrade -1

RUN MIGRATIONS:
  cd backend
  alembic upgrade head        # Apply all pending migrations
  alembic downgrade -1        # Rollback the last migration
  alembic history             # Show migration history
  alembic current             # Show current DB version

INTERVIEW TALKING POINT:
  "I set up Alembic for database migrations so schema changes are
  version-controlled and reversible. In production, migrations run
  as part of the CI/CD pipeline before the new code is deployed."
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Path Setup ────────────────────────────────────────────────────────────────
# Add the backend directory to sys.path so we can import our app modules.
# This script runs from the database/migrations/ directory, so we need to
# navigate up two levels to reach the backend/ directory.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)

# Import the SQLAlchemy Base and all models.
# The models MUST be imported here so Alembic can detect their tables.
# If a model isn't imported, --autogenerate won't include its table.
from app.database.db import Base                         # noqa: E402
from app.models import (                                 # noqa: E402, F401
    user_model,
    accident_model,
    traffic_model,
)
from app.config.settings import settings                 # noqa: E402

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic about our models — it compares these against the DB to find diffs
target_metadata = Base.metadata

# Override the database URL from alembic.ini with our settings
# This means migrations use the same DATABASE_URL as the app
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ── Offline Mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in "offline" mode.
    Generates SQL scripts without connecting to the database.
    Useful for: reviewing changes before applying, running on a different server.

    Usage: alembic upgrade head --sql > migration.sql
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
    Run migrations in "online" mode.
    Connects to the database and applies changes directly.
    This is the normal mode: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # Don't pool connections for migrations
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# ── Dispatch ──────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
