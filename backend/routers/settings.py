"""
backend/routers/settings.py - Account settings: password changes and GDPR data deletion.
"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from pydantic import BaseModel, Field

import database
from backend.config import DATABASE_PATH
from backend.security import get_current_user, verify_password, hash_password, verify_csrf

router = APIRouter(prefix="/settings", tags=["settings"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class DeleteDataRequest(BaseModel):
    confirmation: str = Field(..., description="Must exactly type 'DELETE MY DATA'")


@router.put("/password", dependencies=[Depends(verify_csrf)])
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: database.User = Depends(get_current_user)
):
    if user.is_guest or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest accounts do not have passwords."
        )

    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    new_hash = hash_password(req.new_password)
    database.update_user_password(user.user_id, new_hash, db_path=db_path)

    return {"status": "success", "message": "Password updated successfully."}


@router.delete("/data", dependencies=[Depends(verify_csrf)])
async def delete_all_user_data(
    req: DeleteDataRequest,
    request: Request,
    response: Response,
    user: database.User = Depends(get_current_user)
):
    """
    GDPR Right to Erasure: Permanently cascades and deletes all turns, sessions,
    candidate records, profile data, and user account.
    """
    if req.confirmation.strip() != "DELETE MY DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation string must match exactly: 'DELETE MY DATA'"
        )

    db_path = getattr(request.app.state, "db_path", DATABASE_PATH)
    deleted = database.delete_user_data(user.user_id, db_path=db_path)

    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")

    return {
        "status": "deleted",
        "message": "All personal interview data and account records permanently removed.",
        "details": deleted
    }
