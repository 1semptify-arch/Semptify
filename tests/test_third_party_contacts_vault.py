"""Functional tests for third-party contact overlays in the user vault."""

from types import SimpleNamespace

import pytest

from app.services import third_party_contact_store
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

    monkeypatch.setattr(third_party_contact_store, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(third_party_contact_store, "get_unified_overlay_manager", _manager)
    return managers


@pytest.mark.asyncio
async def test_upsert_creates_and_updates_by_email(store_env):
    user = _FakeUser("user-1")

    first = await third_party_contact_store.upsert_contact(
        user, "Case Manager", "cm@agency.org", None, "caseworker", "import"
    )
    assert first.id.startswith("tpc_")
    assert first.email == "cm@agency.org"

    # Same email upserts the same record, not a duplicate
    second = await third_party_contact_store.upsert_contact(
        user, "Case Manager II", "cm@agency.org", "555-0100", "caseworker", "import"
    )
    assert second.id == first.id
    assert len(await third_party_contact_store.list_active(user)) == 1


@pytest.mark.asyncio
async def test_upsert_matches_by_phone(store_env):
    user = _FakeUser("user-2")

    first = await third_party_contact_store.upsert_contact(
        user, "Landlord", None, "555-9999", "landlord", "import"
    )
    second = await third_party_contact_store.upsert_contact(
        user, "", "ll@example.com", "555-9999", "landlord", "import"
    )
    assert second.id == first.id
    assert len(await third_party_contact_store.list_active(user)) == 1


@pytest.mark.asyncio
async def test_contacts_are_isolated_per_user(store_env):
    user_a = _FakeUser("user-a")
    user_b = _FakeUser("user-b")

    await third_party_contact_store.upsert_contact(user_a, "A Contact", "a@x.com", None, "other", "import")
    await third_party_contact_store.upsert_contact(user_b, "B Contact", "b@x.com", None, "other", "import")

    a_contacts = await third_party_contact_store.list_active(user_a)
    b_contacts = await third_party_contact_store.list_active(user_b)

    assert [c.name for c in a_contacts] == ["A Contact"]
    assert [c.name for c in b_contacts] == ["B Contact"]


@pytest.mark.asyncio
async def test_list_active_excludes_inactive(store_env):
    user = _FakeUser("user-3")

    await third_party_contact_store.upsert_contact(
        user, "Jane Advocate", "jane@legal.org", "555-1234", "attorney", "import"
    )
    old = await third_party_contact_store.upsert_contact(
        user, "Old Contact", "old@x.com", None, "other", "import"
    )

    # Flip the second contact inactive directly on the overlay
    manager = await third_party_contact_store._get_manager(user)
    overlays = await third_party_contact_store._list_overlays(user)
    target = next(o for o in overlays if o.payload.get("email") == "old@x.com")
    target.payload["is_active"] = False
    await manager.update_overlay(target.overlay_id, payload=target.payload)

    active = await third_party_contact_store.list_active(user)
    assert [c.email for c in active] == ["jane@legal.org"]


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
        id=row_id, case_record_id=None, entity_type="attorney", name="Legacy",
        email=f"{row_id}@x.com", phone=None, address=None, source="import",
        source_document_id=None, is_active=True, created_at=None, updated_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_migrate_legacy_contacts_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    user = _FakeUser("user-4")
    rows = [
        _legacy_row("tpc-1", name="Legacy One", email="l1@x.com"),
        _legacy_row("tpc-2", name="Legacy Two", email="l2@x.com", entity_type="landlord"),
    ]
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(rows))

    imported_first = await third_party_contact_store.migrate_legacy_contacts(user)
    imported_second = await third_party_contact_store.migrate_legacy_contacts(user)

    assert imported_first == 2
    assert imported_second == 0  # idempotent via legacy_id

    contacts = await third_party_contact_store.list_active(user)
    assert {c.email for c in contacts} == {"l1@x.com", "l2@x.com"}


@pytest.mark.asyncio
async def test_migrate_legacy_contacts_safe_without_db(store_env):
    """Migration must no-op cleanly when the DB is unreachable."""
    user = _FakeUser("user-5")
    assert await third_party_contact_store.migrate_legacy_contacts(user) == 0
