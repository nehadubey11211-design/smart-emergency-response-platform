"""
FILE: backend/app/routes/accidents.py
===========================================
Accident CRUD Endpoints + WebSocket Live Feed
===========================================
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.integrations.accident_dispatch import trigger_ambulance_dispatch

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
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

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_TRANSITIONS = {
    AccidentStatus.detected:   {AccidentStatus.responding, AccidentStatus.resolved},
    AccidentStatus.responding: {AccidentStatus.resolved},
    AccidentStatus.resolved:   set(),
}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WS client connected. Total: %s", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WS client disconnected. Remaining: %s", len(self.active_connections))

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
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    if decode_token(token) is None:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text('{"type":"ping"}')
                except Exception:
                    break
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get(
    "/",
    response_model=List[AccidentResponse],
    summary="List all accidents",
)
async def get_accidents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
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
    current_user = Depends(get_current_user_from_header),
):
    accident = Accident(**accident_data.model_dump())
    db.add(accident)
    await db.commit()
    await db.refresh(accident)

    logger.info(
        "New accident #%s at %s [%s]",
        accident.id,
        accident.location,
        accident.severity,
    )

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
    current_user = Depends(get_current_user_from_header),
):
    result = await db.execute(select(Accident).where(Accident.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )

    if update_data.status and update_data.status != accident.status:
        allowed = VALID_TRANSITIONS.get(accident.status, set())
        if update_data.status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid transition: {accident.status} → {update_data.status}. "
                    f"Allowed: {[s.value for s in allowed] or 'none (terminal state)'}"
                ),
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
async def delete_accident(
    accident_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(get_admin_user),
):
    result = await db.execute(select(Accident).where(Accident.id == accident_id))
    accident = result.scalar_one_or_none()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )
    await db.delete(accident)
    await db.commit()
