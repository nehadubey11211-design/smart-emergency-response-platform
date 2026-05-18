"""
FILE : backend/app/schemas/ambulance.py
---------------------
Pydantic v2 schemas for the ambulance dispatch feature.

Interview talking point:
  - Schemas are deliberately separate from ORM models (never expose ORM objects
    directly to the API layer — Pydantic catches malformed input before it hits
    the DB, and prevents accidental field leakage in responses)
  - NearbyAmbulanceResponse *extends* AmbulanceResponse by adding computed
    fields (distance_km, eta_minutes) that are not stored in the DB
  - DispatchResult is a composite response: it wraps the ambulance record
    plus the dispatch metadata in one clean payload
"""

from __future__ import annotations
from datetime   import datetime
from typing     import Optional
from pydantic   import BaseModel, Field

from app.models.ambulance import AmbulanceStatus


# ─────────────────────────────────────────────
#  Request schemas  (what the API *receives*)
# ─────────────────────────────────────────────

class AmbulanceCreate(BaseModel):
    """POST /ambulances/register"""
    ambulance_number: str  = Field(..., max_length=20,  example="AMB-001")
    driver_name:      str  = Field(..., max_length=100, example="Rahul Sharma")
    latitude:  Optional[float] = Field(None, example=18.5204)
    longitude: Optional[float] = Field(None, example=73.8567)


class AmbulanceLocationUpdate(BaseModel):
    """PUT /ambulances/{id}/location  — called every ~15 s by device"""
    latitude:  float = Field(..., example=18.5204)
    longitude: float = Field(..., example=73.8567)


class AmbulanceStatusUpdate(BaseModel):
    """PUT /ambulances/{id}/status"""
    status: AmbulanceStatus


# ─────────────────────────────────────────────
#  Response schemas  (what the API *returns*)
# ─────────────────────────────────────────────

class AmbulanceResponse(BaseModel):
    """Standard ambulance record returned by most endpoints."""
    id:               int
    ambulance_number: str
    driver_name:      str
    status:           AmbulanceStatus
    latitude:         Optional[float]
    longitude:        Optional[float]
    last_updated:     Optional[datetime]

    model_config = {"from_attributes": True}   # replaces orm_mode in Pydantic v2


class NearbyAmbulanceResponse(AmbulanceResponse):
    """
    Extends AmbulanceResponse with two computed fields added by the
    service layer after running the Haversine formula.
    These fields exist only in the response — they are not DB columns.
    """
    distance_km:  float = Field(..., description="Great-circle distance in km")
    eta_minutes:  float = Field(..., description="Estimated travel time in minutes")


class DispatchResult(BaseModel):
    """
    Returned by POST /ambulances/dispatch and by the auto-dispatch
    integration hook.  Bundles the assigned unit + routing metadata.
    """
    ambulance:    AmbulanceResponse
    distance_km:  float
    eta_minutes:  float
    message:      str


class DispatchAlertPayload(BaseModel):
    """
    Shape of the JSON pushed over WebSocket to the ambulance dashboard.
    Matches what AmbulanceDashboard.jsx listens for.
    """
    type:             str = "DISPATCH_ALERT"
    accident_id:      int
    accident_lat:     float
    accident_lon:     float
    severity:         str
    confidence:       float          # 0–100 percentage
    distance_km:      float
    eta_minutes:      float
    location:         str = ""
    time_detected:    str            # ISO timestamp string
    message:          str
    sound:            bool = True    # tells the frontend to play alert beep
