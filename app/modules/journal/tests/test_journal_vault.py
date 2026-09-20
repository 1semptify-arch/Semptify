"""Journal vault-persistence tests.

Exercises the Unified Overlay backed journal store (service.py) end-to-end
with an in-memory storage provider: create/list/get/update/delete, per-user
isolation, and legacy-id resolution for migrated rows.

Run locally: python -m pytest app/modules/journal/tests/test_journal_vault.py -v
"""

from datetime import UTC, datetime

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.journal import service
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


@pytest.mark.anyio
async def test_create_list_get_update_delete_roundtrip(storages):
    user = _make_user("GUalice001", "tok-a")

    created = await service.create_entry(
        user,
        entry_type="conversation",
        title="Called landlord",
        content="Landlord said repairs next week.",
        occurred_at=datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC),
        is_urgent=False,
        involved_party="landlord",
        tags="repair,landlord",
        document_link="doc_xyz789",
    )
    assert created.overlay_id
    assert created.overlay_type.value == "journal_entry"
    assert created.created_by == "GUalice001"

    entries, total = await service.list_entries(user)
    assert total == 1
    assert entries[0].overlay_id == created.overlay_id

    fetched = await service.get_entry(user, created.overlay_id)
    assert fetched is not None
    assert fetched.payload["title"] == "Called landlord"

    updated = await service.update_entry(
        user, created.overlay_id, {"is_urgent": True, "title": "Called landlord again"}
    )
    assert updated is not None
    assert updated.payload["is_urgent"] is True
    assert updated.payload["title"] == "Called landlord again"
    assert updated.payload["content"] == "Landlord said repairs next week."

    assert await service.delete_entry(user, created.overlay_id) is True
    assert await service.get_entry(user, created.overlay_id) is None
    entries, total = await service.list_entries(user)
    assert total == 0


@pytest.mark.anyio
async def test_entries_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    created = await service.create_entry(
        alice,
        entry_type="incident",
        title="Leak in ceiling",
        content="Water dripping since Monday.",
        occurred_at=datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC),
        is_urgent=True,
        involved_party=None,
        tags=None,
        document_link=None,
    )

    # Bob cannot see, fetch, update, or delete Alice's entry — even with the id.
    bob_entries, bob_total = await service.list_entries(bob)
    assert bob_total == 0
    assert bob_entries == []
    assert await service.get_entry(bob, created.overlay_id) is None
    assert await service.update_entry(bob, created.overlay_id, {"title": "hijack"}) is None
    assert await service.delete_entry(bob, created.overlay_id) is False

    # Alice still sees her entry untouched.
    fetched = await service.get_entry(alice, created.overlay_id)
    assert fetched is not None
    assert fetched.payload["title"] == "Leak in ceiling"


@pytest.mark.anyio
async def test_get_entry_resolves_legacy_payload_id(storages):
    """Entries fetched by their payload ``id`` (legacy jrn_ id path)."""
    user = _make_user("GUalice001", "tok-a")
    created = await service.create_entry(
        user,
        entry_type="note",
        title="Meter reading",
        content=None,
        occurred_at=datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC),
        is_urgent=False,
        involved_party=None,
        tags=None,
        document_link=None,
    )
    # In the SQLite store the row id IS the payload id — lookups by either
    # the view's overlay_id or the payload id resolve to the same row.
    legacy_id = created.payload["id"]
    assert legacy_id == created.overlay_id

    fetched = await service.get_entry(user, legacy_id)
    assert fetched is not None
    assert fetched.overlay_id == created.overlay_id


@pytest.mark.anyio
async def test_list_filters_and_ordering(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_entry(
        user, entry_type="note", title="old note", content=None,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC), is_urgent=False,
        involved_party=None, tags=None, document_link=None,
    )
    await service.create_entry(
        user, entry_type="incident", title="new incident", content=None,
        occurred_at=datetime(2026, 9, 1, tzinfo=UTC), is_urgent=True,
        involved_party=None, tags=None, document_link=None,
    )

    entries, total = await service.list_entries(user)
    assert total == 2
    assert entries[0].payload["title"] == "new incident"  # newest occurred_at first

    urgent, urgent_total = await service.list_entries(user, is_urgent=True)
    assert urgent_total == 1
    assert urgent[0].payload["entry_type"] == "incident"

    by_type, type_total = await service.list_entries(user, entry_type="note")
    assert type_total == 1
    assert by_type[0].payload["title"] == "old note"


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    """Legacy shim must not break the vault path when the DB has no rows."""
    user = _make_user("GUalice001", "tok-a")
    imported = await service.migrate_legacy_entries(user)
    assert imported == 0
