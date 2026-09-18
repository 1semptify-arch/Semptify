"""
Calendar Service
================
Per-user calendar store backed by the Unified Overlay System.

Each event is a CALENDAR_EVENT overlay anchored to document_id="calendar:{user_id}"
in the user's own cloud storage — same pattern as journal and the rent ledger.
Manual and auto-synced events (document_extraction, rent_ledger) live in the
same store; auto-synced events carry payload["source"] + payload["linked_record_id"]
for idempotent refresh by calendar_sync. No server-side database rows:
the tenant's records live in the tenant's vault (vault-persistence-migration,
Phase 1).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_CALENDAR_FILE
from app.models.models import CalendarEvent as CalendarEventModel
from app.models.unified_overlay_models import CreateOverlayRequest, UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)


def get_calendar_anchor_id(user_id: str) -> str:
    """Return the per-user calendar document_id anchor."""
    return f"calendar:{user_id}"


def get_calendar_vault_path() -> str:
    """Return the canonical vault path used as the calendar anchor."""
    return VAULT_CALENDAR_FILE


async def _get_overlay_manager(user: UserContext):
    """Build an overlay manager for the current user's cloud storage.

    The manager is labelled with the *effective* user id so events created
    during support impersonation belong to the impersonated tenant — matching
    the legacy user_id=effective_id column semantics.
    """
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _owns(user: UserContext, overlay: UnifiedOverlay) -> bool:
    """True if the overlay is a calendar event owned by the effective user."""
    return (
        overlay.overlay_type == OverlayType.CALENDAR_EVENT
        and overlay.created_by == user.get_effective_user_id()
    )


def _owns_id(effective_id: str, overlay: UnifiedOverlay) -> bool:
    """Ownership check for helpers that only have a user id."""
    return overlay.overlay_type == OverlayType.CALENDAR_EVENT and overlay.created_by == effective_id


def _start_key(overlay: UnifiedOverlay) -> str:
    """Sort key: payload start_datetime falling back to creation time."""
    return overlay.payload.get("start_datetime") or overlay.created_at.isoformat()


def _to_iso(value) -> str | None:
    """Normalize a datetime/ISO-string field to an ISO string for the payload."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


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
) -> UnifiedOverlay:
    """Create a calendar event overlay in the user's cloud."""
    manager = await _get_overlay_manager(user)
    request = CreateOverlayRequest(
        overlay_type=OverlayType.CALENDAR_EVENT,
        document_id=get_calendar_anchor_id(user.get_effective_user_id()),
        vault_path=get_calendar_vault_path(),
        payload={
            "id": make_id("cal"),
            "title": title,
            "description": description,
            "start_datetime": _to_iso(start_datetime),
            "end_datetime": _to_iso(end_datetime),
            "all_day": all_day,
            "event_type": event_type,
            "is_critical": is_critical,
            "reminder_days": reminder_days,
            "source": source,
            "linked_record_id": linked_record_id,
        },
        metadata={
            "event_type": event_type,
            "is_critical": is_critical,
            "source": source,
            "scope": "calendar",
        },
    )
    response = await manager.create_overlay(request)
    if not response.success or not response.overlay_id:
        logger.error("Failed to create calendar event for user %s: %s", user.user_id[:8], response.message)
        raise RuntimeError(f"Could not save calendar event: {response.message}")

    overlay = await manager.get_overlay(response.overlay_id)
    if overlay is None:
        raise RuntimeError("Calendar event was reported as created but cannot be retrieved")
    return overlay


async def list_events(
    user: UserContext,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    event_type: str | None = None,
    critical_only: bool = False,
    skip: int = 0,
    limit: int = 500,
) -> tuple[list[UnifiedOverlay], int]:
    """Return (events, total) for the user, sorted by start_datetime ascending.

    Datetime filters accept aware datetimes; payload values are ISO strings so
    comparison is done on ISO-normalized strings (ISO-8601 sorts correctly).
    """
    await migrate_legacy_events(user)
    manager = await _get_overlay_manager(user)
    response = await manager.get_overlays(
        document_id=get_calendar_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.CALENDAR_EVENT,
    )
    if not response.success:
        logger.error("Failed to list calendar events for user %s: %s", user.user_id[:8], response.filters_applied)
        return [], 0

    events = [o for o in response.overlays if _owns(user, o)]
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None
    if start_iso:
        events = [o for o in events if (o.payload.get("start_datetime") or "") >= start_iso]
    if end_iso:
        events = [o for o in events if (o.payload.get("start_datetime") or "") <= end_iso]
    if event_type:
        events = [o for o in events if o.payload.get("event_type") == event_type]
    if critical_only:
        events = [o for o in events if o.payload.get("is_critical")]
    events.sort(key=_start_key)
    return events[skip : skip + limit], len(events)


async def list_events_for_user_id(
    user_id: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    event_type: str | None = None,
    critical_only: bool = False,
) -> tuple[list[UnifiedOverlay], int]:
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


async def _resolve_event(manager, user: UserContext, event_id: str) -> UnifiedOverlay | None:
    """Resolve an event by overlay id, or by a legacy ``cal_`` id carried in
    the overlay payload for migrated rows."""
    overlay = await manager.get_overlay(event_id)
    if overlay is not None and _owns(user, overlay):
        return overlay

    response = await manager.get_overlays(
        document_id=get_calendar_anchor_id(user.get_effective_user_id()),
        overlay_type=OverlayType.CALENDAR_EVENT,
    )
    if not response.success:
        return None
    for candidate in response.overlays:
        if _owns(user, candidate) and (
            candidate.payload.get("id") == event_id or candidate.payload.get("legacy_id") == event_id
        ):
            return candidate
    return None


async def get_event(user: UserContext, event_id: str) -> UnifiedOverlay | None:
    """Get a single calendar event by id, ownership-checked."""
    manager = await _get_overlay_manager(user)
    return await _resolve_event(manager, user, event_id)


async def update_event(user: UserContext, event_id: str, fields: dict) -> UnifiedOverlay | None:
    """Merge fields into an event's payload. Datetime values are normalized
    to ISO strings. Returns the updated overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_event(manager, user, event_id)
    if overlay is None:
        return None

    normalized = {k: _to_iso(v) if k.endswith("_datetime") else v for k, v in fields.items()}
    overlay.payload.update(normalized)
    overlay.payload["updated_at"] = utc_now().isoformat()
    if not await manager.update_overlay(overlay.overlay_id, payload=overlay.payload):
        return None
    return await manager.get_overlay(overlay.overlay_id)


async def delete_event(user: UserContext, event_id: str) -> bool:
    """Delete a calendar event overlay."""
    manager = await _get_overlay_manager(user)
    overlay = await _resolve_event(manager, user, event_id)
    if overlay is None:
        return False
    return await manager.delete_overlay(overlay.overlay_id)


# ---------------------------------------------------------------------------
# Auto-sync helpers (calendar_sync) — caller only has a user_id
# ---------------------------------------------------------------------------


async def existing_link_keys(user_id: str, sources: tuple[str, ...]) -> set[str]:
    """Return the set of payload linked_record_id values already stored for
    the given auto sources. Empty set when context cannot be rebuilt."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return set()
    effective_id = context.get_effective_user_id()
    manager = await _get_overlay_manager(context)
    response = await manager.get_overlays(
        document_id=get_calendar_anchor_id(effective_id),
        overlay_type=OverlayType.CALENDAR_EVENT,
    )
    if not response.success:
        return set()
    return {
        o.payload["linked_record_id"]
        for o in response.overlays
        if _owns_id(effective_id, o)
        and o.payload.get("source") in sources
        and o.payload.get("linked_record_id")
    }


async def delete_source_events(user_id: str, sources: tuple[str, ...]) -> int:
    """Delete all calendar overlays whose payload source is in ``sources``
    (the overwrite path of calendar_sync). Returns count deleted."""
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return 0
    effective_id = context.get_effective_user_id()
    manager = await _get_overlay_manager(context)
    response = await manager.get_overlays(
        document_id=get_calendar_anchor_id(effective_id),
        overlay_type=OverlayType.CALENDAR_EVENT,
    )
    if not response.success:
        return 0
    deleted = 0
    for overlay in response.overlays:
        if _owns_id(effective_id, overlay) and overlay.payload.get("source") in sources:
            if await manager.delete_overlay(overlay.overlay_id):
                deleted += 1
    return deleted


async def create_event_for_user_id(user_id: str, **fields) -> str | None:
    """create_event for callers that only have a user_id (calendar_sync,
    setup). Returns the new overlay id, or None when context/creation fails.
    """
    from app.core.user_context import build_context_for_user_id

    context = await build_context_for_user_id(user_id)
    if context is None:
        return None
    try:
        overlay = await create_event(context, **fields)
    except Exception as e:
        logger.error("Auto calendar event create failed for %s***: %s", user_id[:6], e)
        return None
    return overlay.overlay_id


# ---------------------------------------------------------------------------
# Legacy database migration (non-destructive, idempotent)
# ---------------------------------------------------------------------------
# Rows written before the vault-persistence migration still live in the
# calendar_events table. migrate_legacy_events() imports them into the user's
# vault as CALENDAR_EVENT overlays marked with payload["legacy_id"], so repeat
# runs never duplicate. Source rows are left in place until the table-drop
# phase — this step moves data, it does not delete history.


async def migrate_legacy_events(user: UserContext, max_rows: int = 25) -> int:
    """Import legacy DB calendar rows into vault overlays.

    Bounded to ``max_rows`` per call to stay inside the provider-work budget;
    repeat calls continue where the last one left off (idempotent via
    ``legacy_id``). Returns the count imported this call.
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

    manager = await _get_overlay_manager(user)
    existing = await manager.get_overlays(
        document_id=get_calendar_anchor_id(effective_id),
        overlay_type=OverlayType.CALENDAR_EVENT,
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
                overlay_type=OverlayType.CALENDAR_EVENT,
                document_id=get_calendar_anchor_id(effective_id),
                vault_path=get_calendar_vault_path(),
                payload={
                    "id": row.id,
                    "legacy_id": row.id,
                    "title": row.title or "",
                    "description": row.description,
                    "start_datetime": row.start_datetime.isoformat() if row.start_datetime else None,
                    "end_datetime": row.end_datetime.isoformat() if row.end_datetime else None,
                    "all_day": bool(row.all_day),
                    "event_type": row.event_type or "reminder",
                    "is_critical": bool(row.is_critical),
                    "reminder_days": row.reminder_days,
                    "source": row.source or "manual",
                    "linked_record_id": row.linked_record_id,
                },
                metadata={
                    "migrated_from": "calendar_events",
                    "legacy_created_at": row.created_at.isoformat() if row.created_at else None,
                    "scope": "calendar",
                },
            )
        )
        if response.success:
            imported += 1
        else:
            logger.error("Failed to migrate calendar row %s: %s", row.id, response.message)
    if imported:
        logger.info("Migrated %d legacy calendar events to vault for user %s", imported, effective_id[:8])
    return imported
