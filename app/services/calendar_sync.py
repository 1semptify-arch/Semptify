"""Calendar sync service — auto-populate CALENDAR_EVENT overlays from documents and rent ledger.

Post vault-persistence-migration: generated events are written to the user's
cloud vault via app.modules.calendar.service (same store as manual events).
The ``db`` parameter is retained for signature compatibility with existing
callers but no longer used for calendar writes.
"""

import logging
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_hub import get_document_hub
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

AUTO_SOURCES = ("document_extraction", "rent_ledger")


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a date/datetime string or object into a timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min, tzinfo=UTC)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def _event_link_key(event: dict[str, Any]) -> str:
    """Generate a stable idempotency key for a derived event."""
    return f"{event.get('type', 'event')}:{event.get('title', 'unknown')}:{event.get('date', '')}"


def _rent_link_key(entry_type: str, payment_id: str) -> str:
    return f"rent:{entry_type}:{payment_id}"


async def _sync_document_events(
    user_id: str,
    existing: set[str],
    overwrite: bool,
) -> tuple[list[str], int]:
    """Create CALENDAR_EVENT overlays from DocumentHub-derived dates."""
    from app.modules.calendar.service import create_event_for_user_id

    hub = get_document_hub()
    # Force a refresh so newly-processed documents are included.
    hub.get_case_data(user_id, force_refresh=True)
    doc_events = hub.get_calendar_events(user_id)
    created_ids: list[str] = []
    skipped = 0
    for event in doc_events:
        start = _parse_datetime(event.get("date"))
        if not start:
            skipped += 1
            continue
        link_key = _event_link_key(event)
        if not overwrite and link_key in existing:
            skipped += 1
            continue
        event_id = await create_event_for_user_id(
            user_id,
            title=event.get("title", "Document event"),
            description=event.get("description") or "Auto-synced from documents",
            start_datetime=start,
            end_datetime=None,
            all_day=True,
            event_type=event.get("type", "deadline"),
            is_critical=event.get("critical", False),
            reminder_days=7 if event.get("critical") else 3,
            source="document_extraction",
            linked_record_id=link_key,
        )
        if event_id:
            created_ids.append(event_id)
        else:
            skipped += 1
    return created_ids, skipped


async def _sync_rent_events(
    user_id: str,
    existing: set[str],
    overwrite: bool,
) -> tuple[list[str], int]:
    """Create CALENDAR_EVENT overlays from the rent ledger (vault overlays)."""
    from app.modules.calendar.service import create_event_for_user_id
    from app.modules.rent.service import list_entries_for_user_id

    overlays, _total = await list_entries_for_user_id(user_id)
    created_ids: list[str] = []
    skipped = 0

    for overlay in overlays:
        p = overlay.payload
        payment_id = p.get("id") or overlay.overlay_id
        due_date = _parse_datetime(p.get("due_date"))
        payment_date = _parse_datetime(p.get("payment_date"))
        entry_type = p.get("entry_type") or "payment"
        base_period = p.get("period_covered") or (due_date.strftime("%Y-%m") if due_date else None)

        # Rent due date from the ledger
        if due_date:
            link_key = _rent_link_key("due", payment_id)
            if not overwrite and link_key in existing:
                skipped += 1
            else:
                is_critical = p.get("status") in {"late", "missed"} or due_date < utc_now()
                event_id = await create_event_for_user_id(
                    user_id,
                    title=f"Rent due — {base_period or due_date.strftime('%Y-%m')}",
                    description="Auto-synced from rent ledger",
                    start_datetime=due_date,
                    end_datetime=None,
                    all_day=True,
                    event_type="rent_due",
                    is_critical=is_critical,
                    reminder_days=3,
                    source="rent_ledger",
                    linked_record_id=link_key,
                )
                if event_id:
                    created_ids.append(event_id)
                else:
                    skipped += 1

        # Late-fee / charge trigger date
        if entry_type in {"fee", "charge"} and (due_date or payment_date):
            trigger_date = due_date or payment_date
            link_key = _rent_link_key(entry_type, payment_id)
            if not overwrite and link_key in existing:
                skipped += 1
            else:
                label = "Late fee" if entry_type == "fee" else "Charge"
                event_id = await create_event_for_user_id(
                    user_id,
                    title=f"{label} — {base_period or trigger_date.strftime('%Y-%m')}",
                    description="Auto-synced from rent ledger",
                    start_datetime=trigger_date,
                    end_datetime=None,
                    all_day=True,
                    event_type="late_fee",
                    is_critical=True,
                    reminder_days=1,
                    source="rent_ledger",
                    linked_record_id=link_key,
                )
                if event_id:
                    created_ids.append(event_id)
                else:
                    skipped += 1

    return created_ids, skipped


async def sync_calendar_for_user(
    user_id: str,
    db: AsyncSession | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """
    Sync a user's calendar with auto-derived events.

    Sources:
    - Document extraction (hearings, answer deadlines, action items, future timeline events)
    - Rent ledger (rent due dates and late-fee / charge trigger dates)

    When ``overwrite`` is True, existing auto-synced events are cleared and
    recreated. When False, only events with a new ``linked_record_id`` are added.

    ``db`` is accepted for backward compatibility with pre-migration callers;
    calendar writes now go to the user's cloud vault, not the database.
    """
    _ = db  # legacy signature compatibility — vault path needs no session
    from app.modules.calendar.service import delete_source_events, existing_link_keys

    existing: set[str] = set()
    if overwrite:
        await delete_source_events(user_id, AUTO_SOURCES)
    else:
        existing = await existing_link_keys(user_id, AUTO_SOURCES)

    doc_ids, doc_skipped = await _sync_document_events(user_id, existing, overwrite)
    rent_ids, rent_skipped = await _sync_rent_events(user_id, existing, overwrite)

    return {
        "success": True,
        "user_id": user_id,
        "document_events": len(doc_ids),
        "document_events_skipped": doc_skipped,
        "rent_events": len(rent_ids),
        "rent_events_skipped": rent_skipped,
        "total": len(doc_ids) + len(rent_ids),
        "skipped": doc_skipped + rent_skipped,
        "synced_event_ids": doc_ids + rent_ids,
    }
