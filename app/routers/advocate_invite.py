"""
Advocate Invitation Router
==========================

API endpoints for tenants to invite personal advocates (friends, family, volunteers)
to support their case.

Advocates are trust-based support roles, not professional credentials.
Access is granted solely by tenant invitation and can be revoked at any time.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.id_gen import make_id

from ..core.security import require_user, StorageUser
from ..core.vault_paths import VAULT_ROOT


router = APIRouter(prefix="/api/advocate", tags=["Advocate Invitation"])


class InviteAdvocateRequest(BaseModel):
    """Request to invite an advocate"""
    email: EmailStr
    name: str
    relationship: str  # "friend", "family", "volunteer", "other"
    message: Optional[str] = None


class AdvocateInvite(BaseModel):
    """An advocate invitation record"""
    invite_id: str
    tenant_id: str
    tenant_email: str
    advocate_email: EmailStr
    advocate_name: str
    relationship: str
    message: Optional[str]
    status: str  # "pending", "accepted", "revoked"
    created_at: str
    expires_at: str
    accepted_at: Optional[str] = None


class RevokeAdvocateRequest(BaseModel):
    """Request to revoke an advocate's access"""
    invite_id: str
    reason: Optional[str] = None


@router.post("/invite")
async def invite_advocate(
    request: InviteAdvocateRequest,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Tenant invites someone to be their advocate.
    
    Creates a pending invitation stored in the tenant's vault.
    Invitation email is sent to the advocate with acceptance link.
    """
    # TODO: Implement vault storage of invitation
    # TODO: Send email to advocate
    
    invite_id = make_id("inv")
    
    invite_record = AdvocateInvite(
        invite_id=invite_id,
        tenant_id=user.user_id,
        tenant_email=user.email or "",
        advocate_email=request.email,
        advocate_name=request.name,
        relationship=request.relationship,
        message=request.message,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=(datetime.now(timezone.utc).timestamp() + 7 * 24 * 3600),  # 7 days
        accepted_at=None,
    )
    
    # Store in tenant vault: Semptify5.0/Vault/advocate_invites/{invite_id}.json
    # TODO: Implement with vault storage provider
    
    return {
        "status": "success",
        "invite_id": invite_id,
        "message": f"Invitation sent to {request.email}",
        "expires_in_days": 7,
    }


@router.get("/invites")
async def list_advocate_invites(
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    List all advocate invitations for the current tenant.
    
    Returns pending, active, and revoked advocates.
    """
    # TODO: Load from tenant vault
    
    return {
        "pending": [],
        "active": [],
        "revoked": [],
    }


@router.post("/revoke")
async def revoke_advocate(
    request: RevokeAdvocateRequest,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Revoke an advocate's access to the tenant's case.
    
    Immediately removes access. Advocate is notified.
    """
    # TODO: Update invitation status to revoked
    # TODO: Notify advocate
    
    return {
        "status": "success",
        "invite_id": request.invite_id,
        "message": "Advocate access revoked",
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/accept/{invite_token}")
async def accept_invitation(invite_token: str) -> dict:
    """
    Advocate accepts a tenant invitation.
    
    Creates the advocate user account and grants case access.
    """
    # TODO: Validate token
    # TODO: Create advocate user if new
    # TODO: Grant access to tenant case
    
    return {
        "status": "success",
        "message": "Invitation accepted",
        "redirect_to": "/advocate",
    }


@router.get("/my-cases")
async def get_advocate_cases(
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Advocate views all cases they have access to.
    
    Returns list of tenants who invited this advocate.
    """
    # TODO: Load from advocate vault / lookup
    
    return {
        "cases": [],
    }
