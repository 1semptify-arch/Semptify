"""
External Overlay Client — Phase 3.2a

Read/create overlays on behalf of an external module. Enforces
overlay.read and overlay.write permissions.
"""
import logging
from typing import Any

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.permissions import Permission

logger = logging.getLogger(__name__)


class OverlayClient:
    """External module overlay access — enforces least privilege."""

    def __init__(self, ctx: ExternalModuleContext):
        self._ctx = ctx

    async def list_overlays(
        self,
        overlay_type: str | None = None,
        document_id: str | None = None,
    ) -> list[dict]:
        """List overlays. Requires overlay.read."""
        self._ctx.require_permission(Permission.OVERLAY_READ.value, "list_overlays")
        logger.info(
            "ExternalOverlay: module=%s list_overlays type=%s",
            self._ctx.module_name, overlay_type,
        )
        from app.services.unified_overlay_manager import get_overlays
        return await get_overlays(
            overlay_type=overlay_type,
            document_id=document_id,
            user_id=self._ctx.user_id,
        )

    async def create_overlay(
        self,
        overlay_type: str,
        document_id: str,
        vault_path: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        ephemeral: bool = False,
    ) -> dict:
        """Create a new overlay. Requires overlay.write."""
        self._ctx.require_permission(Permission.OVERLAY_WRITE.value, "create_overlay")
        logger.info(
            "ExternalOverlay: module=%s create_overlay type=%s doc=%s",
            self._ctx.module_name, overlay_type, document_id,
        )
        from app.services.unified_overlay_manager import create_overlay
        return await create_overlay(
            overlay_type=overlay_type,
            document_id=document_id,
            vault_path=vault_path,
            payload=payload,
            metadata=metadata or {},
            ephemeral=ephemeral,
            user_id=self._ctx.user_id,
        )

    async def update_overlay(self, overlay_id: str, payload: dict[str, Any]) -> dict:
        """Update an existing overlay. Requires overlay.write."""
        self._ctx.require_permission(Permission.OVERLAY_WRITE.value, "update_overlay")
        logger.info(
            "ExternalOverlay: module=%s update_overlay id=%s",
            self._ctx.module_name, overlay_id,
        )
        from app.services.unified_overlay_manager import update_overlay
        return await update_overlay(overlay_id=overlay_id, payload=payload)

    async def delete_overlay(self, overlay_id: str) -> bool:
        """Delete an overlay. Requires overlay.write."""
        self._ctx.require_permission(Permission.OVERLAY_WRITE.value, "delete_overlay")
        logger.info(
            "ExternalOverlay: module=%s delete_overlay id=%s",
            self._ctx.module_name, overlay_id,
        )
        from app.services.unified_overlay_manager import delete_overlay
        return await delete_overlay(overlay_id=overlay_id)
