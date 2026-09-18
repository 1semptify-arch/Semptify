"""Complaint wizard vault-persistence tests.

Exercises the Unified Overlay backed complaint draft store end-to-end with
an in-memory storage provider: draft CRUD, per-user isolation, legacy-id
resolution (cmp_* ids preserved), document attachment, mark-as-filed, and
the bounded idempotent legacy migration.

Run locally: python -m pytest tests/test_complaint_wizard_vault.py -v
"""

import pytest

import app.services.storage as storage_mod
from app.core.user_context import StorageProvider, UserContext, UserRole
from app.services.complaint_wizard import ComplaintStatus, complaint_wizard
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

    monkeypatch.setattr(storage_mod, "get_provider", fake_get_provider)
    return stores


@pytest.mark.anyio
async def test_create_get_update_delete_roundtrip(storages):
    user = _make_user("GUalice001", "tok-a")

    draft = await complaint_wizard.create_draft_vault(
        user, agency_id="mn_ag_consumer", subject="Heat not working", complaint_type="habitability"
    )
    assert draft.id.startswith("cmp_")
    assert draft.status == ComplaintStatus.DRAFT
    assert draft.user_id == "GUalice001"

    fetched = await complaint_wizard.get_draft_vault(user, draft.id)
    assert fetched is not None
    assert fetched.subject == "Heat not working"
    assert fetched.agency_id == "mn_ag_consumer"

    updated = await complaint_wizard.update_draft_vault(
        user, draft.id, description="No heat since Monday", respondent_name="ABC Properties"
    )
    assert updated is not None
    assert updated.description == "No heat since Monday"
    assert updated.respondent_name == "ABC Properties"
    assert updated.subject == "Heat not working"

    assert await complaint_wizard.delete_draft_vault(user, draft.id) is True
    assert await complaint_wizard.get_draft_vault(user, draft.id) is None


@pytest.mark.anyio
async def test_drafts_isolated_per_user(storages):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    draft = await complaint_wizard.create_draft_vault(user=alice, agency_id="mn_ag_consumer", subject="x")

    assert await complaint_wizard.get_user_drafts_vault(bob) == []
    assert await complaint_wizard.get_draft_vault(bob, draft.id) is None
    assert await complaint_wizard.update_draft_vault(bob, draft.id, subject="y") is None
    assert await complaint_wizard.delete_draft_vault(bob, draft.id) is False


@pytest.mark.anyio
async def test_user_drafts_sorted_by_updated_desc(storages):
    user = _make_user("GUalice001", "tok-a")
    d1 = await complaint_wizard.create_draft_vault(user, agency_id="mn_ag_consumer", subject="first")
    d2 = await complaint_wizard.create_draft_vault(user, agency_id="hud_fair_housing", subject="second")

    # Touch d1 so it's most-recently-updated
    await complaint_wizard.update_draft_vault(user, d1.id, subject="first-updated")

    drafts = await complaint_wizard.get_user_drafts_vault(user)
    assert len(drafts) == 2
    assert drafts[0].subject == "first-updated"
    assert {d.id for d in drafts} == {d1.id, d2.id}


@pytest.mark.anyio
async def test_attach_documents_and_mark_filed(storages):
    user = _make_user("GUalice001", "tok-a")
    draft = await complaint_wizard.create_draft_vault(user, agency_id="mn_ag_consumer")

    updated = await complaint_wizard.attach_documents_vault(user, draft.id, ["doc_1", "doc_2"])
    assert updated.attached_document_ids == ["doc_1", "doc_2"]

    updated = await complaint_wizard.attach_documents_vault(user, draft.id, ["doc_3"])
    assert updated.attached_document_ids == ["doc_1", "doc_2", "doc_3"]

    filed = await complaint_wizard.mark_as_filed_vault(user, draft.id, confirmation_number="CONF-123")
    assert filed.status == ComplaintStatus.FILED
    assert filed.confirmation_number == "CONF-123"
    assert filed.filed_date is not None


@pytest.mark.anyio
async def test_get_draft_resolves_payload_id(storages):
    """Draft ids (cmp_*) live in the payload — resolution must not require the overlay_id."""
    user = _make_user("GUalice001", "tok-a")
    draft = await complaint_wizard.create_draft_vault(user, agency_id="mn_ag_consumer")

    # get_draft_vault resolves via payload["id"] — the same cmp_* id callers hold
    fetched = await complaint_wizard.get_draft_vault(user, draft.id)
    assert fetched is not None
    assert fetched.id == draft.id


@pytest.mark.anyio
async def test_migration_noops_when_db_unavailable(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await complaint_wizard.migrate_legacy_complaints(user) == 0
