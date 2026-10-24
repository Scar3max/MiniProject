"""
backend/security.py - Security primitives: password hashing, JWT, CSRF, and rate limiting.
"""

import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import bcrypt
import jwt
from fastapi import Request, HTTPException, status, Depends

import database
from backend.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DATABASE_PATH,
)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT payload with expiration timestamp."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def generate_csrf_token() -> str:
    """Generates a cryptographically secure random token for CSRF defense."""
    return secrets.token_urlsafe(32)


# In-memory sliding-window rate limiter
_RATE_LIMIT_STORE: Dict[str, list] = {}


def check_rate_limit(key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """
    Sliding window in-memory rate limiter. Returns True if allowed, False if exceeded.
    """
    import os
    if os.getenv("TESTING") == "1":
        return True

    now = time.time()
    cutoff = now - window_seconds
    timestamps = _RATE_LIMIT_STORE.get(key, [])
    # Filter expired timestamps
    valid_timestamps = [t for t in timestamps if t > cutoff]
    if len(valid_timestamps) >= max_requests:
        _RATE_LIMIT_STORE[key] = valid_timestamps
        return False
    valid_timestamps.append(now)
    _RATE_LIMIT_STORE[key] = valid_timestamps
    return True


async def get_current_user(request: Request) -> database.User:
    """
    FastAPI dependency: resolves current authenticated user from httpOnly cookie or Bearer header.
    """
    token = None
    # 1. Check httpOnly cookie
    if "access_token" in request.cookies:
        token = request.cookies.get("access_token")
    # 2. Check Authorization Bearer header fallback
    elif "authorization" in request.headers:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in or continue as guest.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
        )

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    user = database.get_user_by_id(user_id, db_path=db_path)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    # Check guest expiration
    if user.is_guest and user.guest_expires_at:
        if datetime.now(timezone.utc) > user.guest_expires_at.replace(tzinfo=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Guest session expired. Please sign in or register.",
            )

    return user


async def get_optional_user(request: Request) -> Optional[database.User]:
    """Resolves authenticated user if present, or returns None."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def verify_csrf(request: Request):
    """
    Validates CSRF token for unsafe methods (POST, PUT, DELETE, PATCH).
    Allows bypassing when explicitly authenticating via Bearer header in non-browser clients.
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # If authenticated via Authorization: Bearer, CSRF token is not strictly required
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return

        # Check CSRF header against CSRF cookie
        csrf_header = request.headers.get("X-CSRF-Token")
        csrf_cookie = request.cookies.get("csrf_token")

        if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed.",
            )
