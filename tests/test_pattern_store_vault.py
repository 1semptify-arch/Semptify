"""Functional tests for pattern-record overlays in the user vault."""

from types import SimpleNamespace

import pytest

from app.core.utc import utc_now
from app.services import pattern_store
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
    monkeypatch.setenv("ENABLE_PATTERN_PERSISTENCE", "true")
    managers: dict[str, UnifiedOverlayManager] = {}

    async def _manager(_storage, user_id):
        if user_id not in managers:
            managers[user_id] = UnifiedOverlayManager(FakeStorageProvider(), user_id)
        return managers[user_id]

    monkeypatch.setattr(pattern_store, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(pattern_store, "get_unified_overlay_manager", _manager)
    return managers


def _summary(risk_score=42, risk_level="medium", types=("fee_spike", "notice_gap")):
    return {
        "summary": {"risk_score": risk_score, "risk_level": risk_level},
        "patterns": [{"type": t} for t in types],
    }


@pytest.mark.asyncio
async def test_save_and_history_roundtrip(store_env):
    user = _FakeUser("user-1")

    record = await pattern_store.save_pattern_record(
        user, "comprehensive", _summary(), data_sources={"docs": 3}, notes=None
    )
    assert record.id == 1
    assert record.risk_score == 42
    assert record.risk_level == "medium"
    assert record.pattern_count == 2
    assert set(record.pattern_types) == {"fee_spike", "notice_gap"}
    assert record.to_dict()["analysis_type"] == "comprehensive"

    history = await pattern_store.get_pattern_history(user)
    assert len(history) == 1
    assert history[0].id == record.id


@pytest.mark.asyncio
async def test_integer_ids_increment_per_user(store_env):
    user = _FakeUser("user-2")

    r1 = await pattern_store.save_pattern_record(user, "comprehensive", _summary())
    r2 = await pattern_store.save_pattern_record(user, "fee_focus", _summary())
    assert (r1.id, r2.id) == (1, 2)

    # Per-user isolation — second user starts at 1 and sees only their records
    other = _FakeUser("user-other")
    r3 = await pattern_store.save_pattern_record(other, "comprehensive", _summary())
    assert r3.id == 1
    assert len(await pattern_store.get_pattern_history(other)) == 1


@pytest.mark.asyncio
async def test_get_record_and_mark_reviewed(store_env):
    user = _FakeUser("user-3")

    record = await pattern_store.save_pattern_record(user, "comprehensive", _summary())
    fetched = await pattern_store.get_pattern_record(user, record.id)
    assert fetched.id == record.id
    assert fetched.reviewed is False

    updated = await pattern_store.mark_pattern_reviewed(user, record.id, notes="verified")
    assert updated.reviewed is True
    assert updated.notes == "verified"

    assert await pattern_store.get_pattern_record(user, 999) is None


@pytest.mark.asyncio
async def test_trends_and_stats(store_env):
    user = _FakeUser("user-4")
    await pattern_store.save_pattern_record(user, "comprehensive", _summary(risk_score=40))
    await pattern_store.save_pattern_record(user, "comprehensive", _summary(risk_score=60))

    trends = await pattern_store.get_pattern_trends(user, days=30)
    assert trends["total_analyses"] == 2
    assert trends["pattern_type_frequency"]["fee_spike"] == 2
    assert trends["daily_averages"][0]["avg_risk"] == 50.0

    stats = await pattern_store.get_pattern_stats(user)
    assert stats["total_analyses"] == 2
    assert stats["average_risk_score"] == 50.0
    assert stats["most_common_risk_level"] == "medium"
    assert len(stats["recent_analyses"]) == 2


@pytest.mark.asyncio
async def test_persistence_disabled_returns_empty(store_env, monkeypatch):
    monkeypatch.setenv("ENABLE_PATTERN_PERSISTENCE", "false")
    user = _FakeUser("user-5")

    assert await pattern_store.save_pattern_record(user, "comprehensive", _summary()) is None
    assert await pattern_store.get_pattern_history(user) == []
    assert await pattern_store.get_pattern_record(user, 1) is None
    assert await pattern_store.mark_pattern_reviewed(user, 1) is None
    assert await pattern_store.get_pattern_trends(user) == {}


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


def _legacy_row(row_id: int, **overrides):
    base = dict(
        id=row_id, analysis_type="comprehensive", patterns=_summary(),
        risk_score=55, risk_level="high", data_sources={}, algorithm_version="1.0",
        created_at=utc_now(), reviewed=False, notes=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_migrate_legacy_records_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    user = _FakeUser("user-6")
    rows = [_legacy_row(7), _legacy_row(9, notes="old note")]
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(rows))

    imported_first = await pattern_store.migrate_legacy_records(user)
    imported_second = await pattern_store.migrate_legacy_records(user)

    assert imported_first == 2
    assert imported_second == 0

    # Integer PKs preserved — /record/{id} URLs keep resolving
    record = await pattern_store.get_pattern_record(user, 9)
    assert record is not None
    assert record.notes == "old note"


@pytest.mark.asyncio
async def test_migrate_legacy_records_safe_without_db(store_env):
    user = _FakeUser("user-7")
    assert await pattern_store.migrate_legacy_records(user) == 0
