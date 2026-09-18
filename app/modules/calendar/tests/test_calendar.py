"""Calendar module smoke tests."""

from datetime import UTC

import pytest


def test_calendar_router_is_fastapi_router():
    """Calendar router is an APIRouter instance."""
    from fastapi import APIRouter

    from app.modules.calendar.router import router

    assert isinstance(router, APIRouter)


def test_calendar_router_has_core_routes():
    """Calendar router exposes list, sync, and document-sync routes."""
    from app.modules.calendar.router import router

    methods_by_path = {}
    for r in router.routes:
        for m in r.methods:
            methods_by_path.setdefault(r.path, set()).add(m)

    assert "/" in methods_by_path and "GET" in methods_by_path["/"]
    assert "/" in methods_by_path and "POST" in methods_by_path["/"]
    assert "/sync-documents" in methods_by_path and "POST" in methods_by_path["/sync-documents"]
    assert "/from-documents" in methods_by_path and "GET" in methods_by_path["/from-documents"]


def test_calendar_contracts_registered():
    """Calendar module contracts are registered."""
    import app.modules.calendar.register  # noqa: F401
    from app.core.module_contracts import contract_registry

    for name in (
        "calendar_create_event",
        "calendar_list_events",
        "calendar_upcoming_deadlines",
        "calendar_get_event",
        "calendar_update_event",
        "calendar_delete_event",
        "calendar_from_documents",
        "calendar_sync_documents",
        "calendar_deadline_summary",
        "calendar_notify_deadlines",
    ):
        contract = contract_registry.get("calendar", name)
        assert contract is not None, f"Missing contract calendar::{name}"


def test_model_to_response_includes_source_and_links():
    """_model_to_response surfaces source, linked_record_id, and updated_at."""
    from app.core.overlay_types import OverlayType
    from app.models.unified_overlay_models import UnifiedOverlay
    from app.modules.calendar.router import _model_to_response

    event = UnifiedOverlay(
        overlay_id="ovl_cal_abc123",
        overlay_type=OverlayType.CALENDAR_EVENT,
        document_id="calendar:user_1",
        vault_path="Semptify5.0/Vault/calendar/calendar.json",
        created_by="user_1",
        payload={
            "id": "cal_abc123",
            "title": "Court Hearing",
            "description": "Hearing at 9am",
            "start_datetime": "2026-08-01T09:00:00+00:00",
            "end_datetime": None,
            "all_day": False,
            "event_type": "hearing",
            "is_critical": True,
            "reminder_days": 1,
            "source": "document_extraction",
            "linked_record_id": "hearing:user_1",
            "created_at": "2026-07-20T10:00:00+00:00",
            "updated_at": "2026-07-20T10:00:00+00:00",
        },
    )

    result = _model_to_response(event)
    assert result.source == "document_extraction"
    assert result.linked_record_id == "hearing:user_1"
    assert result.updated_at is not None


def test_parse_datetime_variants():
    """_parse_datetime handles ISO, date-only, and date strings."""
    from datetime import datetime

    from app.services.calendar_sync import _parse_datetime

    assert _parse_datetime("2026-08-01") == datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC)
    assert _parse_datetime("2026-08-01T12:00:00Z") == datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
    assert _parse_datetime("08/15/2026") == datetime(2026, 8, 15, 0, 0, 0, tzinfo=UTC)
    assert _parse_datetime("") is None
    assert _parse_datetime(None) is None


def test_event_link_keys_are_stable():
    """Event link keys remain stable across sync runs."""
    from app.services.calendar_sync import _event_link_key, _rent_link_key

    event = {"type": "hearing", "title": "Court Hearing", "date": "2026-08-01"}
    assert _event_link_key(event) == "hearing:Court Hearing:2026-08-01"
    assert _rent_link_key("due", "rnt_001") == "rent:due:rnt_001"


@pytest.mark.asyncio
async def test_sync_calendar_for_user_creates_auto_events():
    """sync_calendar_for_user creates document and rent ledger events."""
    from datetime import datetime
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.services.calendar_sync import sync_calendar_for_user

    # Mock DocumentHub to return one hearing and one deadline.
    hub = MagicMock()
    hub.get_case_data = MagicMock()
    hub.get_calendar_events = MagicMock(
        return_value=[
            {
                "id": "hearing_user1",
                "title": "Court Hearing",
                "date": "2026-08-01",
                "type": "hearing",
                "critical": True,
            },
            {
                "id": "deadline_user1",
                "title": "Answer Deadline",
                "date": "2026-07-25",
                "type": "deadline",
                "critical": True,
            },
        ]
    )

    # Mock a single rent ledger overlay with a due date.
    from app.core.overlay_types import OverlayType
    from app.models.unified_overlay_models import UnifiedOverlay

    payment_overlay = UnifiedOverlay(
        overlay_id="ovl_rnt001",
        overlay_type=OverlayType.RENT_LEDGER_ENTRY,
        document_id="ledger:user_1",
        vault_path="Semptify5.0/Vault/ledger/ledger.json",
        created_by="user_1",
        payload={
            "id": "rnt_001",
            "entry_type": "payment",
            "due_date": "2026-08-01T00:00:00+00:00",
            "payment_date": "2026-08-05T00:00:00+00:00",
            "period_covered": "2026-08",
            "status": "paid",
        },
    )

    created_ids = []

    async def _fake_create(user_id, **fields):
        oid = f"ovl_{len(created_ids):03d}"
        created_ids.append((oid, fields))
        return oid

    with (
        patch("app.services.calendar_sync.get_document_hub", return_value=hub),
        patch(
            "app.modules.rent.service.list_entries_for_user_id",
            new=AsyncMock(return_value=([payment_overlay], 1)),
        ),
        patch(
            "app.modules.calendar.service.create_event_for_user_id",
            new=_fake_create,
        ),
        patch(
            "app.modules.calendar.service.delete_source_events",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.modules.calendar.service.existing_link_keys",
            new=AsyncMock(return_value=set()),
        ),
    ):
        result = await sync_calendar_for_user("user_1")

    assert result["document_events"] == 2
    assert result["rent_events"] == 1
    assert result["total"] == 3
    assert len(result["synced_event_ids"]) == 3
    sources = {fields["source"] for _oid, fields in created_ids}
    assert sources == {"document_extraction", "rent_ledger"}
