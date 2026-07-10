"""
FILE: backend/app/services/otp_service.py
==========================================
OTP Service — Core Password Reset Business Logic
==========================================
"""

import aiosmtplib
import logging
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.utils.otp_utils import generate_otp, hash_password

logger = logging.getLogger(__name__)

# Redis client (async)
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

OTP_TTL_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 3


class RedisUnavailableError(RuntimeError):
    """Raised when Redis is not available for OTP storage."""


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
        try:
            await OTPService._store_otp(email=email, otp=otp)
        except RedisUnavailableError:
            raise

        await OTPService._send_otp_email(recipient_email=email, otp=otp, user_name=user.name)

        logger.info("OTP generated and sent to %s (user: %s)", email, user.name)
        return f"OTP sent to {email}. It is valid for 5 minutes."

    @staticmethod
    async def reset_password(
        email: str,
        otp: str,
        new_password: str,
        db: AsyncSession,
    ) -> str:
        from app.models.user_model import User

        is_valid, reason = await OTPService._verify_otp(email=email, submitted_otp=otp)
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
        logger.info("Password updated in DB for user: %s", email)

        await OTPService._delete_otp(email)
        return "Password reset successfully. You can now log in with your new password."

    @staticmethod
    async def _store_otp(email: str, otp: str) -> None:
        # Hash the OTP before storing (never store plaintext)
        otp_hash = hmac.new(settings.SECRET_KEY.encode(), otp.encode(), hashlib.sha256).hexdigest()
        key = f"otp:{email}"
        try:
            await redis_client.setex(key, OTP_TTL_SECONDS, json.dumps({
                "otp_hash": otp_hash,
                "attempts": 0
            }))
        except (RedisConnectionError, RedisError) as exc:
            logger.error("Redis unavailable while storing OTP for %s: %s", email, exc)
            raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc

        logger.debug(f"OTP stored for {email} with TTL {OTP_TTL_SECONDS}s")

    @staticmethod
    async def _verify_otp(email: str, submitted_otp: str) -> tuple[bool, str]:
        key = f"otp:{email}"
        try:
            raw = await redis_client.get(key)
        except (RedisConnectionError, RedisError) as exc:
            logger.error("Redis unavailable while verifying OTP for %s: %s", email, exc)
            raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc

        if not raw:
            return False, "not_found"

        record = json.loads(raw)
        if record.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
            try:
                await redis_client.delete(key)
            except (RedisConnectionError, RedisError) as exc:
                logger.error("Redis unavailable while deleting locked OTP for %s: %s", email, exc)
                raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc
            return False, "locked"

        expected_hash = hmac.new(settings.SECRET_KEY.encode(), submitted_otp.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(record["otp_hash"], expected_hash):
            record["attempts"] = record.get("attempts", 0) + 1
            try:
                remaining_ttl = await redis_client.ttl(key)
                await redis_client.setex(key, max(remaining_ttl, 1), json.dumps(record))
            except (RedisConnectionError, RedisError) as exc:
                logger.error("Redis unavailable while updating OTP attempts for %s: %s", email, exc)
                raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc
            remaining = OTP_MAX_ATTEMPTS - record["attempts"]
            return False, f"invalid:{remaining}"

        try:
            await redis_client.delete(key)
        except (RedisConnectionError, RedisError) as exc:
            logger.error("Redis unavailable while deleting OTP after successful verify for %s: %s", email, exc)
            raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc

        return True, "valid"

    @staticmethod
    async def _delete_otp(email: str) -> None:
        key = f"otp:{email}"
        try:
            await redis_client.delete(key)
        except (RedisConnectionError, RedisError) as exc:
            logger.error("Redis unavailable while deleting OTP for %s: %s", email, exc)
            raise RedisUnavailableError("Redis is unavailable. Please start Redis and configure REDIS_URL.") from exc

    @staticmethod
    async def _send_otp_email(recipient_email: str, otp: str, user_name: str) -> None:
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

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=False,
                start_tls=True,
            )
            logger.info("OTP email sent to %s", recipient_email)
        except Exception as e:
            logger.error("OTP email failed for %s: %s", recipient_email, e)
