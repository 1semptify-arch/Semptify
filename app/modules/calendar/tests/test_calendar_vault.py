"""Calendar vault-persistence tests.

Exercises the Unified Overlay backed calendar store (service.py) end-to-end
with an in-memory storage provider: create/list/get/update/delete, per-user
isolation, legacy-id resolution, date-range filtering, and auto-sync helpers
(delete_source_events / existing_link_keys).

Run locally: python -m pytest app/modules/calendar/tests/test_calendar_vault.py -v
"""

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.calendar import service
from tests.test_unified_overlay_manager import FakeStorageProvider


def _make_user(user_id: str, token: str) -> UserContext:
    return UserContext(
        user_id=user_id,
        provider=StorageProvider.GOOGLE_DRIVE,
        storage_user_id=f"drv_{user_id}",
        access_token=token,
        role=UserRole.USER,
    )


@pytest.fixture
def storages(monkeypatch):
    """Map access_token -> FakeStorageProvider so each user gets own vault."""
    stores: dict[str, FakeStorageProvider] = {}

    def fake_get_provider(provider_value: str, access_token: str | None = None):
        _ = provider_value
        return stores.setdefault(access_token or "default", FakeStorageProvider())

    monkeypatch.setattr(service, "get_provider", fake_get_provider)
    return stores


def _event_kwargs(**overrides):
    base = {
        "title": "Court Hearing",
        "description": "Hearing at 9am",
        "start_datetime": "2026-09-15T09:00:00+00:00",
        "end_datetime": None,
        "all_day": False,
        "event_type": "hearing",
        "is_critical": True,
        "reminder_days": 3,
        "source": "manual",
        "linked_record_id": None,
    }
    base.update(overrides)
    return base


@pytest.mark.anyio
async def test_create_list_get_update_delete_roundtrip(storages):
    user = _make_user("GUalice001", "tok-a")

    created = await service.create_event(user, **_event_kwargs())
    assert created.overlay_id
    assert created.overlay_type.value == "calendar_event"
    assert created.created_by == "GUalice001"
    assert created.payload["source"] == "manual"

    events, total = await service.list_events(user)
    assert total == 1
    assert events[0].overlay_id == created.overlay_id

    fetched = await service.get_event(user, created.overlay_id)
    assert fetched is not None
    assert fetched.payload["title"] == "Court Hearing"
    assert fetched.payload["event_type"] == "hearing"

    updated = await service.update_event(
        user, created.overlay_id, {"is_critical": False, "title": "Mediation"}
    )
    assert updated is not None
    assert updated.payload["is_critical"] is False
    assert updated.payload["title"] == "Mediation"
    assert updated.payload["event_type"] == "hearing"

    assert await service.delete_event(user, created.overlay_id) is True
    assert await service.get_event(user, created.overlay_id) is None


@pytest.mark.anyio
async def test_events_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    created = await service.create_event(alice, **_event_kwargs())

    bob_events, bob_total = await service.list_events(bob)
    assert bob_total == 0
    assert bob_events == []
    assert await service.get_event(bob, created.overlay_id) is None
    assert await service.update_event(bob, created.overlay_id, {"title": "x"}) is None
    assert await service.delete_event(bob, created.overlay_id) is False


@pytest.mark.anyio
async def test_list_filters_by_date_range_type_and_critical(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_event(user, **_event_kwargs(
        title="Past", start_datetime="2026-07-01T00:00:00+00:00", is_critical=False, event_type="reminder"
    ))
    await service.create_event(user, **_event_kwargs(
        title="Soon", start_datetime="2026-09-15T00:00:00+00:00", event_type="deadline"
    ))
    await service.create_event(user, **_event_kwargs(
        title="Later", start_datetime="2026-12-01T00:00:00+00:00", is_critical=False, event_type="hearing"
    ))

    from datetime import UTC, datetime

    events, total = await service.list_events(
        user,
        start=datetime(2026, 9, 1, tzinfo=UTC),
        end=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert total == 1
    assert events[0].payload["title"] == "Soon"

    events, total = await service.list_events(user, event_type="hearing")
    assert total == 1
    assert events[0].payload["title"] == "Later"

    events, total = await service.list_events(user, critical_only=True)
    assert total == 1
    assert events[0].payload["title"] == "Soon"

    events, total = await service.list_events(user)
    assert total == 3
    # Sorted by start ascending
    assert [e.payload["title"] for e in events] == ["Past", "Soon", "Later"]


@pytest.mark.anyio
async def test_get_event_resolves_legacy_payload_id(storages):
    user = _make_user("GUalice001", "tok-a")
    created = await service.create_event(user, **_event_kwargs())
    # In the SQLite store the row id IS the payload id — lookups by either
    # the view's overlay_id or the payload id resolve to the same row.
    legacy_id = created.payload["id"]
    assert legacy_id == created.overlay_id

    fetched = await service.get_event(user, legacy_id)
    assert fetched is not None
    assert fetched.overlay_id == created.overlay_id


@pytest.mark.anyio
async def test_auto_sync_helpers_delete_only_auto_sources(storages, monkeypatch):
    user = _make_user("GUalice001", "tok-a")

    await service.create_event(user, **_event_kwargs(title="Manual one", source="manual"))
    auto = await service.create_event(
        user,
        **_event_kwargs(title="Auto one", source="rent_ledger", linked_record_id="rent:due:rnt_1"),
    )

    # Helpers take a bare user_id — rebuild context via ensure_valid_token.
    async def fake_ctx(user_id: str):
        return user

    monkeypatch.setattr("app.core.user_context.build_context_for_user_id", fake_ctx)

    keys = await service.existing_link_keys("GUalice001", ("document_extraction", "rent_ledger"))
    assert keys == {"rent:due:rnt_1"}

    deleted = await service.delete_source_events("GUalice001", ("document_extraction", "rent_ledger"))
    assert deleted == 1

    events, total = await service.list_events(user)
    assert total == 1
    assert events[0].payload["title"] == "Manual one"
    assert await service.get_event(user, auto.overlay_id) is None


@pytest.mark.anyio
async def test_create_event_for_user_id(storages, monkeypatch):
    user = _make_user("GUalice001", "tok-a")

    async def fake_ctx(user_id: str):
        return user

    monkeypatch.setattr("app.core.user_context.build_context_for_user_id", fake_ctx)

    oid = await service.create_event_for_user_id("GUalice001", **_event_kwargs(source="document_extraction"))
    assert oid is not None

    events, total = await service.list_events(user)
    assert total == 1
    assert events[0].payload["source"] == "document_extraction"


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.migrate_legacy_events(user) == 0
