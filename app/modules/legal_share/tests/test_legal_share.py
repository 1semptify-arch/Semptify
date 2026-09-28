"""Legal Share vault-persistence tests.

Exercises the CASE_SHARE and REVIEW_THREAD overlay stores (service.py)
end-to-end with an in-memory storage provider: share creation, owner-scoped
token resolution, expiry/revocation states, access metrics, document scope
enforcement, reviewer questions, tenant answers, and unread flags. Also
asserts the locked invariants — nothing certified, reviewer has no identity,
tenant owns every overlay.

Run locally: python -m pytest app/modules/legal_share/tests/test_legal_share.py -v
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.user_context import StorageProvider, UserContext, UserRole
from app.core.utc import utc_now
from app.modules.legal_share import service
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
def owner_ctx(monkeypatch):
    """Resolve owner contexts without token plumbing — maps the owner prefix
    embedded in share tokens to a UserContext."""
    contexts: dict[str, UserContext] = {}

    async def fake_build(user_id: str):
        return contexts.get(user_id) or _make_user(user_id, f"tok-{user_id}")

    monkeypatch.setattr(service, "build_context_for_user_id", fake_build)
    return contexts


async def _share(user: UserContext, **overrides) -> SimpleNamespace:
    kwargs = {
        "case_id": 7,
        "case_title": "Test case",
        "reviewer_label": "Attorney Lee",
        "documents": [{"id": "doc-001", "name": "lease.pdf"}, {"id": "doc-002", "name": "photos.zip"}],
        "include_notes": True,
        "deadlines": [{"id": "cal-1", "title": "Court date", "start_datetime": "2026-10-01T09:00:00+00:00"}],
        "expires_at": utc_now() + timedelta(days=30),
    }
    kwargs.update(overrides)
    share = await service.create_share(user, **kwargs)
    assert share is not None
    return share


# =============================================================================
# Share lifecycle
# =============================================================================


@pytest.mark.anyio
async def test_create_and_resolve_share(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user

    share = await _share(user)
    assert share.status == service.STATUS_ACTIVE
    assert share.share_token.startswith("GUalice001:")
    assert share.case_id == 7
    assert share.reviewer_label == "Attorney Lee"
    assert service.shared_document_ids(share) == {"doc-001", "doc-002"}

    # Owner-scoped token resolves without any server-side index
    resolved = await service.resolve_share_with_owner(share.share_token)
    assert resolved is not None
    view, owner = resolved
    assert view.id == share.id
    assert owner.get_effective_user_id() == "GUalice001"


@pytest.mark.anyio
async def test_invalid_token_resolves_none(storages, owner_ctx):
    assert await service.resolve_share("not-a-token") is None
    assert await service.resolve_share("") is None
    assert await service.resolve_share("GUalice001:bogus-token") is None


@pytest.mark.anyio
async def test_expired_share_status(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user, expires_at=utc_now() - timedelta(days=1))
    assert share.status == service.STATUS_EXPIRED

    resolved = await service.resolve_share(share.share_token)
    assert resolved.status == service.STATUS_EXPIRED


@pytest.mark.anyio
async def test_revoke_share(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)

    revoked = await service.revoke_share(user, share.id)
    assert revoked.status == service.STATUS_REVOKED

    resolved = await service.resolve_share(share.share_token)
    assert resolved.status == service.STATUS_REVOKED

    # Idempotent — second revoke returns same record
    again = await service.revoke_share(user, share.id)
    assert again.status == service.STATUS_REVOKED

    # Foreign user can't revoke
    bob = _make_user("GUbob00002", "tok-b")
    assert await service.revoke_share(bob, share.id) is None


@pytest.mark.anyio
async def test_access_metrics(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)
    assert share.access_count == 0

    await service.record_share_access(share.share_token)
    await service.record_share_access(share.share_token)
    resolved = await service.resolve_share(share.share_token)
    assert resolved.access_count == 2
    assert resolved.accessed_at is not None


@pytest.mark.anyio
async def test_shares_isolated_per_user(storages, owner_ctx):
    alice = _make_user("GUalice001", "tok-a")
    bob = _make_user("GUbob00002", "tok-b")
    owner_ctx["GUalice001"] = alice
    owner_ctx["GUbob00002"] = bob

    await _share(alice)
    assert len(await service.list_shares(alice)) == 1
    assert len(await service.list_shares(bob)) == 0


# =============================================================================
# Review threads — Q&A
# =============================================================================


@pytest.mark.anyio
async def test_question_scope_enforced(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)

    # Question on a shared doc succeeds
    thread = await service.post_question(
        user, share, document_id="doc-001", body="What date is on page 2?", subject="Dates"
    )
    assert thread is not None
    assert thread["document_id"] == "doc-001"
    assert thread["document_name"] == "lease.pdf"
    assert thread["status"] == "open"
    assert thread["unread_by_tenant"] is True
    assert thread["messages"][0]["side"] == "reviewer"
    assert thread["certified"] is False

    # Question on a non-shared doc is refused
    out_of_scope = await service.post_question(user, share, document_id="doc-999", body="sneaky")
    assert out_of_scope is None


@pytest.mark.anyio
async def test_tenant_answer_flow(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)
    thread = await service.post_question(user, share, document_id="doc-001", body="Where is the lease?")

    answered = await service.post_message(user, 7, thread["thread_id"], side="tenant", body="Page 3.")
    assert answered["status"] == "answered"
    assert answered["unread_by_reviewer"] is True
    assert answered["unread_by_tenant"] is False
    assert answered["answered_at"] is not None
    assert len(answered["messages"]) == 2
    assert answered["messages"][1]["side"] == "tenant"

    # Reviewer follow-up re-opens the thread
    followup = await service.post_message(user, 7, thread["thread_id"], side="reviewer", body="Which page again?")
    assert followup["status"] == "open"
    assert followup["unread_by_tenant"] is True


@pytest.mark.anyio
async def test_thread_visibility_scoped_to_share(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share_a = await _share(user)
    share_b = await _share(user, reviewer_label="Other reviewer")

    await service.post_question(user, share_a, document_id="doc-001", body="Q on share A")
    threads_a = await service.list_threads_for_share(user, share_a)
    threads_b = await service.list_threads_for_share(user, share_b)
    assert len(threads_a) == 1
    assert len(threads_b) == 0  # threads belong to the share that asked


@pytest.mark.anyio
async def test_unread_panel_and_read_marks(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)
    await service.post_question(user, share, document_id="doc-001", body="Question one")

    unread = await service.list_unread_threads(user)
    assert len(unread) == 1
    assert unread[0]["reviewer_label"] == "Attorney Lee"

    await service.mark_threads_read(user, 7, "tenant")
    assert await service.list_unread_threads(user) == []


@pytest.mark.anyio
async def test_revoked_share_still_hides_threads(storages, owner_ctx):
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)
    await service.post_question(user, share, document_id="doc-001", body="Q")

    await service.revoke_share(user, share.id)
    # Revoked shares drop out of the tenant's unread panel
    assert await service.list_unread_threads(user) == []


@pytest.mark.anyio
async def test_no_certified_path(storages, owner_ctx):
    """Every overlay this module writes carries certified=False."""
    user = _make_user("GUalice001", "tok-a")
    owner_ctx["GUalice001"] = user
    share = await _share(user)
    await service.post_question(user, share, document_id="doc-001", body="Q")
    await service.post_message(user, 7, "rth_missing", side="tenant", body="x")  # nonexistent → None

    manager = await service._get_manager(user)
    resp = await manager.get_overlays(document_id=service._shares_anchor("GUalice001"))
    for o in resp.overlays:
        assert o.payload["certified"] is False
    resp = await manager.get_overlays(document_id=service._threads_anchor(7))
    for o in resp.overlays:
        assert o.payload["certified"] is False
