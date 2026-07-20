"""Calendar sync service — auto-populate CalendarEvent rows from documents and rent ledger."""

import logging
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.document_hub import get_document_hub
from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.models.models import CalendarEvent as CalendarEventModel, RentPayment

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


async def _existing_auto_keys(db: AsyncSession, user_id: str) -> set[str]:
    """Return the set of linked_record_id values already stored for auto sources."""
    result = await db.execute(
        select(CalendarEventModel.linked_record_id).where(
            CalendarEventModel.user_id == user_id,
            CalendarEventModel.source.in_(AUTO_SOURCES),
            CalendarEventModel.linked_record_id.is_not(None),
        )
    )
    return {row[0] for row in result.fetchall() if row[0]}


async def _clear_auto_events(db: AsyncSession, user_id: str) -> None:
    """Remove prior auto-synced calendar events for a user."""
    await db.execute(
        delete(CalendarEventModel).where(
            CalendarEventModel.user_id == user_id,
            CalendarEventModel.source.in_(AUTO_SOURCES),
        )
    )


async def _sync_document_events(
    db: AsyncSession,
    user_id: str,
    existing: set[str],
    overwrite: bool,
) -> tuple[list[str], int]:
    """Create CalendarEvent rows from DocumentHub-derived dates."""
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
        event_id = make_id("cal")
        db.add(
            CalendarEventModel(
                id=event_id,
                user_id=user_id,
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
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        created_ids.append(event_id)
    return created_ids, skipped


async def _sync_rent_events(
    db: AsyncSession,
    user_id: str,
    existing: set[str],
    overwrite: bool,
) -> tuple[list[str], int]:
    """Create CalendarEvent rows from the rent ledger."""
    result = await db.execute(select(RentPayment).where(RentPayment.user_id == user_id))
    payments = result.scalars().all()
    created_ids: list[str] = []
    skipped = 0

    for payment in payments:
        base_period = payment.period_covered or (payment.due_date.strftime("%Y-%m") if payment.due_date else None)

        # Rent due date from the ledger
        if payment.due_date:
            link_key = _rent_link_key("due", payment.id)
            if not overwrite and link_key in existing:
                skipped += 1
            else:
                is_critical = payment.status in {"late", "missed"} or payment.due_date < utc_now()
                event_id = make_id("cal")
                db.add(
                    CalendarEventModel(
                        id=event_id,
                        user_id=user_id,
                        title=f"Rent due — {base_period or payment.due_date.strftime('%Y-%m')}",
                        description="Auto-synced from rent ledger",
                        start_datetime=payment.due_date,
                        end_datetime=None,
                        all_day=True,
                        event_type="rent_due",
                        is_critical=is_critical,
                        reminder_days=3,
                        source="rent_ledger",
                        linked_record_id=link_key,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
                created_ids.append(event_id)

        # Late-fee / charge trigger date
        if payment.entry_type in {"fee", "charge"} and (payment.due_date or payment.payment_date):
            trigger_date = payment.due_date or payment.payment_date
            link_key = _rent_link_key(payment.entry_type, payment.id)
            if not overwrite and link_key in existing:
                skipped += 1
            else:
                event_id = make_id("cal")
                label = "Late fee" if payment.entry_type == "fee" else "Charge"
                db.add(
                    CalendarEventModel(
                        id=event_id,
                        user_id=user_id,
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
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
                created_ids.append(event_id)

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
    """
    if db is None:
        async with get_db_session() as session:
            return await sync_calendar_for_user(user_id, session, overwrite)

    existing: set[str] = set()
    if overwrite:
        await _clear_auto_events(db, user_id)
    else:
        existing = await _existing_auto_keys(db, user_id)

    doc_ids, doc_skipped = await _sync_document_events(db, user_id, existing, overwrite)
    rent_ids, rent_skipped = await _sync_rent_events(db, user_id, existing, overwrite)

    if doc_ids or rent_ids or overwrite:
        await db.commit()

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
