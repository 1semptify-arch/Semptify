"""
External Timeline Client — Phase 3.2a

Read/create timeline events on behalf of an external module. Enforces
timeline.read and timeline.write permissions.
"""
import logging
from typing import List, Optional

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.permissions import Permission

logger = logging.getLogger(__name__)


class TimelineClient:
    """External module timeline access — enforces least privilege."""

    def __init__(self, ctx: ExternalModuleContext):
        self._ctx = ctx

    async def list_events(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List timeline events. Requires timeline.read."""
        self._ctx.require_permission(Permission.TIMELINE_READ.value, "list_events")
        target_user = user_id or self._ctx.user_id
        logger.info(
            "ExternalTimeline: module=%s list_events user=%s limit=%d",
            self._ctx.module_name, target_user[:6] + "...", limit,
        )
        # Delegate to internal timeline service
        from app.modules.timeline.service import list_timeline_events
        return await list_timeline_events(
            user_id=target_user,
            limit=limit,
            offset=offset,
        )

    async def create_event(
        self,
        event_type: str,
        title: str,
        description: str = "",
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Create a timeline event. Requires timeline.write."""
        self._ctx.require_permission(Permission.TIMELINE_WRITE.value, "create_event")
        target_user = user_id or self._ctx.user_id
        logger.info(
            "ExternalTimeline: module=%s create_event type=%s user=%s",
            self._ctx.module_name, event_type, target_user[:6] + "...",
        )
        from app.modules.timeline.service import create_timeline_event
        return await create_timeline_event(
            user_id=target_user,
            event_type=event_type,
            title=title,
            description=description,
            metadata=metadata or {},
            source=f"external:{self._ctx.module_name}",
        )
