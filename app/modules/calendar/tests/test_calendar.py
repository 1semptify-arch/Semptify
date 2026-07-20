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
    from datetime import datetime
    from unittest.mock import MagicMock

    from app.modules.calendar.router import _model_to_response

    event = MagicMock()
    event.id = "cal_abc123"
    event.title = "Court Hearing"
    event.description = "Hearing at 9am"
    event.start_datetime = datetime(2026, 8, 1, 9, 0, 0, tzinfo=UTC)
    event.end_datetime = None
    event.all_day = False
    event.event_type = "hearing"
    event.is_critical = True
    event.reminder_days = 1
    event.source = "document_extraction"
    event.linked_record_id = "hearing:user_1"
    event.created_at = datetime(2026, 7, 20, 10, 0, 0, tzinfo=UTC)
    event.updated_at = datetime(2026, 7, 20, 10, 0, 0, tzinfo=UTC)

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

    # Mock a single rent payment with a due date.
    payment = MagicMock()
    payment.id = "rnt_001"
    payment.user_id = "user_1"
    payment.entry_type = "payment"
    payment.due_date = datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC)
    payment.payment_date = datetime(2026, 8, 5, 0, 0, 0, tzinfo=UTC)
    payment.period_covered = "2026-08"
    payment.status = "paid"

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[payment])

    execute_result = MagicMock()
    execute_result.scalars = MagicMock(return_value=scalars)

    from unittest.mock import MagicMock

    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    with (
        patch("app.services.calendar_sync.get_document_hub", return_value=hub),
        patch("app.services.calendar_sync.select") as mock_select,
    ):
        # The first call to select is for existing keys/clear; second for RentPayment.
        mock_select.return_value.where.return_value.where.return_value = MagicMock()
        result = await sync_calendar_for_user("user_1", db=db)

    assert result["document_events"] == 2
    assert result["rent_events"] == 1
    assert result["total"] == 3
    assert len(result["synced_event_ids"]) == 3
    db.commit.assert_awaited()
