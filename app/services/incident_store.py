"""Incident store — INCIDENT overlays in the tenant's cloud vault.

Incidents (case groupings) persist as overlays anchored to
`document_id="incidents:{user_id}"` at VAULT_RECORDS_FILE. Legacy `incidents`
rows migrate on first read: non-destructive, idempotent via
`payload["legacy_id"]`, bounded at 25 rows/call.

The legacy PK is an autoincrement INTEGER used in URL paths and as
`VaultItem.related_incident_id` — payload["incident_id"] preserves it (new
incidents allocate max+1 per user) so vault-item links and int(case_id)
callers keep working.

View contract: list/get return SimpleNamespace objects carrying the ORM
attribute surface (incident_id:int, user_id, title, description, start_date,
end_date, status, incident_type, severity, incident_metadata,
case_overlay_id, fca_readiness_score, fca_readiness_updated_at, created_at,
updated_at) — compatible with IncidentResponse.from_attributes.
"""

import logging
from datetime import datetime
from types import SimpleNamespace

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_RECORDS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)

INCIDENT_FIELDS = (
    "incident_id",
    "title",
    "description",
    "start_date",
    "end_date",
    "status",
    "incident_type",
    "severity",
    "incident_metadata",
    "case_overlay_id",
    "fca_readiness_score",
    "fca_readiness_updated_at",
)


def _anchor(effective_id: str) -> str:
    return f"incidents:{effective_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    """Manager keyed to the effective user so impersonation writes belong to the tenant."""
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


def _to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _view(overlay, effective_id: str) -> SimpleNamespace:
    """ORM-compatible attribute surface for templates and model_validate."""
    p = overlay.payload
    return SimpleNamespace(
        incident_id=p.get("incident_id"),
        user_id=effective_id,
        title=p.get("title"),
        description=p.get("description"),
        start_date=_parse_dt(p.get("start_date")),
        end_date=_parse_dt(p.get("end_date")),
        status=p.get("status") or "active",
        incident_type=p.get("incident_type"),
        severity=p.get("severity"),
        incident_metadata=p.get("incident_metadata"),
        case_overlay_id=p.get("case_overlay_id"),
        fca_readiness_score=p.get("fca_readiness_score"),
        fca_readiness_updated_at=_parse_dt(p.get("fca_readiness_updated_at")),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor(effective_id), overlay_type=OverlayType.INCIDENT)
    if not response.success:
        logger.warning("Incident overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if _owns(effective_id, o)]


async def _resolve_overlay(user: UserContext, incident_id) -> object | None:
    """Resolve an incident by integer payload id or overlay_id."""
    try:
        wanted = int(incident_id)
    except (TypeError, ValueError):
        wanted = None
    for o in await _list_overlays(user):
        if o.overlay_id == incident_id or (wanted is not None and o.payload.get("incident_id") == wanted):
            return o
    return None


async def create_incident(user: UserContext, **fields) -> SimpleNamespace | None:
    """Create an incident overlay. Allocates the next integer incident_id per user."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)

    existing = await _list_overlays(user)
    int_ids = [o.payload.get("incident_id") for o in existing if isinstance(o.payload.get("incident_id"), int)]
    next_id = (max(int_ids) + 1) if int_ids else 1

    payload = {k: _to_iso(v) for k, v in fields.items() if k in INCIDENT_FIELDS}
    payload["incident_id"] = next_id
    payload.setdefault("status", "active")
    payload.setdefault("incident_metadata", {})
    now = utc_now().isoformat()
    payload["created_at"] = payload.get("created_at") or now
    payload["updated_at"] = payload.get("updated_at") or now

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.INCIDENT,
            document_id=_anchor(effective_id),
            vault_path=VAULT_RECORDS_FILE,
            payload=payload,
            metadata={"incident_type": payload.get("incident_type"), "scope": "incidents"},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create incident for user %s: %s", user.user_id[:8], response.message)
        return None
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id) if overlay else None


async def list_incidents(
    user: UserContext, status: str | None = None, incident_type: str | None = None
) -> list[SimpleNamespace]:
    """All incidents for the user, newest updated first (legacy rows migrate first)."""
    await migrate_legacy_incidents(user)
    overlays = await _list_overlays(user)
    if status:
        overlays = [o for o in overlays if o.payload.get("status") == status]
    if incident_type:
        overlays = [o for o in overlays if o.payload.get("incident_type") == incident_type]
    overlays.sort(key=lambda o: o.payload.get("updated_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_view(o, effective_id) for o in overlays]


async def get_incident(user: UserContext, incident_id) -> SimpleNamespace | None:
    overlay = await _resolve_overlay(user, incident_id)
    if not overlay:
        return None
    return _view(overlay, user.get_effective_user_id())


async def get_incident_overlay(user: UserContext, incident_id):
    """Raw overlay access for writers that mutate pointer fields (case_builder)."""
    return await _resolve_overlay(user, incident_id)


async def update_incident(user: UserContext, incident_id, **fields) -> SimpleNamespace | None:
    overlay = await _resolve_overlay(user, incident_id)
    if not overlay:
        return None
    for key, value in fields.items():
        if key in INCIDENT_FIELDS:
            overlay.payload[key] = _to_iso(value)
    overlay.payload["updated_at"] = utc_now().isoformat()
    manager = await _get_manager(user)
    await manager.update_overlay(overlay.overlay_id, payload=overlay.payload)
    return _view(overlay, user.get_effective_user_id())


async def delete_incident(user: UserContext, incident_id) -> bool:
    overlay = await _resolve_overlay(user, incident_id)
    if not overlay:
        return False
    manager = await _get_manager(user)
    return await manager.delete_overlay(overlay.overlay_id)


async def get_incident_for_user_id(user_id: str, incident_id) -> SimpleNamespace | None:
    """user_id-only readers (packet_builder, case_builder helpers)."""
    user = await build_context_for_user_id(user_id)
    return await get_incident(user, incident_id)


async def list_incidents_for_user_id(user_id: str, status: str | None = None, incident_type: str | None = None):
    user = await build_context_for_user_id(user_id)
    return await list_incidents(user, status=status, incident_type=incident_type)


async def count_incidents_for_user_id(user_id: str) -> int:
    """Count for dashboards; returns 0 when context can't resolve (anonymous)."""
    try:
        user = await build_context_for_user_id(user_id)
        return len(await list_incidents(user))
    except Exception:
        return 0


async def migrate_legacy_incidents(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `incidents` rows. Non-destructive, idempotent
    via payload["legacy_id"]; preserves the integer PK in payload["incident_id"]
    so VaultItem.related_incident_id links keep resolving."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import Incident
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    try:
        overlays = await _list_overlays(user)
        # legacy_id == the row's incident_id for imported records, so tracking
        # imported payload ids alone makes the migration idempotent.
        migrated_ids = {
            o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id") is not None
        }
        manager = await _get_manager(user)
        imported = 0

        async with get_db_session() as db:
            result = await db.execute(
                select(Incident).where(Incident.user_id == user.user_id).order_by(Incident.incident_id).limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit or row.incident_id in migrated_ids:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.INCIDENT,
                        document_id=_anchor(effective_id),
                        vault_path=VAULT_RECORDS_FILE,
                        payload={
                            "incident_id": row.incident_id,
                            "title": row.title,
                            "description": row.description,
                            "start_date": row.start_date.isoformat() if row.start_date else None,
                            "end_date": row.end_date.isoformat() if row.end_date else None,
                            "status": row.status,
                            "incident_type": row.incident_type,
                            "severity": row.severity,
                            "incident_metadata": row.incident_metadata or {},
                            "case_overlay_id": row.case_overlay_id,
                            "fca_readiness_score": row.fca_readiness_score,
                            "fca_readiness_updated_at": row.fca_readiness_updated_at.isoformat()
                            if row.fca_readiness_updated_at
                            else None,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                            "legacy_id": row.incident_id,
                            "migrated_from": "incidents",
                        },
                        metadata={"incident_type": row.incident_type, "scope": "incidents"},
                    )
                )
                migrated_ids.add(row.incident_id)
                imported += 1
    except Exception:
        logger.exception("Legacy incident migration failed for user %s", user.user_id[:8])
        return imported

    return imported
