"""
FILE: backend/app/models/hospital_model.py
==================================================
Hospital Database Model
==================================================
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.db import Base


class Hospital(Base):

    # Database table name
    __tablename__ = "hospitals"

    # ── Primary Key ─────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True)

    # ── Hospital Information ────────────────────────────────
    name = Column(String(200), nullable=False)

    # Geographic coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Whether hospital is available for emergency routing
    is_active = Column(Boolean, default=True, nullable=False)

    # Record creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # ── Database Indexes ────────────────────────────────────
    # Improves performance for location-based queries
    __table_args__ = (
        Index("ix_hospital_location", "latitude", "longitude"),
    )

    # ── Debug Representation ────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"<Hospital "
            f"id={self.id} "
            f"name={self.name!r} "
            f"lat={self.latitude} "
            f"lon={self.longitude}>"
        )
