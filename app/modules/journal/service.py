"""
Journal Service
===============
Per-user journal store backed by the Unified Overlay System.

Each entry is a JOURNAL_ENTRY overlay anchored to document_id="journal:{user_id}"
in the user's own cloud storage — the same pattern sticky_notes uses for the
scratchpad. No server-side database rows: the tenant's records live in the
tenant's vault (vault-persistence-migration, Phase 1).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import StorageProvider, UserContext, UserRole
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_JOURNAL_FILE
from app.models.models import JournalEntry as JournalEntryModel
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)


def get_journal_anchor_id(user_id: str) -> str:
    """Return the per-user journal document_id anchor."""
    return f"journal:{user_id}"


def get_journal_vault_path() -> str:
    """Return the canonical vault path used as the journal anchor."""
    return VAULT_JOURNAL_FILE


async def _get_overlay_manager(user: UserContext):
    """Build an overlay manager for the current user's cloud storage.

    The manager is labelled with the *effective* user id so entries created
    during support impersonation belong to the impersonated tenant — matching
    the legacy user_id=effective_id column semantics.
    """
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(user: UserContext, overlay: UnifiedOverlay) -> bool:
    """True if the overlay is a journal entry owned by the effective user."""
    return (
        overlay.overlay_type == OverlayType.JOURNAL_ENTRY
        and overlay.created_by == user.get_effective_user_id()
    )


def _occurred_at(overlay: UnifiedOverlay) -> str:
    """Sort key: payload occurred_at falling back to overlay creation time."""
    return overlay.payload.get("occurred_at") or overlay.created_at.isoformat()


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
) -> UnifiedOverlay:
    """Create a journal entry overlay in the user's cloud."""
    manager = await _get_overlay_manager(user)
    request = CreateOverlayRequest(
        overlay_type=OverlayType.JOURNAL_ENTRY,
        document_id=get_journal_anchor_id(user.get_effective_user_id()),
        vault_path=get_journal_vault_path(),
        payload={
            "id": make_id("jrn"),
            "entry_type": entry_type,
            "title": title,
            "content": content,
            "occurred_at": occurred_at.isoformat(),
            "is_urgent": is_urgent,
            "involved_party": involved_party,
            "tags": tags,
            "document_link": document_link,
            "source": source,
        },
        metadata={
            "entry_type": entry_type,
            "is_urgent": is_urgent,
            "scope": "journal",
        },
    )
    response = await manager.create_overlay(request)
    if not response.success or not response.overlay_id:
        logger.error("Failed to create journal entry for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save journal entry: {response.message}")

    overlay = await manager.get_overlay(response.overlay_id)
    if overlay is None:
        raise RuntimeError("Journal entry was reported as created but cannot be retrieved")
    return overlay


async def _context_for_user_id(user_id: str) -> UserContext | None:
    """Rebuild a minimal UserContext from a bare user_id.

    Cross-module readers (tenant feed, briefcase, dashboard stats) only carry
    the user_id. Provider/role codes are embedded in the id itself; the access
    token comes from the session store via ensure_valid_token. Returns None
    when the id is unparseable or no valid token can be produced.
    """
    from app.core.auto_refresh import ensure_valid_token
    from app.core.user_id import parse_user_id

    provider_name, role_name, _unique = parse_user_id(user_id)
    if not provider_name:
        return None
    try:
        provider = StorageProvider(provider_name)
    except ValueError:
        return None
    try:
        role = UserRole(role_name) if role_name else UserRole.USER
    except ValueError:
        role = UserRole.USER

    try:
        is_valid, token, _status = await ensure_valid_token(user_id)
    except Exception as e:
        logger.warning("Token resolution failed for %s***: %s", user_id[:6], e)
        return None
    if not is_valid or token is None:
        return None

    return UserContext(
        user_id=user_id,
        provider=provider,
        storage_user_id=user_id,
        access_token=token.access_token,
        role=role,
    )


async def list_entries_for_user_id(
    user_id: str,
    *,
    entry_type: str | None = None,
    is_urgent: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[UnifiedOverlay], int]:
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
) -> tuple[list[UnifiedOverlay], int]:
    """Return (entries, total) for the user, newest occurred_at first."""
    await migrate_legacy_entries(user)
    manager = await _get_overlay_manager(user)
    response = await manager.get_overlays(
        document_id=get_journal_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.JOURNAL_ENTRY,
    )
    if not response.success:
        logger.error("Failed to list journal entries for user %s: %s", user.user_id[:8], response.filters_applied)
        return [], 0

    entries = [o for o in response.overlays if _owns(user, o)]
    if entry_type:
        entries = [o for o in entries if o.payload.get("entry_type") == entry_type]
    if is_urgent is not None:
        entries = [o for o in entries if bool(o.payload.get("is_urgent")) == is_urgent]
    entries.sort(key=_occurred_at, reverse=True)
    return entries[skip : skip + limit], len(entries)


async def _resolve_entry(manager, user: UserContext, entry_id: str) -> UnifiedOverlay | None:
    """Resolve an entry by overlay id, or by a legacy ``jrn_`` id carried in
    the overlay payload for migrated rows."""
    overlay = await manager.get_overlay(entry_id)
    if overlay is not None and _owns(user, overlay):
        return overlay

    response = await manager.get_overlays(
        document_id=get_journal_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.JOURNAL_ENTRY,
    )
    if not response.success:
        return None
    for candidate in response.overlays:
        if _owns(user, candidate) and (
            candidate.payload.get("id") == entry_id or candidate.payload.get("legacy_id") == entry_id
        ):
            return candidate
    return None


async def get_entry(user: UserContext, entry_id: str) -> UnifiedOverlay | None:
    """Get a single journal entry by id, ownership-checked."""
    manager = await _get_overlay_manager(user)
    return await _resolve_entry(manager, user, entry_id)


async def update_entry(user: UserContext, entry_id: str, fields: dict) -> UnifiedOverlay | None:
    """Merge fields into an entry's payload. Returns the updated overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_entry(manager, user, entry_id)
    if overlay is None:
        return None

    overlay.payload.update(fields)
    overlay.payload["updated_at"] = utc_now().isoformat()
    if not await manager.update_overlay(overlay.overlay_id, payload=overlay.payload):
        return None
    return await manager.get_overlay(overlay.overlay_id)


async def delete_entry(user: UserContext, entry_id: str) -> bool:
    """Delete a journal entry overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_entry(manager, user, entry_id)
    if overlay is None:
        return False
    return await manager.delete_overlay(overlay.overlay_id)


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Rows written before the vault-persistence migration still live in the
# journal_entries table. migrate_legacy_entries() imports them into the user's
# vault as JOURNAL_ENTRY overlays marked with payload["legacy_id"], so repeat
# runs never duplicate. Source rows are left in place until the table-drop
# phase — this step moves data, it does not delete history.


async def migrate_legacy_entries(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy DB journal rows into vault overlays.

    Bounded to ``max_rows`` per call to stay inside the provider-work budget;
    repeat calls continue where the last one left off (idempotent via
    ``legacy_id``). Returns the count imported this call.
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

    manager = await _get_overlay_manager(user)
    existing = await manager.get_overlays(
        document_id=get_journal_anchor_id(effective_id),
        overlay_type=OverlayType.JOURNAL_ENTRY,
    )
    migrated_ids = {
        o.payload.get("legacy_id")
        for o in existing.overlays
        if _owns(user, o) and o.payload.get("legacy_id")
    }

    imported = 0
    for row in rows:
        if imported >= max_rows:
            break
        if row.id in migrated_ids:
            continue
        response = await manager.create_overlay(
            CreateOverlayRequest(
                overlay_type=OverlayType.JOURNAL_ENTRY,
                document_id=get_journal_anchor_id(effective_id),
                vault_path=get_journal_vault_path(),
                payload={
                    "id": row.id,
                    "legacy_id": row.id,
                    "entry_type": row.entry_type or "note",
                    "title": row.title or "",
                    "content": row.content,
                    "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                    "is_urgent": bool(row.is_urgent),
                    "involved_party": row.involved_party,
                    "tags": row.tags,
                    "document_link": row.document_link,
                    "source": row.source or "manual",
                },
                metadata={
                    "migrated_from": "journal_entries",
                    "legacy_created_at": row.created_at.isoformat() if row.created_at else None,
                    "scope": "journal",
                },
            )
        )
        if response.success:
            imported += 1
        else:
            logger.error("Failed to migrate journal row %s: %s", row.id, response.message)
    if imported:
        logger.info("Migrated %d legacy journal entries to vault for user %s", imported, effective_id[:8])
    return imported
