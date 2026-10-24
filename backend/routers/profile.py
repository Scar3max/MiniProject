"""
backend/routers/profile.py - User profile router: target role, experience, preferred domains, consent settings.
"""

from typing import Optional, List, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel

import database
from backend.config import DATABASE_PATH
from backend.security import get_current_user, verify_csrf

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    college_org: Optional[str] = None
    target_role: Optional[str] = None
    years_of_experience: Optional[Any] = None
    year_experience: Optional[Any] = None
    preferred_domains: Optional[Any] = None
    preferred_difficulty: Optional[str] = None
    consent_save_sessions: Optional[bool] = None


@router.get("")
async def get_profile(request: Request, user: database.User = Depends(get_current_user)):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    profile = database.get_user_profile(user.user_id, db_path=db_path)
    if not profile:
        return {
            "user_id": user.user_id,
            "full_name": None,
            "college_org": None,
            "target_role": None,
            "years_of_experience": None,
            "year_experience": None,
            "preferred_domains": [],
            "preferred_difficulty": "adaptive",
            "consent_save_sessions": True
        }
    return {
        "user_id": user.user_id,
        "full_name": profile.get("full_name"),
        "college_org": profile.get("college_org"),
        "target_role": profile.get("target_role"),
        "years_of_experience": profile.get("year_experience"),
        "year_experience": profile.get("year_experience"),
        "preferred_domains": profile.get("preferred_domains", []),
        "preferred_difficulty": profile.get("preferred_difficulty", "adaptive"),
        "consent_save_sessions": profile.get("consent_save_sessions", True)
    }


@router.put("", dependencies=[Depends(verify_csrf)])
@router.post("", dependencies=[Depends(verify_csrf)])
async def update_profile(
    req: ProfileUpdateRequest,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    profile_data = {}
    if req.full_name is not None:
        profile_data["full_name"] = req.full_name
    if req.college_org is not None:
        profile_data["college_org"] = req.college_org
    if req.target_role is not None:
        profile_data["target_role"] = req.target_role
    y_exp = req.years_of_experience if req.years_of_experience is not None else req.year_experience
    if y_exp is not None:
        profile_data["year_experience"] = str(y_exp)
    if req.preferred_domains is not None:
        profile_data["preferred_domains"] = req.preferred_domains
    if req.preferred_difficulty is not None:
        profile_data["preferred_difficulty"] = req.preferred_difficulty
    if req.consent_save_sessions is not None:
        profile_data["consent_save_sessions"] = req.consent_save_sessions

    updated = database.upsert_user_profile(
        user_id=user.user_id,
        profile_data=profile_data,
        db_path=db_path
    )
    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "profile": updated
    }
