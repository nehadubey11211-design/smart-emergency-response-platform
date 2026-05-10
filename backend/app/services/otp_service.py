"""
FILE: backend/app/services/otp_service.py
==========================================
OTP Service — Core Password Reset Business Logic
==========================================

FOLLOWS THE SAME SERVICE LAYER PATTERN AS:
  - alert_services.py  (AlertService class with static methods)
  - traffic_services.py (TrafficService class with static methods)
  - notification_services.py (NotificationService class with static methods)

INTEGRATIONS WITH EXISTING PROJECT:
  - Uses settings from app/config/settings.py (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)
  - Uses get_db() from app/database/db.py
  - Uses User model from app/models/user_model.py
  - Follows the same smtplib SMTP+STARTTLS pattern as alert_services.py

OTP STORAGE:
  Uses an in-memory Python dict — same as a simple session store.
  This is intentional for a single-server FastAPI deployment.

  ⚠️  Production upgrade path (same note as in traffic_services.py for
  background tasks): replace otp_store with Redis so that:
    1. OTPs survive server restarts
    2. Multiple server instances share the same OTP state
    3. Redis TTL handles expiry automatically (no manual datetime checks needed)

  Redis implementation would look like:
    redis_client.setex(f"otp:{email}", 300, otp)   # key, TTL=5min, value
    stored = redis_client.get(f"otp:{email}")
    redis_client.delete(f"otp:{email}")
"""

import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.utils.otp_utils import generate_otp, hash_password

# Logger — consistent with the rest of the project which uses print()
# for simplicity. In production, switch to structlog or loguru.
logger = logging.getLogger(__name__)


# ─── In-Memory OTP Store ──────────────────────────────────────────────────────
# { "user@example.com": {"otp": "482910", "expires_at": datetime(...)} }
#
# dict is module-level so it persists across requests within one server process.
# It is cleared on every server restart — acceptable for OTPs (short-lived anyway).
#
# Replace with Redis in production (see module docstring above).
_otp_store: dict[str, dict] = {}


class OTPService:
    """
    Stateless service class for OTP-based password reset.
    Uses static methods — same pattern as AlertService and TrafficService.

    Two public entry points (called by the route handlers):
      1. initiate_password_reset() → validates email, generates OTP, sends email
      2. reset_password()          → verifies OTP, hashes + updates password
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    @staticmethod
    async def initiate_password_reset(email: str, db: Session) -> str:
        """
        Called by POST /api/password/forgot.

        Flow:
          1. Check user exists in DB (using the same User model from user_model.py)
          2. Generate a 6-digit OTP
          3. Store OTP in memory with a 5-minute expiry timestamp
          4. Send OTP to user's email (SMTP, same pattern as alert_services.py)
          5. Return success message

        Args:
            email : Submitted by the user in the request body
            db    : SQLAlchemy session (injected via Depends(get_db))

        Returns:
            Success message string (route handler wraps this in MessageResponse)

        Raises:
            ValueError  : If the email is not registered
            smtplib.SMTPException : If email delivery fails
        """
        from app.models.user_model import User  # local import avoids circular deps

        # ── 1. Verify the email is registered ────────────────────────────────
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Raise ValueError — the route handler converts this to HTTP 404.
            # We deliberately do NOT say "email not found" in production
            # to prevent user enumeration, but for a beginner-friendly
            # codebase we keep the message clear.
            raise ValueError("No account is registered with this email address.")

        if not user.is_active:
            # Respect the soft-delete / deactivation pattern from user_model.py
            raise ValueError("This account has been deactivated. Contact an administrator.")

        # ── 2. Generate OTP ──────────────────────────────────────────────────
        otp = generate_otp()   # e.g. "482910"

        # ── 3. Store OTP with expiry ─────────────────────────────────────────
        OTPService._store_otp(email=email, otp=otp, expiry_minutes=5)

        # ── 4. Send email ────────────────────────────────────────────────────
        OTPService._send_otp_email(recipient_email=email, otp=otp, user_name=user.name)

        print(f"🔐 OTP generated and sent to {email} (user: {user.name})")
        return f"OTP sent to {email}. It is valid for 5 minutes."

    @staticmethod
    async def reset_password(
        email: str,
        otp: str,
        new_password: str,
        db: Session,
    ) -> str:
        """
        Called by POST /api/password/verify-otp.

        Flow:
          1. Verify the OTP (correct? not expired?)
          2. Fetch the user from DB
          3. Hash the new password (same bcrypt approach as auth.py)
          4. Update user.password in the DB → db.commit()
          5. Delete the used OTP from the store (prevent reuse)
          6. Return success message

        Args:
            email        : The user's email (identifies the account)
            otp          : The 6-digit code submitted by the user
            new_password : Plain text new password (hashed before storage)
            db           : SQLAlchemy session

        Returns:
            Success message string

        Raises:
            ValueError : Descriptive error for OTP issues or user not found
        """
        from app.models.user_model import User  # local import avoids circular deps

        # ── 1. Verify OTP ────────────────────────────────────────────────────
        is_valid, reason = OTPService._verify_otp(email=email, submitted_otp=otp)
        if not is_valid:
            error_messages = {
                "not_found": "No OTP was requested for this email. Please request a new one.",
                "expired":   "Your OTP has expired (5-minute window). Please request a new one.",
                "invalid":   "Incorrect OTP. Please check the code and try again.",
            }
            raise ValueError(error_messages.get(reason, "OTP verification failed."))

        # ── 2. Fetch user ────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("User not found.")

        # ── 3. Hash new password ─────────────────────────────────────────────
        # Uses same bcrypt rounds=12 as hash_password() in routes/auth.py
        user.password = hash_password(new_password)

        # ── 4. Persist to database ───────────────────────────────────────────
        # SQLAlchemy tracks the change to user.password automatically.
        # db.commit() writes it to Neon/PostgreSQL.
        db.commit()
        print(f"✅ Password updated in DB for user: {email}")

        # ── 5. Delete OTP immediately ─────────────────────────────────────────
        # Once used successfully, remove from store.
        # This means the OTP cannot be replayed even within the 5-minute window.
        OTPService._delete_otp(email)

        return "Password reset successfully. You can now log in with your new password."

    # ── Private Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _store_otp(email: str, otp: str, expiry_minutes: int = 5) -> None:
        """
        Save OTP + expiry timestamp to the in-memory store.

        Overwrites any existing OTP for this email — this means a user
        can re-request a new OTP and the old one is immediately invalidated.
        """
        _otp_store[email] = {
            "otp":        otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=expiry_minutes),
        }
        logger.debug(f"OTP stored for {email}, expires in {expiry_minutes}m")

    @staticmethod
    def _verify_otp(email: str, submitted_otp: str) -> tuple[bool, str]:
        """
        Check that the submitted OTP is valid, not expired, and correct.

        Returns a (success, reason) tuple so the caller knows WHY it failed.
        The reason string maps to a user-friendly message in reset_password().

        Possible outcomes:
            (True,  "valid")      → all checks passed
            (False, "not_found")  → no OTP on record for this email
            (False, "expired")    → OTP exists but datetime.utcnow() > expires_at
            (False, "invalid")    → OTP exists, valid, but wrong digits
        """
        record = _otp_store.get(email)

        if not record:
            return False, "not_found"

        if datetime.utcnow() > record["expires_at"]:
            OTPService._delete_otp(email)   # clean up expired record
            return False, "expired"

        if record["otp"] != submitted_otp:
            return False, "invalid"

        return True, "valid"

    @staticmethod
    def _delete_otp(email: str) -> None:
        """Remove an OTP record from the store."""
        _otp_store.pop(email, None)   # pop with default=None avoids KeyError

    @staticmethod
    def _send_otp_email(recipient_email: str, otp: str, user_name: str) -> None:
        """
        Send the OTP via SMTP.

        Uses the EXACT same smtplib + STARTTLS pattern as alert_services.py:
            smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        Settings used (from app/config/settings.py):
            SMTP_HOST     → "smtp.gmail.com"
            SMTP_PORT     → 587
            SMTP_USER     → your Gmail address
            SMTP_PASSWORD → your Gmail App Password

        The HTML template matches the dark theme styling used in alert_services.py
        for visual consistency across all system emails.

        Args:
            recipient_email : Where to deliver the OTP
            otp             : The 6-digit code to embed
            user_name       : The user's display name (for personalisation)

        Raises:
            smtplib.SMTPException : Caught in the route handler → HTTP 502
        """
        # ── Build message ────────────────────────────────────────────────────
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Your Password Reset OTP — Smart AI Emergency Response"
        msg["From"]    = settings.SMTP_USER
        msg["To"]      = recipient_email

        # Plain-text fallback (same pattern as alert_services.py)
        plain_text = f"""
Hello {user_name},

You requested a password reset for your Smart AI Emergency Response account.

Your OTP code: {otp}

This code is valid for 5 minutes.
If you did not request this, please ignore this email — your password is unchanged.

— Smart AI Emergency Response System
        """.strip()

        # HTML version — dark theme matching alert_services.py email style
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #0a0e1a;
                     color: #e0eaf8; padding: 30px; margin: 0;">
          <div style="max-width: 480px; margin: auto; background: #0f1628;
                      border: 2px solid #3b82f6; border-radius: 8px; padding: 32px;">

            <h2 style="color: #3b82f6; margin: 0 0 8px;">🔐 Password Reset Request</h2>
            <p style="color: #8899aa; font-size: 13px; margin: 0 0 24px;">
              Smart AI Emergency Response System
            </p>

            <p style="color: #e0eaf8;">Hello <strong>{user_name}</strong>,</p>
            <p style="color: #c0cfe8;">
              We received a request to reset your password. Use the OTP below:
            </p>

            <!-- OTP display — large, easy to read -->
            <div style="text-align: center; margin: 28px 0;">
              <div style="display: inline-block; background: #1e2d4a;
                          border: 2px solid #3b82f6; border-radius: 8px;
                          padding: 18px 32px;">
                <span style="font-size: 38px; font-weight: bold;
                             letter-spacing: 12px; color: #60a5fa;
                             font-family: 'Courier New', monospace;">
                  {otp}
                </span>
              </div>
            </div>

            <!-- Metadata table matching alert_services.py table style -->
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
              <tr>
                <td style="color: #8899aa; padding: 4px 0; font-size: 13px;">Expires in</td>
                <td style="color: #fbbf24; font-weight: bold; font-size: 13px;">5 minutes</td>
              </tr>
              <tr>
                <td style="color: #8899aa; padding: 4px 0; font-size: 13px;">Account</td>
                <td style="font-size: 13px;">{recipient_email}</td>
              </tr>
            </table>

            <p style="color: #6b7a8d; font-size: 12px; border-top: 1px solid #1e2d4a;
                      padding-top: 16px; margin-bottom: 0;">
              If you did not request a password reset, please ignore this email.
              Your password will not be changed.
            </p>

          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # ── Send via SMTP (identical to alert_services.py pattern) ───────────
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()   # Upgrade to encrypted connection (port 587)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        print(f"   ✅ OTP email sent to {recipient_email}")
