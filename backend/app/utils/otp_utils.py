"""
FILE: backend/app/utils/otp_utils.py
======================================
OTP Generation & Password Hashing Utilities
======================================
"""

import secrets
import string
import bcrypt


def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically secure random numeric OTP.

    Uses secrets.choice() over random.choices() — the `secrets` module is
    backed by the OS CSPRNG (/dev/urandom on Linux/macOS, CryptGenRandom on
    Windows), making output unpredictable even if an attacker observes prior OTPs.

    Why not random.choices()?
      Python's `random` module uses Mersenne Twister, a PRNG designed for
      statistical simulations — not security. With ~624 observed outputs an
      attacker can fully reconstruct its internal state and predict future OTPs.

    Why 6 digits?
      6 digits = 10^6 = 1,000,000 possible combinations.
      Combined with a 5-minute expiry and rate-limiting/lockout, this is
      secure enough for password-reset flows.

    Args:
        length : Number of digits (default 6)

    Returns:
        String like "048291"

    Example:
        >>> generate_otp()
        "482910"
    """
    return "".join(secrets.choice(string.digits) for _ in range(length))


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
    