"""
FILE : backend/app/routes/ambulance_routes.py
REST + WebSocket endpoints for the ambulance dispatch lifecycle.

New endpoints added (root cause fixes):
  GET  /ambulances/{id}/missed-alerts   → replay missed events on reconnect
  POST /ambulances/{id}/pickup          → patient picked up; find nearest hospital
  POST /ambulances/{id}/complete        → hospital reached; resolve accident
  POST /ambulances/{id}/location        → GPS ping + WS broadcast
  GET  /ambulances/hospitals/nearby     → nearest hospitals to coordinates
  WS   /ambulances/ws/{id}             → persistent real-time channel
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    WebSocket, WebSocketDisconnect, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.routes.auth import decode_token, get_current_user_from_header
from app.models.ambulance import AmbulanceStatus
from app.schemas.ambulance import (
    AmbulanceCreate, AmbulanceLocationUpdate, AmbulanceStatusUpdate,
    AmbulanceResponse, NearbyAmbulanceResponse, DispatchResult,
)
from app.services import ambulance_service as svc
from app.websockets.ambulance_manager import ambulance_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ambulances", tags=["Ambulance Dispatch"])

# ═══════════════════════════════════════
#  Registration & listing
# ═══════════════════════════════════════

@router.post("/register", response_model=AmbulanceResponse, status_code=201)
async def register_ambulance(
    payload: AmbulanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    try:
        return await svc.create_ambulance(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[AmbulanceResponse])
async def list_ambulances(db: AsyncSession = Depends(get_db)):
    return await svc.get_all_ambulances(db)


@router.get("/nearby", response_model=list[NearbyAmbulanceResponse])
async def get_nearby(
    lat: float       = Query(..., ge=-90, le=90),
    lon: float       = Query(..., ge=-180, le=180),
    radius_km: float = Query(20.0),
    limit: int       = Query(5),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_nearby_ambulances(db, lat, lon, radius_km, limit)
  
# ═══════════════════════════════════════
#  Hospital routing
# ═══════════════════════════════════════

@router.get("/hospitals/nearby")
async def get_nearby_hospitals(
    lat: float       = Query(..., description="Pickup/accident latitude"),
    lon: float       = Query(..., description="Pickup/accident longitude"),
    radius_km: float = Query(30.0),
    limit: int       = Query(3),
):
    """
    Find nearest hospitals to a given location.
    Called by frontend after patient pickup to render Route 2.
    """
    hospitals = svc.get_nearby_hospitals(lat, lon, radius_km, limit)
    if not hospitals:
        raise HTTPException(status_code=404, detail="No hospitals found within radius.")
    return hospitals

# ═══════════════════════════════════════
#  Single-unit operations
# ═══════════════════════════════════════

@router.get("/{ambulance_id}", response_model=AmbulanceResponse)
async def get_ambulance(ambulance_id: int, db: AsyncSession = Depends(get_db)):
    unit = await svc.get_ambulance_by_id(db, ambulance_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")
    return unit


@router.put("/{ambulance_id}/location", response_model=AmbulanceResponse)
async def update_location(
    ambulance_id: int,
    payload: AmbulanceLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    """
    GPS ping from ambulance device (called every ~5 seconds).

    Root cause fix for GPS tracking not working:
      - Commits immediately to DB
      - Broadcasts LOCATION_UPDATE via WebSocket so map marker moves in real time
      - Returns updated unit with fresh coords
    """
    unit = await svc.update_location(db, ambulance_id, payload)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    await ambulance_ws_manager.broadcast_all({
        "type": "LOCATION_UPDATE",
        "ambulance_id": ambulance_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return unit


@router.put("/{ambulance_id}/status", response_model=AmbulanceResponse)
async def update_status(
    ambulance_id: int,
    payload: AmbulanceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    unit = await svc.update_status(db, ambulance_id, payload.status)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")
    return unit

# ═══════════════════════════════════════
#  Missed-alert replay (fixes closed dashboard issue)
# ═══════════════════════════════════════

@router.get("/{ambulance_id}/missed-alerts")
async def get_missed_alerts(
    ambulance_id: int,
    since: str = Query(None, description="ISO timestamp — return events after this"),
):
    """
    Return stored alert events for an ambulance.

    Root cause fix for "alerts missed when dashboard was closed":
      Dashboard connects → immediately calls this endpoint with
      the timestamp of its last-seen event → receives all missed events
      → renders them in the alert feed.
    """
    events = ambulance_ws_manager.get_missed_alerts(ambulance_id, since_iso=since)
    return {"events": events, "count": len(events)}

# ═══════════════════════════════════════
#  Dispatch
# ═══════════════════════════════════════
@router.post("/dispatch", response_model=DispatchResult)
async def dispatch(
    lat: float       = Query(..., ge=-90, le=90),
    lon: float       = Query(..., ge=-180, le=180),
    accident_id: int = Query(None, description="Link dispatch to an accident record"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    """
    Auto-dispatch nearest available ambulance.
    Pushes DISPATCH_ALERT to the assigned unit via WebSocket.
    Stores the event for offline replay.
    """
    result = await svc.dispatch_nearest_ambulance(db, lat, lon)
    if not result:
        raise HTTPException(
            status_code = 503,
            detail      = "No available ambulances within range.",
        )

    payload = {
        "type":         "DISPATCH_ALERT",
        "accident_id":  accident_id,
        "accident_lat": lat,
        "accident_lon": lon,
        "distance_km":  result.distance_km,
        "eta_minutes":  result.eta_minutes,
        "message":      result.message,
        "time_detected": datetime.now(timezone.utc).isoformat(),
        "sound":        True,
        # Route 1 waypoints for map rendering
        "route": {
            "from": {"lat": result.ambulance.latitude, "lon": result.ambulance.longitude},
            "to":   {"lat": lat, "lon": lon},
            "type": "AMBULANCE_TO_ACCIDENT",
        },
    }

    # send_to_ambulance stores in history even if offline
    await ambulance_ws_manager.send_to_ambulance(result.ambulance.id, payload)

    return result


@router.post("/{ambulance_id}/accept")
async def accept_dispatch(
    ambulance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    unit = await svc.get_ambulance_by_id(db, ambulance_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    await ambulance_ws_manager.broadcast_all({
        "type":             "DISPATCH_ACCEPTED",
        "ambulance_id":     ambulance_id,
        "ambulance_number": unit.ambulance_number,
        "driver_name":      unit.driver_name,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"{unit.ambulance_number} is en-route."}


@router.post("/{ambulance_id}/pickup")
async def patient_pickup(
    ambulance_id: int,
    accident_lat: float = Query(..., description="Accident/pickup latitude"),
    accident_lon: float = Query(..., description="Accident/pickup longitude"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    """
    Driver has picked up patient.

    Root cause fix for hospital routing:
      1. Find nearest hospitals to pickup location
      2. Return Route 2 waypoints (accident → hospital)
      3. Broadcast HOSPITAL_ROUTE event to dashboard

    Frontend uses response to render Route 2 on the map.
    """
    unit = await svc.get_ambulance_by_id(db, ambulance_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    hospitals = svc.get_nearby_hospitals(accident_lat, accident_lon, limit=1)
    if not hospitals:
        raise HTTPException(status_code=404, detail="No hospitals found nearby.")

    nearest_hospital = hospitals[0]

    hospital_route_payload = {
        "type": "HOSPITAL_ROUTE",
        "ambulance_id": ambulance_id,
        "pickup_lat": accident_lat,
        "pickup_lon": accident_lon,
        "hospital": nearest_hospital,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": {
            "from": {"lat": accident_lat, "lon": accident_lon},
            "to": {
                "lat": nearest_hospital["latitude"],
                "lon": nearest_hospital["longitude"],
            },
            "type": "ACCIDENT_TO_HOSPITAL",
            "hospital_name": nearest_hospital["name"],
            "eta_minutes": nearest_hospital["eta_minutes"],
            "distance_km": nearest_hospital["distance_km"],
        },
    }

    await ambulance_ws_manager.send_to_ambulance(ambulance_id, hospital_route_payload)
    await ambulance_ws_manager.broadcast_all(hospital_route_payload)

    return {
        "message": "Patient picked up. Route to hospital generated.",
        "nearest_hospital": nearest_hospital,
        "route_payload": hospital_route_payload,
    }


@router.post("/{ambulance_id}/complete")
async def complete_dispatch(
    ambulance_id: int,
    accident_id: int = Query(None, description="Accident to mark resolved"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    """
    Hospital reached. Marks:
      - Ambulance → available
      - Accident  → resolved (if accident_id provided)

    Root cause fix for accident status not updating:
      Previously only ambulance status changed.
      Now both ambulance + accident are updated atomically.
    """
    unit, accident = await svc.complete_dispatch(db, ambulance_id, accident_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    completion_payload = {
        "type":             "DISPATCH_COMPLETED",
        "ambulance_id":     ambulance_id,
        "ambulance_number": unit.ambulance_number,
        "accident_id":      accident_id,
        "accident_resolved": accident is not None,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "message":          "Emergency handled. Unit now available.",
    }

    await ambulance_ws_manager.send_to_ambulance(ambulance_id, completion_payload)
    await ambulance_ws_manager.broadcast_all(completion_payload)

    return {
        "ambulance": unit,
        "accident_resolved": accident is not None,
        "message": completion_payload["message"],
    }


# ═══════════════════════════════════════
#  WebSocket — real-time channel
# ═══════════════════════════════════════

@router.websocket("/ws/{ambulance_id}")
async def ambulance_websocket(websocket: WebSocket, ambulance_id: int, token: str = Query(...)):
    """
    Persistent WebSocket connection for one ambulance unit.

    Root cause fixes:
      - Pong NOT stored as alert (handled here, not in manager)
      - connect() dep cycle broken: manager has no React deps
      - Reconnect loop: onclose in frontend uses stable connect()
        with ambulanceId-only dep

    Messages received from client:
      { "type": "ping" }                → keepalive
      { "type": "location_update", "lat": float, "lon": float }
      { "type": "status_update", "status": str }

    Messages pushed to client:
      DISPATCH_ALERT | HOSPITAL_ROUTE | DISPATCH_COMPLETED | LOCATION_UPDATE
    """
    user_id = decode_token(token)
    if user_id is None:
        logger.warning("WS auth failed for ambulance %d (invalid or expired token)", ambulance_id)
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    await ambulance_ws_manager.connect(websocket, ambulance_id)
    logger.info("WS opened: ambulance %d", ambulance_id)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                # Reply pong — NOT stored as an alert event
                await websocket.send_json({"type": "pong"})

            elif msg_type == "location_update":
                # Real-time location via WS (alternative to REST GPS ping)
                lat = data.get("lat")
                lon = data.get("lon")
                logger.debug(
                    "WS location ambulance %d: %s, %s",
                    ambulance_id, lat, lon,
                )

                if lat is not None and lon is not None:
                    # Validate coordinate ranges
                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        await websocket.send_json({"type": "error", "detail": "Invalid coordinates"})
                        continue

                    # Persist to DB — create a fresh AsyncSession for this background operation
                    from app.database.db import SessionLocal
                    from app.schemas.ambulance import AmbulanceLocationUpdate

                    try:
                        async with SessionLocal() as _db:
                            await svc.update_location(
                                _db,
                                ambulance_id,
                                AmbulanceLocationUpdate(latitude=lat, longitude=lon),
                            )
                    except Exception as e:
                        logger.error("WS location save failed for ambulance %d: %s", ambulance_id, e)

                # Broadcast to operator dashboards
                await ambulance_ws_manager.broadcast_all({
                    "type":         "LOCATION_UPDATE",
                    "ambulance_id": ambulance_id,
                    "latitude":     lat,
                    "longitude":    lon,
                    "timestamp":    datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        ambulance_ws_manager.disconnect(ambulance_id)
        logger.info("WS closed cleanly: ambulance %d", ambulance_id)
    except Exception as exc:
        logger.error("WS error ambulance %d: %s", ambulance_id, exc)
        ambulance_ws_manager.disconnect(ambulance_id)
