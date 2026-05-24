"""
FILE: backend/app/config/settings.py
==========================================
Centralised Application Configuration
==========================================
"""


from pydantic import field_validator
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
    DEBUG: bool = False

    # deployment environment: development | staging | production
    ENVIRONMENT: str = "development"

    # ── Database (NEON CONFIGURATION) ────────────────────────────────────────
    # DATABASE_URL must be provided in the environment.
    DATABASE_URL: str

    # ── JWT (JSON Web Token) Authentication ──────────────────────────────────
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


    # Algorithm used to sign JWTs. HS256 is HMAC + SHA-256 (symmetric).
    ALGORITHM: str = "HS256"

    # Token expiry: 24 hours expressed in minutes.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # = 1440 minutes

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Origins allowed to make cross-origin requests to the API.
    # In production: replace with your actual frontend domain(s).
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",   # Vite dev server
    ]

    # ── AI Model ─────────────────────────────────────────────────────────────
    MODEL_PATH: str = "../ai-module/model/accident_model.h5"
    CONFIDENCE_THRESHOLD: float = 0.85

    # Feature flags
    CORRIDOR_SPATIAL_FILTERING_ENABLED: bool = False

    # ── Email Notifications (SMTP) ────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_RECIPIENTS: List[str] = []
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Neon-specific settings ────────────────────────────────────────────────
    # These are used in db.py to configure the SQLAlchemy engine properly

    class Config:
        # Load values from this file if it exists.
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # ── Redis ───────────────────────────────────────────────────────────────
    # URL for Redis used for OTP storage and optional pub/sub/event history.
    REDIS_URL: str = "redis://localhost:6379"


# ── Singleton Instance ────────────────────────────────────────────────────────
settings = Settings()
 