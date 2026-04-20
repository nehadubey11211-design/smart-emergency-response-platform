"""
FILE: backend/app/models/traffic_model.py
================================================
SQLAlchemy ORM Model — Traffic Signals Table
================================================

Each row represents one physical traffic signal controller in the field.
The system communicates with these over IoT protocols (MQTT / HTTP) to
switch them between normal and emergency modes.

SIGNAL MODES:
  auto      — Normal timed cycle (default operation)
  emergency — Green corridor active (ambulance passing through)
  manual    — Operator has taken direct control via dashboard
"""

import enum

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.sql import func

from app.database.db import Base


class SignalMode(str, enum.Enum):
    """
    The three operating modes for a traffic signal.

    Inherits from str so FastAPI can serialise it directly in JSON responses
    without calling .value explicitly.
    """
    auto      = "auto"       # Standard timed cycle — default
    emergency = "emergency"  # All-green for the ambulance corridor
    manual    = "manual"     # Human operator override via dashboard


class TrafficSignal(Base):
    """
    Represents one physical traffic signal controller.

    In a real deployment each signal has an IoT controller (e.g. Raspberry Pi
    or PLC) that listens for commands over MQTT or HTTP.
    This table is the source of truth for each signal's state.

    The `signal_id` field (e.g. "SIG-001") is used as the address when
    sending commands to the physical hardware.
    """

    __tablename__ = "traffic_signals"

    # ── Identity ────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True)

    # Human-readable identifier used to address the IoT controller.
    # unique=True prevents accidentally registering the same signal twice.
    signal_id = Column(String(50), unique=True, nullable=False, index=True)

    # ── Location ────────────────────────────────────────────────────────────
    location = Column(String(255), nullable=False)

    # GPS coordinates — used to find signals along an ambulance route
    latitude  = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # ── State ───────────────────────────────────────────────────────────────
    # Current operating mode — the authoritative state in the system
    current_mode = Column(
        Enum(SignalMode),
        default=SignalMode.auto,
        nullable=False,
    )

    # Whether the signal controller is reachable over the network.
    # Set to False if IoT heartbeat pings time out.
    is_online = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ──────────────────────────────────────────────────────────
    # Tracks when the signal state was last changed.
    # onupdate ensures this auto-updates on every SQLAlchemy UPDATE call.
    last_update = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<TrafficSignal id={self.signal_id!r} "
            f"mode={self.current_mode} online={self.is_online}>"
        )
    