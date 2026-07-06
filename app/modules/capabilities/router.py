"""
Capabilities Module — Admin API for managing user capabilities and overlays.

Endpoints:
    GET  /api/capabilities/{user_id}          — list active modules for a user
    POST /api/capabilities/{user_id}/grant    — grant a module to a user
    POST /api/capabilities/{user_id}/revoke   — revoke a module from a user
    GET  /api/capabilities/{user_id}/overlay  — get active overlay for a user
    POST /api/capabilities/{user_id}/overlay  — attach overlay (admin hot-swap)
    DELETE /api/capabilities/{user_id}/overlay — detach overlay

All write endpoints require admin role.
GET endpoints allow self-inspection (user can read their own capabilities).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import (
    get_user_capabilities,
    grant_capability,
    revoke_capability,
    attach_overlay,
    detach_overlay,
    get_overlay_modules,
)
from app.core.database import get_db
from app.core.security import get_current_user, require_capability
from app.core.user_context import UserContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capabilities", tags=["Capabilities"])


# =============================================================================
# Schemas
# =============================================================================

class GrantRequest(BaseModel):
    module_name: str
    source: str = "admin_grant"


class RevokeRequest(BaseModel):
    module_name: str


class OverlayAttachRequest(BaseModel):
    module_names: list[str]


class CapabilityListResponse(BaseModel):
    user_id: str
    modules: list[str]
    overlay: list[str]


# =============================================================================
# Helpers
# =============================================================================

def _require_admin_or_self(requesting_user: UserContext, target_user_id: str) -> None:
    """Raise 403 if the requesting user is not admin and is not inspecting themselves."""
    if getattr(requesting_user, 'role', None) == 'admin':
        return
    if requesting_user.user_id == target_user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required to manage other users' capabilities.",
    )


def _require_admin(requesting_user: UserContext) -> None:
    if getattr(requesting_user, 'role', None) != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{user_id}", response_model=CapabilityListResponse)
async def list_capabilities(
    user_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active capabilities and overlay for a user. Self or admin only."""
    _require_admin_or_self(current_user, user_id)
    modules = await get_user_capabilities(user_id, db)
    overlay = await get_overlay_modules(user_id)
    return CapabilityListResponse(
        user_id=user_id,
        modules=sorted(modules),
        overlay=overlay,
    )


@router.post("/{user_id}/grant", status_code=status.HTTP_204_NO_CONTENT)
async def grant_module(
    user_id: str,
    body: GrantRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_capability("admin_capabilities"))
):
    """Grant a module to a user. Admin only."""
    _require_admin(current_user)
    await grant_capability(
        user_id=user_id,
        module_name=body.module_name,
        session=db,
        granted_by=current_user.user_id,
        source=body.source,
    )


@router.post("/{user_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_module(
    user_id: str,
    body: RevokeRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_capability("admin_capabilities"))
):
    """Revoke a module from a user. Admin only."""
    _require_admin(current_user)
    await revoke_capability(
        user_id=user_id,
        module_name=body.module_name,
        session=db,
        revoked_by=current_user.user_id,
    )


@router.get("/{user_id}/overlay", response_model=list[str])
async def get_overlay(
    user_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Get the active overlay module list for a user. Self or admin only."""
    _require_admin_or_self(current_user, user_id)
    return await get_overlay_modules(user_id)


@router.post("/{user_id}/overlay", status_code=status.HTTP_204_NO_CONTENT)
async def attach_overlay_endpoint(
    user_id: str,
    body: OverlayAttachRequest,
    current_user: UserContext = Depends(get_current_user),
    _ = Depends(require_capability("admin_capabilities"))
):
    """
    Attach a dev overlay to a user's session. Admin only.

    Temporarily grants access to the listed modules without modifying
    user_capabilities. Overlay lives in Redis and expires in 1 hour,
    or when explicitly detached.

    This is the hot-swap / dev-node mechanism. Add-only — cannot be used
    to remove real capabilities.
    """
    _require_admin(current_user)
    await attach_overlay(
        target_user_id=user_id,
        module_names=body.module_names,
        attached_by=current_user.user_id,
    )


@router.delete("/{user_id}/overlay", status_code=status.HTTP_204_NO_CONTENT)
async def detach_overlay_endpoint(
    user_id: str,
    current_user: UserContext = Depends(get_current_user),
    _ = Depends(require_capability("admin_capabilities"))
):
    """Detach the dev overlay from a user's session. Admin only."""
    _require_admin(current_user)
    await detach_overlay(
        target_user_id=user_id,
        detached_by=current_user.user_id,
    )
