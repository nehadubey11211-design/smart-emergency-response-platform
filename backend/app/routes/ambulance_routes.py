"""
FIEL : backend/app/routes/ambulance_routes.py
=======================================
REST + WebSocket endpoints for the ambulance dispatch lifecycle.
"""

import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    WebSocket, WebSocketDisconnect, status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.ambulance import AmbulanceStatus
from app.schemas.ambulance import (
    AmbulanceCreate, AmbulanceLocationUpdate, AmbulanceStatusUpdate,
    AmbulanceResponse, NearbyAmbulanceResponse, DispatchResult,
)
from app.services import ambulance_service as svc
from app.websockets.ambulance_manager import ambulance_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ambulances", tags=["Ambulance Dispatch"])


@router.post("/register", response_model=AmbulanceResponse, status_code=201)
async def register_ambulance(payload: AmbulanceCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.create_ambulance(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[AmbulanceResponse])
async def list_ambulances(db: AsyncSession = Depends(get_db)):
    return await svc.get_all_ambulances(db)


@router.get("/nearby", response_model=list[NearbyAmbulanceResponse])
async def get_nearby(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(20.0),
    limit: int = Query(5),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_nearby_ambulances(db, lat, lon, radius_km, limit)


@router.get("/hospitals/nearby")
async def get_nearby_hospitals(
    lat: float = Query(..., description="Pickup/accident latitude"),
    lon: float = Query(..., description="Pickup/accident longitude"),
    radius_km: float = Query(30.0),
    limit: int = Query(3),
):
    hospitals = svc.get_nearby_hospitals(lat, lon, radius_km, limit)
    if not hospitals:
        raise HTTPException(status_code=404, detail="No hospitals found within radius.")
    return hospitals


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
):
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
):
    unit = await svc.update_status(db, ambulance_id, payload.status)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")
    return unit


@router.get("/{ambulance_id}/missed-alerts")
async def get_missed_alerts(
    ambulance_id: int,
    since: str = Query(None, description="ISO timestamp — return events after this"),
):
    events = ambulance_ws_manager.get_missed_alerts(ambulance_id, since_iso=since)
    return {"events": events, "count": len(events)}


@router.post("/dispatch", response_model=DispatchResult)
async def dispatch(
    lat: float = Query(...),
    lon: float = Query(...),
    accident_id: int = Query(None, description="Link dispatch to an accident record"),
    db: AsyncSession = Depends(get_db),
):
    result = await svc.dispatch_nearest_ambulance(db, lat, lon)
    if not result:
        raise HTTPException(
            status_code=503,
            detail="No available ambulances within range.",
        )

    payload = {
        "type": "DISPATCH_ALERT",
        "accident_id": accident_id,
        "accident_lat": lat,
        "accident_lon": lon,
        "distance_km": result.distance_km,
        "eta_minutes": result.eta_minutes,
        "message": result.message,
        "time_detected": datetime.now(timezone.utc).isoformat(),
        "sound": True,
        "route": {
            "from": {"lat": result.ambulance.latitude, "lon": result.ambulance.longitude},
            "to": {"lat": lat, "lon": lon},
            "type": "AMBULANCE_TO_ACCIDENT",
        },
    }

    await ambulance_ws_manager.send_to_ambulance(result.ambulance.id, payload)
    return result


@router.post("/{ambulance_id}/accept")
async def accept_dispatch(ambulance_id: int, db: AsyncSession = Depends(get_db)):
    unit = await svc.get_ambulance_by_id(db, ambulance_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    await ambulance_ws_manager.broadcast_all({
        "type": "DISPATCH_ACCEPTED",
        "ambulance_id": ambulance_id,
        "ambulance_number": unit.ambulance_number,
        "driver_name": unit.driver_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": f"{unit.ambulance_number} is en-route."}


@router.post("/{ambulance_id}/pickup")
async def patient_pickup(
    ambulance_id: int,
    accident_lat: float = Query(..., description="Accident/pickup latitude"),
    accident_lon: float = Query(..., description="Accident/pickup longitude"),
    db: AsyncSession = Depends(get_db),
):
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
):
    unit, accident = await svc.complete_dispatch(db, ambulance_id, accident_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Ambulance not found.")

    completion_payload = {
        "type": "DISPATCH_COMPLETED",
        "ambulance_id": ambulance_id,
        "ambulance_number": unit.ambulance_number,
        "accident_id": accident_id,
        "accident_resolved": accident is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Emergency handled. Unit now available.",
    }

    await ambulance_ws_manager.send_to_ambulance(ambulance_id, completion_payload)
    await ambulance_ws_manager.broadcast_all(completion_payload)

    return {
        "ambulance": unit,
        "accident_resolved": accident is not None,
        "message": completion_payload["message"],
    }


@router.websocket("/ws/{ambulance_id}")
async def ambulance_websocket(websocket: WebSocket, ambulance_id: int):
    await ambulance_ws_manager.connect(websocket, ambulance_id)
    logger.info("WS opened: ambulance %d", ambulance_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "location_update":
                logger.debug(
                    "WS location ambulance %d: %s, %s",
                    ambulance_id, data.get("lat"), data.get("lon"),
                )
                await ambulance_ws_manager.broadcast_all({
                    "type": "LOCATION_UPDATE",
                    "ambulance_id": ambulance_id,
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        ambulance_ws_manager.disconnect(ambulance_id)
        logger.info("WS closed cleanly: ambulance %d", ambulance_id)
    except Exception as exc:
        logger.error("WS error ambulance %d: %s", ambulance_id, exc)
        ambulance_ws_manager.disconnect(ambulance_id)
