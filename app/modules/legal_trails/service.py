"""Legal Trails vault persistence — LEGAL_TRAIL_RECORD overlays.

Violations, eviction threats, late-fee violations, broker-oversight records,
and legal claims persist as overlays anchored to
``document_id="legal_trails:{user_id}"`` in the user's own cloud storage
(VAULT_RECORDS_FILE — the shared tenant-records file). ``payload["kind"]``
discriminates the record family; ``payload["id"]`` carries the vio_/thr_/fee_/
bro_/clm_ record id the API returns.

Every create also emits a tenant timeline event (best-effort — the overlay
record is the store of truth). Trail activity therefore appears on the
tenant's timeline and, for a linked advocate, only when the relationship's
``share_timeline`` scope is on — same access rules as the rest of the feed.
"""

import logging
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

# Record families stored under one overlay type; payload["kind"] selects.
KIND_VIOLATION = "violation"
KIND_EVICTION_THREAT = "eviction_threat"
KIND_LATE_FEE = "late_fee"
KIND_BROKER_OVERSIGHT = "broker_oversight"
KIND_CLAIM = "claim"

ALL_KINDS = (
    KIND_VIOLATION,
    KIND_EVICTION_THREAT,
    KIND_LATE_FEE,
    KIND_BROKER_OVERSIGHT,
    KIND_CLAIM,
)

_ID_PREFIX = {
    KIND_VIOLATION: "vio",
    KIND_EVICTION_THREAT: "thr",
    KIND_LATE_FEE: "fee",
    KIND_BROKER_OVERSIGHT: "bro",
    KIND_CLAIM: "clm",
}

# Timeline event_type per kind — readable labels for the tenant feed.
_TIMELINE_TITLE = {
    KIND_VIOLATION: "Violation logged",
    KIND_EVICTION_THREAT: "Eviction threat logged",
    KIND_LATE_FEE: "Late-fee violation logged",
    KIND_BROKER_OVERSIGHT: "Broker oversight record added",
    KIND_CLAIM: "Legal claim tracked",
}


def _anchor_id(effective_id: str) -> str:
    """Per-user anchor document_id for legal-trail overlays."""
    return f"legal_trails:{effective_id}"


async def _get_overlay_manager(user: UserContext) -> UnifiedOverlayManager:
    """Manager keyed to the effective user so support impersonation writes
    records that belong to the tenant."""
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(effective_id: str, overlay) -> bool:
    return overlay.created_by == effective_id


def _view(overlay) -> dict[str, Any]:
    """API-facing record — the stored payload plus the overlay_id needed to
    address the record for updates."""
    record = dict(overlay.payload)
    record["overlay_id"] = overlay.overlay_id
    return record


async def _list_owned(user: UserContext, kind: str) -> list[dict[str, Any]]:
    manager = await _get_overlay_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(
        document_id=_anchor_id(effective_id),
        overlay_type=OverlayType.LEGAL_TRAIL_RECORD,
    )
    if not response.success:
        logger.warning(
            "Legal-trails overlay list failed for user %s: %s", user.user_id[:8], response.message
        )
        return []
    owned = [o for o in response.overlays if _owns(effective_id, o)]
    records = [_view(o) for o in owned if o.payload.get("kind") == kind]
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


async def list_records(user: UserContext, kind: str) -> list[dict[str, Any]]:
    """All records of one kind for the user, newest first."""
    return await _list_owned(user, kind)


async def get_record(user: UserContext, kind: str, record_id: str) -> dict[str, Any] | None:
    """Fetch one record by its payload id (or broker_name for broker records)."""
    for record in await _list_owned(user, kind):
        if record.get("id") == record_id or (
            kind == KIND_BROKER_OVERSIGHT and record.get("broker_name") == record_id
        ):
            return record
    return None


async def counts(user: UserContext) -> dict[str, int]:
    """Per-kind record counts for the overview endpoint."""
    result: dict[str, int] = {}
    for kind in ALL_KINDS:
        result[kind] = len(await _list_owned(user, kind))
    return result


async def create_record(user: UserContext, kind: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    """Create a legal-trail record overlay. Returns the API-facing record, or
    None on storage failure."""
    effective_id = user.get_effective_user_id()
    manager = await _get_overlay_manager(user)
    record_id = make_id(_ID_PREFIX[kind])
    now = utc_now().isoformat()

    payload = {"kind": kind, "id": record_id, "created_at": now, "updated_at": now}
    payload.update(fields)

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.LEGAL_TRAIL_RECORD,
            document_id=_anchor_id(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload=payload,
            metadata={"kind": kind, "scope": "legal_trails"},
        )
    )
    if not response.success:
        logger.error(
            "Failed to create legal-trails %s for user %s: %s",
            kind,
            user.user_id[:8],
            response.message,
        )
        return None

    await _emit_timeline_event(user, kind, fields)
    record = dict(payload)
    record["overlay_id"] = response.overlay_id
    return record


async def update_record_payload(
    user: UserContext, kind: str, record_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply field updates to an existing record. Returns the updated record,
    or None if not found / write failed."""
    existing = await get_record(user, kind, record_id)
    if existing is None or not existing.get("overlay_id"):
        return None

    payload = {k: v for k, v in existing.items() if k != "overlay_id"}
    payload.update(updates)
    payload["updated_at"] = utc_now().isoformat()

    manager = await _get_overlay_manager(user)
    if not await manager.update_overlay(existing["overlay_id"], payload=payload):
        logger.warning(
            "Legal-trails %s update failed for user %s record %s",
            kind,
            user.user_id[:8],
            record_id,
        )
        return None
    payload["overlay_id"] = existing["overlay_id"]
    return payload


async def _emit_timeline_event(user: UserContext, kind: str, fields: dict[str, Any]) -> None:
    """Best-effort timeline event so trail activity lands in the tenant feed —
    and in an advocate's view only when share_timeline scope is on."""
    try:
        from app.services.timeline_store import create_event

        title = _TIMELINE_TITLE.get(kind, "Record logged")
        detail_bits = []
        if fields.get("perpetrator"):
            detail_bits.append(str(fields["perpetrator"]))
        if fields.get("company"):
            detail_bits.append(str(fields["company"]))
        if fields.get("violation_type"):
            detail_bits.append(str(fields["violation_type"]))
        if fields.get("title"):
            detail_bits.append(str(fields["title"]))

        await create_event(
            user,
            event_type="legal_trail",
            title=title,
            description=" — ".join(detail_bits) if detail_bits else None,
            tags='["legal_trails"]',
        )
    except Exception:  # noqa: BLE001 — timeline is a projection, never a write blocker
        logger.warning(
            "Legal-trails timeline event failed for user %s (kind=%s)", user.user_id[:8], kind
        )
