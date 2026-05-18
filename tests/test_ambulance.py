"""
FILE :tests/test_ambulance.py
------------------------
Pytest tests for the ambulance dispatch feature.
Follows the same pattern as your existing test_backend.py:
  - In-memory SQLite via FastAPI dependency override
  - TestClient for HTTP assertions
  - No real PostgreSQL required

Run:  pytest tests/test_ambulance.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy         import create_engine
from sqlalchemy.orm     import sessionmaker

from app.main       import app
from app.database   import Base, get_db
from app.models     import Ambulance, AmbulanceStatus  # noqa: F401 — needed for create_all

# ── In-memory SQLite (no Neon connection needed for tests) ──────────────────
SQLITE_URL     = "sqlite:///./test_ambulance.db"
test_engine    = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════
#  Unit tests — pure functions (no DB, no HTTP)
# ═══════════════════════════════════════════════════════════════════

class TestHaversine:
    def test_same_point_is_zero(self):
        from app.services.ambulance_service import haversine_distance
        assert haversine_distance(18.5204, 73.8567, 18.5204, 73.8567) == 0.0

    def test_known_distance(self):
        """Pune to Mumbai is approximately 149 km."""
        from app.services.ambulance_service import haversine_distance
        dist = haversine_distance(18.5204, 73.8567, 19.0760, 72.8777)
        assert 140 < dist < 160, f"Expected ~149 km, got {dist:.1f}"

    def test_eta_calculation(self):
        from app.services.ambulance_service import estimate_eta
        # 20 km at 40 km/h = 30 minutes
        assert estimate_eta(20.0, speed_kmh=40.0) == 30.0

    def test_eta_zero_speed(self):
        from app.services.ambulance_service import estimate_eta
        assert estimate_eta(10.0, speed_kmh=0.0) == 0.0


# ═══════════════════════════════════════════════════════════════════
#  Integration tests — HTTP via TestClient
# ═══════════════════════════════════════════════════════════════════

class TestAmbulanceRegistration:
    def test_register_success(self):
        res = client.post("/api/ambulances/register", json={
            "ambulance_number": "TEST-001",
            "driver_name":      "Test Driver",
            "latitude":         18.5204,
            "longitude":        73.8567,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["ambulance_number"] == "TEST-001"
        assert data["status"] == "available"

    def test_register_duplicate_number(self):
        payload = {"ambulance_number": "DUP-001", "driver_name": "Driver A"}
        client.post("/api/ambulances/register", json=payload)
        res = client.post("/api/ambulances/register", json=payload)
        assert res.status_code == 400

    def test_list_ambulances(self):
        client.post("/api/ambulances/register", json={"ambulance_number": "L-001", "driver_name": "D"})
        res = client.get("/api/ambulances/")
        assert res.status_code == 200
        assert len(res.json()) >= 1


class TestAmbulanceLocation:
    def test_update_location(self):
        reg = client.post("/api/ambulances/register", json={
            "ambulance_number": "LOC-001",
            "driver_name":      "GPS Driver",
        })
        amb_id = reg.json()["id"]
        res = client.put(f"/api/ambulances/{amb_id}/location", json={
            "latitude": 18.5300, "longitude": 73.8600,
        })
        assert res.status_code == 200
        assert res.json()["latitude"] == 18.53

    def test_update_location_not_found(self):
        res = client.put("/api/ambulances/9999/location", json={"latitude": 0.0, "longitude": 0.0})
        assert res.status_code == 404


class TestNearbyAndDispatch:
    def _register(self, number, lat, lon):
        return client.post("/api/ambulances/register", json={
            "ambulance_number": number,
            "driver_name":      "Driver",
            "latitude":         lat,
            "longitude":        lon,
        }).json()

    def test_get_nearby(self):
        self._register("NEAR-001", 18.5204, 73.8567)  # at accident site
        self._register("NEAR-002", 18.5210, 73.8580)  # 200 m away
        res = client.get("/api/ambulances/nearby?lat=18.5204&lon=73.8567&radius_km=1")
        assert res.status_code == 200
        units = res.json()
        assert len(units) >= 1
        # First result must be the closest
        assert units[0]["distance_km"] <= units[-1]["distance_km"]

    def test_dispatch_marks_busy(self):
        self._register("DISP-001", 18.5204, 73.8567)
        res = client.post("/api/ambulances/dispatch?lat=18.5204&lon=73.8567")
        assert res.status_code == 200
        data = res.json()
        assert data["ambulance"]["status"] == "busy"
        assert data["distance_km"] >= 0

    def test_dispatch_no_units(self):
        # No units registered → 503
        res = client.post("/api/ambulances/dispatch?lat=0.0&lon=0.0")
        assert res.status_code == 503


class TestStatusLifecycle:
    def test_accept_and_complete(self):
        reg = client.post("/api/ambulances/register", json={
            "ambulance_number": "LIFE-001",
            "driver_name":      "Lifecycle Driver",
            "latitude":         18.5204,
            "longitude":        73.8567,
        }).json()
        amb_id = reg["id"]

        # Dispatch
        client.post(f"/api/ambulances/dispatch?lat=18.5204&lon=73.8567")

        # Accept
        res = client.post(f"/api/ambulances/{amb_id}/accept")
        assert res.status_code == 200

        # Complete
        res = client.post(f"/api/ambulances/{amb_id}/complete")
        assert res.status_code == 200
        assert res.json()["status"] == "available"
