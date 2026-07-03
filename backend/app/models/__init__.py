"""
FILE : backend/app/models/__init__.py
======================================
Re-exports every ORM model/enum so callers can do `from app.models import X`
instead of reaching into each submodule individually.

This also matters for testing: Base.metadata.create_all(...) only creates
tables for models that have actually been imported somewhere. Importing
everything here guarantees all tables exist once `app.models` is imported.
"""

from app.models.user_model import User
from app.models.accident_model import Accident, SeverityLevel, accident_status
from app.models.ambulance import Ambulance, AmbulanceStatus
from app.models.hospital_model import Hospital
from app.models.traffic_model import TrafficSignal, TrafficSignalEvent, SignalMode

__all__ = [
    "User",
    "Accident",
    "SeverityLevel",
    "accident_status",
    "Ambulance",
    "AmbulanceStatus",
    "Hospital",
    "TrafficSignal",
    "TrafficSignalEvent",
    "SignalMode",
]
