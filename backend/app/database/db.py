import logging

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config.settings import settings

logger = logging.getLogger(__name__)


# ─── Detect Database Type ─────────────────────────────────────────────────────
# Auto-detect whether we're connecting to Neon or a local database.
# This drives which engine configuration we use.

is_neon    = "neon.tech"      in settings.DATABASE_URL
is_sqlite  = "sqlite"         in settings.DATABASE_URL
is_local_pg = "postgresql" in settings.DATABASE_URL and not is_neon

logger.info(
    "Database type detected: %s",
    "Neon serverless PostgreSQL" if is_neon else "SQLite (local dev)" if is_sqlite else "Local PostgreSQL",
)


# ─── URL Conversion ───────────────────────────────────────────────────────────
# Async SQLAlchemy requires an async driver URL for runtime engine creation.
# We keep the user's .env value intact and convert it here automatically.

def make_async_url(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


# ─── Engine Configuration ─────────────────────────────────────────────────────
# Build the correct engine kwargs based on the detected database type.

def build_engine_kwargs() -> dict:
    if is_neon:
        return {
            "connect_args": {                         
                "ssl": True,                          
                "prepared_statement_cache_size": 0,
            },     
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 5,
            "pool_timeout": 30,
            "pool_recycle": 240,
            "echo": False ,
        }

    elif is_sqlite:
        return {
            "connect_args": {"check_same_thread": False},
            "echo": settings.DEBUG,
        }

    else:
        return {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
            "echo": settings.DEBUG,
        }


# ─── Create Async Engine ──────────────────────────────────────────────────────
# The engine is created once at module load time and shared across the app.
# It does NOT open a connection immediately — connections are lazy (on demand).

engine = create_async_engine(
    make_async_url(settings.DATABASE_URL),
    **build_engine_kwargs(),
)


# ─── SQLite Specific: Enable Foreign Keys ─────────────────────────────────────
# SQLite disables foreign key enforcement by default.
# This event listener enables it for every new connection.
# (PostgreSQL and Neon enforce foreign keys automatically — no action needed.)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key enforcement in SQLite connections."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ─── Session Factory ──────────────────────────────────────────────────────────
# SessionLocal is a factory that produces AsyncSession objects.

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ─── Declarative Base ──────────────────────────────────────────────────────────
# All SQLAlchemy model classes inherit from this Base.
# Base.metadata holds the registry of all tables.

Base = declarative_base()


# ─── Dependency: get_db ───────────────────────────────────────────────────────
# FastAPI dependency used in route handlers via Depends(get_db).

async def get_db():
    """
    Yield an AsyncSession scoped to a single HTTP request.
    The session is automatically closed when the request finishes.
    """
    async with SessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()


# ─── Connection Health Check ──────────────────────────────────────────────────

async def check_database_connection() -> bool:
    """
    Test the database connection at startup.
    Useful for the /health endpoint and startup validation.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(
            "Database connection verified (%s)",
            "Neon" if is_neon else "SQLite" if is_sqlite else "PostgreSQL",
        )
        return True
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        return False
