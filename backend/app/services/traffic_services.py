"""
FILE: backend/app/services/traffic_service.py
====================================================
Traffic Service — Signal Control & Green Corridor Logic
====================================================
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import SessionLocal
from app.models.accident_model import Accident
from app.models.traffic_model import SignalMode, TrafficSignal


class TrafficService:

    @staticmethod
    async def send_signal_command(signal_id: str, command: str) -> bool:
        print(f"   📡 IoT → Signal {signal_id}: {command}")
        await asyncio.sleep(0.05)
        return True

    @staticmethod
    async def create_green_corridor(
        accident_id: int,
        hospital_id: str,
        db: AsyncSession,
    ) -> dict:
        CORRIDOR_DURATION_SECONDS = 300

        accident_result = await db.execute(select(Accident).where(Accident.id == accident_id))
        accident = accident_result.scalar_one_or_none()
        if not accident:
            return {"error": f"Accident id={accident_id} not found"}

        print(
            f"🚑 Creating green corridor: Accident #{accident_id} "
            f"at '{accident.location}' → Hospital {hospital_id}"
        )
        print(f"   📍 Routing to hospital: {hospital_id}")
        print("   🗺  Route computed (mock — all signals activated)")

        result = await db.execute(
            select(TrafficSignal).where(TrafficSignal.is_online == True)
        )
        signals = result.scalars().all()

        activated_signals = []
        failed_signals = []

        for signal in signals:
            signal.current_mode = SignalMode.emergency
            success = await TrafficService.send_signal_command(
                signal.signal_id, "EMERGENCY_GREEN"
            )
            if success:
                activated_signals.append(signal.signal_id)
            else:
                failed_signals.append(signal.signal_id)

        await db.commit()
        print(f"   ✅ {len(activated_signals)} signals activated | {len(failed_signals)} failed")

        asyncio.create_task(
            TrafficService._auto_reset_corridor(
                [s.signal_id for s in signals],
                CORRIDOR_DURATION_SECONDS,
            )
        )

        return {
            "message": "Green corridor activated",
            "accident_id": accident_id,
            "hospital_id": hospital_id,
            "activated_signals": activated_signals,
            "failed_signals": failed_signals,
            "auto_reset_in_s": CORRIDOR_DURATION_SECONDS,
        }

    @staticmethod
    async def _auto_reset_corridor(
        signal_ids: list,
        delay_seconds: int,
    ) -> None:
        print(f"   ⏱  Corridor will auto-reset in {delay_seconds}s")
        await asyncio.sleep(delay_seconds)

        print("   🔄 Auto-resetting corridor signals...")
        async with SessionLocal() as db:
            for signal_id in signal_ids:
                result = await db.execute(
                    select(TrafficSignal).where(TrafficSignal.signal_id == signal_id)
                )
                signal = result.scalar_one_or_none()
                if signal and signal.current_mode == SignalMode.emergency:
                    signal.current_mode = SignalMode.auto
                    await TrafficService.send_signal_command(signal_id, "RESUME_AUTO")
            await db.commit()
        print(f"   ✅ {len(signal_ids)} signals reset to AUTO")
