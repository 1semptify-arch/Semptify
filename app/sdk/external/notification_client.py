"""
External Notification Client — Phase 3.2a

Send notifications to users on behalf of an external module. Enforces
notification.send permission. All notifications are audited with the
originating module name.
"""

import logging

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.permissions import Permission

logger = logging.getLogger(__name__)


class NotificationClient:
    """External module notification access — enforces least privilege."""

    def __init__(self, ctx: ExternalModuleContext):
        self._ctx = ctx

    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        category: str = "external_module",
        action_url: str | None = None,
    ) -> dict:
        """Send a notification to a user. Requires notification.send."""
        self._ctx.require_permission(Permission.NOTIFICATION_SEND.value, "send_notification")
        logger.info(
            "ExternalNotification: module=%s send to user=%s title=%s",
            self._ctx.module_name,
            user_id[:6] + "...",
            title,
        )
        from app.modules.communication.service import send_notification

        return await send_notification(
            user_id=user_id,
            title=title,
            body=body,
            category=category,
            action_url=action_url,
            source=f"external:{self._ctx.module_name}:{self._ctx.vendor}",
        )
