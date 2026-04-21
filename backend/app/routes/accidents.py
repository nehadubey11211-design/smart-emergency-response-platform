"""
FILE: backend/app/routes/accidents.py
===========================================
Accident CRUD Endpoints + WebSocket Live Feed
===========================================

This module handles:
  1. REST endpoints for creating, reading, and updating accident records
  2. A WebSocket endpoint that pushes real-time alerts to all connected dashboards

WEBSOCKET PATTERN — ConnectionManager:
  The ConnectionManager class maintains a list of active WebSocket connections.
  When a new accident is created (by the AI module), it broadcasts the event
  to EVERY connected dashboard client simultaneously.

  This is the Observer / Pub-Sub pattern:
    Publisher  : POST /api/accidents/  (AI module)
    Subscribers: All dashboards connected via ws://... /api/accidents/ws

  In production you'd replace the in-memory list with Redis Pub-Sub so that
  multiple backend server instances can all broadcast to all connected clients.

INTERVIEW TALKING POINT:
  "I used WebSockets instead of polling because emergency alerts need to reach
  operators within 1 second. HTTP polling every 5 seconds means a worst-case
  delay of 5 seconds — unacceptable in a life-safety context."
"""

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.accident_model import Accident, AccidentStatus
from app.schemas.accident_schema import (
    AccidentCreate,
    AccidentResponse,
    AccidentUpdate,
)
from app.services.alert_services import AlertService
from app.services.notification_services import NotificationService

router = APIRouter()


# ─── WebSocket Connection Manager ────────────────────────────────────────────

class ConnectionManager:
    """
    Manages all active WebSocket connections from dashboard clients.

    Design decisions:
      - Simple in-memory list (sufficient for a single-server deployment)
      - Production upgrade: replace with Redis Pub/Sub for multi-server clusters
      - Gracefully skips dead connections during broadcast (try/except)
    """

    def __init__(self):
        # List of currently connected WebSocket clients
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket handshake and register the connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔗 WS client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client from the registry."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WS client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Send a JSON message to ALL connected clients simultaneously.

        We iterate over a COPY of the list because a send failure triggers
        disconnect() which modifies the original list — iterating a list
        while modifying it causes a RuntimeError.
        """
        disconnected = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # This connection is dead — mark for removal
                disconnected.append(connection)

        # Clean up dead connections after the loop
        for conn in disconnected:
            self.disconnect(conn)


# Module-level singleton — shared across all requests in this process
manager = ConnectionManager()


# ─── WebSocket Endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Persistent WebSocket connection for real-time incident alerts.

    Frontend usage:
      const ws = new WebSocket("ws://localhost:8000/api/accidents/ws");
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "NEW_ACCIDENT") showAlert(msg.data);
      };

    The server keeps this connection open indefinitely.
    The while True loop keeps the coroutine alive; receive_text() yields
    control back to the event loop while waiting for client messages.
    """
    await manager.connect(websocket)
    try:
        while True:
            # We don't use client messages here, but we must keep receiving
            # to detect disconnects and release the connection slot.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[AccidentResponse],
    summary="List all accidents",
)
def get_accidents(
    skip:   int = 0,
    limit:  int = 50,
    status: str = None,    # Optional filter: detected | responding | resolved
    db: Session = Depends(get_db),
):
    """
    Paginated list of accidents, newest first.

    Pagination via skip/limit is a standard REST pattern:
      GET /accidents/?skip=0&limit=20   → first page
      GET /accidents/?skip=20&limit=20  → second page

    skip + limit is simpler than cursor-based pagination and works well
    for moderate data sizes (< 1 million rows).
    """
    query = db.query(Accident)

    # Apply optional status filter
    if status:
        query = query.filter(Accident.status == status)

    return (
        query
        .order_by(Accident.detected_at.desc())  # Newest first
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/",
    response_model=AccidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new accident (called by AI module)",
)
async def create_accident(
    accident_data: AccidentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new accident record.

    Called by detect_accident.py in the AI module whenever the CNN detects
    an accident with sufficient confidence.

    After saving to the DB, this handler does three things in parallel:
      1. Broadcasts a WebSocket alert to all connected dashboards
      2. Sends an email notification to operators
      3. Logs to console (for debugging)

    Using async def here because we await WebSocket broadcast + email send.
    """
    # ── Persist to database ─────────────────────────────────────────────────
    accident = Accident(**accident_data.model_dump())
    db.add(accident)
    db.commit()
    db.refresh(accident)

    print(f"🚨 New accident #{accident.id} at {accident.location} [{accident.severity}]")

    # ── Real-time alert to dashboard(s) ─────────────────────────────────────
    # Keep the WebSocket payload small — dashboard fetches full details via REST
    await manager.broadcast({
        "type": "NEW_ACCIDENT",
        "data": {
            "id":          accident.id,
            "location":    accident.location,
            "severity":    accident.severity,
            "confidence":  accident.confidence,
            "detected_at": str(accident.detected_at),
        },
    })

    # ── Notification pipeline ─────────────────────────────────────────────────
    # Runs email + console log; won't crash the endpoint if it fails
    await AlertService.send_alert(accident)
    await NotificationService.notify_all(accident)

    return accident


@router.get(
    "/{accident_id}",
    response_model=AccidentResponse,
    summary="Get a single accident by ID",
)
def get_accident(accident_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific accident record.
    Returns 404 if not found rather than an empty response.
    """
    accident = db.query(Accident).filter(Accident.id == accident_id).first()
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
def update_accident(
    accident_id:  int,
    update_data:  AccidentUpdate,
    db: Session = Depends(get_db),
):
    """
    Partial update for an accident (PATCH semantics).
    Operators use this to:
      - Acknowledge an alert (detected → responding)
      - Close an incident  (responding → resolved)
      - Escalate severity  (medium → high)

    model_dump(exclude_unset=True) returns only the fields the client
    actually sent — so un-sent fields don't overwrite existing values.
    This is the correct implementation of PATCH (as opposed to PUT which
    replaces the whole resource).
    """
    accident = db.query(Accident).filter(Accident.id == accident_id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )

    # Apply only the fields that were included in the request
    updates = update_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(accident, field, value)

    # Auto-stamp resolution time when an incident is closed
    if update_data.status == AccidentStatus.resolved and accident.resolved_at is None:
        accident.resolved_at = datetime.now(tz=timezone.utc)

    db.commit()
    db.refresh(accident)
    return accident


@router.delete(
    "/{accident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an accident record (admin only)",
)
def delete_accident(accident_id: int, db: Session = Depends(get_db)):
    """
    Hard-delete an accident record.
    NOTE: In production, prefer soft-deletes (is_deleted flag) to preserve
    audit history.  Hard deletes are provided here for development cleanup.
    """
    accident = db.query(Accident).filter(Accident.id == accident_id).first()
    if not accident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Accident with id={accident_id} not found",
        )
    db.delete(accident)
    db.commit()
    # 204 No Content — no response body
