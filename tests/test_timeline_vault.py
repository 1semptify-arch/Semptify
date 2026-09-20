"""Functional tests for timeline events in the user vault SQLite store."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.utc import utc_now
from app.services import timeline_store
from app.services.unified_overlay_manager import UnifiedOverlayManager
from tests.test_unified_overlay_manager import FakeStorageProvider


class _FakeUser:
    provider = type("P", (), {"value": "google_drive"})()

    def __init__(self, user_id: str):
        self.user_id = user_id
        # Distinct token per user — each user's vault.db lives in their own
        # storage, so per-token stores preserve tenant isolation.
        self.access_token = f"token-{user_id}"

    def get_effective_user_id(self):
        return self.user_id


@pytest.fixture
def store_env(monkeypatch):
    managers: dict[str, UnifiedOverlayManager] = {}
    stores: dict[str, FakeStorageProvider] = {}

    def _provider(_provider_value, access_token=None):
        return stores.setdefault(access_token or "default", FakeStorageProvider())

    async def _manager(_storage, user_id):
        if user_id not in managers:
            managers[user_id] = UnifiedOverlayManager(FakeStorageProvider(), user_id)
        return managers[user_id]

    monkeypatch.setattr(timeline_store, "get_provider", _provider)
    monkeypatch.setattr(timeline_store, "get_unified_overlay_manager", _manager)
    return stores


@pytest.mark.asyncio
async def test_create_and_list_roundtrip(store_env):
    user = _FakeUser("user-1")

    event = await timeline_store.create_event(
        user,
        event_type="notice",
        title="Eviction Notice",
        event_date=utc_now(),
        description="Notice to quit",
        urgency="high",
        is_evidence=True,
        tags='["eviction_notice"]',
        attached_document_ids='["doc-1"]',
    )
    assert event.id.startswith("tevt_")
    assert event.title == "Eviction Notice"
    assert event.is_evidence is True
    # Raw JSON strings preserved (retaliation_tracker contract)
    assert event.tags == '["eviction_notice"]'

    events = await timeline_store.list_events(user)
    assert len(events) == 1
    assert events[0].id == event.id


@pytest.mark.asyncio
async def test_events_are_isolated_per_user(store_env):
    user_a = _FakeUser("user-a")
    user_b = _FakeUser("user-b")

    await timeline_store.create_event(user_a, "payment", "A Event", utc_now())
    await timeline_store.create_event(user_b, "notice", "B Event", utc_now())

    a_events = await timeline_store.list_events(user_a)
    b_events = await timeline_store.list_events(user_b)

    assert [e.title for e in a_events] == ["A Event"]
    assert [e.title for e in b_events] == ["B Event"]


@pytest.mark.asyncio
async def test_find_event_dedupe(store_env):
    user = _FakeUser("user-3")
    now = utc_now()

    await timeline_store.create_event(
        user, "filing", "Court Filing (doc.pdf)", now, document_id="doc-7"
    )

    found = await timeline_store.find_event(
        user, document_id="doc-7", event_date=now, event_type="filing"
    )
    assert found is not None

    missing = await timeline_store.find_event(
        user, document_id="doc-7", event_date=now, event_type="notice"
    )
    assert missing is None


@pytest.mark.asyncio
async def test_list_sorted_newest_first(store_env):
    user = _FakeUser("user-4")
    now = utc_now()

    await timeline_store.create_event(user, "notice", "older", now - timedelta(days=10))
    await timeline_store.create_event(user, "notice", "newer", now - timedelta(days=1))

    events = await timeline_store.list_events(user)
    assert [e.title for e in events] == ["newer", "older"]


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
        id=row_id, event_type="notice", title="Legacy Event", description=None,
        event_date=utc_now(), event_date_end=None, event_status=None,
        parent_event_id=None, sequence_number=0, source_extraction_id=None,
        footnote_number=None, highlight_color=None, urgency="normal",
        is_deadline=False, document_id=None, who_involved=None, location=None,
        attached_document_ids=None, tags=None, is_evidence=False, created_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_migrate_legacy_events_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    user = _FakeUser("user-5")
    rows = [
        _legacy_row("evt-1", title="Legacy One"),
        _legacy_row("evt-2", title="Legacy Two", tags='["subtype"]', is_evidence=True),
    ]
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(rows))

    imported_first = await timeline_store.migrate_legacy_events(user)
    imported_second = await timeline_store.migrate_legacy_events(user)

    assert imported_first == 2
    assert imported_second == 0

    events = await timeline_store.list_events(user)
    assert {e.id for e in events} == {"evt-1", "evt-2"}
    migrated = next(e for e in events if e.id == "evt-2")
    assert migrated.tags == '["subtype"]'
    assert migrated.is_evidence is True


@pytest.mark.asyncio
async def test_migrate_legacy_events_safe_without_db(store_env):
    user = _FakeUser("user-6")
    assert await timeline_store.migrate_legacy_events(user) == 0
