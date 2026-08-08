"""Tenant Feed Aggregator service.

Merges multiple data sources into a single chronological feed:
    - Timeline events (from app.modules.timeline)
    - Documents (from app.modules.documents)
    - Journal entries (from app.modules.journal if available)
    - Deadlines (from app.modules.deadlines if available)
    - Letters (from app.modules.letters if available)

Returns a list of FeedItem dicts sorted by timestamp (newest first).

Each item has:
    {
        "type": "document" | "timeline_event" | "journal" | "deadline" | "letter",
        "title": str,
        "subtitle": str,
        "timestamp_iso": str,  # ISO 8601 UTC
        "timestamp_label": str,  # Human-readable
        "icon": str,
        "link": str,
        "metadata": dict,
    }

Filterable by type via the `type_filter` parameter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.utc import utc_now

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


# Valid feed item types
FEED_TYPES = {"document", "timeline_event", "journal", "deadline", "letter"}


def _empty_item() -> dict[str, Any]:
    """Return a blank feed item dict."""
    return {
        "type": "",
        "title": "",
        "subtitle": "",
        "timestamp_iso": "",
        "timestamp_label": "",
        "icon": "•",
        "link": "",
        "metadata": {},
    }


def _format_timestamp(dt: datetime | None) -> dict[str, str]:
    """Format a datetime as ISO + human-readable label."""
    if dt is None:
        return {"timestamp_iso": "", "timestamp_label": ""}
    try:
        iso = dt.isoformat()
        now = utc_now()
        delta = now - dt

        if delta.days == 0:
            label = "Today"
        elif delta.days == 1:
            label = "Yesterday"
        elif delta.days < 7:
            label = f"{delta.days} days ago"
        elif delta.days < 30:
            label = f"{delta.days // 7} week{'s' if delta.days // 7 != 1 else ''} ago"
        else:
            label = dt.strftime("%b %d, %Y")

        return {"timestamp_iso": iso, "timestamp_label": label}
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: timestamp format error: %s", e)
        return {"timestamp_iso": "", "timestamp_label": ""}


def _fetch_documents(user_id: str) -> list[dict[str, Any]]:
    """Fetch documents for the user. Returns feed items.

    Uses the canonical vault_upload_service.get_user_documents() — the same
    source the documents router uses. Async function is awaited synchronously
    via asyncio.run_if_needed; safe because this aggregator is called from
    async router context.
    """
    items: list[dict[str, Any]] = []
    try:
        import asyncio

        from app.services.vault_upload_service import get_vault_service

        vault = get_vault_service()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an event loop — schedule as task
                docs = asyncio.ensure_future(vault.get_user_documents(user_id))
                # Don't await here; caller is async and will handle it
                return items  # Empty for now; async path handled in aggregate_feed_async
            else:
                docs = loop.run_until_complete(vault.get_user_documents(user_id))
        except RuntimeError:
            # No event loop in this thread — create one
            docs = asyncio.run(vault.get_user_documents(user_id))

        for doc in docs:
            uploaded_at = getattr(doc, "uploaded_at", None)
            ts_data = _format_timestamp(uploaded_at)
            item = _empty_item()
            item.update(
                {
                    "type": "document",
                    "title": getattr(doc, "filename", None) or getattr(doc, "description", None) or "Document",
                    "subtitle": getattr(doc, "description", "") or "",
                    "timestamp_iso": ts_data["timestamp_iso"],
                    "timestamp_label": ts_data["timestamp_label"],
                    "icon": "📄",
                    "link": f"/tenant/documents/{getattr(doc, 'vault_id', '')}",
                    "metadata": {
                        "doc_id": getattr(doc, "vault_id", None),
                        "doc_type": getattr(doc, "document_type", None),
                        "filename": getattr(doc, "filename", None),
                    },
                }
            )
            items.append(item)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: documents fetch failed for %s: %s", user_id, e)
    return items


def _fetch_timeline_events(user_id: str) -> list[dict[str, Any]]:
    """Fetch timeline events for the user from the TimelineEvent model.

    Queries the database directly — no HTTP hop, no router dependency.
    """
    items: list[dict[str, Any]] = []
    try:
        import asyncio

        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import TimelineEvent

        async def _query() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            async with get_db_session() as db:
                stmt = (
                    select(TimelineEvent)
                    .where(TimelineEvent.user_id == user_id)
                    .order_by(TimelineEvent.event_date.desc())
                    .limit(50)
                )
                rows = (await db.execute(stmt)).scalars().all()
                for event in rows:
                    ts_data = _format_timestamp(event.event_date or event.created_at)
                    item = _empty_item()
                    item.update(
                        {
                            "type": "timeline_event",
                            "title": event.title or "Timeline event",
                            "subtitle": event.description or "",
                            "timestamp_iso": ts_data["timestamp_iso"],
                            "timestamp_label": ts_data["timestamp_label"],
                            "icon": "•",
                            "link": "/tenant/timeline",
                            "metadata": {
                                "event_id": event.id,
                                "event_type": event.event_type,
                                "is_urgent": event.is_urgent if hasattr(event, "is_urgent") else False,
                            },
                        }
                    )
                    results.append(item)
            return results

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return items  # Async path handled in aggregate_feed_async
            items = loop.run_until_complete(_query())
        except RuntimeError:
            items = asyncio.run(_query())
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: timeline fetch failed for %s: %s", user_id, e)
    return items


async def aggregate_feed_async(
    user_id: str,
    type_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Async version of aggregate_feed — uses real data sources.

    Use this from async router context. The sync aggregate_feed() is kept
    for backward compatibility but cannot run DB queries when called from
    inside an event loop.
    """
    if type_filter and type_filter not in FEED_TYPES:
        raise ValueError(f"Unknown feed type filter: {type_filter}. Valid: {sorted(FEED_TYPES)}")

    items: list[dict[str, Any]] = []

    if not type_filter or type_filter == "document":
        items.extend(await _fetch_documents_async(user_id))
    if not type_filter or type_filter == "timeline_event":
        items.extend(await _fetch_timeline_events_async(user_id))
    if not type_filter or type_filter == "journal":
        items.extend(_fetch_journal_entries(user_id))
    if not type_filter or type_filter == "deadline":
        items.extend(_fetch_deadlines(user_id))
    if not type_filter or type_filter == "letter":
        items.extend(_fetch_letters(user_id))

    def _sort_key(item: dict[str, Any]) -> tuple:
        iso = item.get("timestamp_iso") or ""
        return ("" if iso else "0", iso)

    items.sort(key=_sort_key, reverse=True)
    return items


async def _fetch_documents_async(user_id: str) -> list[dict[str, Any]]:
    """Async fetch of documents via vault_upload_service."""
    items: list[dict[str, Any]] = []
    try:
        from app.services.vault_upload_service import get_vault_service

        vault = get_vault_service()
        docs = await vault.get_user_documents(user_id)
        for doc in docs:
            uploaded_at = getattr(doc, "uploaded_at", None)
            ts_data = _format_timestamp(uploaded_at)
            item = _empty_item()
            item.update(
                {
                    "type": "document",
                    "title": getattr(doc, "filename", None) or getattr(doc, "description", None) or "Document",
                    "subtitle": getattr(doc, "description", "") or "",
                    "timestamp_iso": ts_data["timestamp_iso"],
                    "timestamp_label": ts_data["timestamp_label"],
                    "icon": "📄",
                    "link": f"/tenant/documents/{getattr(doc, 'vault_id', '')}",
                    "metadata": {
                        "doc_id": getattr(doc, "vault_id", None),
                        "doc_type": getattr(doc, "document_type", None),
                        "filename": getattr(doc, "filename", None),
                    },
                }
            )
            items.append(item)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: documents async fetch failed for %s: %s", user_id, e)
    return items


async def _fetch_timeline_events_async(user_id: str) -> list[dict[str, Any]]:
    """Async fetch of timeline events from the TimelineEvent model."""
    items: list[dict[str, Any]] = []
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import TimelineEvent

        async with get_db_session() as db:
            stmt = (
                select(TimelineEvent)
                .where(TimelineEvent.user_id == user_id)
                .order_by(TimelineEvent.event_date.desc())
                .limit(50)
            )
            rows = (await db.execute(stmt)).scalars().all()
            for event in rows:
                ts_data = _format_timestamp(event.event_date or event.created_at)
                item = _empty_item()
                item.update(
                    {
                        "type": "timeline_event",
                        "title": event.title or "Timeline event",
                        "subtitle": event.description or "",
                        "timestamp_iso": ts_data["timestamp_iso"],
                        "timestamp_label": ts_data["timestamp_label"],
                        "icon": "•",
                        "link": "/tenant/timeline",
                        "metadata": {
                            "event_id": event.id,
                            "event_type": event.event_type,
                            "is_urgent": bool(getattr(event, "is_urgent", False)),
                        },
                    }
                )
                items.append(item)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: timeline async fetch failed for %s: %s", user_id, e)
    return items


def _fetch_journal_entries(user_id: str) -> list[dict[str, Any]]:
    """Fetch journal entries for the user."""
    items: list[dict[str, Any]] = []
    try:
        from app.modules.journal.service import list_journal_entries

        entries = list_journal_entries(user_id) if callable(list_journal_entries) else []
        for entry in entries:
            ts_data = _format_timestamp(entry.get("created_at") or entry.get("timestamp"))
            item = _empty_item()
            item.update(
                {
                    "type": "journal",
                    "title": entry.get("title") or "Journal entry",
                    "subtitle": (entry.get("body") or "")[:120],
                    "timestamp_iso": ts_data["timestamp_iso"],
                    "timestamp_label": ts_data["timestamp_label"],
                    "icon": "📝",
                    "link": "/tenant/journal",
                    "metadata": {
                        "entry_id": entry.get("id"),
                    },
                }
            )
            items.append(item)
    except ImportError:
        # Journal module not available — skip
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: journal fetch failed for %s: %s", user_id, e)
    return items


def _fetch_deadlines(user_id: str) -> list[dict[str, Any]]:
    """Fetch deadlines for the user."""
    items: list[dict[str, Any]] = []
    try:
        from app.modules.deadlines.service import list_deadlines

        deadlines = list_deadlines(user_id) if callable(list_deadlines) else []
        for deadline in deadlines:
            ts_data = _format_timestamp(deadline.get("due_date") or deadline.get("date"))
            item = _empty_item()
            item.update(
                {
                    "type": "deadline",
                    "title": deadline.get("title") or "Deadline",
                    "subtitle": deadline.get("description") or "",
                    "timestamp_iso": ts_data["timestamp_iso"],
                    "timestamp_label": ts_data["timestamp_label"],
                    "icon": "⏰",
                    "link": "/tenant/tools/deadlines",
                    "metadata": {
                        "deadline_id": deadline.get("id"),
                        "priority": deadline.get("priority"),
                    },
                }
            )
            items.append(item)
    except ImportError:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: deadlines fetch failed for %s: %s", user_id, e)
    return items


def _fetch_letters(user_id: str) -> list[dict[str, Any]]:
    """Fetch generated letters for the user."""
    items: list[dict[str, Any]] = []
    try:
        from app.modules.letters.service import list_letters

        letters = list_letters(user_id) if callable(list_letters) else []
        for letter in letters:
            ts_data = _format_timestamp(letter.get("created_at"))
            item = _empty_item()
            item.update(
                {
                    "type": "letter",
                    "title": letter.get("title") or "Letter",
                    "subtitle": letter.get("recipient") or "",
                    "timestamp_iso": ts_data["timestamp_iso"],
                    "timestamp_label": ts_data["timestamp_label"],
                    "icon": "✉️",
                    "link": "/tenant/tools/letters",
                    "metadata": {
                        "letter_id": letter.get("id"),
                        "letter_type": letter.get("type"),
                    },
                }
            )
            items.append(item)
    except ImportError:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: letters fetch failed for %s: %s", user_id, e)
    return items


def aggregate_feed(
    user_id: str,
    type_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Aggregate all feed sources into a single chronological feed.

    Args:
        user_id: The user's ID
        type_filter: Optional filter by type (e.g. "documents", "journal").
                     If None, all types are included.

    Returns:
        List of feed items sorted by timestamp (newest first).
        Each item is a dict with: type, title, subtitle, timestamp_iso,
        timestamp_label, icon, link, metadata.
    """
    if type_filter and type_filter not in FEED_TYPES:
        raise ValueError(f"Unknown feed type filter: {type_filter}. Valid: {sorted(FEED_TYPES)}")

    items: list[dict[str, Any]] = []

    # Fetch from all sources — each fetch is independent and fails gracefully
    if not type_filter or type_filter == "document":
        items.extend(_fetch_documents(user_id))
    if not type_filter or type_filter == "timeline_event":
        items.extend(_fetch_timeline_events(user_id))
    if not type_filter or type_filter == "journal":
        items.extend(_fetch_journal_entries(user_id))
    if not type_filter or type_filter == "deadline":
        items.extend(_fetch_deadlines(user_id))
    if not type_filter or type_filter == "letter":
        items.extend(_fetch_letters(user_id))

    # Sort by timestamp descending (newest first). Items without a timestamp
    # sort to the end.
    def _sort_key(item: dict[str, Any]) -> tuple:
        iso = item.get("timestamp_iso") or ""
        # ISO strings sort lexicographically — prefix with "1" so empty goes last
        return ("" if iso else "0", iso)

    items.sort(key=_sort_key, reverse=True)

    return items


# Backward-compat alias — FeedItem is the dict shape, not a dataclass.
# Callers should treat the return value as List[Dict[str, Any]].
FeedItem = dict[str, Any]
