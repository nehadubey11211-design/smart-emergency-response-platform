"""
FILE: backend/app/services/otp_service.py
==========================================
OTP Service — Core Password Reset Business Logic
==========================================
"""

import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.utils.otp_utils import generate_otp, hash_password

logger = logging.getLogger(__name__)

_otp_store: dict[str, dict] = {}


class OTPService:
    @staticmethod
    async def initiate_password_reset(email: str, db: AsyncSession) -> str:
        from app.models.user_model import User

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("No account is registered with this email address.")

        if not user.is_active:
            raise ValueError("This account has been deactivated. Contact an administrator.")

        otp = generate_otp()
        OTPService._store_otp(email=email, otp=otp, expiry_minutes=5)
        OTPService._send_otp_email(recipient_email=email, otp=otp, user_name=user.name)

        print(f"🔐 OTP generated and sent to {email} (user: {user.name})")
        return f"OTP sent to {email}. It is valid for 5 minutes."

    @staticmethod
    async def reset_password(
        email: str,
        otp: str,
        new_password: str,
        db: AsyncSession,
    ) -> str:
        from app.models.user_model import User

        is_valid, reason = OTPService._verify_otp(email=email, submitted_otp=otp)
        if not is_valid:
            if reason == "locked":
                raise ValueError(
                    "Too many incorrect attempts. Your OTP has been invalidated. Please request a new one."
                )
            if reason.startswith("invalid:"):
                remaining = reason.split(":")[1]
                raise ValueError(
                    f"Incorrect OTP. {remaining} attempt(s) remaining before lockout."
                )

            error_messages = {
                "not_found": "No OTP was requested for this email. Please request a new one.",
                "expired":   "Your OTP has expired (5-minute window). Please request a new one.",
            }
            raise ValueError(error_messages.get(reason, "OTP verification failed."))

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found.")

        user.password = hash_password(new_password)
        await db.commit()
        print(f"✅ Password updated in DB for user: {email}")

        OTPService._delete_otp(email)
        return "Password reset successfully. You can now log in with your new password."

    @staticmethod
    def _store_otp(email: str, otp: str, expiry_minutes: int = 5) -> None:
        _otp_store[email] = {
            "otp":        otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=expiry_minutes),
            "attempts": 0,
        }
        logger.debug(f"OTP stored for {email}, expires in {expiry_minutes}m")

    @staticmethod
    def _verify_otp(email: str, submitted_otp: str) -> tuple[bool, str]:
        record = _otp_store.get(email)

        if not record:
            return False, "not_found"

        if datetime.utcnow() > record["expires_at"]:
            OTPService._delete_otp(email)
            return False, "expired"

        if record["attempts"] >= 3:
            OTPService._delete_otp(email)
            return False, "locked"

        if record["otp"] != submitted_otp:
            record["attempts"] += 1
            remaining = 3 - record["attempts"]
            logger.warning(f"Wrong OTP for {email} — {remaining} attempt(s) left")
            return False, f"invalid:{remaining}"

        return True, "valid"

    @staticmethod
    def _delete_otp(email: str) -> None:
        _otp_store.pop(email, None)

    @staticmethod
    def _send_otp_email(recipient_email: str, otp: str, user_name: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Your Password Reset OTP — Smart AI Emergency Response"
        msg["From"] = settings.SMTP_USER
        msg["To"] = recipient_email

        plain_text = f"""
Hello {user_name},

You requested a password reset for your Smart AI Emergency Response account.

Your OTP code: {otp}

This code is valid for 5 minutes.
If you did not request this, please ignore this email — your password is unchanged.

— Smart AI Emergency Response System
        """.strip()

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

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        print(f"   ✅ OTP email sent to {recipient_email}")
