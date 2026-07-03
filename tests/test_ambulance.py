"""
FILE :tests/test_ambulance.py
==================================
Run:  pytest tests/test_ambulance.py -v
"""

import pytest

from app.models import Ambulance, AmbulanceStatus

# ═══════════════════════════════════════════════════════════════════
#  Unit tests — pure functions (no DB, no HTTP)
# ═══════════════════════════════════════════════════════════════════

class TestHaversine:
    def test_same_point_is_zero(self):
        from app.services.ambulance_service import haversine_distance
        assert haversine_distance(18.5204, 73.8567, 18.5204, 73.8567) == 0.0

    def test_known_distance(self):
        """
        Pune to Mumbai straight-line (haversine) distance is ~120 km.
        Note: the ~149 km figure often quoted is the NH48 driving distance,
        not straight-line — haversine can never return that number.
        """
        from app.services.ambulance_service import haversine_distance
        dist = haversine_distance(18.5204, 73.8567, 19.0760, 72.8777)
        assert 110 < dist < 130, f"Expected ~120 km, got {dist:.1f}"

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
    def test_register_success(self, client, auth_headers):
        res = client.post("/api/ambulances/register", json={
            "ambulance_number": "TEST-001",
            "driver_name":      "Test Driver",
            "latitude":         18.5204,
            "longitude":        73.8567,
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["ambulance_number"] == "TEST-001"
        assert data["status"] == "available"

    def test_register_duplicate_number(self, client, auth_headers):
        payload = {"ambulance_number": "DUP-001", "driver_name": "Driver A"}
        client.post("/api/ambulances/register", json=payload, headers=auth_headers)
        res = client.post("/api/ambulances/register", json=payload, headers=auth_headers)
        assert res.status_code == 400

    def test_list_ambulances(self, client, auth_headers):
        client.post("/api/ambulances/register", json={"ambulance_number": "L-001", "driver_name": "D"}, headers=auth_headers)
        res = client.get("/api/ambulances/")
        assert res.status_code == 200
        assert len(res.json()) >= 1


class TestAmbulanceLocation:
    def test_update_location(self, client, auth_headers):
        reg = client.post("/api/ambulances/register", json={
            "ambulance_number": "LOC-001",
            "driver_name":      "GPS Driver",
        }, headers=auth_headers)
        amb_id = reg.json()["id"]
        res = client.put(f"/api/ambulances/{amb_id}/location", json={
            "latitude": 18.5300, "longitude": 73.8600,
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["latitude"] == 18.53

    def test_update_location_not_found(self, client, auth_headers):
        res = client.put("/api/ambulances/9999/location", json={"latitude": 0.0, "longitude": 0.0}, headers=auth_headers)
        assert res.status_code == 404


class TestNearbyAndDispatch:
    def _register(self, client, auth_headers, number, lat, lon):
        return client.post("/api/ambulances/register", json={
            "ambulance_number": number,
            "driver_name":      "Driver",
            "latitude":         lat,
            "longitude":        lon,
        }, headers=auth_headers).json()

    def test_get_nearby(self, client, auth_headers):
        self._register(client, auth_headers, "NEAR-001", 18.5204, 73.8567)  # at accident site
        self._register(client, auth_headers, "NEAR-002", 18.5210, 73.8580)  # 200 m away
        res = client.get("/api/ambulances/nearby?lat=18.5204&lon=73.8567&radius_km=1")
        assert res.status_code == 200
        units = res.json()
        assert len(units) >= 1
        # First result must be the closest
        assert units[0]["distance_km"] <= units[-1]["distance_km"]

    def test_dispatch_marks_busy(self, client, auth_headers):
        self._register(client, auth_headers, "DISP-001", 18.5204, 73.8567)
        res = client.post("/api/ambulances/dispatch?lat=18.5204&lon=73.8567", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["ambulance"]["status"] == "busy"
        assert data["distance_km"] >= 0

    def test_dispatch_no_units(self, client, auth_headers):
        # No units registered → 503
        res = client.post("/api/ambulances/dispatch?lat=0.0&lon=0.0", headers=auth_headers)
        assert res.status_code == 503


class TestStatusLifecycle:
    def test_accept_and_complete(self, client, auth_headers):
        reg = client.post("/api/ambulances/register", json={
            "ambulance_number": "LIFE-001",
            "driver_name":      "Lifecycle Driver",
            "latitude":         18.5204,
            "longitude":        73.8567,
        }, headers=auth_headers).json()
        amb_id = reg["id"]

        # Dispatch
        client.post("/api/ambulances/dispatch?lat=18.5204&lon=73.8567", headers=auth_headers)

        # Accept
        res = client.post(f"/api/ambulances/{amb_id}/accept", headers=auth_headers)
        assert res.status_code == 200

        # Complete
        res = client.post(f"/api/ambulances/{amb_id}/complete", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["ambulance"]["status"] == "available"
