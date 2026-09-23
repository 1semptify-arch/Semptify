"""
Semptify 5.0 - Role Upgrade API
Allows users to request elevated roles with verification.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.core.role_validation import (
    VerificationStatus,
    get_role_validator,
)
from app.core.security import get_current_user
from app.core.user_context import UserContext, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roles", tags=["Role Management"])


# =============================================================================
# Request Models
# =============================================================================


class RoleUpgradeRequest(BaseModel):
    """Request to upgrade to an elevated role."""

    requested_role: str  # "advocate" or "legal"
    email: str | None = None
    bar_number: str | None = None
    hud_cert_number: str | None = None
    invite_code: str | None = None
    attestation: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"requested_role": "advocate", "email": "counselor@homeline.org", "invite_code": "EXAMPLE-ADVOCATE-CODE"}
        }
    )


class RoleRequirementsResponse(BaseModel):
    """Requirements for a specific role."""

    role: str
    name: str
    requirements: str
    verification_options: list
    warning: str | None = None


class RoleVerificationResponse(BaseModel):
    """Response from role verification request."""

    success: bool
    status: str
    role: str
    method: str
    message: str
    next_steps: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/available")
async def get_available_roles():
    """
    Get all available roles and their requirements.
    """
    # ONBOARDING SOLO (Brad, 2026-09-23): tenant is the only role in this
    # repo. Professional roles are not advertised — they onboard via a
    # separate add-on repo, not through this endpoint.
    return {
        "roles": [
            {
                "role": "tenant",
                "name": "Tenant",
                "requirements": "Connect a cloud storage provider.",
                "verification_options": [],
                "warning": None,
                "self_service": True,
            }
        ],
        "note": "Tenant is the only role.",
    }


@router.get("/requirements/{role}")
async def get_role_requirements(role: str):
    """
    Get detailed requirements for a specific role.
    """
    # ONBOARDING SOLO: tenant is the only role — anything else does not exist.
    if role.lower() not in ("tenant", "user"):
        raise HTTPException(status_code=404, detail="Not Found")

    return RoleRequirementsResponse(
        role="tenant",
        name="Tenant",
        requirements="Connect a cloud storage provider.",
        verification_options=[],
        warning=None,
    )


@router.post("/upgrade")
async def request_role_upgrade(request: RoleUpgradeRequest, user: UserContext | None = Depends(get_current_user)):
    """
    Request an upgrade to an elevated role.

    Verification methods (in order of trust):
    1. Partner invite code
    2. Trusted organization email domain
    3. MN Bar number (for attorney role)
    4. HUD certification number (for advocate role)
    5. Self-attestation (creates audit trail)
    """
    validator = get_role_validator()

    # ONBOARDING SOLO (Brad, 2026-09-23): tenant is the only role in this
    # repo — there is no upgrade target and no elevation path at all.
    if request.requested_role.lower() not in ("tenant", "user"):
        raise HTTPException(status_code=404, detail="Not Found")

    requested_role = UserRole.USER

    # Get user ID (from session or generate temp)
    user_id = user.user_id if user else "temp_" + str(hash(request.email or "anon"))[:8]

    # Perform verification
    verification = validator.validate_for_role(
        user_id=user_id,
        requested_role=requested_role,
        email=request.email,
        bar_number=request.bar_number,
        hud_cert_number=request.hud_cert_number,
        invite_code=request.invite_code,
        attestation=request.attestation,
    )

    # Build response
    if verification.status == VerificationStatus.VERIFIED:
        return RoleVerificationResponse(
            success=True,
            status="verified",
            role=requested_role.value,
            method=verification.method.value,
            message=f"✅ Role upgrade approved! You now have {requested_role.value} access.",
            next_steps="Refresh the page to access your new dashboard.",
        )

    elif verification.status == VerificationStatus.PENDING:
        return RoleVerificationResponse(
            success=False,
            status="pending",
            role=requested_role.value,
            method=verification.method.value,
            message="⏳ Your request is pending manual review.",
            next_steps=(
                "An administrator will review your request within 1-2 business days. "
                "You'll receive an email when approved."
            ),
        )

    else:  # REJECTED
        return RoleVerificationResponse(
            success=False,
            status="rejected",
            role=requested_role.value,
            method=verification.method.value,
            message=f"❌ Verification failed: {verification.notes}",
            next_steps=(
                "Please verify your credentials and try again, or contact support if you believe this is an error."
            ),
        )


@router.get("/my-role")
async def get_my_role(user: UserContext | None = Depends(get_current_user)):
    """
    Get current user's role and permissions.
    """
    if not user:
        return {
            "role": "user",
            "display_name": "Tenant",
            "permissions": [],
            "verified": False,
            "message": "Not logged in. Default tenant role applies.",
        }

    validator = get_role_validator()
    requirements = validator.get_role_requirements(user.role)

    return {
        "role": user.role.value,
        "display_name": requirements.get("name", user.role.value),
        "permissions": list(user.permissions),
        "verified": True,
        "storage_provider": user.provider.value if user.provider else None,
    }


@router.get("/trusted-organizations")
async def get_trusted_organizations():
    """
    ONBOARDING SOLO: no elevated roles exist in this repo, so there are no
    trusted verification domains to advertise. Kept (empty) for API
    compatibility with dormant pro-role modules.
    """
    return {"advocate_domains": [], "legal_domains": [], "note": "Tenant is the only role."}
