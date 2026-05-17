"""
FILE : backend/app/models/ambulance.py
-------------------
SQLAlchemy ORM model for the ambulances table.

Interview talking point:
  - Uses Python Enum so status is type-safe at both application + DB level
  - ENUM in PostgreSQL enforces validity even if someone writes SQL directly
  - last_updated uses server_default + onupdate so DB always tracks freshness
    without the application needing to set it manually
"""

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func

# Import the shared Base from your existing database module
from app.database.db import Base


class AmbulanceStatus(str, enum.Enum):
    """
    Three-state lifecycle:
        available  →  busy  (on dispatch)
        busy       →  available  (job complete)
        any state  →  offline  (manual override / shift end)

    Inherits str so Pydantic serialises it as a plain string in JSON responses.
    """
    available = "available"
    busy      = "busy"
    offline   = "offline"


class Ambulance(Base):
    """
    Represents a single ambulance unit in the fleet.

    GPS columns are nullable — a newly registered unit may not have
    sent its first location ping yet.  The dispatch logic skips units
    where latitude/longitude IS NULL.
    """
    __tablename__ = "ambulances"

    id               = Column(Integer, primary_key=True, index=True)
    ambulance_number = Column(String(20),  unique=True, nullable=False, index=True)
    driver_name      = Column(String(100), nullable=False)

    # Operational status — indexed because dispatch queries filter on this
    status = Column(
        SAEnum(AmbulanceStatus, name="ambulance_status"),
        nullable=False,
        default=AmbulanceStatus.available,
        index=True,
    )

    # GPS coordinates — updated by the ambulance device every ~15 seconds
    latitude  = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Auto-managed timestamp — never touch this in application code
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Ambulance #{self.id} {self.ambulance_number} [{self.status}]>"