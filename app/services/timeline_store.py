"""Timeline event store — rows in the tenant's vault SQLite database.

Timeline events (notices, payments, maintenance, communications, court
events, quick captures, document uploads) persist in the
``timeline_events`` table of the tenant-owned
``Semptify5.0/.semptify/vault.db`` (live-reads-retarget-sqlite; Phase-1
JSON overlays are now an export/provenance layer, not the live store).

Two bounded, idempotent import paths run on read so history is never
stranded: ``migrate_overlay_events`` copies Phase-1 TIMELINE_EVENT
overlays into SQLite (dedupe by primary key, overlay files left in
place), and ``migrate_legacy_events`` imports pre-overlay server DB rows.

Consumers (readers): unified timeline merge, tenant feed, tenant briefcase,
housing accountability, advocate/manager tenant views, workflow signals,
search, data export, eviction case builder, form data, retaliation
correlation.
Consumers (writers): document-added subscriber, quick capture, retaliation
capture, intake communication import, document timeline extraction, setup
seeding, document flow orchestrator.

View contract: functions return SimpleNamespace objects carrying the ORM
attribute surface — id, user_id, event_type, title, description,
event_date, event_date_end, event_status, parent_event_id, sequence_number,
source_extraction_id, footnote_number, highlight_color, urgency,
is_deadline, document_id, who_involved, location, attached_document_ids,
tags, is_evidence, created_at. Datetimes are `datetime` objects;
`tags`/`attached_document_ids`/`who_involved` stay raw JSON-array strings
(or None) to match the ORM contract
(`retaliation_tracker.parse_event_tags` reads them).
"""

import logging
from datetime import datetime
from types import SimpleNamespace

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.sdk.vault import (
    VaultDbError,
    mutate_remote_ensured,
    read_remote,
)
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# timeline_events columns that map to payload keys (all except id).
_EVENT_COLUMNS = (
    "event_type",
    "title",
    "description",
    "event_date",
    "event_date_end",
    "event_status",
    "parent_event_id",
    "sequence_number",
    "source_extraction_id",
    "footnote_number",
    "highlight_color",
    "urgency",
    "is_deadline",
    "is_evidence",
    "document_id",
    "who_involved",
    "location",
    "attached_document_ids",
    "tags",
)


def _anchor(effective_id: str) -> str:
    return f"timeline:{effective_id}"


def _get_storage(user: UserContext):
    """Storage provider for the current user's cloud vault."""
    return get_provider(user.provider.value, access_token=user.access_token)


async def _get_manager(user: UserContext):
    """Overlay manager — now used ONLY by the Phase-1 import path."""
    storage = _get_storage(user)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _view(row, effective_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=row["id"],
        user_id=effective_id,
        event_type=row["event_type"],
        title=row["title"],
        description=row["description"],
        event_date=_parse_dt(row["event_date"]),
        event_date_end=_parse_dt(row["event_date_end"]),
        event_status=row["event_status"],
        parent_event_id=row["parent_event_id"],
        sequence_number=row["sequence_number"] or 0,
        source_extraction_id=row["source_extraction_id"],
        footnote_number=row["footnote_number"],
        highlight_color=row["highlight_color"],
        urgency=row["urgency"] or "normal",
        is_deadline=bool(row["is_deadline"]),
        document_id=row["document_id"],
        who_involved=row["who_involved"],
        location=row["location"],
        attached_document_ids=row["attached_document_ids"],
        tags=row["tags"],
        is_evidence=bool(row["is_evidence"]),
        created_at=_parse_dt(row["created_at"]),
    )


async def _list_rows(user: UserContext) -> list:
    """All timeline_events rows for the user's vault DB (dicts)."""
    storage = _get_storage(user)

    def work(conn):
        conn.row_factory = _dict_factory
        return conn.execute("SELECT * FROM timeline_events").fetchall()

    try:
        return await read_remote(storage, work, default=[])
    except VaultDbError as e:
        logger.warning("Timeline event list failed for user %s: %s", user.user_id[:8], e)
        return []


async def list_events(user: UserContext) -> list[SimpleNamespace]:
    """All timeline events for the user, newest event_date first."""
    await migrate_legacy_events(user)
    await migrate_overlay_events(user)
    rows = await _list_rows(user)
    views = [_view(row, user.get_effective_user_id()) for row in rows]
    views.sort(key=lambda v: v.event_date or v.created_at or datetime.min, reverse=True)
    return views


async def list_events_for_user_id(user_id: str) -> list[SimpleNamespace]:
    """user_id-only reader for feed/briefcase/search/workflow/advocate/manager
    consumers. Returns [] when the user context can't be resolved."""
    try:
        user = await build_context_for_user_id(user_id)
    except Exception:
        return []
    if user is None:
        return []
    return await list_events(user)


async def count_events_for_user_id(user_id: str) -> int:
    """Count of timeline events for housing accountability / advocate / manager."""
    return len(await list_events_for_user_id(user_id))


async def create_event(user: UserContext, event_type: str, title: str, event_date: datetime | None = None, **fields) -> SimpleNamespace:
    """Create a timeline event row. `fields` accepts any column key:
    description, event_date_end, event_status, parent_event_id,
    sequence_number, source_extraction_id, footnote_number, highlight_color,
    urgency, is_deadline, is_evidence, document_id, who_involved, location,
    attached_document_ids, tags. `source_document_id` aliases to
    document_id. Keys outside the table's columns are ignored."""
    effective_id = user.get_effective_user_id()
    storage = _get_storage(user)

    if "source_document_id" in fields and "document_id" not in fields:
        fields["document_id"] = fields.pop("source_document_id")

    event_id = make_id("tevt")
    now = utc_now().isoformat()
    values = {
        "event_type": event_type,
        "title": title,
        "event_date": (event_date or utc_now()).isoformat(),
        "sequence_number": 0,
        "urgency": "normal",
        "is_deadline": 0,
        "is_evidence": 0,
    }
    for key, value in fields.items():
        if key not in _EVENT_COLUMNS:
            continue
        if isinstance(value, datetime):
            value = value.isoformat()
        elif key in ("is_deadline", "is_evidence"):
            value = int(bool(value))
        values[key] = value

    columns = list(values.keys())
    placeholders = ",".join("?" for _ in columns)

    def work(conn):
        conn.row_factory = _dict_factory
        conn.execute(
            f"INSERT INTO timeline_events (id, {', '.join(columns)}, created_at, updated_at)"  # nosec B608 — columns are whitelisted _EVENT_COLUMNS keys; placeholders are generated `?` marks; values parameterized
            f" VALUES (?, {placeholders}, ?, ?)",
            (event_id, *[values[c] for c in columns], now, now),
        )
        return conn.execute(
            "SELECT * FROM timeline_events WHERE id = ?", (event_id,)
        ).fetchone()

    try:
        row = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        raise RuntimeError(f"Failed to persist timeline event: {e}") from e
    return _view(row, effective_id)


async def find_event(
    user: UserContext,
    document_id: str | None = None,
    event_date: datetime | None = None,
    event_type: str | None = None,
) -> SimpleNamespace | None:
    """First event matching the given keys — used by document timeline
    extraction dedupe (same doc + date + type = skip)."""
    for view in await list_events(user):
        if document_id is not None and view.document_id != document_id:
            continue
        if event_type is not None and view.event_type != event_type:
            continue
        if event_date is not None and view.event_date != event_date:
            continue
        return view
    return None


# ---------------------------------------------------------------------------
# Phase-1 overlay import (non-destructive, idempotent)
# ---------------------------------------------------------------------------


def _insert_event_row(conn, event_id: str, payload: dict, fallback_created: str | None) -> bool:
    """INSERT OR IGNORE one overlay/legacy-shaped row. True if inserted."""
    now = utc_now().isoformat()
    created = payload.get("created_at") or fallback_created or now
    values = {key: payload.get(key) for key in _EVENT_COLUMNS if key in payload}
    values.setdefault("event_type", "note")
    values.setdefault("title", "")
    for flag in ("is_deadline", "is_evidence"):
        if flag in values:
            values[flag] = int(bool(values[flag]))
    for key, value in values.items():
        if isinstance(value, datetime):
            values[key] = value.isoformat()
    columns = list(values.keys())
    cur = conn.execute(
        f"INSERT OR IGNORE INTO timeline_events (id, {', '.join(columns)}, created_at, updated_at)"
        f" VALUES (?, {', '.join('?' for _ in columns)}, ?, ?)",
        (event_id, *[values[c] for c in columns], created, payload.get("updated_at") or created),
    )
    return cur.rowcount > 0


async def migrate_overlay_events(user: UserContext, limit: int = 25) -> int:
    """Import Phase-1 TIMELINE_EVENT overlays into vault SQLite.

    Bounded to ``limit`` new rows per call; idempotent via primary-key
    dedupe (the overlay payload id becomes the row id). Returns the count
    imported this call.
    """
    effective_id = user.get_effective_user_id()
    try:
        manager = await _get_manager(user)
        response = await manager.get_overlays(
            document_id=_anchor(effective_id), overlay_type=OverlayType.TIMELINE_EVENT
        )
    except Exception as e:
        logger.warning("Timeline overlay import skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not response.success:
        return 0

    owned = [
        o
        for o in response.overlays
        if o.overlay_type == OverlayType.TIMELINE_EVENT and o.created_by == effective_id
    ]
    if not owned:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM timeline_events")}
        imported = 0
        for overlay in owned:
            if imported >= limit:
                break
            rid = overlay.payload.get("id") or overlay.overlay_id
            if rid in existing:
                continue
            fallback = overlay.created_at.isoformat() if overlay.created_at else None
            if _insert_event_row(conn, rid, overlay.payload, fallback):
                imported += 1
        return imported

    try:
        imported = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Timeline overlay import failed for user %s: %s", user.user_id[:8], e)
        return 0
    if imported:
        logger.info("Imported %d timeline overlays to vault.db for user %s", imported, effective_id[:8])
    return imported


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------


async def migrate_legacy_events(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `timeline_events` server-DB rows into vault
    SQLite. Non-destructive, idempotent via primary-key dedupe."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import TimelineEvent
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(TimelineEvent).where(TimelineEvent.user_id == user.user_id).limit(limit)
            )
            rows = list(result.scalars().all())
    except Exception:
        logger.exception("Legacy timeline event read failed for user %s", user.user_id[:8])
        return 0
    if not rows:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM timeline_events")}
        imported = 0
        for row in rows:
            if imported >= limit or row.id in existing:
                continue
            if _insert_event_row(
                conn,
                row.id,
                {
                    "event_type": row.event_type,
                    "title": row.title,
                    "description": row.description,
                    "event_date": row.event_date.isoformat() if row.event_date else None,
                    "event_date_end": row.event_date_end.isoformat() if row.event_date_end else None,
                    "event_status": row.event_status,
                    "parent_event_id": row.parent_event_id,
                    "sequence_number": row.sequence_number or 0,
                    "source_extraction_id": row.source_extraction_id,
                    "footnote_number": row.footnote_number,
                    "highlight_color": row.highlight_color,
                    "urgency": row.urgency or "normal",
                    "is_deadline": bool(row.is_deadline),
                    "document_id": row.document_id,
                    "who_involved": row.who_involved,
                    "location": row.location,
                    "attached_document_ids": row.attached_document_ids,
                    "tags": row.tags,
                    "is_evidence": bool(row.is_evidence),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                },
                row.created_at.isoformat() if row.created_at else None,
            ):
                imported += 1
        return imported

    try:
        imported = await mutate_remote_ensured(storage, work)
    except VaultDbError:
        logger.exception("Legacy timeline event migration failed for user %s", user.user_id[:8])
        return 0
    return imported
