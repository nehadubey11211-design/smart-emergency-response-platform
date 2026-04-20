"""
FILE: backend/app/schemas/user_schema.py
==============================================
Pydantic Schemas — User Request & Response Validation
==============================================

WHY PYDANTIC SCHEMAS?

  SQLAlchemy models define the DATABASE structure.
  Pydantic schemas define the API CONTRACT — what the API accepts and returns.

  Keeping them separate is a best practice because:
    1. SECURITY: We never accidentally return the hashed password in an API response
    2. FLEXIBILITY: DB columns can change without breaking the API contract
    3. VALIDATION: Pydantic validates types, required fields, and email format
       automatically — no manual if/else checks needed
    4. DOCUMENTATION: FastAPI generates Swagger UI from these schemas

  The flow:
    Client sends JSON → Pydantic validates it → Route handler gets clean object
    Route handler queries DB → SQLAlchemy model → Pydantic serialises response

INTERVIEW TALKING POINT:
  "Pydantic runs validation at parse time, not at DB write time. So invalid
  requests are rejected before they even hit the database — cleaner and faster."
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


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
    password: str      = Field(..., min_length=8,
                               description="Plaintext password (hashed before storage)")
    role:     str      = Field(default="operator",
                               description="User role: 'admin' or 'operator'")


class UserLogin(BaseModel):
    """Schema for POST /api/auth/login."""
    email:    EmailStr
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
