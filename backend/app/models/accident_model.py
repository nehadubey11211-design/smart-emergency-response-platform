"""
FILE: backend/app/models/accident_model.py
=================================================
SQLAlchemy ORM Model — Accidents Table
=================================================

This model captures every accident event detected by the AI module.
It stores the full lifecycle from detection → response → resolution.

ENUM TYPES:
  Python's enum.Enum + SQLAlchemy's Enum column type creates a PostgreSQL
  ENUM type in the database.  This enforces valid values at the DB level —
  even if someone bypasses the API and inserts directly into the DB.

  SeverityLevel : How serious the incident is (drives alert priority)
  AccidentStatus: Current state in the response workflow
"""

import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Index
from sqlalchemy.sql import func

from app.database.db import Base


# ─── Enum Definitions ─────────────────────────────────────────────────────────
# Inheriting from both str and enum.Enum makes these JSON-serialisable,
# so FastAPI can include them directly in API responses.

class SeverityLevel(str, enum.Enum):
    """
    Describes how serious an accident is.
    Used to prioritise dispatcher attention and determine notification urgency.
    """
    low      = "low"       # Minor incident, no serious injuries apparent
    medium   = "medium"    # Moderate — possible injuries, 1 lane blocked
    high     = "high"      # Serious — multiple vehicles, lane closure
    critical = "critical"  # Life-threatening — multiple casualties, road blocked


class AccidentStatus(str, enum.Enum):
    """
    Tracks where the incident is in the response lifecycle.
    Drives the dashboard UI colour coding and filter options.
    """
    detected   = "detected"    # AI just detected it — no human action yet
    responding = "responding"  # Operator acknowledged, units dispatched
    resolved   = "resolved"    # Incident cleared, road normal


# ─── Accident Model ───────────────────────────────────────────────────────────

class Accident(Base):
    """
    Represents a single detected accident event.

    Lifecycle:
      AI module detects accident
        → creates row (status=detected)
        → operator dispatches units (status=responding)
        → units clear the scene (status=resolved, resolved_at is set)

    GPS coordinates (latitude, longitude) enable map visualisation and
    route computation for green corridor activation.
    """

    __tablename__ = "accidents"

    # ── Identity ────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True)

    # ── Location ────────────────────────────────────────────────────────────
    # Human-readable address (e.g. "MG Road Junction, Pune")
    location = Column(String(255), nullable=False)

    # GPS coordinates — nullable because GPS may not always be available.
    # In production these come from GIS data linked to the camera ID.
    latitude  = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Which ambulance was dispatched to this accident (nullable until assigned)
    dispatched_ambulance_id = Column(
        Integer,
        ForeignKey("ambulances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Classification ──────────────────────────────────────────────────────
    # severity is set either by the AI (based on confidence) or by an operator
    severity = Column(
        Enum(SeverityLevel, name="severity_level"),
        default=SeverityLevel.medium,
        nullable=False,
    )

    # Status moves through the lifecycle: detected → responding → resolved
    status = Column(
        Enum(AccidentStatus, name="accident_status"),
        default=AccidentStatus.detected,
        nullable=False,
        index=True,   # Indexed because we frequently filter by status
    )

    # ── AI Metadata ─────────────────────────────────────────────────────────
    # The raw probability output from the CNN (0.0 to 1.0)
    # Useful for post-hoc analysis of model performance
    confidence = Column(Float, nullable=True)

    # Which camera detected this incident (e.g. "CAM-001")
    camera_id = Column(String(100), nullable=True, index=True)

    # Path to the saved frame snapshot (evidence / review)
    image_path = Column(String(500), nullable=True)

    # Operator or auto-generated description
    description = Column(String(1000), nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────────
    # index=True because we frequently ORDER BY or filter by detected_at
    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Nullable — only set when status transitions to "resolved"
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_accident_status_detected", "status", detected_at.desc()),
        Index("ix_accident_camera_detected", "camera_id", "detected_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Accident id={self.id} location={self.location!r} "
            f"severity={self.severity} status={self.status}>"
        )

    @property
    def response_time_minutes(self) -> float | None:
        """
        Calculate how long it took to resolve this incident.
        Returns None if the incident is still active.

        This is a computed property — not stored in the DB, calculated on-demand.
        """
        if not (self.resolved_at and self.detected_at):
            return None

        # Normalize both to aware UTC before subtraction
        def to_utc(dt):
            from datetime import timezone

            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        delta = to_utc(self.resolved_at) - to_utc(self.detected_at)
        return round(delta.total_seconds() / 60, 1)
    