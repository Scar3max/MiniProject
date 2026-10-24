"""
backend/routers/auth.py - Authentication router: registration, login, guest access, session verification, logout.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field

import database
from backend.config import (
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DATABASE_PATH,
)
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_csrf_token,
    check_rate_limit,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_guest: bool


class AuthResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    message: str


def _set_auth_cookies(response: Response, user_id: int, role: str) -> str:
    """Helper to issue and attach JWT access token and CSRF token cookies."""
    token = create_access_token(data={"sub": str(user_id), "role": role})
    csrf_token = generate_csrf_token()

    max_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # 1. HttpOnly access_token cookie
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/"
    )

    # 2. Readable csrf_token cookie for the frontend client
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/"
    )

    return csrf_token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"register:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please wait a minute.")

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    # Check if email is already taken
    existing_user = database.get_user_by_email(req.email, db_path=db_path)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    # Create User
    pwd_hash = hash_password(req.password)
    user = database.create_user(
        email=req.email,
        password_hash=pwd_hash,
        role="candidate",
        is_guest=False,
        db_path=db_path
    )

    # Decision 3: Registration always creates a brand new candidate row (never links to old rows)
    database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)

    # Create user profile with full_name and consent
    database.upsert_user_profile(
        user_id=user.user_id,
        profile_data={
            "full_name": req.full_name,
            "consent_save_sessions": True
        },
        db_path=db_path
    )

    csrf_token = _set_auth_cookies(response, user.user_id, user.role)

    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": req.full_name,
            "role": user.role,
            "is_guest": False
        },
        "csrf_token": csrf_token,
        "message": "Account created successfully."
    }


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"login:{client_ip}", max_requests=15, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait a minute.")

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    user = database.get_user_by_email(req.email, db_path=db_path)

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    profile = database.get_user_profile(user.user_id, db_path=db_path)
    csrf_token = _set_auth_cookies(response, user.user_id, user.role)

    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": profile.get("full_name") if profile else None,
            "role": user.role,
            "is_guest": user.is_guest
        },
        "csrf_token": csrf_token,
        "message": "Login successful."
    }


@router.post("/guest", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_session(request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"guest:{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many guest session creations. Please wait.")

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)

    # Guest user lifecycle: 7 days
    guest_uuid = uuid.uuid4().hex[:12]
    guest_email = f"guest-{guest_uuid}@guest.local"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    user = database.create_user(
        email=guest_email,
        password_hash=None,
        role="guest",
        is_guest=True,
        guest_expires_at=expires_at,
        db_path=db_path
    )

    # Create candidate record for guest
    database.get_or_create_candidate_for_user(user_id=user.user_id, db_path=db_path)

    # Guest profile defaults
    database.upsert_user_profile(
        user_id=user.user_id,
        profile_data={
            "full_name": "Guest Candidate",
            "consent_save_sessions": True
        },
        db_path=db_path
    )

    csrf_token = _set_auth_cookies(response, user.user_id, user.role)

    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": "Guest Candidate",
            "role": user.role,
            "is_guest": True
        },
        "csrf_token": csrf_token,
        "message": "Guest session created."
    }


@router.get("/me")
async def get_me(request: Request, user: database.User = Depends(get_current_user)):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    profile = database.get_user_profile(user.user_id, db_path=db_path)

    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": profile.get("full_name") if profile else None,
        "role": user.role,
        "is_guest": user.is_guest,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "profile": {
            "target_role": profile.get("target_role") if profile else None,
            "years_of_experience": profile.get("year_experience") if profile else None,
            "preferred_domains": profile.get("preferred_domains") if profile else [],
            "consent_save_sessions": profile.get("consent_save_sessions", True) if profile else True
        } if profile else None
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    return {"status": "logged_out", "message": "Successfully logged out."}
