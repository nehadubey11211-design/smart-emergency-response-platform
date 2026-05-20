"""
FILE : backend/app/integrations/accident_dispatch.py
-----------------------------------
The single integration point between your existing accident detection
pipeline and the new ambulance dispatch system.

HOW TO USE (only change needed in accident_routes.py):
──────────────────────────────────────────────────────
    from app.integrations.accident_dispatch import trigger_ambulance_dispatch

    @router.post("/accidents/")
    async def create_accident(payload: AccidentCreate, db: Session = Depends(get_db)):
        # ... your existing code that saves the accident ...
        accident = save_accident_to_db(db, payload)          # ← existing

        # ↓ ADD THIS ONE CALL — nothing else changes
        await trigger_ambulance_dispatch(
            db            = db,
            accident_id   = accident.id,
            accident_lat  = payload.latitude,
            accident_lon  = payload.longitude,
            severity      = payload.severity,
            confidence    = payload.confidence,
            location_desc = payload.location or "",
        )

        return accident                                        # ← existing

Interview talking point — Anti-corruption layer:
  This file is an adapter.  The accident module doesn't know ambulances exist.
  The ambulance module doesn't know how accidents are detected.
  They communicate through this single, well-defined async function.
  Swap out either side without touching the other.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ambulance_service import (
    get_nearby_ambulances,
    dispatch_nearest_ambulance,
)
from app.websockets.ambulance_manager import ambulance_ws_manager

logger = logging.getLogger(__name__)

_AWARENESS_RADIUS_KM = 15.0


async def trigger_ambulance_dispatch(
    db:            AsyncSession,
    accident_id:   int,
    accident_lat:  float,
    accident_lon:  float,
    severity:      str,
    confidence:    float,
    location_desc: str = "",
) -> None:
    time_detected = datetime.now(timezone.utc).isoformat()

    logger.info(
        "[Dispatch] Accident #%d at (%.4f, %.4f) — severity=%s confidence=%.0f%%",
        accident_id, accident_lat, accident_lon, severity, confidence * 100,
    )

    try:
        result = await dispatch_nearest_ambulance(db, accident_lat, accident_lon)
    except Exception as exc:
        logger.error("[Dispatch] dispatch_nearest_ambulance raised: %s", exc)
        result = None

    dispatched_id: int | None = None

    if result:
        dispatched_id = result.ambulance.id
        dispatch_payload = {
            "type":          "DISPATCH_ALERT",
            "ambulance_id":  dispatched_id,
            "accident_id":   accident_id,
            "accident_lat":  accident_lat,
            "accident_lon":  accident_lon,
            "severity":      severity,
            "confidence":    round(confidence * 100, 1),
            "distance_km":   result.distance_km,
            "eta_minutes":   result.eta_minutes,
            "location":      location_desc,
            "time_detected": time_detected,
            "message":       result.message,
            "sound":         True,
        }
        try:
            delivered = await ambulance_ws_manager.send_to_ambulance(
                dispatched_id, dispatch_payload
            )
            if not delivered:
                logger.warning(
                    "[Dispatch] Ambulance %d is not connected to WebSocket — dispatch saved in DB but realtime alert not delivered.",
                    dispatched_id,
                )
        except Exception as exc:
            logger.error("[Dispatch] WebSocket send failed: %s", exc)
    else:
        logger.warning(
            "[Dispatch] No available ambulances near accident #%d.", accident_id
        )

    try:
        nearby = await get_nearby_ambulances(
            db, accident_lat, accident_lon, radius_km=_AWARENESS_RADIUS_KM
        )
        awareness_ids = [u.id for u in nearby if u.id != dispatched_id]

        if awareness_ids:
            awareness_payload = {
                "type":           "NEARBY_ACCIDENT_ALERT",
                "accident_id":    accident_id,
                "accident_lat":   accident_lat,
                "accident_lon":   accident_lon,
                "severity":       severity,
                "confidence":     round(confidence * 100, 1),
                "location":       location_desc,
                "time_detected":  time_detected,
                "dispatched_unit": (
                    result.ambulance.ambulance_number if result else None
                ),
                "message": (
                    f"Accident nearby — {result.ambulance.ambulance_number} dispatched."
                    if result else
                    "Accident nearby — no unit available yet."
                ),
                "sound": False,
            }
            await ambulance_ws_manager.broadcast_to_nearby(awareness_ids, awareness_payload)
            logger.info("[Dispatch] Awareness alert sent to %d nearby units.", len(awareness_ids))

    except Exception as exc:
        logger.error("[Dispatch] Awareness broadcast failed: %s", exc)
