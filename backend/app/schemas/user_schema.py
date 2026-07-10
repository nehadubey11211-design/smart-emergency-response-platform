"""
FILE: backend/app/schemas/user_schema.py
==============================================
Pydantic Schemas — User Request & Response Validation
==============================================

WHY PYDANTIC SCHEMAS?
  SQLAlchemy models define the DATABASE structure.
  Pydantic schemas define the API CONTRACT — what the API accepts and returns.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field , field_validator


# ─── Request Schemas (Incoming Data) ─────────────────────────────────────────
# These validate what the client sends to the API.

class UserCreate(BaseModel):
    """
    Schema for POST /api/auth/register.
    EmailStr validates that the email is properly formatted (uses email-validator).
    Field(...) means required — no default, must be provided.
    """
    name:     str      = Field(..., min_length=2, max_length=100,
                               description="Full display name")
    email:    EmailStr = Field(..., description="Unique login email")
    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v
    password: str                     = Field(
        ..., min_length=8,
        description="Plaintext password (hashed before storage)",
    )
    role:     Literal["operator"] = "operator"


class UserLogin(BaseModel):
    """Schema for POST /api/auth/login."""
    email:    EmailStr
    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v
    password: str


class UserUpdate(BaseModel):
    """Schema for PATCH /api/auth/users/{id} — all fields optional."""
    name:      Optional[str]  = None
    role:      Optional[str]  = None
    is_active: Optional[bool] = None


# ─── Response Schemas (Outgoing Data) ────────────────────────────────────────
# These control what we send BACK to the client.
# The password field is intentionally ABSENT here — it is never returned.

class UserResponse(BaseModel):
    """
    Safe representation of a User — returned in API responses.
    The password hash is never included.

    model_config with from_attributes=True (Pydantic v2) or
    class Config: orm_mode = True (Pydantic v1) lets Pydantic read
    attributes from a SQLAlchemy model object directly.
    """
    id:         int
    name:       str
    email:      str
    role:       str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Returned after successful login or registration.
    The frontend stores the access_token in localStorage and sends it
    in the Authorization header of subsequent requests.
    """
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse   # Embed user data so the frontend doesn't need a 2nd request
