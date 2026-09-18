"""Rent ledger vault-persistence tests.

Exercises the Unified Overlay backed ledger store (service.py) end-to-end
with an in-memory storage provider: create/list/get/update/delete, per-user
isolation, legacy-id resolution, and running-balance ordering.

Run locally: python -m pytest app/modules/rent/tests/test_ledger_vault.py -v
"""

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.rent import service
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


def _payment_kwargs(**overrides):
    base = {
        "entry_type": "payment",
        "amount_cents": 95000,
        "payment_date": "2026-09-01T00:00:00+00:00",
        "due_date": "2026-09-05T00:00:00+00:00",
        "period_covered": "2026-09",
        "status": "paid",
        "payment_method": "check",
        "source": "user_entered",
        "receipt_document_id": None,
        "overlay_link": None,
        "notes": None,
    }
    base.update(overrides)
    return base


@pytest.mark.anyio
async def test_create_list_get_update_delete_roundtrip(storages):
    user = _make_user("GUalice001", "tok-a")

    created = await service.create_entry(user, **_payment_kwargs())
    assert created.overlay_id
    assert created.overlay_type.value == "rent_ledger_entry"
    assert created.created_by == "GUalice001"

    entries, total = await service.list_entries(user)
    assert total == 1
    assert entries[0].overlay_id == created.overlay_id

    fetched = await service.get_entry(user, created.overlay_id)
    assert fetched is not None
    assert fetched.payload["amount"] == 95000
    assert fetched.payload["period_covered"] == "2026-09"

    updated = await service.update_entry(user, created.overlay_id, {"status": "late", "amount": 50000})
    assert updated is not None
    assert updated.payload["status"] == "late"
    assert updated.payload["amount"] == 50000
    assert updated.payload["payment_method"] == "check"

    assert await service.delete_entry(user, created.overlay_id) is True
    assert await service.get_entry(user, created.overlay_id) is None


@pytest.mark.anyio
async def test_entries_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    created = await service.create_entry(alice, **_payment_kwargs())

    bob_entries, bob_total = await service.list_entries(bob)
    assert bob_total == 0
    assert bob_entries == []
    assert await service.get_entry(bob, created.overlay_id) is None
    assert await service.update_entry(bob, created.overlay_id, {"amount": 1}) is None
    assert await service.delete_entry(bob, created.overlay_id) is False


@pytest.mark.anyio
async def test_list_orders_oldest_first_for_running_balance(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_entry(user, **_payment_kwargs(payment_date="2026-09-01T00:00:00+00:00"))
    await service.create_entry(user, **_payment_kwargs(payment_date="2026-08-01T00:00:00+00:00", period_covered="2026-08"))
    await service.create_entry(user, **_payment_kwargs(payment_date="2026-07-01T00:00:00+00:00", period_covered="2026-07"))

    entries, total = await service.list_entries(user)
    assert total == 3
    # Oldest first — running balance needs chronological order.
    assert entries[0].payload["period_covered"] == "2026-07"
    assert entries[2].payload["period_covered"] == "2026-09"


@pytest.mark.anyio
async def test_get_entry_resolves_legacy_payload_id(storages):
    user = _make_user("GUalice001", "tok-a")
    created = await service.create_entry(user, **_payment_kwargs())
    legacy_id = created.payload["id"]
    assert legacy_id != created.overlay_id

    fetched = await service.get_entry(user, legacy_id)
    assert fetched is not None
    assert fetched.overlay_id == created.overlay_id


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.migrate_legacy_entries(user) == 0
