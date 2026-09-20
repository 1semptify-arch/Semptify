"""Timeline event store — TIMELINE_EVENT overlays in the tenant's vault.

Timeline events (notices, payments, maintenance, communications, court
events, quick captures, document uploads) persist as overlays anchored to
`document_id="timeline:{user_id}"` at VAULT_TIMELINE_EVENTS_FILE. Legacy
`timeline_events` rows migrate on first read: non-destructive, idempotent
via `payload["legacy_id"]`, bounded 25 rows/call.

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
`tags`/`attached_document_ids` stay raw JSON-array strings (or None) to
match the ORM contract (`retaliation_tracker.parse_event_tags` reads them).
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

# Payload keys that hold ISO datetimes (everything else passes through).
_DATETIME_FIELDS = ("event_date", "event_date_end", "created_at")


def _anchor(effective_id: str) -> str:
    return f"timeline:{effective_id}"


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
        event_type=p.get("event_type"),
        title=p.get("title"),
        description=p.get("description"),
        event_date=_parse_dt(p.get("event_date")),
        event_date_end=_parse_dt(p.get("event_date_end")),
        event_status=p.get("event_status"),
        parent_event_id=p.get("parent_event_id"),
        sequence_number=p.get("sequence_number") or 0,
        source_extraction_id=p.get("source_extraction_id"),
        footnote_number=p.get("footnote_number"),
        highlight_color=p.get("highlight_color"),
        urgency=p.get("urgency") or "normal",
        is_deadline=bool(p.get("is_deadline", False)),
        document_id=p.get("document_id"),
        who_involved=p.get("who_involved"),
        location=p.get("location"),
        attached_document_ids=p.get("attached_document_ids"),
        tags=p.get("tags"),
        is_evidence=bool(p.get("is_evidence", False)),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
    )


async def _list_overlays(user: UserContext) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(
        document_id=_anchor(effective_id), overlay_type=OverlayType.TIMELINE_EVENT
    )
    if not response.success:
        logger.warning("Timeline event list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if _owns(effective_id, o)]


async def list_events(user: UserContext) -> list[SimpleNamespace]:
    """All timeline events for the user, newest event_date first."""
    await migrate_legacy_events(user)
    overlays = await _list_overlays(user)
    views = [_view(o, user.get_effective_user_id()) for o in overlays]
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
    """Create a timeline event overlay. `fields` accepts any payload key:
    description, event_date_end, event_status, parent_event_id,
    sequence_number, source_extraction_id, footnote_number, highlight_color,
    urgency, is_deadline, is_evidence, document_id, who_involved, location,
    attached_document_ids, tags, plus extension keys (importance,
    auto_generated, source_document_id→document_id)."""
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)

    if "source_document_id" in fields and "document_id" not in fields:
        fields["document_id"] = fields.pop("source_document_id")

    event_id = make_id("tevt")
    now = utc_now().isoformat()
    payload = {
        "id": event_id,
        "event_type": event_type,
        "title": title,
        "event_date": (event_date or utc_now()).isoformat(),
        "sequence_number": 0,
        "urgency": "normal",
        "is_deadline": False,
        "is_evidence": False,
        "created_at": now,
    }
    for key, value in fields.items():
        if isinstance(value, datetime):
            payload[key] = value.isoformat()
        else:
            payload[key] = value

    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.TIMELINE_EVENT,
            document_id=_anchor(effective_id),
            vault_path=VAULT_TIMELINE_EVENTS_FILE,
            payload=payload,
            metadata={"event_type": event_type, "scope": "timeline"},
        )
    )
    if not response.success or not response.overlay_id:
        raise RuntimeError(f"Failed to persist timeline event: {response.message}")
    overlay = await manager.get_overlay(response.overlay_id)
    return _view(overlay, effective_id)


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


async def migrate_legacy_events(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy `timeline_events` rows. Non-destructive,
    idempotent via payload["legacy_id"]."""
    try:
        from sqlalchemy import select

        from app.core.database import get_db_session
        from app.models.models import TimelineEvent
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
                select(TimelineEvent).where(TimelineEvent.user_id == user.user_id).limit(limit)
            )
            for row in result.scalars().all():
                if imported >= limit or row.id in migrated:
                    continue
                await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.TIMELINE_EVENT,
                        document_id=_anchor(effective_id),
                        vault_path=VAULT_TIMELINE_EVENTS_FILE,
                        payload={
                            "id": row.id,
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
                            "legacy_id": row.id,
                            "migrated_from": "timeline_events",
                        },
                        metadata={"event_type": row.event_type, "scope": "timeline"},
                    )
                )
                migrated.add(row.id)
                imported += 1
    except Exception:
        logger.exception("Legacy timeline event migration failed for user %s", user.user_id[:8])
        return imported

    return imported
