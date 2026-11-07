"""Legal Trails vault-persistence tests.

Exercises the LEGAL_TRAIL_RECORD overlay store (service.py) end-to-end with
an in-memory storage provider: record creation for each kind, per-user
isolation (the old global in-memory store leaked records across users),
payload-id lookup, status/linked updates, and the view contract the router
and page rely on.

Run locally: python -m pytest app/modules/legal_trails/tests -v
"""

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.legal_trails import service
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
    # Timeline events are a projection — keep them out of these tests.
    async def _no_timeline(user, kind, fields):
        return None

    monkeypatch.setattr(service, "_emit_timeline_event", _no_timeline)
    return stores


@pytest.mark.anyio
async def test_violation_create_and_list(storages):
    user = _make_user("GUalice001", "tok-a")

    record = await service.create_record(
        user,
        service.KIND_VIOLATION,
        {
            "violation_type": "retaliation",
            "date_occurred": "2026-10-01",
            "description": "Eviction threat after repair request",
            "perpetrator": "Pat Manager",
            "perpetrator_role": "Property Manager",
            "company": "ABC Properties",
        },
    )
    assert record is not None
    assert record["id"].startswith("vio_")
    assert record["overlay_id"]

    records = await service.list_records(user, service.KIND_VIOLATION)
    assert len(records) == 1
    assert records[0]["perpetrator"] == "Pat Manager"
    assert records[0]["kind"] == "violation"

    fetched = await service.get_record(user, service.KIND_VIOLATION, record["id"])
    assert fetched is not None
    assert fetched["id"] == record["id"]


@pytest.mark.anyio
async def test_records_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    await service.create_record(
        alice,
        service.KIND_VIOLATION,
        {"violation_type": "fraud", "date_occurred": "2026-09-15", "description": "x",
         "perpetrator": "P", "perpetrator_role": "PM", "company": "C"},
    )
    await service.create_record(
        bob,
        service.KIND_LATE_FEE,
        {"date_charged": "2026-10-02", "amount_charged": 75.0, "rent_amount": 1000.0,
         "days_late": 5, "lease_allows_late_fee": True},
    )

    # Cross-user isolation — the old module's global dicts leaked these.
    assert await service.list_records(bob, service.KIND_VIOLATION) == []
    assert await service.list_records(alice, service.KIND_LATE_FEE) == []
    assert len(await service.list_records(alice, service.KIND_VIOLATION)) == 1
    assert len(await service.list_records(bob, service.KIND_LATE_FEE)) == 1
    # And a record id from one user never resolves under another.
    alice_v = (await service.list_records(alice, service.KIND_VIOLATION))[0]
    assert await service.get_record(bob, service.KIND_VIOLATION, alice_v["id"]) is None


@pytest.mark.anyio
async def test_kinds_do_not_cross_list(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_record(
        user, service.KIND_EVICTION_THREAT,
        {"date_threatened": "2026-10-03", "threat_method": "verbal",
         "threat_content": "get out", "context": "after repair request",
         "perpetrator": "P", "perpetrator_role": "Landlord"},
    )
    assert await service.list_records(user, service.KIND_VIOLATION) == []
    assert len(await service.list_records(user, service.KIND_EVICTION_THREAT)) == 1

    counts = await service.counts(user)
    assert counts[service.KIND_EVICTION_THREAT] == 1
    assert counts[service.KIND_VIOLATION] == 0


@pytest.mark.anyio
async def test_claim_status_update(storages):
    user = _make_user("GUalice001", "tok-a")
    record = await service.create_record(
        user, service.KIND_CLAIM,
        {"title": "Retaliation claim", "claim_type": "civil", "status": "documenting",
         "filing_deadline": "2027-01-01", "statute_of_limitations_date": "2032-10-01"},
    )
    updated = await service.update_record_payload(
        user, service.KIND_CLAIM, record["id"], {"status": "ready_to_file"}
    )
    assert updated is not None
    assert updated["status"] == "ready_to_file"

    fetched = await service.get_record(user, service.KIND_CLAIM, record["id"])
    assert fetched["status"] == "ready_to_file"


@pytest.mark.anyio
async def test_broker_link_violation(storages):
    user = _make_user("GUalice001", "tok-a")
    violation = await service.create_record(
        user, service.KIND_VIOLATION,
        {"violation_type": "license_violation", "date_occurred": "2026-10-01",
         "description": "x", "perpetrator": "P", "perpetrator_role": "PM", "company": "C"},
    )
    await service.create_record(
        user, service.KIND_BROKER_OVERSIGHT,
        {"broker_name": "Bro Ker", "broker_company": "C", "company_address": "1 Main St"},
    )
    broker = await service.get_record(user, service.KIND_BROKER_OVERSIGHT, "Bro Ker")
    watched = list(broker.get("violations_under_watch") or []) + [violation["id"]]
    updated = await service.update_record_payload(
        user, service.KIND_BROKER_OVERSIGHT, "Bro Ker", {"violations_under_watch": watched}
    )
    assert updated is not None
    assert violation["id"] in updated["violations_under_watch"]


@pytest.mark.anyio
async def test_update_missing_record_returns_none(storages):
    user = _make_user("GUalice001", "tok-a")
    assert (
        await service.update_record_payload(user, service.KIND_CLAIM, "clm_missing", {"status": "filed"})
        is None
    )
