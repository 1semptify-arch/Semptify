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
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


# Valid feed item types
FEED_TYPES = {"document", "timeline_event", "journal", "deadline", "letter"}


def _empty_item() -> Dict[str, Any]:
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


def _format_timestamp(dt: Optional[datetime]) -> Dict[str, str]:
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


def _fetch_documents(user_id: str) -> List[Dict[str, Any]]:
    """Fetch documents for the user. Returns feed items.

    Calls the documents service directly (sync) — no HTTP hop.
    """
    items: List[Dict[str, Any]] = []
    try:
        # Import lazily so a failure doesn't break the whole feed
        from app.modules.documents.service import list_user_documents
        docs = list_user_documents(user_id) if hasattr(
            list_user_documents, "__call__"
        ) else []
        for doc in docs:
            ts_data = _format_timestamp(doc.get("created_at") or doc.get("uploaded_at"))
            item = _empty_item()
            item.update({
                "type": "document",
                "title": doc.get("title") or doc.get("filename") or "Document",
                "subtitle": doc.get("summary") or doc.get("category") or "",
                "timestamp_iso": ts_data["timestamp_iso"],
                "timestamp_label": ts_data["timestamp_label"],
                "icon": "📄",
                "link": f"/tenant/documents/{doc.get('id', '')}",
                "metadata": {
                    "doc_id": doc.get("id"),
                    "category": doc.get("category"),
                    "filename": doc.get("filename"),
                },
            })
            items.append(item)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: documents fetch failed for %s: %s", user_id, e)
    return items


def _fetch_timeline_events(user_id: str) -> List[Dict[str, Any]]:
    """Fetch timeline events for the user."""
    items: List[Dict[str, Any]] = []
    try:
        from app.modules.timeline.service import list_timeline_events
        events = list_timeline_events(user_id) if hasattr(
            list_timeline_events, "__call__"
        ) else []
        for event in events:
            ts_data = _format_timestamp(event.get("timestamp") or event.get("created_at"))
            item = _empty_item()
            item.update({
                "type": "timeline_event",
                "title": event.get("title") or "Timeline event",
                "subtitle": event.get("description") or "",
                "timestamp_iso": ts_data["timestamp_iso"],
                "timestamp_label": ts_data["timestamp_label"],
                "icon": event.get("icon") or "•",
                "link": "/tenant/timeline",
                "metadata": {
                    "event_id": event.get("id"),
                    "event_type": event.get("type"),
                },
            })
            items.append(item)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: timeline fetch failed for %s: %s", user_id, e)
    return items


def _fetch_journal_entries(user_id: str) -> List[Dict[str, Any]]:
    """Fetch journal entries for the user."""
    items: List[Dict[str, Any]] = []
    try:
        from app.modules.journal.service import list_journal_entries
        entries = list_journal_entries(user_id) if hasattr(
            list_journal_entries, "__call__"
        ) else []
        for entry in entries:
            ts_data = _format_timestamp(entry.get("created_at") or entry.get("timestamp"))
            item = _empty_item()
            item.update({
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
            })
            items.append(item)
    except ImportError:
        # Journal module not available — skip
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: journal fetch failed for %s: %s", user_id, e)
    return items


def _fetch_deadlines(user_id: str) -> List[Dict[str, Any]]:
    """Fetch deadlines for the user."""
    items: List[Dict[str, Any]] = []
    try:
        from app.modules.deadlines.service import list_deadlines
        deadlines = list_deadlines(user_id) if hasattr(
            list_deadlines, "__call__"
        ) else []
        for deadline in deadlines:
            ts_data = _format_timestamp(deadline.get("due_date") or deadline.get("date"))
            item = _empty_item()
            item.update({
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
            })
            items.append(item)
    except ImportError:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: deadlines fetch failed for %s: %s", user_id, e)
    return items


def _fetch_letters(user_id: str) -> List[Dict[str, Any]]:
    """Fetch generated letters for the user."""
    items: List[Dict[str, Any]] = []
    try:
        from app.modules.letters.service import list_letters
        letters = list_letters(user_id) if hasattr(
            list_letters, "__call__"
        ) else []
        for letter in letters:
            ts_data = _format_timestamp(letter.get("created_at"))
            item = _empty_item()
            item.update({
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
            })
            items.append(item)
    except ImportError:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Feed: letters fetch failed for %s: %s", user_id, e)
    return items


def aggregate_feed(
    user_id: str,
    type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
        raise ValueError(
            f"Unknown feed type filter: {type_filter}. Valid: {sorted(FEED_TYPES)}"
        )

    items: List[Dict[str, Any]] = []

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
    def _sort_key(item: Dict[str, Any]) -> tuple:
        iso = item.get("timestamp_iso") or ""
        # ISO strings sort lexicographically — prefix with "1" so empty goes last
        return ("" if iso else "0", iso)

    items.sort(key=_sort_key, reverse=True)

    return items


# Backward-compat alias — FeedItem is the dict shape, not a dataclass.
# Callers should treat the return value as List[Dict[str, Any]].
FeedItem = Dict[str, Any]
