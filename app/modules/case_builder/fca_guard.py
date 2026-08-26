"""Feature-gate and allowlist guard for the FCA/Qui Tam readiness workflow.

This guard is applied to every FCA endpoint and to the rendered page route.
It returns a 404 (not 403) so the feature stays invisible when disabled.
"""

from fastapi import Depends, HTTPException, status

from app.core.config import get_settings
from app.core.features import Feature, features
from app.core.security import StorageUser, yellow_access


async def is_fca_readiness_visible(user_id: str) -> bool:
    """Return True if the FCA readiness feature is visible for this user."""
    if not await features.is_enabled(Feature.FCA_READINESS):
        return False

    settings = get_settings()
    allowed = settings.fca_readiness_allowed_user_ids
    if allowed and user_id not in allowed:
        return False

    return True


async def require_fca_readiness(user: StorageUser = Depends(yellow_access)) -> StorageUser:
    """Require the FCA readiness feature flag and optional user allowlist."""
    if not await is_fca_readiness_visible(user.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    return user
