"""Dispute tracker vault-persistence tests.

Exercises the Unified Overlay backed dispute store (service.py) end-to-end
with an in-memory storage provider: dispute + comparison creation, per-user
isolation, payload-id linkage (cmp_* → dis_*), view-object template contract,
and the safe migration no-op.

Run locally: python -m pytest app/modules/dispute_tracker/tests -v
"""

from datetime import UTC, datetime

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.dispute_tracker import service
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
    stores: dict[str, FakeStorageProvider] = {}

    def fake_get_provider(provider_value: str, access_token: str | None = None):
        _ = provider_value
        return stores.setdefault(access_token or "default", FakeStorageProvider())

    monkeypatch.setattr(service, "get_provider", fake_get_provider)
    return stores


@pytest.mark.anyio
async def test_dispute_create_and_list(storages):
    user = _make_user("GUalice001", "tok-a")

    dispute_id = await service.create_dispute(
        user,
        dispute_type="fees",
        landlord_entity="ABC Properties",
        property_name="Oakwood Apts",
        status="active",
        jurisdiction="MN",
    )
    assert dispute_id is not None
    assert dispute_id.startswith("dis_")

    disputes = await service.list_disputes(user)
    assert len(disputes) == 1
    d = disputes[0]
    # Template contract — attribute access on view objects
    assert d.id == dispute_id
    assert d.dispute_type == "fees"
    assert d.status == "active"
    assert d.landlord_entity == "ABC Properties"
    assert d.property_name == "Oakwood Apts"
    assert d.jurisdiction == "MN"


@pytest.mark.anyio
async def test_comparison_links_to_dispute(storages):
    user = _make_user("GUalice001", "tok-a")

    dispute_id = await service.create_dispute(user, dispute_type="fees")
    entry_id = await service.create_comparison(
        user,
        dispute_record_id=dispute_id,
        comparison_type="fee",
        fee_type="late_fee",
        amount_cents=7500,
        period="monthly",
        effective_date=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert entry_id is not None
    assert entry_id.startswith("cmp_")

    comparisons = await service.list_comparisons(user)
    assert len(comparisons) == 1
    c = comparisons[0]
    assert c.dispute_record_id == dispute_id
    assert c.comparison_type == "fee"
    assert c.fee_type == "late_fee"
    assert c.amount_cents == 7500
    assert c.period == "monthly"
    # effective_date must be a datetime — the template calls .strftime on it
    assert c.effective_date.strftime("%Y-%m-%d") == "2026-08-01"


@pytest.mark.anyio
async def test_disputes_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    await service.create_dispute(alice, dispute_type="retaliation")
    await service.create_comparison(bob, dispute_record_id="dis_other", comparison_type="term")

    assert await service.list_disputes(bob) == []
    assert await service.list_comparisons(alice) == []
    assert len(await service.list_disputes(alice)) == 1
    assert len(await service.list_comparisons(bob)) == 1


@pytest.mark.anyio
async def test_list_sorted_newest_first(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_dispute(user, dispute_type="fees", landlord_entity="first")
    await service.create_dispute(user, dispute_type="habitability", landlord_entity="second")

    disputes = await service.list_disputes(user)
    assert len(disputes) == 2
    assert disputes[0].created_at >= disputes[1].created_at


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.migrate_legacy_disputes(user) == 0
