"""
FILE :backend/app/websockets/ambulance_manager.py
============================================
Ambulance WebSocket Connection Manager

Root cause fixes:
  - Alerts missed when dashboard closed: store last N events in memory
    so reconnecting clients can fetch missed events via REST
  - Continuous reconnect loop: manager never causes side effects
  - Pong/keepalive not stored as alerts: handled at route level

Architecture:
  - ambulance_id → WebSocket (one connection per unit)
  - event_history: last 50 events per ambulance_id stored in memory
    so /api/ambulances/{id}/missed-alerts endpoint can replay them
"""

import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# How many events to keep in memory per ambulance (for replay on reconnect)
EVENT_HISTORY_SIZE = 50


class AmbulanceConnectionManager:
    def __init__(self) -> None:
        # ambulance_id → active WebSocket
        self._connections: Dict[int, WebSocket] = {}

        # ambulance_id → deque of last N events (for missed-alert replay)
        self._event_history: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=EVENT_HISTORY_SIZE)
        )

        # Global event log (for operator dashboard queries)
        self._global_history: deque = deque(maxlen=200)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, ambulance_id: int) -> None:
        await websocket.accept()
        self._connections[ambulance_id] = websocket
        logger.info(
            "Ambulance %d connected via WS. Active: %d",
            ambulance_id, len(self._connections),
        )

    def disconnect(self, ambulance_id: int) -> None:
        self._connections.pop(ambulance_id, None)
        logger.info(
            "Ambulance %d disconnected. Remaining: %d",
            ambulance_id, len(self._connections),
        )

    def is_connected(self, ambulance_id: int) -> bool:
        ws = self._connections.get(ambulance_id)
        return ws is not None

    # ── Messaging ──────────────────────────────────────────────────────────

    def _store_event(self, ambulance_id: int, payload: dict) -> None:
        """
        Persist event in memory so reconnecting clients can retrieve it.
        Only stores real alert events (not pong/keepalive).
        """
        ALERT_TYPES = {
            "DISPATCH_ALERT", "NEARBY_ACCIDENT_ALERT",
            "DISPATCH_ACCEPTED", "DISPATCH_COMPLETED", "LOCATION_UPDATE",
        }
        if payload.get("type") in ALERT_TYPES:
            stamped = {**payload, "server_timestamp": datetime.now(timezone.utc).isoformat()}
            self._event_history[ambulance_id].append(stamped)
            self._global_history.append({**stamped, "ambulance_id": ambulance_id})

    async def send_to_ambulance(self, ambulance_id: int, payload: dict) -> bool:
        """
        Send to ONE ambulance. Returns True if delivered via WS.
        Always stores in history regardless of delivery.
        """
        self._store_event(ambulance_id, payload)

        ws = self._connections.get(ambulance_id)
        if not ws:
            logger.debug(
                "Ambulance %d not connected — event stored for replay.", ambulance_id
            )
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception as exc:
            logger.warning("send_to_ambulance %d failed: %s", ambulance_id, exc)
            self.disconnect(ambulance_id)
            return False

    async def broadcast_to_nearby(
        self, ambulance_ids: List[int], payload: dict
    ) -> None:
        """Push awareness alert to multiple nearby units."""
        stale: List[int] = []
        for amb_id in ambulance_ids:
            self._store_event(amb_id, payload)
            ws = self._connections.get(amb_id)
            if not ws:
                continue
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("Broadcast failed for ambulance %d: %s", amb_id, exc)
                stale.append(amb_id)
        for amb_id in stale:
            self.disconnect(amb_id)

    async def broadcast_all(self, payload: dict) -> None:
        """Send system-wide message to every connected unit."""
        stale: List[int] = []
        for amb_id, ws in list(self._connections.items()):
            self._store_event(amb_id, payload)
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(amb_id)
        for amb_id in stale:
            self.disconnect(amb_id)

    # ── Replay / History ───────────────────────────────────────────────────

    def get_missed_alerts(
        self, ambulance_id: int, since_iso: Optional[str] = None
    ) -> List[dict]:
        """
        Return stored events for an ambulance, optionally filtered by timestamp.
        Called by GET /api/ambulances/{id}/missed-alerts on reconnect.

        This is the fix for "alerts missed when dashboard was closed":
        client reconnects → fetches missed alerts → renders them.
        """
        history = list(self._event_history.get(ambulance_id, []))
        if since_iso:
            try:
                since = datetime.fromisoformat(since_iso)
                history = [
                    e for e in history
                    if datetime.fromisoformat(e.get("server_timestamp", "1970-01-01")) > since
                ]
            except ValueError:
                pass
        return history

    def get_global_history(self, limit: int = 50) -> List[dict]:
        """For operator dashboard — recent events across all ambulances."""
        return list(self._global_history)[-limit:]

    @property
    def connected_ids(self) -> List[int]:
        return list(self._connections.keys())

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton
ambulance_ws_manager = AmbulanceConnectionManager()