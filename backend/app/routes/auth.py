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

from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.db import get_db
from app.models.user_model import User
from app.schemas.user_schema import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

from app.main import limiter

router = APIRouter()


# ─── Password Helpers ─────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ─── JWT Helpers ──────────────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
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


async def get_current_user_from_header(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    return await get_current_user(token, db)


async def get_admin_user(
    user: User = Depends(get_current_user_from_header),
):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("3/hour")
async def register(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive an access token",
)

@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    dummy_hash = "$2b$12$dummyhashfortimingprevention00000000000000000000000000"
    stored_hash = user.password if user else dummy_hash
    password_valid = verify_password(credentials.password, stored_hash)

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
async def get_me(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.split(" ")[1]
    return await get_current_user(token, db)
