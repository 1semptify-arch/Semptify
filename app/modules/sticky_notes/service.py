"""
Sticky Notes Service
====================
Per-user scratch-pad backed by the Unified Overlay System.

Each user's notepad is a logical scratchpad (document_id="scratchpad:{user_id}")
with STICKY_NOTE overlays stored in the user's own cloud storage. No
vault-certified document is required; the scratchpad is a lightweight overlay
anchor for notes the tenant copies or types.
"""

from __future__ import annotations

import logging

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext
from app.core.vault_paths import VAULT_SCRATCHPAD_FILE
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)


def get_scratchpad_id(user_id: str) -> str:
    """Return the per-user scratchpad document_id."""
    return f"scratchpad:{user_id}"


def get_scratchpad_vault_path() -> str:
    """Return the canonical vault path used as the scratchpad anchor."""
    return VAULT_SCRATCHPAD_FILE


async def _get_overlay_manager(user: UserContext):
    """Build an overlay manager for the current user's cloud storage."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.user_id)


async def create_sticky_note(
    user: UserContext,
    text: str,
    source: str | None = None,
) -> UnifiedOverlay:
    """Create a new sticky note overlay in the user's cloud."""
    manager = await _get_overlay_manager(user)
    request = CreateOverlayRequest(
        overlay_type=OverlayType.STICKY_NOTE,
        document_id=get_scratchpad_id(user.user_id),
        vault_path=get_scratchpad_vault_path(),
        payload={
            "id": make_id("stky"),
            "text": text,
            "source": source or "",
        },
        metadata={
            "source": source or "",
            "scope": "scratchpad",
        },
    )
    response = await manager.create_overlay(request)
    if not response.success or not response.overlay_id:
        logger.error("Failed to create sticky note for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save sticky note: {response.message}")

    overlay = await manager.get_overlay(response.overlay_id)
    if overlay is None:
        raise RuntimeError("Sticky note was reported as created but cannot be retrieved")
    return overlay


async def list_sticky_notes(
    user: UserContext,
) -> list[UnifiedOverlay]:
    """Return all sticky note overlays for the user, newest first."""
    manager = await _get_overlay_manager(user)
    response = await manager.get_overlays(
        document_id=get_scratchpad_id(user.user_id),
        overlay_type=OverlayType.STICKY_NOTE,
    )
    if not response.success:
        logger.error("Failed to list sticky notes for user %s: %s", user.user_id[:8], response.filters_applied)
        return []
    return response.overlays


async def update_sticky_note(
    user: UserContext,
    overlay_id: str,
    text: str,
) -> bool:
    """Update an existing sticky note's text."""
    manager = await _get_overlay_manager(user)
    overlay = await manager.get_overlay(overlay_id)
    if not overlay:
        return False
    if overlay.created_by != user.user_id or overlay.overlay_type != OverlayType.STICKY_NOTE:
        return False

    overlay.payload["text"] = text
    return await manager.update_overlay(overlay_id, payload=overlay.payload)


async def delete_sticky_note(user: UserContext, overlay_id: str) -> bool:
    """Delete a sticky note."""
    manager = await _get_overlay_manager(user)
    overlay = await manager.get_overlay(overlay_id)
    if not overlay:
        return False
    if overlay.created_by != user.user_id or overlay.overlay_type != OverlayType.STICKY_NOTE:
        return False
    return await manager.delete_overlay(overlay_id)
