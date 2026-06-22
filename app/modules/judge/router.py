"""Judge module router — dev_only placeholder.

This module is intentionally minimal. It exists only so the admin module-flags
UI can display the judge role as 'in development' (dev_only lifecycle).

Do NOT add functional endpoints here without explicit project-owner approval.
The judge role is read-only by design (see user_context.py JUDGE role).
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.request_utils import require_request_user_id
from app.core.user_context import get_role_from_user_id, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/judge", tags=["Judge"])


def _require_judge(user_id: str) -> None:
    role = get_role_from_user_id(user_id)
    if role not in (UserRole.JUDGE, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Only judge or admin roles can access this endpoint.",
        )


@router.get("/info")
async def judge_info(request: Request):
    """Return judge module status. Dev_only — not for active use."""
    user_id = require_request_user_id(request)
    _require_judge(user_id)
    return {
        "module": "judge",
        "lifecycle": "dev_only",
        "status": "placeholder",
        "message": "Judge module is in development. No functional endpoints available.",
    }
