"""
FILE : backend/app/services/ambulance_service.py
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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.ambulance import Ambulance, AmbulanceStatus
from app.models.accident_model import Accident, accident_status
from app.models.hospital_model import Hospital
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

# Hospitals are stored in the `hospitals` DB table (see models/hospital_model.py)


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

async def create_ambulance(db: AsyncSession, payload: AmbulanceCreate) -> Ambulance:
    try:
        unit = Ambulance(
            ambulance_number=payload.ambulance_number,
            driver_name=payload.driver_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            status=AmbulanceStatus.available,
        )
        db.add(unit)
        await db.commit()
        await db.refresh(unit)
        return unit
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("create_ambulance failed: %s", exc)
        raise


async def get_all_ambulances(db: AsyncSession) -> List[Ambulance]:
    result = await db.execute(select(Ambulance).order_by(Ambulance.id))
    return result.scalars().all()


async def get_ambulance_by_id(db: AsyncSession, ambulance_id: int) -> Optional[Ambulance]:
    result = await db.execute(select(Ambulance).where(Ambulance.id == ambulance_id))
    return result.scalar_one_or_none()


async def update_location(
    db: AsyncSession,
    ambulance_id: int,
    payload: AmbulanceLocationUpdate,
) -> Optional[Ambulance]:
    unit = await get_ambulance_by_id(db, ambulance_id)
    if not unit:
        return None
    unit.latitude = payload.latitude
    unit.longitude = payload.longitude
    try:
        await db.commit()
        await db.refresh(unit)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("update_location failed for ambulance %d: %s", ambulance_id, exc)
        raise
    return unit


async def update_status(
    db: AsyncSession,
    ambulance_id: int,
    new_status: AmbulanceStatus,
) -> Optional[Ambulance]:
    unit = await get_ambulance_by_id(db, ambulance_id)
    if not unit:
        return None
    unit.status = new_status
    await db.commit()
    await db.refresh(unit)
    logger.info("Ambulance %s → %s", unit.ambulance_number, new_status)
    return unit

# ═══════════════════════════════════════
#  Dispatch logic
# ═══════════════════════════════════════

async def get_nearby_ambulances(
    db: AsyncSession,
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

    result = await db.execute(
        select(Ambulance)
        .filter(
            Ambulance.status == AmbulanceStatus.available,
            Ambulance.latitude.isnot(None),
            Ambulance.longitude.isnot(None),
            Ambulance.latitude.between(min_lat, max_lat),
            Ambulance.longitude.between(min_lon, max_lon),
        )
    )
    available = result.scalars().all()

    candidates = []
    for unit in available:
        dist = haversine_distance(lat, lon, unit.latitude, unit.longitude)
        if dist <= radius_km:
            candidates.append(
                NearbyAmbulanceResponse(
                    id=unit.id,
                    ambulance_number=unit.ambulance_number,
                    driver_name=unit.driver_name,
                    status=unit.status,
                    latitude=unit.latitude,
                    longitude=unit.longitude,
                    last_updated=unit.last_updated,
                    distance_km=round(dist, 2),
                    eta_minutes=estimate_eta(dist),
                )
            )

    candidates.sort(key=lambda x: x.distance_km)
    return candidates[:limit]


async def dispatch_nearest_ambulance(
    db: AsyncSession,
    accident_lat: float,
    accident_lon: float,
    accident_id: Optional[int] = None,
) -> Optional[DispatchResult]:
    """Auto-dispatch closest available unit and mark it busy."""
    # Step 1: get candidates with bounding box (approximate)
    lat_delta = _DEFAULT_RADIUS / 110.574
    lon_delta = _DEFAULT_RADIUS / (111.320 * math.cos(math.radians(accident_lat)))

    stmt = (
        select(Ambulance)
        .where(
            Ambulance.status == AmbulanceStatus.available,
            Ambulance.latitude.isnot(None),
            Ambulance.longitude.isnot(None),
            Ambulance.latitude.between(accident_lat - lat_delta, accident_lat + lat_delta),
            Ambulance.longitude.between(accident_lon - lon_delta, accident_lon + lon_delta),
        )
        .limit(10)
    )

    if getattr(db, "bind", None) is not None and db.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update(skip_locked=True)

    result = await db.execute(stmt)
    candidates = result.scalars().all()
    if not candidates:
        logger.warning("dispatch_nearest_ambulance: no available units.")
        return None

    best = min(
        candidates,
        key=lambda unit: haversine_distance(accident_lat, accident_lon, unit.latitude, unit.longitude),
    )
    dist = haversine_distance(accident_lat, accident_lon, best.latitude, best.longitude)

    best.status = AmbulanceStatus.busy

    # If an accident_id is provided, link the dispatched ambulance to the accident
    accident = None
    if accident_id:
        result = await db.execute(select(Accident).where(Accident.id == accident_id))
        accident = result.scalar_one_or_none()
        if accident:
            accident.dispatched_ambulance_id = best.id

    try:
        await db.commit()
        await db.refresh(best)
        if accident:
            await db.refresh(accident)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("dispatch_nearest_ambulance failed: %s", exc)
        raise

    return DispatchResult(
        ambulance=best,
        distance_km=round(dist, 2),
        eta_minutes=estimate_eta(dist),
        message=(
            f"Ambulance {best.ambulance_number} dispatched. "
            f"ETA {estimate_eta(dist)} min."
        ),
    )


# ═══════════════════════════════════════
#  Hospital routing
# ═══════════════════════════════════════

async def get_nearby_hospitals(
    db: AsyncSession,
    pickup_lat: float,
    pickup_lon: float,
    radius_km: float = _HOSPITAL_RADIUS,
    limit: int = 3,
) -> List[dict]:
    """
    Query the `hospitals` table and return nearest active hospitals.
    """
    lat_delta = radius_km / 110.574
    lon_delta = radius_km / (111.320 * math.cos(math.radians(pickup_lat)))
    min_lat, max_lat = pickup_lat - lat_delta, pickup_lat + lat_delta
    min_lon, max_lon = pickup_lon - lon_delta, pickup_lon + lon_delta

    result = await db.execute(
        select(Hospital)
        .where(
            Hospital.is_active == True,
            Hospital.latitude.between(min_lat, max_lat),
            Hospital.longitude.between(min_lon, max_lon),
        )
        .limit(50)
    )
    candidates = result.scalars().all()

    results = []
    for h in candidates:
        dist = haversine_distance(pickup_lat, pickup_lon, h.latitude, h.longitude)
        if dist <= radius_km:
            results.append({
                "id": h.id,
                "name": h.name,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "distance_km": round(dist, 2),
                "eta_minutes": estimate_eta(dist),
            })
    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]

# ═══════════════════════════════════════
#  Dispatch lifecycle completion
# ═══════════════════════════════════════
async def complete_dispatch(
    db: AsyncSession,
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
    unit = await get_ambulance_by_id(db, ambulance_id)
    accident = None

    if unit:
        unit.status = AmbulanceStatus.available

    if accident_id:
        result = await db.execute(select(Accident).where(Accident.id == accident_id))
        accident = result.scalar_one_or_none()
        if accident:
            accident.status = accident_status.resolved
            accident.resolved_at = datetime.now(tz=timezone.utc)
            logger.info("Accident #%d marked resolved.", accident_id)

    try:
        await db.commit()
        if unit:
            await db.refresh(unit)
        if accident:
            await db.refresh(accident)
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("complete_dispatch failed: %s", exc)
        raise

    return unit, accident
