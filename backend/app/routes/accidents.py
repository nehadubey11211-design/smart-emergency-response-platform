"""
FILE: backend/app/routes/accidents.py
===========================================
Accident CRUD Endpoints + WebSocket Live Feed
===========================================
"""

import json
from datetime import datetime, timezone
from typing import List, Optional
from app.integrations.accident_dispatch import trigger_ambulance_dispatch

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.integrations.accident_dispatch import trigger_ambulance_dispatch
from app.models.accident_model import Accident, accident_status
from app.schemas.accident_schema import (
    AccidentCreate,
    AccidentResponse,
    AccidentUpdate,
)
from app.services.alert_services import AlertService
from app.services.notification_services import NotificationService

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔗 WS client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WS client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get(
    "/",
    response_model=List[AccidentResponse],
    summary="List all accidents",
)
async def get_accidents(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Accident)
    if status:
        query = query.filter(Accident.status == status)

    result = await db.execute(
        query.order_by(Accident.detected_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post(
    "/",
    response_model=AccidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new accident (called by AI module)",
)
async def create_accident(
    accident_data: AccidentCreate,
    db: AsyncSession = Depends(get_db),
):
    accident = Accident(**accident_data.model_dump())
    db.add(accident)
    await db.commit()
    await db.refresh(accident)

    print(f"🚨 New accident #{accident.id} at {accident.location} [{accident.severity}]")

    await manager.broadcast({
        "type": "NEW_ACCIDENT",
        "data": {
            "id": accident.id,
            "location": accident.location,
            "severity": accident.severity,
            "confidence": accident.confidence,
            "detected_at": str(accident.detected_at),
        },
    })

    await AlertService.send_alert(accident)
    await NotificationService.notify_all(accident)

    # ── Ambulance dispatch ─────────────────────────────────────
    if accident.latitude and accident.longitude:
        await trigger_ambulance_dispatch(
            db            = db,
            accident_id   = accident.id,
            accident_lat  = accident.latitude,
            accident_lon  = accident.longitude,
            severity      = accident.severity,
            confidence    = accident.confidence or 0.0,
            location_desc = accident.location or "",
        )

    return accident


@router.get(
    "/{accident_id}",
    response_model=AccidentResponse,
    summary="Get a single accident by ID",
)
async def get_accident(accident_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Accident).where(Accident.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )
    return accident


@router.patch(
    "/{accident_id}",
    response_model=AccidentResponse,
    summary="Update accident status or severity",
)
async def update_accident(
    accident_id: int,
    update_data: AccidentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Accident).where(Accident.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )

    updates = update_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(accident, field, value)

    if update_data.status == accident_status.resolved and accident.resolved_at is None:
        accident.resolved_at = datetime.now(tz=timezone.utc)

    await db.commit()
    await db.refresh(accident)
    return accident


@router.delete(
    "/{accident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an accident record (admin only)",
)
async def delete_accident(accident_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Accident).where(Accident.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )
    await db.delete(accident)
    await db.commit()
