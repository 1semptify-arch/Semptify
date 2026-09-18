"""Contacts vault-persistence tests.

Exercises the Unified Overlay backed contacts store (service.py) end-to-end
with an in-memory storage provider: contact CRUD, per-user isolation,
legacy-id resolution, filters/search, interaction logging (including the
contact's interaction_count/last_contact_date stamps), and the
dedup/user_id helper paths.

Run locally: python -m pytest app/modules/contacts/tests/test_contacts_vault.py -v
"""

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.contacts import service
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


def _contact_kwargs(**overrides):
    base = {
        "contact_type": "landlord",
        "role": "opposing_party",
        "name": "ABC Properties",
        "organization": "ABC Properties LLC",
        "phone": "555-0100",
        "email": "leasing@abc.example",
        "address_line1": "123 Main St",
        "city": "Burnsville",
        "state": "MN",
        "zip_code": "55337",
        "source": "manual",
    }
    base.update(overrides)
    return base


@pytest.mark.anyio
async def test_create_list_get_update_delete_roundtrip(storages):
    user = _make_user("GUalice001", "tok-a")

    created = await service.create_contact(user, **_contact_kwargs())
    assert created.overlay_id
    assert created.overlay_type.value == "contact"
    assert created.created_by == "GUalice001"
    assert created.payload["is_active"] is True
    assert created.payload["interaction_count"] == 0

    contacts, total = await service.list_contacts(user)
    assert total == 1
    assert contacts[0].overlay_id == created.overlay_id

    fetched = await service.get_contact(user, created.overlay_id)
    assert fetched is not None
    assert fetched.payload["name"] == "ABC Properties"

    updated = await service.update_contact(user, created.overlay_id, {"is_starred": True, "phone": "555-0199"})
    assert updated is not None
    assert updated.payload["is_starred"] is True
    assert updated.payload["phone"] == "555-0199"
    assert updated.payload["name"] == "ABC Properties"

    assert await service.delete_contact(user, created.overlay_id) is True
    assert await service.get_contact(user, created.overlay_id) is None


@pytest.mark.anyio
async def test_contacts_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    created = await service.create_contact(alice, **_contact_kwargs())

    bob_contacts, bob_total = await service.list_contacts(bob)
    assert bob_total == 0
    assert bob_contacts == []
    assert await service.get_contact(bob, created.overlay_id) is None
    assert await service.update_contact(bob, created.overlay_id, {"name": "x"}) is None
    assert await service.delete_contact(bob, created.overlay_id) is False


@pytest.mark.anyio
async def test_list_filters_and_search(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.create_contact(user, **_contact_kwargs(name="AAA Landlord", is_starred=True))
    await service.create_contact(user, **_contact_kwargs(
        contact_type="witness", role="my_witness", name="Neighbor Ned", organization=None, email=None
    ))
    await service.create_contact(user, **_contact_kwargs(
        contact_type="attorney", role="opposing_counsel", name="Opp Counsel", is_active=False
    ))

    contacts, total = await service.list_contacts(user)
    assert total == 2  # inactive attorney excluded by default
    # Starred sorts first
    assert contacts[0].payload["name"] == "AAA Landlord"

    contacts, total = await service.list_contacts(user, active_only=False)
    assert total == 3

    contacts, total = await service.list_contacts(user, contact_type="witness")
    assert total == 1
    assert contacts[0].payload["name"] == "Neighbor Ned"

    contacts, total = await service.list_contacts(user, role="opposing_counsel", active_only=False)
    assert total == 1

    contacts, total = await service.list_contacts(user, search="neighbor")
    assert total == 1

    contacts, total = await service.list_contacts(user, starred_only=True)
    assert total == 1


@pytest.mark.anyio
async def test_get_contact_resolves_legacy_payload_id(storages):
    user = _make_user("GUalice001", "tok-a")
    created = await service.create_contact(user, **_contact_kwargs())
    legacy_id = created.payload["id"]
    assert legacy_id != created.overlay_id

    fetched = await service.get_contact(user, legacy_id)
    assert fetched is not None
    assert fetched.overlay_id == created.overlay_id


@pytest.mark.anyio
async def test_interaction_log_updates_contact_stamps(storages):
    user = _make_user("GUalice001", "tok-a")
    contact = await service.create_contact(user, **_contact_kwargs())

    interaction = await service.create_interaction(
        user,
        contact.overlay_id,
        interaction_type="phone_call",
        direction="outgoing",
        subject="Repair request",
        interaction_date="2026-09-10T14:00:00+00:00",
        follow_up_needed=True,
    )
    assert interaction is not None
    assert interaction.overlay_type.value == "contact_interaction"
    assert interaction.payload["contact_id"] == contact.overlay_id

    interactions = await service.list_interactions(user, contact.overlay_id)
    assert len(interactions) == 1
    assert interactions[0].payload["subject"] == "Repair request"

    # Legacy semantics: last_contact_date + interaction_count stamped on contact
    refreshed = await service.get_contact(user, contact.overlay_id)
    assert refreshed.payload["interaction_count"] == 1
    assert refreshed.payload["last_contact_date"] == "2026-09-10T14:00:00+00:00"

    # Interactions also resolve via the contact's legacy payload id
    interactions = await service.list_interactions(user, contact.payload["id"])
    assert len(interactions) == 1


@pytest.mark.anyio
async def test_interaction_for_missing_contact_returns_none(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.create_interaction(
        user, "con_missing", interaction_type="email", direction="incoming"
    ) is None


@pytest.mark.anyio
async def test_find_and_create_for_user_id(storages, monkeypatch):
    user = _make_user("GUalice001", "tok-a")

    async def fake_ctx(user_id: str):
        return user

    monkeypatch.setattr("app.core.user_context.build_context_for_user_id", fake_ctx)

    assert await service.find_contact_by_name_type("GUalice001", "ABC Properties", "landlord") is None

    contact = await service.create_contact_for_user_id("GUalice001", **_contact_kwargs())
    assert contact is not None

    found = await service.find_contact_by_name_type("GUalice001", "ABC Properties", "landlord")
    assert found is not None
    assert found.overlay_id == contact.overlay_id


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.migrate_legacy_contacts(user) == 0
