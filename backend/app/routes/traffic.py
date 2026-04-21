"""
FILE: backend/app/routes/traffic.py
==========================================
Traffic Signal Management Endpoints
==========================================

This module controls traffic signals in the field.
The core feature is the "green corridor" — automatically setting all signals
along an ambulance route to green so the vehicle passes without stopping.

STATE MACHINE:
  Each signal transitions between modes:

    auto  ──────────────────► emergency
      ▲                           │
      └───────────────────────────┘
              (manual reset or auto-timeout)

  auto      : Default timed cycle (red/amber/green rotation)
  emergency : All signal heads on the ambulance route are green
  manual    : Operator has overridden via dashboard

PRODUCTION EXTENSION:
  In a real deployment, after changing the DB state here, you'd also
  publish an MQTT message to the signal's IoT controller, e.g.:
    mqtt.publish("signals/SIG-001/command", "EMERGENCY_GREEN")

INTERVIEW TALKING POINT:
  "The green corridor feature demonstrates event-driven design. The accident
  detection triggers a chain: detect → alert operator → dispatch → green corridor.
  Each step is loosely coupled through the REST API."
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.traffic_model import TrafficSignal, SignalMode
from app.services.traffic_services import TrafficService

router = APIRouter()


# ─── Signal Status Endpoints ──────────────────────────────────────────────────

@router.get(
    "/signals",
    summary="List all traffic signals and their current status",
)
def get_all_signals(db: Session = Depends(get_db)) -> List[dict]:
    """
    Returns the full list of registered traffic signals with their current mode.
    Used by the TrafficPanel component on the dashboard.
    """
    signals = db.query(TrafficSignal).order_by(TrafficSignal.signal_id).all()
    return [
        {
            "signal_id":    s.signal_id,
            "location":     s.location,
            "latitude":     s.latitude,
            "longitude":    s.longitude,
            "current_mode": s.current_mode,
            "is_online":    s.is_online,
            "last_update":  str(s.last_update),
        }
        for s in signals
    ]


@router.get(
    "/signals/{signal_id}",
    summary="Get a specific signal's status",
)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    """Retrieve a single signal's current state by its identifier."""
    signal = db.query(TrafficSignal).filter(
        TrafficSignal.signal_id == signal_id
    ).first()

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found",
        )
    return signal


# ─── Signal Control Endpoints ─────────────────────────────────────────────────

@router.post(
    "/signals/{signal_id}/emergency",
    summary="Activate emergency (green corridor) mode on a signal",
)
async def activate_emergency(signal_id: str, db: Session = Depends(get_db)):
    """
    Switch a specific signal to EMERGENCY mode.

    This endpoint is called:
      1. Automatically by create_green_corridor() for all signals along a route
      2. Manually by an operator clicking the ⚡ button on the dashboard

    After updating the DB, it sends an IoT command to the physical controller.
    """
    signal = db.query(TrafficSignal).filter(
        TrafficSignal.signal_id == signal_id
    ).first()

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found",
        )

    if not signal.is_online:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Signal '{signal_id}' is offline",
        )

    # Update DB state
    signal.current_mode = SignalMode.emergency
    db.commit()

    # Send command to physical IoT controller
    # In production: MQTT publish or HTTP call to the signal hardware
    await TrafficService.send_signal_command(signal_id, "EMERGENCY_GREEN")

    return {
        "message": f"Signal {signal_id} activated to EMERGENCY mode",
        "signal_id": signal_id,
        "new_mode": "emergency",
    }


@router.post(
    "/signals/{signal_id}/reset",
    summary="Reset a signal back to automatic timed mode",
)
async def reset_signal(signal_id: str, db: Session = Depends(get_db)):
    """
    Return a signal to its normal AUTO mode.
    Called when the ambulance has passed or an incident is resolved.
    """
    signal = db.query(TrafficSignal).filter(
        TrafficSignal.signal_id == signal_id
    ).first()

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found",
        )

    signal.current_mode = SignalMode.auto
    db.commit()

    await TrafficService.send_signal_command(signal_id, "RESUME_AUTO")

    return {
        "message": f"Signal {signal_id} reset to AUTO mode",
        "signal_id": signal_id,
        "new_mode": "auto",
    }


# ─── Green Corridor ───────────────────────────────────────────────────────────

@router.post(
    "/green-corridor",
    summary="Activate a green corridor from an accident to a hospital",
)
async def create_green_corridor(
    accident_id: int,
    hospital_id: str,
    db: Session = Depends(get_db),
):
    """
    Core emergency feature:
      1. Compute the optimal route from accident location → hospital
      2. Find all traffic signals along that route
      3. Switch them all to EMERGENCY mode
      4. Schedule auto-reset after the ambulance has passed

    Route computation currently uses a mock (all signals).
    Production integration: Google Maps Directions API or OpenStreetMap + OSRM.

    The hospital_id allows routing to the nearest available hospital,
    or a specific hospital chosen by the dispatch operator.
    """
    result = await TrafficService.create_green_corridor(accident_id, hospital_id, db)
    return result


@router.post(
    "/reset-corridor",
    summary="Reset all signals from emergency back to auto",
)
async def reset_corridor(db: Session = Depends(get_db)):
    """
    Reset ALL signals currently in EMERGENCY mode back to AUTO.
    Used as a bulk reset after an incident is resolved.
    """
    emergency_signals = db.query(TrafficSignal).filter(
        TrafficSignal.current_mode == SignalMode.emergency
    ).all()

    reset_count = 0
    for signal in emergency_signals:
        signal.current_mode = SignalMode.auto
        await TrafficService.send_signal_command(signal.signal_id, "RESUME_AUTO")
        reset_count += 1

    db.commit()

    return {
        "message": f"Reset {reset_count} signals to AUTO mode",
        "reset_count": reset_count,
    }
