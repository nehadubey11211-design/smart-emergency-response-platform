"""
FILE: backend/app/schemas/accident_schema.py
===================================================
Pydantic Schemas — Accident Request & Response Validation
===================================================

Three schema categories for accidents:
  1. AccidentCreate  — what the AI module POSTs when it detects something
  2. AccidentUpdate  — what an operator PATCHes (status/severity changes)
  3. AccidentResponse — what the API returns to the dashboard

Using separate Create/Update/Response schemas is a standard REST API pattern:
  - POST bodies often have fewer fields than stored records
  - PATCH bodies should have ALL fields optional (partial update)
  - Response adds server-generated fields (id, timestamps) the client never sends
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.accident_model import SeverityLevel, AccidentStatus


# ─── Create Schema ────────────────────────────────────────────────────────────

class AccidentCreate(BaseModel):
    """
    Sent by the AI module (detect_accident.py) when it detects an incident.
    Only fields the AI knows about are required here.
    """
    # Required: where it happened
    location: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Human-readable location e.g. 'MG Road Junction'",
    )

    # Optional GPS coordinates (linked to camera position in production)
    latitude:  Optional[float] = Field(None, ge=-90,  le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Severity defaults to medium; the AI or operator can override
    severity: Optional[SeverityLevel] = SeverityLevel.medium

    # Raw CNN confidence score (0.0 to 1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Which camera triggered this
    camera_id: Optional[str] = Field(None, max_length=100)

    # Auto-generated description from AI or entered by operator
    description: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_gps_pair(self):
      if (self.latitude is None) != (self.longitude is None):
        raise ValueError("latitude and longitude must both be provided or both omitted")
      return self


# ─── Update Schema ────────────────────────────────────────────────────────────

class AccidentUpdate(BaseModel):
    """
    Used for PATCH /api/accidents/{id}.
    All fields are Optional — the client sends only what changed.
    This is the standard 'partial update' pattern.
    """
    status:      Optional[AccidentStatus] = None
    severity:    Optional[SeverityLevel]  = None
    description: Optional[str]            = Field(None, max_length=1000)


# ─── Response Schema ──────────────────────────────────────────────────────────

class AccidentResponse(BaseModel):
    """
    Full accident object returned by the API.
    Includes server-generated fields (id, timestamps) that the client never sends.
    """
    id:           int
    location:     str
    latitude:     Optional[float]
    longitude:    Optional[float]
    severity:     SeverityLevel
    status:       AccidentStatus
    confidence:   Optional[float]
    camera_id:    Optional[str]
    description:  Optional[str]
    detected_at:  datetime
    resolved_at:  Optional[datetime]

    # response_time_minutes is computed from the @property on the model
    # It appears in the API response even though it's not a DB column.
    response_time_minutes: Optional[float] = None

    model_config = {"from_attributes": True}
