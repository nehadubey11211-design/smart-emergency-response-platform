"""
tests/conftest.py
==================
Shared test infrastructure for the whole suite.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_emergency.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-not-for-prod-use")

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.database.db import Base, get_db
from app.models import User
from app.routes.auth import create_access_token, hash_password

app.state.limiter.enabled = False

SQLITE_TEST_URL = "sqlite+aiosqlite:///./test_suite.db"

test_engine = create_async_engine(
    SQLITE_TEST_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
)


async def override_get_db():
    """
    Replaces the real get_db() dependency during tests.
    Instead of connecting to PostgreSQL/Neon, returns an async SQLite session.
    """
    async with TestingSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_and_teardown_db():
    """
    Run before EVERY test: create all tables.
    Run after EVERY test: drop all tables.
    Gives each test a completely clean database state.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    """FastAPI TestClient — sends HTTP requests to the app without a real server."""
    return TestClient(app)


@pytest.fixture
def db_sessionmaker():
    """
    Exposes TestingSessionLocal to other test files as a fixture rather than
    a plain import. `tests/` has no __init__.py, so it isn't a real Python
    package — `from tests.conftest import TestingSessionLocal` resolves
    inconsistently depending on how pytest was invoked and can fail
    collection entirely ("ERROR tests/test_ambulance.py ... Interrupted: 1
    error during collection"). Fixtures are auto-discovered by pytest from
    conftest.py regardless of package structure, so this is the reliable way
    to share it.
    """
    return TestingSessionLocal


@pytest_asyncio.fixture
async def auth_headers(db_sessionmaker):
    """
    Create a throwaway user directly in the DB and mint a token for it,
    returning an Authorization header. Shared by any test file that needs
    to call an endpoint behind get_current_user_from_header — e.g. ambulance
    writes, POST/PATCH /api/accidents/, and the entire /api/analytics/
    router (mounted with `dependencies=[Depends(get_current_user_from_header)]`
    in analytics.py, so every route under it needs this even for GETs).

    Deliberately inserts the user directly rather than going through
    /api/auth/register + /api/auth/login — keeps this fixture's user
    creation independent of the rate limiter entirely (see note above app
    .state.limiter.enabled), and independent of the register/login flow
    itself, which is what TestAuthentication's own tests exist to verify.
    """
    async with db_sessionmaker() as db:
        user = User(
            name="Test Operator",
            email="fixture-operator@test.com",
            password=hash_password("testpass123"),
            role="operator",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}
