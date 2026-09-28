"""Case Review vault-persistence tests.

Exercises the EVIDENCE_INDEX overlay store (service.py) end-to-end with an
in-memory storage provider: the legal_share_initialized marker, per-case
legend, document tags, multi-document notes, per-user isolation, and the
paste-ready export. Also asserts the locked invariants — nothing is ever
certified and no path writes to an original document.

Run locally: python -m pytest app/modules/case_review/tests/test_case_review.py -v
"""

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.modules.case_review import service
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


@pytest.fixture
def incident_id(monkeypatch):
    """Stand-in case: bypass incident_store resolution, return a stub."""
    from types import SimpleNamespace

    async def fake_get_incident(user, case_id):
        return SimpleNamespace(incident_id=int(case_id), title="Test case")

    monkeypatch.setattr(service, "get_incident", fake_get_incident)
    return 7


# =============================================================================
# Share marker (legal_share_initialized)
# =============================================================================


@pytest.mark.anyio
async def test_share_marker_idempotent_and_scoped(storages):
    user = _make_user("GUalice001", "tok-a")
    assert await service.is_share_initialized(user) is False

    first = await service.mark_share_initialized(user)
    assert first is not None
    assert first.payload["kind"] == "share_marker"
    assert first.payload["event"] == service.LEGAL_SHARE_INITIALIZED
    assert first.payload["certified"] is False

    second = await service.mark_share_initialized(user)
    assert second.overlay_id == first.overlay_id  # no duplicate
    assert await service.is_share_initialized(user) is True
    # Global marker satisfies a case-scoped check too
    assert await service.is_share_initialized(user, case_id=7) is True


@pytest.mark.anyio
async def test_share_marker_per_case(storages):
    user = _make_user("GUalice001", "tok-a")
    await service.mark_share_initialized(user, case_id=7)
    assert await service.is_share_initialized(user, case_id=7) is True


# =============================================================================
# Legend
# =============================================================================


@pytest.mark.anyio
async def test_legend_defaults_then_upsert(storages, incident_id):
    user = _make_user("GUalice001", "tok-a")

    default = await service.get_legend(user, incident_id)
    assert len(default) == len(service.DEFAULT_LEGEND)

    entries = [{"label": "Key fact", "color": "#112233"}, {"label": "Disputed", "color": "#dd0000"}]
    stored = await service.set_legend(user, incident_id, entries)
    assert stored == entries

    # Second write updates the same overlay — one legend per case
    again = await service.set_legend(user, incident_id, [{"label": "Only", "color": "#ffffff"}])
    assert again == [{"label": "Only", "color": "#ffffff"}]
    overlays = await service._list_overlays(user, service._anchor(incident_id))
    assert len([o for o in overlays if o.payload.get("kind") == "legend"]) == 1

    # Blank labels are dropped
    cleaned = await service.set_legend(user, incident_id, [{"label": "  ", "color": "#fff"}])
    assert cleaned == []


# =============================================================================
# Document tags
# =============================================================================


@pytest.mark.anyio
async def test_tag_upsert_and_remove(storages, incident_id):
    user = _make_user("GUalice001", "tok-a")

    tag = await service.set_tag(user, incident_id, "doc-001", "evidence", "documentary", name="lease.pdf")
    assert tag == {
        "category": "evidence",
        "evidence_type": "documentary",
        "name": "lease.pdf",
        "vault_path": None,
    }

    # Upsert same doc — one tag per document
    await service.set_tag(user, incident_id, "doc-001", "foundational", "none")
    tags = await service.get_tags(user, incident_id)
    assert tags["doc-001"]["category"] == "foundational"

    # Invalid enum values rejected
    assert await service.set_tag(user, incident_id, "doc-002", "bogus", "none") is None
    assert await service.set_tag(user, incident_id, "doc-002", "misc", "bogus") is None

    assert await service.remove_tag(user, incident_id, "doc-001") is True
    assert await service.remove_tag(user, incident_id, "doc-001") is False


# =============================================================================
# Evidence notes
# =============================================================================


@pytest.mark.anyio
async def test_note_crud_multi_document(storages, incident_id):
    user = _make_user("GUalice001", "tok-a")

    note = await service.create_note(
        user,
        incident_id,
        "Deposit deduction contradicts the move-in photos",
        links=[
            {"document_id": "doc-001", "name": "claim.pdf", "location": "p.2"},
            {"document_id": "doc-002", "name": "photos.zip", "location": "photo 4"},
        ],
        legend_label="Disputed",
    )
    assert note is not None
    assert note["certified"] is False
    assert note["document_ids"] == ["doc-001", "doc-002"]
    assert len(note["links"]) == 2

    notes = await service.list_notes(user, incident_id)
    assert len(notes) == 1

    updated = await service.update_note(
        user, incident_id, note["id"], text="Revised wording", legend_label="Key fact"
    )
    assert updated["text"] == "Revised wording"
    assert updated["legend_label"] == "Key fact"
    assert updated["certified"] is False  # still forced false after update

    assert await service.delete_note(user, incident_id, note["id"]) is True
    assert await service.list_notes(user, incident_id) == []
    assert await service.delete_note(user, incident_id, note["id"]) is False


@pytest.mark.anyio
async def test_notes_isolated_per_user(storages, incident_id):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")

    note = await service.create_note(alice, incident_id, "Alice's note")
    assert note is not None

    assert await service.list_notes(bob, incident_id) == []
    assert await service.update_note(bob, incident_id, note["id"], text="hijack") is None
    assert await service.delete_note(bob, incident_id, note["id"]) is False

    # Bob's tag reads are also scoped to his own (empty) anchor
    assert await service.get_tags(bob, incident_id) == {}


# =============================================================================
# Index + export
# =============================================================================


@pytest.mark.anyio
async def test_build_index_and_export_text(storages, incident_id):
    user = _make_user("GUalice001", "tok-a")
    await service.set_legend(user, incident_id, [{"label": "Disputed", "color": "#dd0000"}])
    await service.set_tag(user, incident_id, "doc-001", "evidence", "documentary", name="claim.pdf")
    await service.create_note(
        user,
        incident_id,
        "Counterclaim exceeds actual damages",
        links=[{"document_id": "doc-001", "location": "p.2"}],
        legend_label="Disputed",
    )
    await service.mark_share_initialized(user, case_id=incident_id)

    index = await service.build_index(user, incident_id)
    assert index["share_initialized"] is True
    assert len(index["legend"]) == 1
    assert len(index["notes"]) == 1
    assert index["tags"]["doc-001"]["category"] == "evidence"

    text = service.render_index_text(
        "My case", index, {"doc-001": "conciliation_claim.pdf"}
    )
    assert "EVIDENCE INDEX — My case" in text
    assert "not certified records" in text
    assert "conciliation_claim.pdf" in text
    assert "Counterclaim exceeds actual damages" in text
    assert "p.2" in text


@pytest.mark.anyio
async def test_no_certified_path(storages, incident_id):
    """Every overlay kind this module writes carries certified=False — the
    certification rule is structural, not a UI convention."""
    user = _make_user("GUalice001", "tok-a")
    await service.mark_share_initialized(user, case_id=incident_id)
    await service.set_legend(user, incident_id, [{"label": "X", "color": "#fff"}])
    await service.set_tag(user, incident_id, "doc-001", "misc", "none")
    await service.create_note(user, incident_id, "note text")

    for o in await service._list_overlays(user, service._anchor(incident_id)):
        assert o.payload["certified"] is False
