"""
Journal Service
===============
Per-user journal store backed by the tenant's vault SQLite database.

Entries live in the ``journal_entries`` table of the tenant-owned
``Semptify5.0/.semptify/vault.db`` — the tenant's records live in the
tenant's vault (live-reads-retarget-sqlite; Phase-1 JSON overlays are now
an export/provenance layer, not the live store).

Two bounded, idempotent import paths run on read so history is never
stranded:

- ``migrate_overlay_entries`` — Phase-1 JOURNAL_ENTRY overlays -> SQLite
  (deduped by primary key, non-destructive: overlay files stay in place).
- ``migrate_legacy_entries`` — pre-overlay server DB rows -> SQLite.

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
from app.core.vault_paths import VAULT_JOURNAL_FILE
from app.models.models import JournalEntry as JournalEntryModel
from app.sdk.vault import (
    VaultDbError,
    mutate_remote_ensured,
    read_remote,
)
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Payload keys that map to journal_entries columns. Unknown update keys are
# ignored — the overlay store accepted any payload key; the table cannot.
_ENTRY_COLUMNS = (
    "entry_type",
    "title",
    "content",
    "occurred_at",
    "is_urgent",
    "involved_party",
    "tags",
    "document_link",
    "source",
)


def get_journal_anchor_id(user_id: str) -> str:
    """Return the per-user journal document_id anchor."""
    return f"journal:{user_id}"


def get_journal_vault_path() -> str:
    """Return the canonical vault path used as the journal anchor."""
    return VAULT_JOURNAL_FILE


def _get_storage(user: UserContext):
    """Storage provider for the current user's cloud vault."""
    return get_provider(user.provider.value, access_token=user.access_token)


async def _get_overlay_manager(user: UserContext):
    """Overlay manager — now used ONLY by the Phase-1 import path."""
    storage = _get_storage(user)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


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
    """Build the overlay-shaped view consumers expect from a table row."""
    occurred_at = row["occurred_at"]
    created_at = row["created_at"]
    payload = {
        "id": row["id"],
        "entry_type": row["entry_type"],
        "title": row["title"],
        "content": row["content"],
        "occurred_at": occurred_at,
        "is_urgent": bool(row["is_urgent"]),
        "involved_party": row["involved_party"],
        "tags": row["tags"],
        "document_link": row["document_link"],
        "source": row["source"],
    }
    return SimpleNamespace(
        overlay_id=row["id"],
        overlay_type=OverlayType.JOURNAL_ENTRY,
        created_by=effective_id,
        document_id=get_journal_anchor_id(effective_id),
        vault_path=VAULT_JOURNAL_FILE,
        payload=payload,
        created_at=_parse_dt(created_at),
        updated_at=_parse_dt(row["updated_at"]),
    )


async def create_entry(
    user: UserContext,
    *,
    entry_type: str,
    title: str,
    content: str | None,
    occurred_at: datetime,
    is_urgent: bool,
    involved_party: str | None,
    tags: str | None,
    document_link: str | None,
    source: str = "manual",
) -> SimpleNamespace:
    """Create a journal entry row in the user's vault SQLite."""
    effective_id = user.get_effective_user_id()
    entry_id = make_id("jrn")
    now = utc_now().isoformat()
    occurred_iso = (
        occurred_at.isoformat() if isinstance(occurred_at, datetime) else str(occurred_at)
    )
    storage = _get_storage(user)

    def work(conn):
        conn.row_factory = _dict_factory
        conn.execute(
            "INSERT INTO journal_entries "
            "(id, entry_type, title, content, occurred_at, is_urgent,"
            " involved_party, tags, document_link, source, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                entry_id,
                entry_type,
                title,
                content,
                occurred_iso,
                int(is_urgent),
                involved_party,
                tags,
                document_link,
                source,
                now,
                now,
            ),
        )
        return conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()

    try:
        row = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Failed to create journal entry for user %s: %s", user.user_id[:8], e)
        raise RuntimeError(f"Could not save journal entry: {e}") from e
    return _view(row, effective_id)


async def _context_for_user_id(user_id: str) -> UserContext | None:
    """Rebuild a minimal UserContext from a bare user_id — delegates to the
    canonical implementation in user_context (shared by all vault stores)."""
    from app.core.user_context import build_context_for_user_id

    return await build_context_for_user_id(user_id)


async def list_entries_for_user_id(
    user_id: str,
    *,
    entry_type: str | None = None,
    is_urgent: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SimpleNamespace], int]:
    """list_entries for callers that only have a user_id (feed, briefcase).

    Returns ([], 0) when the user's context/token cannot be reconstructed —
    callers treat journal as simply empty, matching legacy failure semantics.
    """
    context = await _context_for_user_id(user_id)
    if context is None:
        return [], 0
    return await list_entries(context, entry_type=entry_type, is_urgent=is_urgent, skip=skip, limit=limit)


async def list_entries(
    user: UserContext,
    *,
    entry_type: str | None = None,
    is_urgent: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SimpleNamespace], int]:
    """Return (entries, total) for the user, newest occurred_at first."""
    await migrate_legacy_entries(user)
    await migrate_overlay_entries(user)
    storage = _get_storage(user)
    effective_id = user.get_effective_user_id()

    def work(conn):
        conn.row_factory = _dict_factory
        sql = "SELECT * FROM journal_entries"
        clauses: list[str] = []
        params: list = []
        if entry_type:
            clauses.append("entry_type = ?")
            params.append(entry_type)
        if is_urgent is not None:
            clauses.append("is_urgent = ?")
            params.append(int(is_urgent))
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY occurred_at DESC, created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return rows

    try:
        rows = await read_remote(storage, work, default=[])
    except VaultDbError as e:
        logger.error("Failed to list journal entries for user %s: %s", user.user_id[:8], e)
        return [], 0

    views = [_view(row, effective_id) for row in rows]
    return views[skip : skip + limit], len(views)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


async def get_entry(user: UserContext, entry_id: str) -> SimpleNamespace | None:
    """Get a single journal entry by id."""
    storage = _get_storage(user)
    effective_id = user.get_effective_user_id()

    def work(conn):
        conn.row_factory = _dict_factory
        return conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()

    try:
        row = await read_remote(storage, work, default=None)
    except VaultDbError as e:
        logger.error("Failed to read journal entry for user %s: %s", user.user_id[:8], e)
        return None
    return _view(row, effective_id) if row else None


async def update_entry(user: UserContext, entry_id: str, fields: dict) -> SimpleNamespace | None:
    """Merge fields into an entry row. Returns the updated view."""
    effective_id = user.get_effective_user_id()
    storage = _get_storage(user)

    updates: list[str] = []
    params: list = []
    for key, value in fields.items():
        if key not in _ENTRY_COLUMNS:
            continue
        if key == "is_urgent":
            value = int(bool(value))
        elif key == "occurred_at" and isinstance(value, datetime):
            value = value.isoformat()
        updates.append(f"{key} = ?")
        params.append(value)
    if not updates:
        return await get_entry(user, entry_id)
    updates.append("updated_at = ?")
    params.append(utc_now().isoformat())
    params.append(entry_id)

    def work(conn):
        conn.row_factory = _dict_factory
        cur = conn.execute(
            f"UPDATE journal_entries SET {', '.join(updates)} WHERE id = ?",  # nosec B608 — updates contain only whitelisted _ENTRY_COLUMNS keys as `key = ?`; values are parameterized
            params,
        )
        if cur.rowcount == 0:
            return None
        return conn.execute(
            "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()

    try:
        row = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Failed to update journal entry for user %s: %s", user.user_id[:8], e)
        return None
    return _view(row, effective_id) if row else None


async def delete_entry(user: UserContext, entry_id: str) -> bool:
    """Delete a journal entry row."""
    storage = _get_storage(user)

    def work(conn):
        cur = conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    try:
        return bool(await mutate_remote_ensured(storage, work))
    except VaultDbError as e:
        logger.error("Failed to delete journal entry for user %s: %s", user.user_id[:8], e)
        return False


# ---------------------------------------------------------------------------
# Phase-1 overlay import (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Entries written while JSON overlays were the live store still live in the
# tenant's overlay files. migrate_overlay_entries() copies them into
# journal_rows (dedupe by primary key), bounded per call to stay inside the
# provider-work budget. Overlay files are left in place as provenance —
# this step copies data, it does not delete history.


def _insert_entry_row(conn, entry_id: str, payload: dict, fallback_created: str | None) -> bool:
    """INSERT OR IGNORE one overlay/legacy-shaped row. Returns True if inserted."""
    now = utc_now().isoformat()
    occurred = payload.get("occurred_at") or fallback_created or now
    created = payload.get("created_at") or fallback_created or now
    cur = conn.execute(
        "INSERT OR IGNORE INTO journal_entries "
        "(id, entry_type, title, content, occurred_at, is_urgent,"
        " involved_party, tags, document_link, source, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            entry_id,
            payload.get("entry_type") or "note",
            payload.get("title") or "",
            payload.get("content"),
            occurred,
            int(bool(payload.get("is_urgent"))),
            payload.get("involved_party"),
            payload.get("tags"),
            payload.get("document_link"),
            payload.get("source") or "manual",
            created,
            payload.get("updated_at") or created,
        ),
    )
    return cur.rowcount > 0


async def migrate_overlay_entries(user: UserContext, limit: int = 25) -> int:
    """Import Phase-1 JOURNAL_ENTRY overlays into vault SQLite.

    Bounded to ``limit`` new rows per call; idempotent via primary-key
    dedupe (the overlay payload id becomes the row id). Returns the count
    imported this call.
    """
    effective_id = user.get_effective_user_id()
    try:
        manager = await _get_overlay_manager(user)
        response = await manager.get_overlays(
            document_id=get_journal_anchor_id(effective_id),
            overlay_type=OverlayType.JOURNAL_ENTRY,
        )
    except Exception as e:
        logger.warning("Journal overlay import skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not response.success:
        return 0

    owned = [
        o
        for o in response.overlays
        if o.overlay_type == OverlayType.JOURNAL_ENTRY and o.created_by == effective_id
    ]
    if not owned:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM journal_entries")}
        imported = 0
        for overlay in owned:
            if imported >= limit:
                break
            rid = overlay.payload.get("id") or overlay.overlay_id
            if rid in existing:
                continue
            fallback = overlay.created_at.isoformat() if overlay.created_at else None
            if _insert_entry_row(conn, rid, overlay.payload, fallback):
                imported += 1
        return imported

    try:
        imported = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Journal overlay import failed for user %s: %s", user.user_id[:8], e)
        return 0
    if imported:
        logger.info("Imported %d journal overlays to vault.db for user %s", imported, effective_id[:8])
    return imported


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Rows written before the vault-persistence migration still live in the
# server-side journal_entries table. migrate_legacy_entries() imports them
# into the tenant's vault SQLite (dedupe by primary key — the legacy row id
# is preserved as the row id). Source rows are left in place until the
# table-drop phase — this step moves data, it does not delete history.


async def migrate_legacy_entries(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy DB journal rows into vault SQLite.

    Bounded to ``max_rows`` per call to stay inside the provider-work
    budget; repeat calls continue where the last one left off (idempotent
    via primary-key dedupe). Returns the count imported this call.
    """
    effective_id = user.get_effective_user_id()
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(JournalEntryModel).where(JournalEntryModel.user_id == effective_id)
            )
            rows = list(result.scalars().all())
    except Exception as e:
        # Transition shim must never break the vault path — unreachable DB or
        # a dropped legacy table just means there is nothing left to import.
        logger.warning("Legacy journal migration skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not rows:
        return 0

    storage = _get_storage(user)

    def work(conn):
        existing = {r[0] for r in conn.execute("SELECT id FROM journal_entries")}
        imported = 0
        for row in rows:
            if imported >= max_rows or row.id in existing:
                continue
            if _insert_entry_row(
                conn,
                row.id,
                {
                    "entry_type": row.entry_type,
                    "title": row.title,
                    "content": row.content,
                    "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                    "is_urgent": row.is_urgent,
                    "involved_party": row.involved_party,
                    "tags": row.tags,
                    "document_link": row.document_link,
                    "source": row.source,
                },
                row.created_at.isoformat() if row.created_at else None,
            ):
                imported += 1
        return imported

    try:
        imported = await mutate_remote_ensured(storage, work)
    except VaultDbError as e:
        logger.error("Legacy journal migration failed for user %s: %s", user.user_id[:8], e)
        return 0
    if imported:
        logger.info("Migrated %d legacy journal entries to vault.db for user %s", imported, effective_id[:8])
    return imported
