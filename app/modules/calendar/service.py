"""
Calendar Service
================
Per-user calendar store backed by the tenant's vault SQLite database.

Events live in the ``calendar_events`` table of the tenant-owned
``Semptify5.0/.semptify/vault.db`` (live-reads-retarget-sqlite; Phase-1
JSON overlays are now an export/provenance layer, not the live store).
Manual and auto-synced events (document_extraction, rent_ledger) live in
the same store; auto-synced events carry ``source`` +
``linked_record_id`` for idempotent refresh by calendar_sync.

Two bounded, idempotent import paths run on read so history is never
stranded: ``migrate_overlay_events`` copies Phase-1 CALENDAR_EVENT
overlays into SQLite (dedupe by primary key, overlay files left in
place), and ``migrate_legacy_events`` imports pre-overlay server DB rows.

View contract: functions return SimpleNamespace objects carrying the
UnifiedOverlay attribute surface — ``overlay_id``, ``overlay_type``,
``created_by``, ``document_id``, ``vault_path``, ``payload`` (dict),
``created_at``/``updated_at`` (datetime) — so every consumer keeps
working unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_CALENDAR_FILE
from app.models.models import CalendarEvent as CalendarEventModel
from app.sdk.vault import (
    VaultDbError,
    mutate_remote_ensured,
    read_remote,
)
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Payload keys that map to calendar_events columns.
_EVENT_COLUMNS = (
    "title",
    "description",
    "start_datetime",
    "end_datetime",
    "all_day",
    "event_type",
    "is_critical",
    "reminder_days",
    "source",
    "linked_record_id",
)


def get_calendar_anchor_id(user_id: str) -> str:
    """Return the per-user calendar document_id anchor."""
    return f"calendar:{user_id}"


def get_calendar_vault_path() -> str:
    """Return the canonical vault path used as the calendar anchor."""
    return VAULT_CALENDAR_FILE


def _get_storage(user: UserContext):
    """Storage provider for the current user's cloud vault."""
    return get_provider(user.provider.value, access_token=user.access_token)


async def _get_overlay_manager(user: UserContext):
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


def _to_iso(value) -> str | None:
    """Normalize a datetime/ISO-string field to an ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _view(row, effective_id: str) -> SimpleNamespace:
    """Build the overlay-shaped view consumers expect from a table row."""
    payload = {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "start_datetime": row["start_datetime"],
        "end_datetime": row["end_datetime"],
        "all_day": bool(row["all_day"]),
        "event_type": row["event_type"],
        "is_critical": bool(row["is_critical"]),
        "reminder_days": row["reminder_days"],
        "source": row["source"],
        "linked_record_id": row["linked_record_id"],
    }
    return SimpleNamespace(
        overlay_id=row["id"],
        overlay_type=OverlayType.CALENDAR_EVENT,
        created_by=effective_id,
        document_id=get_calendar_anchor_id(effective_id),
        vault_path=VAULT_CALENDAR_FILE,
        payload=payload,
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


async def create_event(
    user: UserContext,
    *,
    title: str,
    start_datetime,
    end_datetime=None,
    all_day: bool = False,
    event_type: str,
    is_critical: bool = False,
    reminder_days: int | None = None,
    description: str | None = None,
    source: str = "manual",
    linked_record_id: str | None = None,
) -> SimpleNamespace:
    """Create a calendar event row in the user's vault SQLite."""
    effective_id = user.get_effective_user_id()
    event_id = make_id("cal")
    now = utc_now().isoformat()
    storage = _get_storage(user)

    def work(conn):
        conn.row_factory = _dict_factory
        conn.execute(
            "INSERT INTO calendar_events "
            "(id, title, description, start_datetime, end_datetime, all_day,"
            " event_type, is_critical, reminder_days, source, linked_record_id,"
            " created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                event_id,
                title,
                description,
                _to_iso(start_datetime),
                _to_iso(end_datetime),
                int(all_day),
                event_type,
                int(is_critical),
                reminder_days,
                source,
                linked_record_id,
                now,
                now,
            ),
        )
        return conn.execute(
            "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
        ).fetchone()

    try:
        row = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Failed to create calendar event for user %s: %s", user.user_id[:8], e)
        raise RuntimeError(f"Could not save calendar event: {e}") from e
    return _view(row, effective_id)


async def list_events(
    user: UserContext,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    event_type: str | None = None,
    critical_only: bool = False,
    skip: int = 0,
    limit: int = 500,
) -> tuple[list[SimpleNamespace], int]:
    """Return (events, total) for the user, sorted by start_datetime ascending.

    Datetime filters accept aware datetimes; stored values are ISO strings so
    comparison is done on ISO-normalized strings (ISO-8601 sorts correctly).
    """
    await migrate_legacy_events(user)
    await migrate_overlay_events(user)
    storage = _get_storage(user)
    effective_id = user.get_effective_user_id()

    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None

    def work(conn):
        conn.row_factory = _dict_factory
        clauses: list[str] = []
        params: list = []
        if start_iso:
            clauses.append("start_datetime >= ?")
            params.append(start_iso)
        if end_iso:
            clauses.append("start_datetime <= ?")
            params.append(end_iso)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if critical_only:
            clauses.append("is_critical = 1")
        sql = "SELECT * FROM calendar_events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY COALESCE(start_datetime, created_at) ASC"
        return conn.execute(sql, params).fetchall()

    try:
        rows = await read_remote(storage, work, default=[])
    except VaultDbError as e:
        logger.error("Failed to list calendar events for user %s: %s", user.user_id[:8], e)
        return [], 0

    views = [_view(row, effective_id) for row in rows]
    return views[skip : skip + limit], len(views)


async def list_events_for_user_id(
    user_id: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    event_type: str | None = None,
    critical_only: bool = False,
) -> tuple[list[SimpleNamespace], int]:
    """list_events for callers that only have a user_id (timeline, workflow,
    case builder, calendar_sync).

    Returns ([], 0) when the user's context/token cannot be reconstructed —
    callers treat calendar as simply empty, matching legacy failure semantics.
    """
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return [], 0
    return await list_events(
        context, start=start, end=end, event_type=event_type, critical_only=critical_only
    )


async def get_event(user: UserContext, event_id: str) -> SimpleNamespace | None:
    """Get a single calendar event by id."""
    storage = _get_storage(user)
    effective_id = user.get_effective_user_id()

    def work(conn):
        conn.row_factory = _dict_factory
        return conn.execute(
            "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
        ).fetchone()

    try:
        row = await read_remote(storage, work, default=None)
    except VaultDbError as e:
        logger.error("Failed to read calendar event for user %s: %s", user.user_id[:8], e)
        return None
    return _view(row, effective_id) if row else None


async def update_event(user: UserContext, event_id: str, fields: dict) -> SimpleNamespace | None:
    """Merge fields into an event row. Datetime values are normalized
    to ISO strings. Returns the updated view."""
    effective_id = user.get_effective_user_id()
    storage = _get_storage(user)

    updates: list[str] = []
    params: list = []
    for key, value in fields.items():
        if key not in _EVENT_COLUMNS:
            continue
        if key.endswith("_datetime"):
            value = _to_iso(value)
        elif key in ("all_day", "is_critical"):
            value = int(bool(value))
        updates.append(f"{key} = ?")
        params.append(value)
    if not updates:
        return await get_event(user, event_id)
    updates.append("updated_at = ?")
    params.append(utc_now().isoformat())
    params.append(event_id)

    def work(conn):
        conn.row_factory = _dict_factory
        cur = conn.execute(
            f"UPDATE calendar_events SET {', '.join(updates)} WHERE id = ?",  # nosec B608 — updates contain only whitelisted _EVENT_COLUMNS keys as `key = ?`; values are parameterized
            params,
        )
        if cur.rowcount == 0:
            return None
        return conn.execute(
            "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
        ).fetchone()

    try:
        row = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Failed to update calendar event for user %s: %s", user.user_id[:8], e)
        return None
    return _view(row, effective_id) if row else None


async def delete_event(user: UserContext, event_id: str) -> bool:
    """Delete a calendar event row."""
    storage = _get_storage(user)

    def work(conn):
        cur = conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        return cur.rowcount > 0

    try:
        return bool(await mutate_remote_ensured(storage, work))
    except VaultDbError as e:
        logger.error("Failed to delete calendar event for user %s: %s", user.user_id[:8], e)
        return False


# ---------------------------------------------------------------------------
# Auto-sync helpers (calendar_sync) — caller only has a user_id
# ---------------------------------------------------------------------------


async def existing_link_keys(user_id: str, sources: tuple[str, ...]) -> set[str]:
    """Return the set of linked_record_id values already stored for the
    given auto sources. Empty set when context cannot be rebuilt."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return set()
    storage = _get_storage(context)
    placeholders = ",".join("?" for _ in sources)

    def work(conn):
        rows = conn.execute(
            f"SELECT DISTINCT linked_record_id FROM calendar_events"  # nosec B608 — placeholders are generated `?` marks; source values are parameterized
            f" WHERE source IN ({placeholders}) AND linked_record_id IS NOT NULL",
            list(sources),
        ).fetchall()
        return {r[0] for r in rows}

    try:
        return await read_remote(storage, work, default=set())
    except VaultDbError:
        return set()


async def delete_source_events(user_id: str, sources: tuple[str, ...]) -> int:
    """Delete all calendar rows whose source is in ``sources`` (the
    overwrite path of calendar_sync). Returns count deleted."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return 0
    storage = _get_storage(context)
    placeholders = ",".join("?" for _ in sources)

    def work(conn):
        cur = conn.execute(
            f"DELETE FROM calendar_events WHERE source IN ({placeholders})",  # nosec B608 — placeholders are generated `?` marks; source values are parameterized
            list(sources),
        )
        return cur.rowcount

    try:
        return int(await mutate_remote_ensured(storage, work))
    except VaultDbError:
        return 0


async def create_event_for_user_id(user_id: str, **fields) -> str | None:
    """create_event for callers that only have a user_id (calendar_sync,
    setup). Returns the new event id, or None when context/creation fails.
    """
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return None
    try:
        view = await create_event(context, **fields)
    except Exception as e:
        logger.error("Auto calendar event create failed for %s***: %s", user_id[:6], e)
        return None
    return view.overlay_id


# ---------------------------------------------------------------------------
# Phase-1 overlay import (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Events written while JSON overlays were the live store still live in the
# tenant's overlay files. migrate_overlay_events() copies them into
# calendar_events (dedupe by primary key), bounded per call. Overlay files
# are left in place as provenance.


def _insert_event_row(conn, event_id: str, payload: dict, fallback_created: str | None) -> bool:
    """INSERT OR IGNORE one overlay/legacy-shaped row. True if inserted."""
    now = utc_now().isoformat()
    created = payload.get("created_at") or fallback_created or now
    cur = conn.execute(
        "INSERT OR IGNORE INTO calendar_events "
        "(id, title, description, start_datetime, end_datetime, all_day,"
        " event_type, is_critical, reminder_days, source, linked_record_id,"
        " created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            event_id,
            payload.get("title") or "",
            payload.get("description"),
            _to_iso(payload.get("start_datetime")),
            _to_iso(payload.get("end_datetime")),
            int(bool(payload.get("all_day"))),
            payload.get("event_type") or "reminder",
            int(bool(payload.get("is_critical"))),
            payload.get("reminder_days"),
            payload.get("source") or "manual",
            payload.get("linked_record_id"),
            created,
            payload.get("updated_at") or created,
        ),
    )
    return cur.rowcount > 0


async def migrate_overlay_events(user: UserContext, limit: int = 25) -> int:
    """Import Phase-1 CALENDAR_EVENT overlays into vault SQLite.

    Bounded to ``limit`` new rows per call; idempotent via primary-key
    dedupe (the overlay payload id becomes the row id). Returns the count
    imported this call.
    """
    effective_id = user.get_effective_user_id()
    try:
        manager = await _get_overlay_manager(user)
        response = await manager.get_overlays(
            document_id=get_calendar_anchor_id(effective_id),
            overlay_type=OverlayType.CALENDAR_EVENT,
        )
    except Exception as e:
        logger.warning("Calendar overlay import skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not response.success:
        return 0

    owned = [
        o
        for o in response.overlays
        if o.overlay_type == OverlayType.CALENDAR_EVENT and o.created_by == effective_id
    ]
    if not owned:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM calendar_events")}
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
        logger.error("Calendar overlay import failed for user %s: %s", user.user_id[:8], e)
        return 0
    if imported:
        logger.info("Imported %d calendar overlays to vault.db for user %s", imported, effective_id[:8])
    return imported


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Rows written before the vault-persistence migration still live in the
# server-side calendar_events table. migrate_legacy_events() imports them
# into the tenant's vault SQLite (dedupe by primary key — the legacy row id
# is preserved as the row id). Source rows are left in place until the
# table-drop phase — this step moves data, it does not delete history.


async def migrate_legacy_events(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy DB calendar rows into vault SQLite.

    Bounded to ``max_rows`` per call to stay inside the provider-work
    budget; repeat calls continue where the last one left off (idempotent
    via primary-key dedupe). Returns the count imported this call.
    """
    effective_id = user.get_effective_user_id()
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(CalendarEventModel).where(CalendarEventModel.user_id == effective_id)
            )
            rows = list(result.scalars().all())
    except Exception as e:
        # Transition shim must never break the vault path — unreachable DB or
        # a dropped legacy table just means there is nothing left to import.
        logger.warning("Legacy calendar migration skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not rows:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM calendar_events")}
        imported = 0
        for row in rows:
            if imported >= max_rows or row.id in existing:
                continue
            if _insert_event_row(
                conn,
                row.id,
                {
                    "title": row.title,
                    "description": row.description,
                    "start_datetime": row.start_datetime.isoformat() if row.start_datetime else None,
                    "end_datetime": row.end_datetime.isoformat() if row.end_datetime else None,
                    "all_day": row.all_day,
                    "event_type": row.event_type or "reminder",
                    "is_critical": row.is_critical,
                    "reminder_days": row.reminder_days,
                    "source": row.source or "manual",
                    "linked_record_id": row.linked_record_id,
                },
                row.created_at.isoformat() if row.created_at else None,
            ):
                imported += 1
        return imported

    try:
        imported = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Legacy calendar migration failed for user %s: %s", user.user_id[:8], e)
        return 0
    if imported:
        logger.info("Migrated %d legacy calendar events to vault.db for user %s", imported, effective_id[:8])
    return imported
