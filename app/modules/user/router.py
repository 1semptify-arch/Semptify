"""
User module router — role hierarchy and impersonation endpoints.

Endpoints:
- POST /api/user/act-as   — Start impersonating another user (admin/advocate only)
- DELETE /api/user/act-as — Stop impersonating
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.database import get_db_session
from app.core.security import can_access, get_current_user, update_session_impersonation
from app.core.user_context import UserContext, UserRole

router = APIRouter()


class ActAsRequest(BaseModel):
    target_user_id: str
    reason: str = ""


@router.post("/api/user/act-as")
async def start_acting_as(
    request: Request,
    body: ActAsRequest,
    semptify_session: str | None = Cookie(None),
    current_user: UserContext | None = Depends(get_current_user),
):
    """
    Start impersonating another user.

    Only admin and advocate roles may impersonate.
    A valid relationship must exist in the user_relationships table.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Only admin and advocate may act-as
    if current_user.role not in (UserRole.ADMIN, UserRole.ADVOCATE):
        raise HTTPException(status_code=403, detail="Only admin or advocate may act on behalf of another user")

    # Need a session cookie to update impersonation state
    if not semptify_session:
        raise HTTPException(status_code=400, detail="Session cookie required")

    # Verify relationship exists
    async with get_db_session() as db:
        allowed = await can_access(
            from_user_id=current_user.user_id,
            to_user_id=body.target_user_id,
            db=db,
        )

    if not allowed:
        raise HTTPException(status_code=403, detail="No active relationship permits acting on behalf of this user")

    # Set impersonation state on the stored session
    session = update_session_impersonation(
        session_id=semptify_session,
        acting_as=body.target_user_id,
        acting_as_role="tenant",  # Default to tenant when acting on behalf
    )

    if not session:
        raise HTTPException(status_code=400, detail="Session not found — cannot set impersonation")

    return {
        "success": True,
        "acting_as": body.target_user_id,
        "original_user": current_user.user_id,
        "reason": body.reason,
    }


@router.delete("/api/user/act-as")
async def stop_acting_as(
    semptify_session: str | None = Cookie(None),
    current_user: UserContext | None = Depends(get_current_user),
):
    """Clear impersonation and return to original user context."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not semptify_session:
        raise HTTPException(status_code=400, detail="Session cookie required")

    if not current_user.is_impersonating:
        return {"success": True, "message": "Not impersonating — no action taken"}

    session = update_session_impersonation(
        session_id=semptify_session,
        acting_as=None,
        acting_as_role=None,
    )

    if not session:
        raise HTTPException(status_code=400, detail="Session not found")

    return {
        "success": True,
        "message": "Impersonation cleared",
        "restored_user": current_user.user_id,
    }


# =============================================================================
# Module Contracts — SSOT signatures, visible in admin contract browser
# =============================================================================

try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(
        FunctionGroupContract(
            module="user",
            group_name="act_as_start",
            title="Start Acting As Role (SSOT)",
            description=(
                "CANONICAL role impersonation via POST /api/user/act-as. "
                "Allows admin/manager to act as another role for testing. "
                "Sets acting_as and acting_as_role on stored session."
            ),
            inputs=("role", "reason", "septify_session", "user_id"),
            outputs=("acting_as", "acting_as_role"),
            dependencies=(
                "app.modules.user.router",
                "app.core.security.can_access",
            ),
            deterministic=True,
        )
    )

    register_function_group(
        FunctionGroupContract(
            module="user",
            group_name="act_as_stop",
            title="Stop Acting As Role (SSOT)",
            description=(
                "CANONICAL stop impersonation via DELETE /api/user/act-as. "
                "Clears acting_as and acting_as_role from stored session."
            ),
            inputs=("septify_session", "user_id"),
            outputs=("status",),
            dependencies=("app.modules.user.router",),
            deterministic=True,
        )
    )

except Exception:
    pass
