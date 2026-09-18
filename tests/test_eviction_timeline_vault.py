"""Functional tests for eviction timeline overlays in the user vault."""

from types import SimpleNamespace

import pytest

from app.core.utc import utc_now
from app.services import eviction_timeline_store
from app.services.unified_overlay_manager import UnifiedOverlayManager
from tests.test_unified_overlay_manager import FakeStorageProvider


class _FakeUser:
    provider = type("P", (), {"value": "google_drive"})()

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.access_token = "token"

    def get_effective_user_id(self):
        return self.user_id


@pytest.fixture
def store_env(monkeypatch):
    managers: dict[str, UnifiedOverlayManager] = {}

    async def _manager(_storage, user_id):
        if user_id not in managers:
            managers[user_id] = UnifiedOverlayManager(FakeStorageProvider(), user_id)
        return managers[user_id]

    monkeypatch.setattr(eviction_timeline_store, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(eviction_timeline_store, "get_unified_overlay_manager", _manager)
    return managers


@pytest.mark.asyncio
async def test_create_and_list_roundtrip(store_env):
    user = _FakeUser("user-1")

    event = await eviction_timeline_store.create_event(
        user,
        event_type="court_filing",
        event_date=utc_now(),
        source="court",
        subject_id="sub-1",
        source_document_id="doc-9",
        content_overlay_id="ovl-x",
    )
    assert event.id.startswith("ete_")
    assert event.event_type == "court_filing"
    assert event.subject_id == "sub-1"
    assert event.content_overlay_id == "ovl-x"

    events = await eviction_timeline_store.list_events(user)
    assert len(events) == 1
    assert events[0].id == event.id


@pytest.mark.asyncio
async def test_events_are_isolated_per_user(store_env):
    user_a = _FakeUser("user-a")
    user_b = _FakeUser("user-b")

    await eviction_timeline_store.create_event(user_a, "notice", utc_now(), source="manual")
    await eviction_timeline_store.create_event(user_b, "hearing", utc_now(), source="court")

    a_events = await eviction_timeline_store.list_events(user_a)
    b_events = await eviction_timeline_store.list_events(user_b)

    assert [e.event_type for e in a_events] == ["notice"]
    assert [e.event_type for e in b_events] == ["hearing"]


@pytest.mark.asyncio
async def test_list_sorted_newest_first(store_env):
    from datetime import timedelta

    user = _FakeUser("user-3")
    now = utc_now()

    await eviction_timeline_store.create_event(user, "older", now - timedelta(days=10))
    await eviction_timeline_store.create_event(user, "newer", now - timedelta(days=1))

    events = await eviction_timeline_store.list_events(user)
    assert [e.event_type for e in events] == ["newer", "older"]


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _query):
        return _FakeResult(self._rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _legacy_row(row_id: str, **overrides):
    base = dict(
        id=row_id, subject_id=None, event_type="notice", event_date=utc_now(),
        source="manual", source_document_id=None, content_overlay_id=None,
        jurisdiction="MN", created_at=None, updated_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_migrate_legacy_events_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    user = _FakeUser("user-4")
    rows = [
        _legacy_row("ete-1", event_type="notice"),
        _legacy_row("ete-2", event_type="filing", subject_id="sub-9"),
    ]
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(rows))

    imported_first = await eviction_timeline_store.migrate_legacy_events(user)
    imported_second = await eviction_timeline_store.migrate_legacy_events(user)

    assert imported_first == 2
    assert imported_second == 0

    events = await eviction_timeline_store.list_events(user)
    assert {e.id for e in events} == {"ete-1", "ete-2"}
    assert next(e for e in events if e.id == "ete-2").subject_id == "sub-9"


@pytest.mark.asyncio
async def test_migrate_legacy_events_safe_without_db(store_env):
    user = _FakeUser("user-5")
    assert await eviction_timeline_store.migrate_legacy_events(user) == 0
