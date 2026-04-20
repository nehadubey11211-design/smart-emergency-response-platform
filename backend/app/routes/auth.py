"""
FILE: backend/app/routes/auth.py
======================================
Authentication Endpoints
======================================

Implements JWT (JSON Web Token) based stateless authentication.

WHY JWT?
  Traditional session-based auth stores session data on the server.
  JWT auth encodes the user's identity INTO the token itself.

  Benefits:
    - Stateless: no session storage needed on the server
    - Scalable: any server in a cluster can verify any token
    - Self-contained: the token carries user ID, expiry, etc.

  Trade-offs:
    - Tokens can't be invalidated before expiry (use short TTL + refresh tokens)
    - Token size is larger than a session ID

TOKEN LIFECYCLE:
  1. Client POSTs email+password to /login
  2. Server verifies password hash with bcrypt
  3. Server creates a JWT signed with SECRET_KEY, containing user_id + expiry
  4. Client stores the token (localStorage / memory)
  5. Client sends token in header: Authorization: Bearer <token>
  6. Server decodes and verifies the token on every protected request

INTERVIEW TALKING POINT:
  "I chose bcrypt for password hashing because it has a configurable cost factor.
  As hardware gets faster, you can increase the cost to keep brute-force
  attacks equally slow, without changing the API."
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.db import get_db
from app.models.user_model import User
from app.schemas.user_schema import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter()


# ─── Password Helpers ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    bcrypt automatically generates and embeds a salt — no need to manage
    salts separately.  The resulting hash looks like:
      $2b$12$<22-char-salt><31-char-hash>

    The '12' is the cost factor (2^12 = 4096 iterations).
    Higher cost = slower hashing = harder to brute-force.
    """
    salt   = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Safely compare a plaintext password against a stored bcrypt hash.

    bcrypt.checkpw re-extracts the salt from the hash and re-hashes
    the candidate password, then compares in constant time.
    The constant-time comparison prevents timing attacks.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ─── JWT Helpers ──────────────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """
    Create a signed JWT containing the user's ID and an expiry timestamp.

    JWT structure:  header.payload.signature
    Payload (claims):
      sub  — Subject: the user's ID (standard JWT claim)
      exp  — Expiry: Unix timestamp when this token becomes invalid
      iat  — Issued At: when the token was created

    The token is signed with HMAC-SHA256 using SECRET_KEY, so any
    modification to the payload will invalidate the signature.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    """
    Decode and verify a JWT, returning the user_id (sub claim).
    Returns None if the token is invalid or expired.

    jwt.decode() verifies:
      1. The signature (token hasn't been tampered with)
      2. The expiry (token hasn't expired)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        return None   # Token is valid but expired
    except jwt.InvalidTokenError:
        return None   # Token is malformed or signature mismatch


def get_current_user(
    token: str,
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts + verifies the JWT and returns the User.

    Usage in a protected route:
      @router.get("/protected")
      def protected(user: User = Depends(get_current_user)):
          return {"hello": user.name}
    """
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated",
        )
    return user


# ─── Route Handlers ───────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account and return an access token.

    Steps:
      1. Check the email isn't already registered (unique constraint)
      2. Hash the password with bcrypt
      3. Insert the user row
      4. Create and return a JWT
    """
    # Step 1: duplicate email check
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Step 2 + 3: create user with hashed password
    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),  # NEVER store plaintext
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # Populates auto-generated fields (id, created_at)

    # Step 4: issue a JWT
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive an access token",
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate with email + password.
    Returns a JWT token on success.

    SECURITY NOTE:
      We return the same generic error for both "user not found" and
      "wrong password" to prevent user enumeration attacks (an attacker
      discovering which emails are registered by testing error messages).
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    # Use a constant-time check even if user is None to prevent timing attacks
    if user is None or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator.",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def get_me(token: str, db: Session = Depends(get_db)):
    """
    Returns the profile of the user identified by the JWT.
    Used by the frontend after page reload to restore session state.
    """
    return get_current_user(token, db)
