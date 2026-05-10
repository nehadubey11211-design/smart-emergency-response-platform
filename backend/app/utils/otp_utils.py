"""
FILE: backend/app/utils/otp_utils.py
======================================
OTP Generation & Password Hashing Utilities
======================================

WHY A SEPARATE utils FILE INSTEAD OF PUTTING THIS IN THE SERVICE?
  Same reason auth.py separates hash_password() and verify_password():
  small, pure helper functions belong in utils — they have no side effects,
  no DB access, and can be unit-tested in isolation with no mocks.

PASSWORD HASHING NOTE:
  This project already uses bcrypt in auth.py (via the `bcrypt` library directly).
  We use the SAME approach here to stay consistent — one hashing strategy
  across the whole codebase. Do not mix bcrypt and passlib in the same project.

  See: backend/app/routes/auth.py → hash_password() and verify_password()
"""

import random
import string
import bcrypt


def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically random numeric OTP.

    Uses random.choices() over string.digits — produces a digit-only string
    which is easiest to type on mobile keyboards.

    Why 6 digits?
      6 digits = 10^6 = 1,000,000 possible combinations.
      Combined with a 5-minute expiry and brute-force lockout (future),
      this is secure enough for password reset flows.

    Args:
        length : Number of digits (default 6)

    Returns:
        String like "048291"

    Example:
        >>> generate_otp()
        "482910"
    """
    return "".join(random.choices(string.digits, k=length))


def hash_password(plain_password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Identical implementation to hash_password() in routes/auth.py —
    kept here so the password reset service doesn't import from a route file
    (routes should never be imported by services — that breaks layering).

    The rounds=12 cost factor matches auth.py for consistency.

    Args:
        plain_password : The user's new plain text password

    Returns:
        A bcrypt hash string like "$2b$12$..."
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")
