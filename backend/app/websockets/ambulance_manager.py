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
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Redis client for storing event history (streams)
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

STREAM_MAXLEN = 100
GLOBAL_STREAM_KEY = "ambulance:events:global"
GLOBAL_STREAM_MAXLEN = 200


class AmbulanceConnectionManager:
    def __init__(self) -> None:
        # ambulance_id → active WebSocket
        self._connections: Dict[int, WebSocket] = {}

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

    async def _store_event(self, ambulance_id: int, payload: dict) -> None:
        """
        Persist event in Redis Streams so reconnecting clients can retrieve it.
        Only stores real alert events (not pong/keepalive).
        """
        ALERT_TYPES = {
            "DISPATCH_ALERT", "NEARBY_ACCIDENT_ALERT",
            "DISPATCH_ACCEPTED", "DISPATCH_COMPLETED", "LOCATION_UPDATE", "HOSPITAL_ROUTE",
        }
        if payload.get("type") not in ALERT_TYPES:
            return
        stamped = {**payload, "server_timestamp": datetime.now(timezone.utc).isoformat()}
        stream_key = f"ambulance:events:{ambulance_id}"
        # Add to per-ambulance stream
        await redis_client.xadd(stream_key, {"data": json.dumps(stamped)}, maxlen=STREAM_MAXLEN)
        # Add to global stream with ambulance_id included
        await redis_client.xadd(GLOBAL_STREAM_KEY, {"data": json.dumps({**stamped, "ambulance_id": ambulance_id})}, maxlen=GLOBAL_STREAM_MAXLEN)

    async def send_to_ambulance(self, ambulance_id: int, payload: dict) -> bool:
        """
        Send to ONE ambulance. Returns True if delivered via WS.
        Always stores in history regardless of delivery.
        """
        await self._store_event(ambulance_id, payload)

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
            await self._store_event(amb_id, payload)
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
            await self._store_event(amb_id, payload)
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(amb_id)
        for amb_id in stale:
            self.disconnect(amb_id)

    # ── Replay / History ───────────────────────────────────────────────────

    async def get_missed_alerts(
        self, ambulance_id: int, since_iso: Optional[str] = None
    ) -> List[dict]:
        """
        Return stored events for an ambulance, optionally filtered by timestamp.
        Called by GET /api/ambulances/{id}/missed-alerts on reconnect.

        This is the fix for "alerts missed when dashboard was closed":
        client reconnects → fetches missed alerts → renders them.
        """
        stream_key = f"ambulance:events:{ambulance_id}"
        if since_iso:
            try:
                since_dt = datetime.fromisoformat(since_iso)
                since_ms = int(since_dt.timestamp() * 1000)
                entries = await redis_client.xrange(stream_key, min=f"{since_ms}-0")
            except Exception:
                entries = await redis_client.xrange(stream_key)
        else:
            entries = await redis_client.xrange(stream_key)
        # entries: list of (id, {field: value})
        return [json.loads(e[1]["data"]) for e in entries]

    async def get_global_history(self, limit: int = 50) -> List[dict]:
        """For operator dashboard — recent events across all ambulances."""
        # Use XRANGE/XREVRANGE to get the most recent `limit` entries from the global stream
        try:
            entries = await redis_client.xrevrange(GLOBAL_STREAM_KEY, count=limit)
            # xrevrange returns newest → oldest; reverse to chronological
            entries = list(reversed(entries))
            return [json.loads(e[1]["data"]) for e in entries]
        except Exception:
            return []

    @property
    def connected_ids(self) -> List[int]:
        return list(self._connections.keys())

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton
ambulance_ws_manager = AmbulanceConnectionManager()
