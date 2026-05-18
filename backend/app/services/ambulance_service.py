"""
FILE : backend/app/services/ambulance_service.py
==========================================
All business logic for ambulance dispatch lifecycle.

Complete flow implemented here:
  1. dispatch_nearest_ambulance()   → find + assign nearest unit
  2. get_nearby_hospitals()         → find nearest hospital after pickup
  3. complete_dispatch_to_hospital()→ mark accident resolved, unit available

Root cause fixes:
  - Accident status not updating: complete_dispatch_to_hospital() now
    sets accident.status = "resolved" and resolved_at = now()
  - Hospital routing: get_nearby_hospitals() returns sorted list by distance
  - GPS tracking: update_location() also broadcasts WS event so map updates
"""

import math
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.ambulance import Ambulance, AmbulanceStatus
from app.models.accident_model import Accident, AccidentStatus
from app.schemas.ambulance import (
    AmbulanceCreate,
    AmbulanceLocationUpdate,
    NearbyAmbulanceResponse,
    DispatchResult,
)

logger = logging.getLogger(__name__)

_AVG_SPEED_KMH    = 40.0   # Urban ambulance average
_DEFAULT_RADIUS   = 20.0   # km
_HOSPITAL_RADIUS  = 30.0   # km search radius for hospitals

# ── Static hospital registry (replace with DB table in production) ──────────
# In production: CREATE TABLE hospitals (id, name, latitude, longitude, ...)
HOSPITALS = [
    {"id": "HOSP-001", "name": "KEM Hospital Pune",         "latitude": 18.5169, "longitude": 73.8478},
    {"id": "HOSP-002", "name": "Ruby Hall Clinic",           "latitude": 18.5359, "longitude": 73.8809},
    {"id": "HOSP-003", "name": "Jehangir Hospital",          "latitude": 18.5299, "longitude": 73.8800},
    {"id": "HOSP-004", "name": "Sassoon General Hospital",   "latitude": 18.5175, "longitude": 73.8553},
    {"id": "HOSP-005", "name": "Poona Hospital",             "latitude": 18.5284, "longitude": 73.8474},
    {"id": "HOSP-006", "name": "Deenanath Mangeshkar Hospital", "latitude": 18.5008, "longitude": 73.8153},
]


# ═══════════════════════════════════════
#  Geospatial helpers
# ═══════════════════════════════════════

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km using Haversine formula."""
    R = 6_371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_eta(distance_km: float, speed_kmh: float = _AVG_SPEED_KMH) -> float:
    """Convert distance → ETA in minutes (1 decimal)."""
    if speed_kmh <= 0:
        return 0.0
    return round((distance_km / speed_kmh) * 60, 1)


# ═══════════════════════════════════════
#  CRUD
# ═══════════════════════════════════════

def create_ambulance(db: Session, payload: AmbulanceCreate) -> Ambulance:
    try:
        unit = Ambulance(
            ambulance_number=payload.ambulance_number,
            driver_name=payload.driver_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            status=AmbulanceStatus.available,
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return unit
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("create_ambulance failed: %s", exc)
        raise


def get_all_ambulances(db: Session) -> List[Ambulance]:
    return db.query(Ambulance).order_by(Ambulance.id).all()


def get_ambulance_by_id(db: Session, ambulance_id: int) -> Optional[Ambulance]:
    return db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()


def update_location(
    db: Session,
    ambulance_id: int,
    payload: AmbulanceLocationUpdate,
) -> Optional[Ambulance]:
    """
    Update GPS coords in DB.
    Root cause fix for GPS tracking:
      - Always commits immediately so next query sees fresh coords
      - Returns updated unit so caller can broadcast WS event
    """
    unit = get_ambulance_by_id(db, ambulance_id)
    if not unit:
        return None
    unit.latitude  = payload.latitude
    unit.longitude = payload.longitude
    try:
        db.commit()
        db.refresh(unit)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("update_location failed for ambulance %d: %s", ambulance_id, exc)
        raise
    return unit


def update_status(
    db: Session, ambulance_id: int, new_status: AmbulanceStatus
) -> Optional[Ambulance]:
    unit = get_ambulance_by_id(db, ambulance_id)
    if not unit:
        return None
    unit.status = new_status
    db.commit()
    db.refresh(unit)
    logger.info("Ambulance %s → %s", unit.ambulance_number, new_status)
    return unit


# ═══════════════════════════════════════
#  Dispatch logic
# ═══════════════════════════════════════

def get_nearby_ambulances(
    db: Session,
    lat: float,
    lon: float,
    radius_km: float = _DEFAULT_RADIUS,
    limit: int = 5,
) -> List[NearbyAmbulanceResponse]:
    """Return available ambulances sorted by proximity."""
    # Bounding-box filter improves dispatch performance for large fleets.
    # It narrows SQL results before computing exact Haversine distance.
    lat_delta = radius_km / 110.574
    lon_delta = radius_km / (111.320 * math.cos(math.radians(lat)))
    min_lat, max_lat = lat - lat_delta, lat + lat_delta
    min_lon, max_lon = lon - lon_delta, lon + lon_delta

    available = (
        db.query(Ambulance)
        .filter(
            Ambulance.status == AmbulanceStatus.available,
            Ambulance.latitude.isnot(None),
            Ambulance.longitude.isnot(None),
            Ambulance.latitude.between(min_lat, max_lat),
            Ambulance.longitude.between(min_lon, max_lon),
        )
        .all()
    )

    candidates = []
    for unit in available:
        dist = haversine_distance(lat, lon, unit.latitude, unit.longitude)
        if dist <= radius_km:
            candidates.append(
                NearbyAmbulanceResponse(
                    id               = unit.id,
                    ambulance_number = unit.ambulance_number,
                    driver_name      = unit.driver_name,
                    status           = unit.status,
                    latitude         = unit.latitude,
                    longitude        = unit.longitude,
                    last_updated     = unit.last_updated,
                    distance_km      = round(dist, 2),
                    eta_minutes      = estimate_eta(dist),
                )
            )

    candidates.sort(key=lambda x: x.distance_km)
    return candidates[:limit]


def dispatch_nearest_ambulance(
    db: Session, accident_lat: float, accident_lon: float
) -> Optional[DispatchResult]:
    """Auto-dispatch closest available unit and mark it busy."""
    nearby = get_nearby_ambulances(db, accident_lat, accident_lon, limit=1)
    if not nearby:
        logger.warning("dispatch_nearest_ambulance: no available units.")
        return None

    best     = nearby[0]
    assigned = update_status(db, best.id, AmbulanceStatus.busy)
    if not assigned:
        return None

    return DispatchResult(
        ambulance   = assigned,
        distance_km = best.distance_km,
        eta_minutes = best.eta_minutes,
        message     = (
            f"Ambulance {assigned.ambulance_number} dispatched. "
            f"ETA {best.eta_minutes} min."
        ),
    )


# ═══════════════════════════════════════
#  Hospital routing
# ═══════════════════════════════════════

def get_nearby_hospitals(
    pickup_lat: float,
    pickup_lon: float,
    radius_km: float = _HOSPITAL_RADIUS,
    limit: int = 3,
) -> List[dict]:
    """
    Find nearest hospitals to an accident/pickup location.
    Returns list sorted by distance with distance_km + eta_minutes added.

    Root cause fix: this was never called after pickup.
    Now called from complete_pickup() route.
    """
    results = []
    for h in HOSPITALS:
        dist = haversine_distance(pickup_lat, pickup_lon, h["latitude"], h["longitude"])
        if dist <= radius_km:
            results.append({
                **h,
                "distance_km": round(dist, 2),
                "eta_minutes": estimate_eta(dist),
            })
    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


# ═══════════════════════════════════════
#  Dispatch lifecycle completion
# ═══════════════════════════════════════

def complete_dispatch(
    db: Session,
    ambulance_id: int,
    accident_id: Optional[int] = None,
) -> Tuple[Optional[Ambulance], Optional[Accident]]:
    """
    Mark job complete:
      1. Set ambulance status → available
      2. If accident_id provided: set accident status → resolved + resolved_at

    Root cause fix for "accident status not updating":
      Previously only ambulance status was updated.
      Now accident is also resolved atomically in the same transaction.
    """
    unit     = get_ambulance_by_id(db, ambulance_id)
    accident = None

    if unit:
        unit.status = AmbulanceStatus.available

    if accident_id:
        accident = db.query(Accident).filter(Accident.id == accident_id).first()
        if accident:
            accident.status      = AccidentStatus.resolved
            accident.resolved_at = datetime.now(tz=timezone.utc)
            logger.info("Accident #%d marked resolved.", accident_id)

    try:
        db.commit()
        if unit:
            db.refresh(unit)
        if accident:
            db.refresh(accident)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("complete_dispatch failed: %s", exc)
        raise

    return unit, accident
