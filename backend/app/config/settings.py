"""
FILE: backend/app/config/settings.py
==========================================
Centralised Application Configuration
==========================================

WHY THIS PATTERN?
  All configuration values are read from environment variables (or a .env file)
  in one single place. This is the 12-Factor App methodology (factor III:
  "Store config in the environment").

  Benefits:
  - No hard-coded secrets in source code
  - Easy to swap values between dev/staging/production without code changes
  - A single file to audit for misconfiguration

  pydantic-settings reads .env files and validates types automatically.
  e.g. ACCESS_TOKEN_EXPIRE_MINUTES will raise a ValidationError if set to "abc".

NEON DATABASE MIGRATION NOTES:
  Neon is a serverless PostgreSQL provider.
  Key differences from a local PostgreSQL setup:

  1. CONNECTION STRING FORMAT:
     Neon provides a connection string like:
       postgresql://user:password@ep-xxxx.us-east-1.aws.neon.tech/dbname?sslmode=require
     The ?sslmode=require at the end is MANDATORY for Neon connections.
     Without it, Neon will reject the connection.

  2. SSL IS REQUIRED:
     Neon enforces SSL on all connections.
     We handle this via the DATABASE_URL query parameter (?sslmode=require)
     AND via SQLAlchemy connect_args in db.py.

  3. CONNECTION POOLING:
     Neon has built-in connection pooling via PgBouncer.
     Neon provides two connection strings:
       - Direct connection:  postgresql://...@ep-xxx.neon.tech/dbname
       - Pooled connection:  postgresql://...@ep-xxx-pooler.neon.tech/dbname
     For serverless/edge environments, use the POOLED connection string.
     For long-running servers like FastAPI, either works fine.

  4. IDLE CONNECTIONS:
     Neon automatically suspends compute after 5 minutes of inactivity
     (on the free tier). The first query after suspension takes ~1-2s
     to "wake up" the database. pool_pre_ping=True in db.py handles this.

  HOW TO GET YOUR NEON DATABASE_URL:
    Step 1: Go to https://neon.tech and create a free account
    Step 2: Create a new project
    Step 3: In the dashboard, go to "Connection Details"
    Step 4: Copy the connection string — it looks like:
              postgresql://username:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
    Step 5: Paste it as DATABASE_URL in your .env file

INTERVIEW TALKING POINT:
  "I migrated from local PostgreSQL to Neon, a serverless PostgreSQL provider.
  The main change was adding SSL enforcement via sslmode=require in the
  connection string and connect_args in SQLAlchemy. Neon is PostgreSQL-
  compatible, so no schema, model, or query changes were needed."
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    All settings are declared as class attributes.
    Pydantic reads values from environment variables (case-insensitive)
    or from the .env file specified in Config.env_file.
    Default values are used when the env var is not set.
    """

    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "Smart AI Emergency Response System"

    # DEBUG=True enables hot-reload, verbose error messages, etc.
    # NEVER set this to True in production.
    DEBUG: bool = True

    # ── Database (NEON CONFIGURATION) ────────────────────────────────────────
    # CHANGED FROM LOCAL POSTGRESQL TO NEON:
    #
    # OLD (local PostgreSQL):
    #   DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/emergency_db"
    #
    # NEW (Neon serverless PostgreSQL):
    #   DATABASE_URL must be set in your .env file.
    #   Get this URL from your Neon dashboard → Connection Details.
    #
    # FORMAT:
    #   postgresql://[user]:[password]@[neon-host]/[dbname]?sslmode=require
    #
    # EXAMPLE (do NOT use this — get your own from Neon dashboard):
    #   postgresql://alice:abc123@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
    #
    # THE ?sslmode=require PART IS MANDATORY — Neon rejects non-SSL connections.
    #
    # For local development fallback (if Neon is not configured),
    # we default to SQLite so the app still starts without crashing.
    # REMOVE this default in production and make DATABASE_URL required.
    DATABASE_URL: str = "postgresql://user:password@ep-xxx.neon.tech/dbname?sslmode=require"

    # ── JWT (JSON Web Token) Authentication ──────────────────────────────────
    # SECRET_KEY is used to sign JWT tokens. Anyone with this key can forge
    # valid tokens, so use a long random string in production.
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "postgresql://user:password@ep-xxx.neon.tech/dbname?sslmode=require"


    # Algorithm used to sign JWTs. HS256 is HMAC + SHA-256 (symmetric).
    ALGORITHM: str = "HS256"

    # Token expiry: 24 hours expressed in minutes.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # = 1440 minutes

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Origins allowed to make cross-origin requests to the API.
    # In production: replace with your actual frontend domain(s).
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Create React App / alternate port
    ]

    # ── AI Model ─────────────────────────────────────────────────────────────
    MODEL_PATH: str = "../ai-module/model/accident_model.h5"
    CONFIDENCE_THRESHOLD: float = 0.75

    # ── Email Notifications (SMTP) ────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # ── Neon-specific settings ────────────────────────────────────────────────
    # These are used in db.py to configure the SQLAlchemy engine properly
    # for Neon's serverless PostgreSQL.
    #
    # NEON_SSL_REQUIRED:
    #   Set to True when connecting to Neon (always required).
    #   Set to False only for local SQLite development.
    #   The app auto-detects this based on the DATABASE_URL.
    #
    # We don't need a separate setting — we check if DATABASE_URL contains
    # "neon.tech" in db.py to apply SSL-specific settings automatically.

    class Config:
        # Load values from this file if it exists.
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ── Singleton Instance ────────────────────────────────────────────────────────
settings = Settings()
