"""Eviction timeline store — EVICTION_TIMELINE_EVENT overlays in the tenant's vault.

Eviction-specific timeline events persist as overlays anchored to
`document_id="eviction_timeline:{user_id}"` at VAULT_TIMELINE_EVENTS_FILE.
The model was designed "structure and pointers only" — subject_id references
the accountability ledger, content_overlay_id points at the narrative PII
overlay; both pointers carry through into the payload unchanged.

Legacy `eviction_timeline_events` rows migrate on first read:
non-destructive, idempotent via `payload["legacy_id"]`, bounded 25 rows/call.

Consumers:
- `app.modules.eviction_timeline.router` — page list + event creation
- `app.modules.timeline.router` — unified timeline merge
- `app.modules.tenant_feed.service` — feed aggregation

View contract: functions return SimpleNamespace objects carrying the ORM
attribute surface (id, user_id, subject_id, event_type, event_date, source,
source_document_id, content_overlay_id, jurisdiction, created_at,
updated_at). `event_date`/`created_at`/`updated_at` are datetimes.
"""

import logging
from datetime import datetime
from types import SimpleNamespace

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext, build_context_for_user_id
from app.core.vault_paths import VAULT_TIMELINE_EVENTS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)


def _anchor(effective_id: str) -> str:
    return f"eviction_timeline:{effective_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
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


def _view(overlay, effective_id: str) -> SimpleNamespace:
    p = overlay.payload
    return SimpleNamespace(
        id=p.get("id") or overlay.overlay_id,
        user_id=effective_id,
        subject_id=p.get("subject_id"),
        event_type=p.get("event_type"),
        event_date=_parse_dt(p.get("event_date")),
        source=p.get("source") or "manual",
        source_document_id=p.get("source_document_id"),
        content_overlay_id=p.get("content_overlay_id"),
        jurisdiction=p.get("jurisdiction") or "MN",
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(
        document_id=_anchor(effective_id), overlay_type=OverlayType.EVICTION_TIMELINE_EVENT
    )
    if not response.success:
        logger.warning("Eviction timeline list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if _owns(effective_id, o)]


async def list_events(user: UserContext) -> list[SimpleNamespace]:
    """All eviction timeline events for the user, newest event_date first."""
    await migrate_legacy_events(user)
    overlays = await _list_overlays(user)
    views = [_view(o, user.get_effective_user_id()) for o in overlays]
    views.sort(key=lambda v: v.event_date or v.created_at or datetime.min, reverse=True)
    return views


async def list_events_for_user_id(user_id: str) -> list[SimpleNamespace]:
    """user_id-only reader for timeline merge + tenant feed."""
    try:
        user = await build_context_for_user_id(user_id)
    except Exception:
        return []
    return await list_events(user)


async def create_event(
    user: UserContext,
    event_type: str,
    event_date: datetime,
    source: str = "manual",
    subject_id: str | None = None,
    jurisdiction: str = "MN",
    source_document_id: str | None = None,
    content_overlay_id: str | None = None,
) -> SimpleNamespace:
    """Create an eviction timeline event overlay."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)
    event_id = make_id("ete")
    now = utc_now().isoformat()
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.EVICTION_TIMELINE_EVENT,
            document_id=_anchor(effective_id),
            vault_path=VAULT_TIMELINE_EVENTS_FILE,
            payload={
                "id": event_id,
                "subject_id": subject_id,
                "event_type": event_type,
                "event_date": event_date.isoformat() if event_date else None,
                "source": source,
                "source_document_id": source_document_id,
                "content_overlay_id": content_overlay_id,
                "jurisdiction": jurisdiction,
                "created_at": now,
                "updated_at": now,
            },
            metadata={"event_type": event_type, "scope": "eviction_timeline"},
        )
    )
    if not response.success or not response.overlay_id:
        raise RuntimeError(f"Failed to persist eviction timeline event: {response.message}")
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id)


async def migrate_legacy_events(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `eviction_timeline_events` rows.
    Non-destructive, idempotent via payload["legacy_id"]."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import EvictionTimelineEvent
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    imported = 0
    try:
        overlays = await _list_overlays(user)
        migrated = {o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id")}
        manager = await _get_manager(user)

        async with get_db_session() as db:
            result = await db.execute(
                select(EvictionTimelineEvent).where(EvictionTimelineEvent.user_id == user.user_id).limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit or row.id in migrated:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.EVICTION_TIMELINE_EVENT,
                        document_id=_anchor(effective_id),
                        vault_path=VAULT_TIMELINE_EVENTS_FILE,
                        payload={
                            "id": row.id,
                            "subject_id": row.subject_id,
                            "event_type": row.event_type,
                            "event_date": row.event_date.isoformat() if row.event_date else None,
                            "source": row.source,
                            "source_document_id": row.source_document_id,
                            "content_overlay_id": row.content_overlay_id,
                            "jurisdiction": row.jurisdiction,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                            "legacy_id": row.id,
                            "migrated_from": "eviction_timeline_events",
                        },
                        metadata={"event_type": row.event_type, "scope": "eviction_timeline"},
                    )
                )
                migrated.add(row.id)
                imported += 1
    except Exception:
        logger.exception("Legacy eviction timeline migration failed for user %s", user.user_id[:8])
        return imported

    return imported
