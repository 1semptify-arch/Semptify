"""Dispute Tracker vault persistence — DISPUTE_RECORD / COMPARISON_ENTRY overlays.

Disputes and their comparison entries persist as overlays anchored to
`document_id="disputes:{user_id}"` in the user's own cloud storage
(VAULT_RECORDS_FILE — the shared tenant-records file). Legacy
`dispute_records` / `comparison_entries` rows are imported by
`migrate_legacy_disputes()` on first read: non-destructive, idempotent via
`payload["legacy_id"]`, bounded at 25 rows per call.

Payload ids (`dis_*`, `cmp_*`) are preserved so comparison entries keep
resolving their parent dispute through `dispute_record_id`.

Template contract: list_* functions return SimpleNamespace view objects —
disputes expose id/dispute_type/status/landlord_entity/property_name/
jurisdiction; comparisons expose id/dispute_record_id/comparison_type/
fee_type/amount_cents/period/effective_date (datetime for strftime).
"""

import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext
from app.core.vault_paths import VAULT_RECORDS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)


def _anchor_id(effective_id: str) -> str:
    """Per-user anchor document_id for dispute overlays."""
    return f"disputes:{effective_id}"


async def _get_overlay_manager(user: UserContext) -> UnifiedOverlayManager:
    """Manager keyed to the effective user so support impersonation writes
    records that belong to the tenant."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(effective_id: str, overlay) -> bool:
    return overlay.created_by == effective_id


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _dispute_view(overlay) -> SimpleNamespace:
    p = overlay.payload
    return SimpleNamespace(
        id=p.get("id") or overlay.overlay_id,
        dispute_type=p.get("dispute_type"),
        status=p.get("status"),
        landlord_entity=p.get("landlord_entity"),
        property_name=p.get("property_name"),
        jurisdiction=p.get("jurisdiction"),
        content_overlay_id=p.get("content_overlay_id"),
        evidence_overlay_id=p.get("evidence_overlay_id"),
        created_at=_parse_dt(p.get("created_at")),
        updated_at=_parse_dt(p.get("updated_at")),
    )


def _comparison_view(overlay) -> SimpleNamespace:
    p = overlay.payload
    return SimpleNamespace(
        id=p.get("id") or overlay.overlay_id,
        dispute_record_id=p.get("dispute_record_id"),
        comparison_type=p.get("comparison_type"),
        fee_type=p.get("fee_type"),
        amount_cents=p.get("amount_cents"),
        period=p.get("period"),
        effective_date=_parse_dt(p.get("effective_date")),
        created_at=_parse_dt(p.get("created_at")),
        updated_at=_parse_dt(p.get("updated_at")),
    )


async def _list_owned(user: UserContext, overlay_type: OverlayType) -> list:
    manager = await _get_overlay_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor_id(effective_id), overlay_type=overlay_type)
    if not response.success:
        logger.warning("Dispute overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if _owns(effective_id, o)]


async def list_disputes(user: UserContext) -> list[SimpleNamespace]:
    """All dispute records for the user, newest first (legacy rows migrate first)."""
    await migrate_legacy_disputes(user)
    overlays = await _list_owned(user, OverlayType.DISPUTE_RECORD)
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    return [_dispute_view(o) for o in overlays]


async def list_comparisons(user: UserContext) -> list[SimpleNamespace]:
    """All comparison entries for the user, newest first."""
    overlays = await _list_owned(user, OverlayType.COMPARISON_ENTRY)
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    return [_comparison_view(o) for o in overlays]


async def create_dispute(
    user: UserContext,
    dispute_type: str,
    landlord_entity: str | None = None,
    property_name: str | None = None,
    status: str = "active",
    jurisdiction: str = "MN",
) -> str | None:
    """Create a dispute record overlay. Returns the dis_* id, or None on failure."""
    effective_id = user.get_effective_user_id()
    manager = await _get_overlay_manager(user)
    record_id = make_id("dis")
    now = utc_now().isoformat()

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.DISPUTE_RECORD,
            document_id=_anchor_id(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload={
                "id": record_id,
                "dispute_type": dispute_type,
                "landlord_entity": landlord_entity,
                "property_name": property_name,
                "status": status,
                "jurisdiction": jurisdiction,
                "content_overlay_id": None,
                "evidence_overlay_id": None,
                "created_at": now,
                "updated_at": now,
            },
            metadata={"dispute_type": dispute_type, "scope": "disputes"},
        )
    )
    if not response.success:
        logger.error("Failed to create dispute for user %s: %s", user.user_id[:8], response.message)
        return None
    return record_id


async def create_comparison(
    user: UserContext,
    dispute_record_id: str,
    comparison_type: str,
    fee_type: str | None = None,
    amount_cents: int | None = None,
    period: str | None = None,
    effective_date: datetime | None = None,
) -> str | None:
    """Create a comparison entry overlay linked to a dispute. Returns cmp_* id or None."""
    effective_id = user.get_effective_user_id()
    manager = await _get_overlay_manager(user)
    entry_id = make_id("cmp")
    now = utc_now().isoformat()

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.COMPARISON_ENTRY,
            document_id=_anchor_id(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload={
                "id": entry_id,
                "dispute_record_id": dispute_record_id,
                "comparison_type": comparison_type,
                "fee_type": fee_type,
                "amount_cents": amount_cents,
                "period": period,
                "effective_date": effective_date.isoformat() if effective_date else None,
                "created_at": now,
                "updated_at": now,
            },
            metadata={"comparison_type": comparison_type, "scope": "disputes"},
        )
    )
    if not response.success:
        logger.error("Failed to create comparison for user %s: %s", user.user_id[:8], response.message)
        return None
    return entry_id


async def migrate_legacy_disputes(user: UserContext, limit: int = 25) -> int:
    """One-shot bounded import of legacy dispute_records + comparison_entries rows.

    Non-destructive (rows stay until the table-drop phase) and idempotent via
    payload["legacy_id"]. Returns the number imported this call. Never raises —
    returns 0 when the legacy store is unreachable.
    """
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import ComparisonEntry, DisputeRecord
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()

    try:
        disputes = await _list_owned(user, OverlayType.DISPUTE_RECORD)
        comparisons = await _list_owned(user, OverlayType.COMPARISON_ENTRY)
        migrated = {
            o.payload.get("legacy_id") for o in disputes + comparisons if o.payload.get("legacy_id")
        }
        manager = await _get_overlay_manager(user)
        imported = 0

        async with get_db_session() as db:
            # Link old numeric/string dispute ids to their payload ids so
            # comparison imports keep pointing at the right parent.
            result = await db.execute(
                select(DisputeRecord).where(DisputeRecord.user_id == user.user_id).limit(limit)
            )
            dispute_rows = result.scalars().all()
            for row in dispute_rows:
                if imported >= limit or row.id in migrated:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.DISPUTE_RECORD,
                        document_id=_anchor_id(effective_id),
                        vault_path=VAULT_RECORDS_FILE,
                        payload={
                            "id": row.id,
                            "dispute_type": row.dispute_type,
                            "landlord_entity": row.landlord_entity,
                            "property_name": row.property_name,
                            "status": row.status,
                            "jurisdiction": row.jurisdiction,
                            "content_overlay_id": row.content_overlay_id,
                            "evidence_overlay_id": row.evidence_overlay_id,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                            "legacy_id": row.id,
                            "migrated_from": "dispute_records",
                        },
                        metadata={"dispute_type": row.dispute_type, "scope": "disputes"},
                    )
                )
                migrated.add(row.id)
                imported += 1

            if imported < limit:
                result = await db.execute(
                    select(ComparisonEntry).where(ComparisonEntry.user_id == user.user_id).limit(limit)
                )
                for row in result.scalars().all():
                    if imported >= limit or row.id in migrated:
                        continue
                    await manager.create_overlay(
                        CreateOverlayRequest(
                            overlay_type=OverlayType.COMPARISON_ENTRY,
                            document_id=_anchor_id(effective_id),
                            vault_path=VAULT_RECORDS_FILE,
                            payload={
                                "id": row.id,
                                "dispute_record_id": row.dispute_record_id,
                                "comparison_type": row.comparison_type,
                                "fee_type": row.fee_type,
                                "amount_cents": row.amount_cents,
                                "period": row.period,
                                "effective_date": row.effective_date.isoformat() if row.effective_date else None,
                                "created_at": row.created_at.isoformat() if row.created_at else None,
                                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                                "legacy_id": row.id,
                                "migrated_from": "comparison_entries",
                            },
                            metadata={"comparison_type": row.comparison_type, "scope": "disputes"},
                        )
                    )
                    migrated.add(row.id)
                    imported += 1
    except Exception:
        logger.exception("Legacy dispute migration failed for user %s", user.user_id[:8])
        return imported

    return imported
