"""
FILE: backend/app/services/traffic_service.py
====================================================
Traffic Service — Signal Control & Green Corridor Logic
====================================================

This service handles the business logic for controlling traffic signals.
It bridges the gap between the REST API and the physical IoT infrastructure.

GREEN CORRIDOR ALGORITHM:
  Input:  accident location + hospital destination
  Steps:
    1. Geocode both locations to GPS coordinates
    2. Query a routing API (Google Maps / OSRM) for the driving route
    3. Find all registered signals within X metres of the route polyline
    4. Switch those signals to EMERGENCY mode
    5. Schedule auto-reset after the ambulance has passed

PRODUCTION INTEGRATIONS (stub points in this file):
  - Google Maps Directions API  (route computation)
  - MQTT broker                 (IoT signal commands)
  - GIS/PostGIS                 (spatial query: signals near route)

INTERVIEW TALKING POINT:
  "The green corridor uses a spatial query to find signals within a radius
  of the computed route. In production I'd use PostGIS's ST_DWithin() for
  this, which can handle millions of points efficiently with a spatial index."
"""

import asyncio

from sqlalchemy.orm import Session

from app.models.accident_model import Accident
from app.models.traffic_model import SignalMode, TrafficSignal


class TrafficService:
    """
    Stateless service class for traffic signal operations.
    Static methods are used because there's no instance state.
    """

    @staticmethod
    async def send_signal_command(signal_id: str, command: str) -> bool:
        """
        Send a control command to a physical traffic signal IoT controller.

        CURRENT: Simulated (prints to console)
        PRODUCTION: Publish to an MQTT topic

        MQTT example:
          import paho.mqtt.client as mqtt
          client = mqtt.Client()
          client.connect("mqtt-broker-host", 1883)
          client.publish(f"signals/{signal_id}/cmd", command)

        HTTP REST example (if the controller has a web server):
          async with httpx.AsyncClient() as client:
            await client.post(f"http://signal-ctrl.local/{signal_id}", json={"cmd": command})

        Returns True if command was sent successfully, False otherwise.
        """
        print(f"   📡 IoT → Signal {signal_id}: {command}")
        # Simulate network latency to the physical device
        await asyncio.sleep(0.05)
        return True

    @staticmethod
    async def create_green_corridor(
        accident_id: int,
        hospital_id: str,
        db: Session,
    ) -> dict:
        """
        Activate a full green corridor from the accident location to the hospital.

        Algorithm (production-ready design, mock implementation):
          Step 1: Load accident from DB to get GPS coordinates
          Step 2: Resolve hospital_id to GPS coordinates (hospital registry lookup)
          Step 3: Call Google Maps Directions API to get the route polyline
          Step 4: Use PostGIS ST_DWithin() to find signals within 50m of the route
          Step 5: Set each found signal to EMERGENCY mode
          Step 6: Send IoT command to each signal controller
          Step 7: Schedule auto-reset after CORRIDOR_DURATION_SECONDS

        CURRENT: All signals are activated (no route filtering).
        Replace Step 4 with a real spatial query once PostGIS is available.
        """
        CORRIDOR_DURATION_SECONDS = 300  # Auto-reset after 5 minutes

        # ── Step 1: Load accident ─────────────────────────────────────────────
        accident = db.query(Accident).filter(Accident.id == accident_id).first()
        if not accident:
            return {"error": f"Accident id={accident_id} not found"}

        print(
            f"🚑 Creating green corridor: Accident #{accident_id} "
            f"at '{accident.location}' → Hospital {hospital_id}"
        )

        # ── Step 2: Hospital lookup (mock) ────────────────────────────────────
        # In production: query a hospitals table or external API
        print(f"   📍 Routing to hospital: {hospital_id}")

        # ── Step 3: Route computation (mock) ──────────────────────────────────
        # In production:
        # route = await TrafficService._compute_route(
        #     origin=(accident.latitude, accident.longitude),
        #     destination=hospital_gps,
        # )
        print("   🗺  Route computed (mock — all signals activated)")

        # ── Step 4+5: Activate signals along route ────────────────────────────
        # Mock: activate ALL registered online signals
        # Production: filter to only signals within 50m of the route polyline
        signals = db.query(TrafficSignal).filter(
            TrafficSignal.is_online == True  # noqa: E712 — SQLAlchemy requires == not `is`
        ).all()

        activated_signals = []
        failed_signals    = []

        for signal in signals:
            # Update DB state
            signal.current_mode = SignalMode.emergency

            # Send IoT command
            success = await TrafficService.send_signal_command(
                signal.signal_id, "EMERGENCY_GREEN"
            )

            if success:
                activated_signals.append(signal.signal_id)
            else:
                failed_signals.append(signal.signal_id)

        db.commit()
        print(f"   ✅ {len(activated_signals)} signals activated | {len(failed_signals)} failed")

        # ── Step 7: Schedule auto-reset ───────────────────────────────────────
        # Fire-and-forget background task.
        # In production, use Celery or a background task queue for reliability.
        asyncio.create_task(
            TrafficService._auto_reset_corridor(
                [s.signal_id for s in signals],
                CORRIDOR_DURATION_SECONDS,
                db,
            )
        )

        return {
            "message":           "Green corridor activated",
            "accident_id":       accident_id,
            "hospital_id":       hospital_id,
            "activated_signals": activated_signals,
            "failed_signals":    failed_signals,
            "auto_reset_in_s":   CORRIDOR_DURATION_SECONDS,
        }

    @staticmethod
    async def _auto_reset_corridor(
        signal_ids: list,
        delay_seconds: int,
        db: Session,
    ) -> None:
        """
        Wait for the ambulance to pass, then reset all corridor signals to AUTO.

        This runs as a background asyncio task (fire-and-forget).
        In production: use a proper task queue (Celery + Redis) so the reset
        survives server restarts.
        """
        print(f"   ⏱  Corridor will auto-reset in {delay_seconds}s")
        await asyncio.sleep(delay_seconds)

        print("   🔄 Auto-resetting corridor signals...")
        for signal_id in signal_ids:
            signal = db.query(TrafficSignal).filter(
                TrafficSignal.signal_id == signal_id
            ).first()
            if signal and signal.current_mode == SignalMode.emergency:
                signal.current_mode = SignalMode.auto
                await TrafficService.send_signal_command(signal_id, "RESUME_AUTO")

        db.commit()
        print(f"   ✅ {len(signal_ids)} signals reset to AUTO")
