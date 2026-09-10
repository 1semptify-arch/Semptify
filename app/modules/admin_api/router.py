"""Admin API router — elevated admin operations.

These endpoints live under /admin/api and require a valid admin elevation cookie.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.admin_elevation import require_elevation
from app.core.logging_service import get_log_tail, set_log_level
from app.core.module_registry_loader import run_sync_and_verify

router = APIRouter(tags=["admin"])


@router.put("/admin/api/logs/level")
async def admin_set_log_level(level: str, admin_uid: str = Depends(require_elevation)):
    """Set the runtime root log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)."""
    return {"level": set_log_level(level)}


@router.post("/admin/api/verify")
async def admin_verify_api(admin_uid: str = Depends(require_elevation)):
    """Run sync_registry + verify_modules and return the updated registry."""
    return await run_sync_and_verify()
