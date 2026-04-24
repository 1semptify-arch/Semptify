"""
Invite Codes API Router
=======================

Endpoints for managing and redeeming invite codes for
Advocate and Legal role validation.

Routes:
- POST /api/invite-codes/validate - Check if code is valid
- POST /api/invite-codes/redeem - Redeem code for current user
- POST /api/invite-codes/create - Create new code (manager/admin only)
- GET /api/invite-codes/list - List codes for organization
- DELETE /api/invite-codes/{code} - Deactivate a code
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.database import get_db_session
from app.core.invite_codes import (
    create_invite_code,
    validate_invite_code,
    redeem_invite_code,
    get_organization_codes,
    deactivate_invite_code,
    get_code_stats,
)
from app.core.user_id import COOKIE_USER_ID

router = APIRouter(prefix="/api/invite-codes", tags=["Invite Codes"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ValidateCodeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=32, description="Invite code to validate")


class ValidateCodeResponse(BaseModel):
    valid: bool
    message: str
    role: Optional[str] = None
    organization: Optional[str] = None


class RedeemCodeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=32, description="Invite code to redeem")


class RedeemCodeResponse(BaseModel):
    success: bool
    message: str
    role: Optional[str] = None
    organization: Optional[str] = None


class CreateCodeRequest(BaseModel):
    role: str = Field(default="advocate", description="Role to grant: advocate, legal, admin")
    max_uses: int = Field(default=1, ge=1, le=100, description="Maximum number of uses")
    expires_days: Optional[int] = Field(default=None, ge=1, le=365, description="Days until expiration")
    description: Optional[str] = Field(default=None, max_length=200, description="Optional note")
    custom_code: Optional[str] = Field(default=None, max_length=32, description="Custom code (optional)")


class CreateCodeResponse(BaseModel):
    success: bool
    code: str
    role: str
    expires_at: Optional[str] = None


class CodeInfo(BaseModel):
    code: str
    role: str
    organization: Optional[str]
    max_uses: int
    uses_count: int
    remaining_uses: int
    is_active: bool
    is_expired: bool
    expires_at: Optional[str]
    created_at: str
    description: Optional[str]


# =============================================================================
# Public Endpoints (for onboarding flow)
# =============================================================================

@router.post("/validate", response_model=ValidateCodeResponse)
async def validate_code(
    request: Request,
    body: ValidateCodeRequest,
):
    """
    Validate an invite code without redeeming it.
    
    Used during onboarding to check if a code is valid
    before the user completes registration.
    """
    with get_db_session() as db:
        is_valid, message, invite = validate_invite_code(body.code, db)
        
        return ValidateCodeResponse(
            valid=is_valid,
            message=message,
            role=invite.role if invite else None,
            organization=invite.organization_name if invite else None,
        )


@router.post("/redeem", response_model=RedeemCodeResponse)
async def redeem_code(
    request: Request,
    body: RedeemCodeRequest,
):
    """
    Redeem an invite code for the current user.
    
    This permanently associates the code with the user's account
    and grants them the specified role.
    """
    user_id = request.cookies.get(COOKIE_USER_ID)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    with get_db_session() as db:
        success, message, invite = redeem_invite_code(body.code, user_id, db)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return RedeemCodeResponse(
            success=True,
            message=message,
            role=invite.role if invite else None,
            organization=invite.organization_name if invite else None,
        )


# =============================================================================
# Manager/Admin Endpoints (require elevated permissions)
# =============================================================================

@router.post("/create", response_model=CreateCodeResponse)
async def create_code(
    request: Request,
    body: CreateCodeRequest,
):
    """
    Create a new invite code.
    
    Requires manager or admin role. The created code will be
    associated with the creator's organization.
    """
    from app.core.user_context import get_role_from_user_id, UserRole
    from app.models.models import User
    
    user_id = request.cookies.get(COOKIE_USER_ID)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check permissions
    role = get_role_from_user_id(user_id)
    if role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only managers and admins can create invite codes")
    
    with get_db_session() as db:
        # Get user's organization info
        user = db.query(User).filter_by(id=user_id).first()
        org_id = user_id[:12] if user else None  # Use part of user ID as org ID
        org_name = user.display_name if user else "Unknown Organization"
        
        # Create the code
        invite = create_invite_code(
            created_by=user_id,
            role=body.role,
            organization_id=org_id,
            organization_name=org_name,
            max_uses=body.max_uses,
            expires_days=body.expires_days,
            description=body.description,
            custom_code=body.custom_code,
        )
        
        db.add(invite)
        db.commit()
        
        return CreateCodeResponse(
            success=True,
            code=invite.code,
            role=invite.role,
            expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
        )


@router.get("/list")
async def list_codes(request: Request):
    """
    List all invite codes for the current user's organization.
    
    Returns active and inactive codes with usage statistics.
    """
    from app.core.user_context import get_role_from_user_id, UserRole
    from app.models.models import User
    
    user_id = request.cookies.get(COOKIE_USER_ID)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check permissions
    role = get_role_from_user_id(user_id)
    if role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only managers and admins can view invite codes")
    
    with get_db_session() as db:
        # Get user's organization
        user = db.query(User).filter_by(id=user_id).first()
        org_id = user_id[:12] if user else None
        
        codes = get_organization_codes(org_id, db, include_inactive=True)
        
        return {
            "codes": [
                {
                    "code": c.code,
                    "role": c.role,
                    "max_uses": c.max_uses,
                    "uses_count": c.uses_count,
                    "remaining_uses": c.remaining_uses,
                    "is_active": c.is_active,
                    "is_expired": c.is_expired,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "created_at": c.created_at.isoformat(),
                    "description": c.description,
                }
                for c in codes
            ]
        }


@router.delete("/{code}")
async def delete_code(code: str, request: Request):
    """
    Deactivate an invite code.
    
    The code becomes permanently invalid but remains in the
    database for audit purposes.
    """
    from app.core.user_context import get_role_from_user_id, UserRole
    
    user_id = request.cookies.get(COOKIE_USER_ID)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check permissions
    role = get_role_from_user_id(user_id)
    if role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only managers and admins can deactivate invite codes")
    
    with get_db_session() as db:
        success = deactivate_invite_code(code, db)
        
        if not success:
            raise HTTPException(status_code=404, detail="Invite code not found")
        
        return {"success": True, "message": "Invite code deactivated"}


@router.get("/{code}/stats")
async def code_stats(code: str, request: Request):
    """
    Get detailed statistics about a specific invite code.
    """
    from app.core.user_context import get_role_from_user_id, UserRole
    
    user_id = request.cookies.get(COOKIE_USER_ID)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check permissions
    role = get_role_from_user_id(user_id)
    if role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only managers and admins can view code stats")
    
    with get_db_session() as db:
        stats = get_code_stats(code, db)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Invite code not found")
        
        return stats
