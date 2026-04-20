"""
FILE: tests/test_backend.py
==================================
Backend Unit & Integration Tests — pytest
==================================

WHY TEST?
  - Catches regressions (changes that break existing functionality)
  - Documents expected behaviour (tests are living documentation)
  - Enables confident refactoring
  - Required for most production codebases

PYTEST CONCEPTS:
  @pytest.fixture     — Reusable setup/teardown logic (like setUp in unittest)
  autouse=True        — Apply a fixture to every test automatically
  TestClient          — FastAPI's built-in test client (no real HTTP server needed)
  Depends override    — Replace FastAPI dependencies with test versions

TEST DATABASE:
  We use SQLite (in-memory) instead of PostgreSQL for tests.
  Benefits:
    - No external service needed (tests run anywhere)
    - Fast (in-memory, no disk I/O)
    - Isolated (each test starts with a fresh DB)
  Trade-off: SQLite has slightly different behaviour from PostgreSQL
  (e.g. ENUM types aren't supported natively — SQLAlchemy handles this).

TEST ISOLATION:
  The autouse=True fixture creates ALL tables before each test and drops them after.
  This ensures tests don't affect each other (test independence).

INTERVIEW TALKING POINT:
  "I used FastAPI's dependency injection system to swap the real PostgreSQL
  database for an in-memory SQLite database in tests. This means tests run
  without any external services and complete in under 1 second."
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our FastAPI app and database components
from app.main import app
from app.database.db import Base, get_db

# ─── Test Database Setup ──────────────────────────────────────────────────────

# SQLite in-memory database URL
# :memory: means the DB exists only while the engine is alive (no file created)
SQLITE_TEST_URL = "sqlite:///./test_emergency.db"

test_engine = create_engine(
    SQLITE_TEST_URL,
    # SQLite requires this flag for multi-threaded use
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


def override_get_db():
    """
    Replaces the real get_db() dependency during tests.
    Instead of connecting to PostgreSQL, returns a SQLite session.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the database dependency globally for all tests
app.dependency_overrides[get_db] = override_get_db


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """
    Run before EVERY test: create all tables.
    Run after EVERY test: drop all tables.

    autouse=True means this fixture is automatically applied without
    listing it as a parameter in every test function.

    This gives each test a completely clean database state.
    """
    Base.metadata.create_all(bind=test_engine)
    yield   # Test runs here
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """
    FastAPI TestClient — sends HTTP requests to the app without a real server.
    The app processes them synchronously, making tests fast and deterministic.
    """
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """
    Register a test user and return the response data.
    Used by tests that need an authenticated user.
    """
    response = client.post("/api/auth/register", json={
        "name":     "Test Operator",
        "email":    "operator@test.com",
        "password": "testpass123",
        "role":     "operator",
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_token(registered_user):
    """Return just the access token from a registered user."""
    return registered_user["access_token"]


# ─── Health Check Tests ───────────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for the /health and / endpoints."""

    def test_root_endpoint_returns_200(self, client):
        """Root endpoint should be accessible to anyone."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_health_check_returns_ok(self, client):
        """Health check should return status: ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ─── Authentication Tests ─────────────────────────────────────────────────────

class TestAuthentication:
    """Tests for /api/auth endpoints."""

    def test_register_new_user_returns_201(self, client):
        """Registering with valid data returns a token and user profile."""
        response = client.post("/api/auth/register", json={
            "name":     "Alice",
            "email":    "alice@test.com",
            "password": "securepassword",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "alice@test.com"
        # SECURITY: Password must never be returned
        assert "password" not in data["user"]

    def test_register_duplicate_email_returns_400(self, client):
        """Registering the same email twice should fail."""
        payload = {"name": "Bob", "email": "bob@test.com", "password": "pass1234"}
        client.post("/api/auth/register", json=payload)   # First registration

        response = client.post("/api/auth/register", json=payload)  # Duplicate
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_login_with_correct_credentials_returns_token(self, client):
        """Login with the correct email+password returns a JWT."""
        # Register first
        client.post("/api/auth/register", json={
            "name": "Carol", "email": "carol@test.com", "password": "mypassword"
        })
        # Login
        response = client.post("/api/auth/login", json={
            "email": "carol@test.com", "password": "mypassword"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_with_wrong_password_returns_401(self, client):
        """Wrong password should return 401 Unauthorized."""
        client.post("/api/auth/register", json={
            "name": "Dave", "email": "dave@test.com", "password": "realpassword"
        })
        response = client.post("/api/auth/login", json={
            "email": "dave@test.com", "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client):
        """
        A non-existent email should return the same 401 as a wrong password.
        This prevents user enumeration — attacker can't distinguish
        "email not found" from "wrong password".
        """
        response = client.post("/api/auth/login", json={
            "email": "nobody@test.com", "password": "anything"
        })
        assert response.status_code == 401


# ─── Accident CRUD Tests ──────────────────────────────────────────────────────

class TestAccidents:
    """Tests for /api/accidents endpoints."""

    VALID_ACCIDENT = {
        "location":   "Test Junction, Pune",
        "severity":   "high",
        "confidence": 0.91,
        "camera_id":  "CAM-TEST",
    }

    def test_get_accidents_returns_empty_list_initially(self, client):
        """No accidents initially — should return an empty list, not 404."""
        response = client.get("/api/accidents/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_accident_returns_201(self, client):
        """Creating a valid accident should return 201 with the created record."""
        response = client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        assert response.status_code == 201
        data = response.json()
        assert data["location"]   == self.VALID_ACCIDENT["location"]
        assert data["severity"]   == self.VALID_ACCIDENT["severity"]
        assert data["status"]     == "detected"   # Default status
        assert data["confidence"] == self.VALID_ACCIDENT["confidence"]
        assert "id" in data                        # Server-generated ID
        assert "detected_at" in data               # Server-generated timestamp

    def test_created_accident_appears_in_list(self, client):
        """After creating an accident, it should appear in GET /accidents/."""
        client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        response = client.get("/api/accidents/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_get_single_accident_by_id(self, client):
        """GET /accidents/{id} should return the specific accident."""
        create_res = client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        accident_id = create_res.json()["id"]

        response = client.get(f"/api/accidents/{accident_id}")
        assert response.status_code == 200
        assert response.json()["id"] == accident_id

    def test_get_nonexistent_accident_returns_404(self, client):
        """Requesting a non-existent ID should return 404, not 500."""
        response = client.get("/api/accidents/99999")
        assert response.status_code == 404

    def test_update_accident_status_to_resolved(self, client):
        """
        PATCH /accidents/{id} with status=resolved should:
          - Return the updated record
          - Set resolved_at timestamp automatically
        """
        create_res = client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        accident_id = create_res.json()["id"]

        response = client.patch(
            f"/api/accidents/{accident_id}",
            json={"status": "resolved"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"]     == "resolved"
        assert data["resolved_at"] is not None   # Auto-stamped

    def test_update_only_sends_changed_fields(self, client):
        """PATCH should only change specified fields (partial update)."""
        create_res = client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        accident_id = create_res.json()["id"]

        # Only update severity — location should remain unchanged
        client.patch(f"/api/accidents/{accident_id}", json={"severity": "critical"})

        get_res = client.get(f"/api/accidents/{accident_id}")
        assert get_res.json()["severity"]  == "critical"
        assert get_res.json()["location"]  == self.VALID_ACCIDENT["location"]

    def test_filter_by_status(self, client):
        """GET /accidents/?status=detected should only return matching records."""
        # Create two accidents
        client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        res2 = client.post("/api/accidents/", json=self.VALID_ACCIDENT)
        accident_id = res2.json()["id"]

        # Resolve one of them
        client.patch(f"/api/accidents/{accident_id}", json={"status": "resolved"})

        # Filter for detected only
        response = client.get("/api/accidents/?status=detected")
        assert response.status_code == 200
        accidents = response.json()
        assert all(a["status"] == "detected" for a in accidents)


# ─── Analytics Tests ──────────────────────────────────────────────────────────

class TestAnalytics:
    """Tests for /api/analytics endpoints."""

    def test_summary_returns_expected_keys(self, client):
        """Summary endpoint should return all required KPI fields."""
        response = client.get("/api/analytics/summary")
        assert response.status_code == 200
        data = response.json()

        required_keys = [
            "total_today",
            "active_incidents",
            "resolved_today",
            "avg_response_time_minutes",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_summary_increments_after_creating_accident(self, client):
        """Creating an accident should increase total_today by 1."""
        before = client.get("/api/analytics/summary").json()["total_today"]

        client.post("/api/accidents/", json={
            "location": "Somewhere", "severity": "low"
        })

        after = client.get("/api/analytics/summary").json()["total_today"]
        assert after == before + 1

    def test_trends_returns_list(self, client):
        """Trends endpoint should return a list (possibly empty)."""
        response = client.get("/api/analytics/trends?days=7")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_severity_breakdown_returns_list(self, client):
        """Severity breakdown should return a list of {severity, count} objects."""
        client.post("/api/accidents/", json={
            "location": "Test", "severity": "high"
        })
        response = client.get("/api/analytics/severity-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all("severity" in item and "count" in item for item in data)
