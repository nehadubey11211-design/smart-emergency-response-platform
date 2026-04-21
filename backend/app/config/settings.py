"""
FILE: backend/app/config/settings.py
==========================================
Centralised Application Configuration
==========================================

WHY THIS PATTERN?
  All configuration values are read from environment variables (or a .env file)
  in one single place.  This is the 12-Factor App methodology (factor III:
  "Store config in the environment").

  Benefits:
  - No hard-coded secrets in source code
  - Easy to swap values between dev/staging/production without code changes
  - A single file to audit for misconfiguration

  pydantic-settings reads .env files and validates types automatically.
  e.g. ACCESS_TOKEN_EXPIRE_MINUTES will raise a ValidationError if set to "abc".

INTERVIEW TALKING POINT:
  "I used pydantic-settings so that all configuration is type-validated at
  startup.  If a required env var is missing or has the wrong type, the app
  crashes immediately with a clear error — better than a cryptic failure later."
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

    # ── Database ─────────────────────────────────────────────────────────────
    # Format: postgresql://<user>:<password>@<host>:<port>/<database>
    # For development, using SQLite (no server required)
    DATABASE_URL: str = "sqlite:///./emergency.db"

    # ── JWT (JSON Web Token) Authentication ──────────────────────────────────
    # SECRET_KEY is used to sign JWT tokens.  Anyone with this key can forge
    # valid tokens, so use a long random string in production.
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "dev-secret-key-change-this-in-production-please"

    # Algorithm used to sign JWTs.  HS256 is HMAC + SHA-256 (symmetric).
    # RS256 (asymmetric) is better for microservices but adds complexity.
    ALGORITHM: str = "HS256"

    # Token expiry: 24 hours expressed in minutes.
    # Short-lived tokens reduce risk if a token is stolen.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # = 1440 minutes

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Origins allowed to make cross-origin requests to the API.
    # In production: replace with your actual frontend domain(s).
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Create React App / alternate port
    ]

    # ── AI Model ─────────────────────────────────────────────────────────────
    # Path to the trained Keras model file, relative to the backend process.
    MODEL_PATH: str = "../ai-module/model/accident_model.h5"

    # Minimum AI confidence score (0.0 – 1.0) required to trigger an alert.
    # 0.75 means "only alert if the model is at least 75% confident."
    # Lower = more alerts but more false positives.
    CONFIDENCE_THRESHOLD: float = 0.75

    # ── Email Notifications (SMTP) ────────────────────────────────────────────
    # Leave SMTP_USER empty to disable email notifications.
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""       # e.g. your-account@gmail.com
    SMTP_PASSWORD: str = ""   # App password, not your Gmail login

    class Config:
        # Load values from this file if it exists.
        # Values in the environment always override .env file values.
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow extra env vars without raising an error
        extra = "ignore"


# ── Singleton Instance ────────────────────────────────────────────────────────
# Import this object wherever settings are needed:
#   from app.config.settings import settings
# This ensures the .env file is parsed only once at module load time.
settings = Settings()
