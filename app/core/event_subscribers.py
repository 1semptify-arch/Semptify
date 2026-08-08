"""
Event Subscribers
=================

All event_bus subscriptions live here.
Called once from lifespan Stage 5 (init_services).

Rule: subscribers must never block the request that fired the event.
      All DB work runs inside the fire-and-forget async task.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _on_document_added(event: Any) -> None:
    """
    DOCUMENT_ADDED → write a TimelineEvent row so the upload appears
    on the tenant's timeline automatically.
    """
    try:
        data = event.data or {}
        user_id: str = data.get("user_id") or getattr(event, "user_id", None)
        vault_id: str = data.get("vault_id") or data.get("doc_id") or ""
        filename: str = data.get("filename") or data.get("original_filename") or "Uploaded document"
        data.get("document_type") or "document"

        if not user_id:
            logger.warning("_on_document_added: no user_id in event data, skipping")
            return

        from app.core.database import get_db_session
        from app.core.id_gen import make_id
        from app.core.utc import utc_now
        from app.models.models import TimelineEvent

        async with get_db_session() as session:
            evt = TimelineEvent(
                id=make_id("tevt"),
                user_id=user_id,
                event_type="document_uploaded",
                title=f"Document uploaded: {filename}",
                description=f"vault_id={vault_id}" if vault_id else None,
                event_date=utc_now(),
                urgency="normal",
                is_deadline=False,
                is_evidence=False,
                document_id=vault_id or None,
                source_extraction_id=None,
            )
            session.add(evt)
            await session.commit()

        logger.info("Timeline event created for document upload: %s (user=%s)", filename, user_id)

    except Exception as e:
        logger.error("_on_document_added subscriber failed: %s", e)


def register_all_subscribers() -> None:
    """
    Register all async event subscribers.
    Call this once during application startup (Stage 5).
    """
    from app.core.event_bus import EventType, subscribe_async_to_event

    subscribe_async_to_event(EventType.DOCUMENT_ADDED, _on_document_added)
    logger.info("Event subscribers registered: DOCUMENT_ADDED → timeline")
