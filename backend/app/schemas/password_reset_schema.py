"""
FILE: backend/app/schemas/password_reset_schema.py
=====================================================
Pydantic Schemas — Password Reset Request & Response
=====================================================
"""

from pydantic import BaseModel, EmailStr, Field , field_validator


# ─── Request Schemas ──────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """
    Step 1 — POST /api/password/forgot

    The user submits just their email address.
    EmailStr auto-validates format (e.g. rejects "notanemail").
    """
    email: EmailStr
    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class VerifyOTPRequest(BaseModel):
    """
    Step 2 — POST /api/password/verify-otp

    The user submits all three fields together:
      - email        : identifies their account
      - otp          : the 6-digit code from the email
      - new_password : what they want to change their password to

    Validation rules:
      otp          → exactly 6 digits, no letters or symbols
      new_password → minimum 8 characters (matches UserCreate in user_schema.py)
    """
    email: EmailStr
    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric OTP sent to the user's registered email",
    )

    new_password: str = Field(
        ...,
        min_length=8,
        description="New password — minimum 8 characters",
    )


# ─── Response Schema ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """
    Simple message wrapper used by both endpoints.

    Example:
        { "message": "OTP sent to user@example.com. Valid for 5 minutes." }
        { "message": "Password reset successfully. You can now log in." }
    """
    message: str
