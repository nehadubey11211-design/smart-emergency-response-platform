"""
FILE: backend/app/routes/password_reset.py
============================================
Password Reset Endpoints
============================================

FOLLOWS THE SAME ROUTE PATTERN AS auth.py:
  - APIRouter with prefix and tags
  - Depends(get_db) for the SQLAlchemy session
  - Thin handlers: validate input → call service → return response
  - Consistent HTTP status codes and error handling

REGISTRATION IN main.py:
  Add these two lines to backend/app/main.py alongside the other routers:

      from app.routes import password_reset           # ← add this import

      app.include_router(
          password_reset.router,
          prefix="/api/password",
          tags=["🔐 Password Reset"],
      )

  After adding that, the Swagger UI at /docs will show:
      POST /api/password/forgot
      POST /api/password/verify-otp

API FLOW — step by step:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Step 1: User forgets their password                            │
  │    → POST /api/password/forgot  { "email": "user@example.com" }│
  │    → Server: checks DB, generates OTP, sends email              │
  │    → Response: 200 { "message": "OTP sent..." }                 │
  │                                                                 │
  │  Step 2: User checks email, gets OTP, submits new password      │
  │    → POST /api/password/verify-otp                              │
  │         { "email": "...", "otp": "482910", "new_password": "..." }│
  │    → Server: verifies OTP, hashes password, updates DB          │
  │    → Response: 200 { "message": "Password reset successfully." }│
  └─────────────────────────────────────────────────────────────────┘
"""

import smtplib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.password_reset_schema import (
    ForgotPasswordRequest,
    VerifyOTPRequest,
    MessageResponse,
)
from app.services.otp_service import OTPService

logger = logging.getLogger(__name__)

# ── Router ────────────────────────────────────────────────────────────────────
# No prefix here — prefix="/api/password" is set in main.py's include_router(),
# which is consistent with how auth.router uses prefix="/api/auth" in main.py.
router = APIRouter()


# ── Endpoint 1: Request OTP ───────────────────────────────────────────────────

@router.post(
    "/forgot",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset OTP",
    description=(
        "Validates the email, generates a 6-digit OTP, and sends it to "
        "the user's registered email address. OTP expires in 5 minutes. "
        "Always returns 200 to prevent email enumeration attacks."
    ),
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    POST /api/password/forgot

    Request body:
        { "email": "user@example.com" }

    Success (200) — always returned regardless of whether email exists:
        { "message": "If the account exists, an OTP has been sent to the registered email." }

    Errors:
        502 → SMTP delivery failure (email server unreachable)
        500 → unexpected server error

    Security note:
        A generic 200 response is returned for both registered and unregistered
        emails to prevent email enumeration attacks. Only SMTP and unexpected
        errors are surfaced to the client.
    """
    # ── Generic response used for all valid/invalid email cases ──────────────
    _generic_response = MessageResponse(
        message="If the account exists, an OTP has been sent to the registered email."
    )

    try:
        await OTPService.initiate_password_reset(
            email=request.email,
            db=db,
        )
        return _generic_response

    except ValueError:
        # Email not registered or account deactivated.
        # Return the same 200 + generic message so attackers cannot tell
        # whether an email exists in the system (email enumeration prevention).
        logger.warning(
            f"Password reset requested for unknown or inactive account: {request.email!r}"
        )
        return _generic_response

    except smtplib.SMTPException as e:
        # SMTP failure — email couldn't be delivered.
        # Safe to surface this: it reveals nothing about account existence.
        logger.error(f"SMTP error sending OTP to {request.email!r}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Failed to send OTP email. "
                "Please check your SMTP settings in .env or try again later."
            ),
        )

    except Exception as e:
        # Catch-all — always log so nothing silently fails.
        logger.exception(f"Unexpected error in forgot_password for {request.email!r}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# ── Endpoint 2: Verify OTP & Reset Password ───────────────────────────────────

@router.post(
    "/verify-otp",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and reset password",
    description=(
        "Verifies the OTP sent to the user's email. "
        "If valid and not expired, hashes the new password and updates it in the database. "
        "The OTP is deleted immediately after successful use."
    ),
)
async def verify_otp_and_reset(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    """
    POST /api/password/verify-otp

    Request body:
        {
            "email":        "user@example.com",
            "otp":          "482910",
            "new_password": "MyNewSecurePass@123"
        }

    Success (200):
        { "message": "Password reset successfully. You can now log in." }

    Errors:
        400 → OTP not found / expired / incorrect
        500 → unexpected server error

    After success:
        The user can immediately log in via POST /api/auth/login
        with their new password.
    """
    try:
        message = await OTPService.reset_password(
            email=request.email,
            otp=request.otp,
            new_password=request.new_password,
            db=db,
        )
        return MessageResponse(message=message)

    except ValueError as e:
        # ValueError from OTPService = OTP invalid/expired/not found, or user missing.
        # 400 is appropriate here: the OTP step is post-submission, so no
        # additional information about account existence is leaked.
        logger.warning(f"OTP verification failed for {request.email!r}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.exception(f"Unexpected error in verify_otp_and_reset for {request.email!r}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )
