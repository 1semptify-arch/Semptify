"""Judge module — DEPRECATED. Merged into Legal role as sub_role='judge'.

As of 2026-06-23, the Judge role is no longer a standalone role. Judges
are now a sub-role of Legal (legal_sub_role='judge' on User model).

This module stub remains for backward compatibility with existing
JUDGE references in services (court_learning, mndes, recognition, etc.).
Those services should migrate to checking is_legal_sub_role(user_id, 'judge')
instead of role == UserRole.JUDGE.

Do NOT add new functional endpoints here. New judge functionality should
be added to the Legal module (app/modules/legal/) with sub-role checks.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id, is_legal_sub_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/judge", tags=["Judge (Deprecated)"])


def _require_judge(user_id: str) -> None:
    """Verify the current user is a judge — either legacy JUDGE role or LEGAL with sub_role='judge'."""
    role = get_role_from_user_id(user_id)
    if role == UserRole.JUDGE:
        return  # Legacy compat
    if role == UserRole.LEGAL and is_legal_sub_role(user_id, "judge"):
        return
    if role == UserRole.ADMIN:
        return  # Admin can always access
    raise HTTPException(
        status_code=403,
        detail="Only legal users with judge sub-role can access this endpoint.",
    )


@router.get("/info")
async def judge_info(request: Request):
    """Return judge module status. Deprecated — merged into Legal sub-role."""
    user_id = require_request_user_id(request)
    _require_judge(user_id)
    return {
        "module": "judge",
        "lifecycle": "deprecated",
        "status": "merged_into_legal",
        "message": (
            "Judge role is deprecated. Judges are now a sub-role of Legal "
            "(legal_sub_role='judge'). Use /api/legal/ endpoints for new functionality."
        ),
        "sub_role_check": "is_legal_sub_role(user_id, 'judge')",
    }
