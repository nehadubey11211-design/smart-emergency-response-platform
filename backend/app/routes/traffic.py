"""
FILE: backend/app/routes/traffic.py
==========================================
Traffic Signal Management Endpoints
==========================================
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.routes.auth import get_current_user_from_header
from app.models.traffic_model import TrafficSignal, SignalMode, TrafficSignalEvent
from app.services.traffic_services import TrafficService

router = APIRouter()


@router.get(
    "/signals",
    summary="List all traffic signals and their current status",
)
async def get_all_signals(db: AsyncSession = Depends(get_db)) -> List[dict]:
    result = await db.execute(select(TrafficSignal).order_by(TrafficSignal.signal_id))
    signals = result.scalars().all()
    return [
        {
            "signal_id": s.signal_id,
            "location": s.location,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "current_mode": s.current_mode,
            "is_online": s.is_online,
            "last_update": str(s.last_update),
        }
        for s in signals
    ]


@router.get(
    "/signals/{signal_id}",
    summary="Get a specific signal's status",
)
async def get_signal(signal_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrafficSignal).where(TrafficSignal.signal_id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found",
        )
    return signal


@router.post(
    "/signals/{signal_id}/emergency",
    summary="Activate emergency (green corridor) mode on a signal",
)
async def activate_emergency(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    result = await db.execute(select(TrafficSignal).where(TrafficSignal.signal_id == signal_id))
    signal = result.scalar_one_or_none()

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

    old_mode = signal.current_mode
    signal.current_mode = SignalMode.emergency
    # Log the state transition in the audit table
    event = TrafficSignalEvent(
        signal_id=signal.signal_id,
        from_mode=old_mode,
        to_mode=SignalMode.emergency,
        triggered_by=f"operator:{current_user.id}",
    )
    db.add(event)

    await db.commit()

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
async def reset_signal(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    result = await db.execute(select(TrafficSignal).where(TrafficSignal.signal_id == signal_id))
    signal = result.scalar_one_or_none()

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal '{signal_id}' not found",
        )

    old_mode = signal.current_mode
    signal.current_mode = SignalMode.auto
    # Log reset event
    event = TrafficSignalEvent(
        signal_id=signal.signal_id,
        from_mode=old_mode,
        to_mode=SignalMode.auto,
        triggered_by=f"operator:{current_user.id}",
    )
    db.add(event)

    await db.commit()

    await TrafficService.send_signal_command(signal_id, "RESUME_AUTO")

    return {
        "message": f"Signal {signal_id} reset to AUTO mode",
        "signal_id": signal_id,
        "new_mode": "auto",
    }


@router.post(
    "/green-corridor",
    summary="Activate a green corridor from an accident to a hospital",
)
async def create_green_corridor(
    accident_id: int,
    hospital_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    result = await TrafficService.create_green_corridor(accident_id, hospital_id, db)
    return result


@router.post(
    "/reset-corridor",
    summary="Reset all signals from emergency back to auto",
)
async def reset_corridor(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_from_header),
):
    result = await db.execute(
        select(TrafficSignal).where(TrafficSignal.current_mode == SignalMode.emergency)
    )
    emergency_signals = result.scalars().all()

    reset_count = 0
    for signal in emergency_signals:
        signal.current_mode = SignalMode.auto
        await TrafficService.send_signal_command(signal.signal_id, "RESUME_AUTO")
        reset_count += 1

    await db.commit()

    return {
        "message": f"Reset {reset_count} signals to AUTO mode",
        "reset_count": reset_count,
    }
