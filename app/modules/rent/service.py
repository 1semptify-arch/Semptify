"""
Rent Ledger Service
===================
Per-user rent ledger backed by the Unified Overlay System.

Each ledger entry (payment, fee, deposit, credit, charge) is a
RENT_LEDGER_ENTRY overlay anchored to document_id="ledger:{user_id}" in the
user's own cloud storage. No server-side database rows: the tenant's ledger
lives in the tenant's vault (vault-persistence-migration, Phase 1).

Amounts are stored in cents (integer) in the payload, matching the legacy
schema — running-balance math stays exact.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_LEDGER_FILE
from app.models.models import RentPayment
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)


def get_ledger_anchor_id(user_id: str) -> str:
    """Return the per-user ledger document_id anchor."""
    return f"ledger:{user_id}"


def get_ledger_vault_path() -> str:
    """Return the canonical vault path used as the ledger anchor."""
    return VAULT_LEDGER_FILE


async def _get_overlay_manager(user: UserContext):
    """Build an overlay manager for the current user's cloud storage."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(user: UserContext, overlay: UnifiedOverlay) -> bool:
    """True if the overlay is a ledger entry owned by the effective user."""
    return (
        overlay.overlay_type == OverlayType.RENT_LEDGER_ENTRY
        and overlay.created_by == user.get_effective_user_id()
    )


def _sort_key(overlay: UnifiedOverlay) -> tuple:
    """Chronological key: payment_date then payload id — matches legacy ordering."""
    p = overlay.payload
    return (p.get("payment_date") or "", p.get("id") or overlay.overlay_id)


async def create_entry(
    user: UserContext,
    *,
    entry_type: str,
    amount_cents: int,
    payment_date: str,
    due_date: str | None,
    period_covered: str | None,
    status: str | None,
    payment_method: str | None,
    source: str,
    receipt_document_id: str | None,
    overlay_link: str | None,
    notes: str | None,
) -> UnifiedOverlay:
    """Create a ledger entry overlay in the user's cloud."""
    manager = await _get_overlay_manager(user)
    request = CreateOverlayRequest(
        overlay_type=OverlayType.RENT_LEDGER_ENTRY,
        document_id=get_ledger_anchor_id(user.get_effective_user_id()),
        vault_path=get_ledger_vault_path(),
        payload={
            "id": make_id("rnt"),
            "entry_type": entry_type,
            "amount": amount_cents,
            "payment_date": payment_date,
            "due_date": due_date,
            "period_covered": period_covered,
            "status": status,
            "payment_method": payment_method,
            "source": source,
            "receipt_document_id": receipt_document_id,
            "overlay_link": overlay_link,
            "notes": notes,
        },
        metadata={
            "entry_type": entry_type,
            "scope": "ledger",
        },
    )
    response = await manager.create_overlay(request)
    if not response.success or not response.overlay_id:
        logger.error("Failed to create ledger entry for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save ledger entry: {response.message}")

    overlay = await manager.get_overlay(response.overlay_id)
    if overlay is None:
        raise RuntimeError("Ledger entry was reported as created but cannot be retrieved")
    return overlay


async def list_entries(
    user: UserContext,
    *,
    limit: int = 1000,
) -> tuple[list[UnifiedOverlay], int]:
    """Return (entries, total) oldest-first for running-balance computation."""
    await migrate_legacy_entries(user)
    manager = await _get_overlay_manager(user)
    response = await manager.get_overlays(
        document_id=get_ledger_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.RENT_LEDGER_ENTRY,
    )
    if not response.success:
        logger.error("Failed to list ledger entries for user %s", user.user_id[:8])
        return [], 0

    entries = [o for o in response.overlays if _owns(user, o)]
    entries.sort(key=_sort_key)
    return entries[:limit], len(entries)


async def list_entries_for_user_id(
    user_id: str,
    *,
    limit: int = 1000,
) -> tuple[list[UnifiedOverlay], int]:
    """list_entries for callers that only have a user_id (calendar sync,
    case builder). Returns ([], 0) when the context can't be reconstructed."""
    context = await build_context_for_user_id(user_id)
    if context is None:
        return [], 0
    return await list_entries(context, limit=limit)


async def _resolve_entry(manager, user: UserContext, entry_id: str) -> UnifiedOverlay | None:
    """Resolve an entry by overlay id, or by a legacy ``rnt_`` id carried in
    the overlay payload for migrated rows."""
    overlay = await manager.get_overlay(entry_id)
    if overlay is not None and _owns(user, overlay):
        return overlay

    response = await manager.get_overlays(
        document_id=get_ledger_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.RENT_LEDGER_ENTRY,
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
    """Get a single ledger entry by id, ownership-checked."""
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
    """Delete a ledger entry overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_entry(manager, user, entry_id)
    if overlay is None:
        return False
    return await manager.delete_overlay(overlay.overlay_id)


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------


async def migrate_legacy_entries(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy rent_payments rows into vault overlays.

    Bounded per call (provider-work budget); idempotent via ``legacy_id``.
    Source rows are left in place until the table-drop phase.
    """
    effective_id = user.get_effective_user_id()
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(RentPayment).where(RentPayment.user_id == effective_id)
            )
            rows = list(result.scalars().all())
    except Exception as e:
        logger.warning("Legacy ledger migration skipped for %s***: %s", effective_id[:6], e)
        return 0
    if not rows:
        return 0

    manager = await _get_overlay_manager(user)
    existing = await manager.get_overlays(
        document_id=get_ledger_anchor_id(effective_id),
        overlay_type=OverlayType.RENT_LEDGER_ENTRY,
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
                overlay_type=OverlayType.RENT_LEDGER_ENTRY,
                document_id=get_ledger_anchor_id(effective_id),
                vault_path=get_ledger_vault_path(),
                payload={
                    "id": row.id,
                    "legacy_id": row.id,
                    "entry_type": row.entry_type or "payment",
                    "amount": row.amount,
                    "payment_date": row.payment_date.isoformat() if row.payment_date else None,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                    "period_covered": row.period_covered,
                    "status": row.status,
                    "payment_method": row.payment_method,
                    "source": row.source or "user_entered",
                    "receipt_document_id": row.receipt_document_id,
                    "overlay_link": row.overlay_link,
                    "notes": row.notes,
                },
                metadata={
                    "migrated_from": "rent_payments",
                    "legacy_created_at": row.created_at.isoformat() if row.created_at else None,
                    "scope": "ledger",
                },
            )
        )
        if response.success:
            imported += 1
        else:
            logger.error("Failed to migrate ledger row %s: %s", row.id, response.message)
    if imported:
        logger.info("Migrated %d legacy ledger entries to vault for user %s", imported, effective_id[:8])
    return imported
