"""Focused auth tests for the document_overlays router.

Covers:
  - Bearer token write success (correct scope + correct document)
  - Bearer token read success (correct scope)
  - Bearer token GET single overlay success (correct scope + correct document)
  - Wrong scope (read-only token on POST) → 403 token_scope_denied
  - Wrong document constraint (token scoped to doc-B, request for doc-A) → 403 token_document_denied
  - Wrong document constraint on GET single overlay → 403 token_document_denied
  - Invalid (unknown) Bearer token → 401
  - Expired Bearer token → 401
  - Cookie auth (advocate role) write → 200
  - Cookie auth (user role) read → 200
  - Cookie auth (user role) write → 403 (insufficient role)
  - No auth at all → 403
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import FUNCTION_ACCESS_TOKENS, issue_function_access_token
from app.routers import document_overlays as overlay_router
from app.services.document_overlay_service import DocumentOverlayService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="overlay_svc")
def fixture_overlay_svc(tmp_path, monkeypatch):
    """Isolated overlay service backed by a temp file; patched into both import sites."""
    svc = DocumentOverlayService(store_path=tmp_path / "overlay_auth_tests.json")
    monkeypatch.setattr(
        "app.services.document_overlay_service.document_overlay_service", svc
    )
    monkeypatch.setattr(overlay_router, "document_overlay_service", svc)
    return svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAYLOAD_DOC_A = {
    "document_id": "doc-A",
    "overlay_type": "annotation",
    "payload": {"note": "auth-test"},
}


def _issue_write_token(user_id: str = "GVadv00001", document_ids=None) -> str:
    ctx: dict = {"scopes": ["overlay:write"]}
    if document_ids is not None:
        ctx["document_ids"] = document_ids
    return issue_function_access_token(user_id, ttl_seconds=60, context=ctx)["token"]


def _issue_read_token(user_id: str = "GVadv00002", document_ids=None) -> str:
    ctx: dict = {"scopes": ["overlay:read"]}
    if document_ids is not None:
        ctx["document_ids"] = document_ids
    return issue_function_access_token(user_id, ttl_seconds=60, context=ctx)["token"]


async def _seed_overlay(client, document_id: str = "doc-A") -> str:
    """Create an overlay record via cookie auth; returns overlay_id."""
    resp = await client.post(
        "/api/document-overlays/records",
        json={"document_id": document_id, "overlay_type": "annotation", "payload": {}},
        cookies={"semptify_uid": "GVadv00099"},
    )
    assert resp.status_code == 200, f"seed failed: {resp.text}"
    return resp.json()["overlay_id"]


# ---------------------------------------------------------------------------
# Bearer – success paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bearer_write_success(client, overlay_svc):
    token = _issue_write_token(document_ids=["doc-A"])
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["document_id"] == "doc-A"


@pytest.mark.anyio
async def test_bearer_read_list_success(client, overlay_svc):
    await _seed_overlay(client)
    token = _issue_read_token()
    resp = await client.get(
        "/api/document-overlays/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_bearer_get_single_success(client, overlay_svc):
    overlay_id = await _seed_overlay(client, "doc-A")
    token = _issue_read_token(document_ids=["doc-A"])
    resp = await client.get(
        f"/api/document-overlays/records/{overlay_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["overlay_id"] == overlay_id


# ---------------------------------------------------------------------------
# Bearer – scope enforcement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bearer_read_scope_blocks_write(client, overlay_svc):
    token = _issue_read_token()  # overlay:read only
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "token_scope_denied"


# ---------------------------------------------------------------------------
# Bearer – document constraint enforcement
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bearer_wrong_doc_blocks_create(client, overlay_svc):
    token = _issue_write_token(document_ids=["doc-B"])  # scoped to doc-B, request is doc-A
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "token_document_denied"


@pytest.mark.anyio
async def test_bearer_wrong_doc_blocks_get_single(client, overlay_svc):
    overlay_id = await _seed_overlay(client, "doc-A")
    token = _issue_read_token(document_ids=["doc-B"])  # token allows doc-B only
    resp = await client.get(
        f"/api/document-overlays/records/{overlay_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "token_document_denied"


# ---------------------------------------------------------------------------
# Bearer – invalid / expired tokens
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bearer_invalid_token_returns_401(client, overlay_svc):
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        headers={"Authorization": "Bearer totally-fake-token-xyz"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_bearer_expired_token_returns_401(client, overlay_svc):
    token = _issue_write_token(user_id="GVadv00099")
    # Force-expire the token in the in-memory store
    FUNCTION_ACCESS_TOKENS[token]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cookie auth – success paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cookie_advocate_write_success(client, overlay_svc):
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        cookies={"semptify_uid": "GVadv00010"},  # GV = advocate
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_cookie_user_read_success(client, overlay_svc):
    await _seed_overlay(client)
    resp = await client.get(
        "/api/document-overlays/records",
        cookies={"semptify_uid": "GUuser00001"},  # GU = user
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Cookie auth – rejection paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cookie_user_write_blocked(client, overlay_svc):
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
        cookies={"semptify_uid": "GUuser00002"},  # GU = user, not in _WRITE_ROLES
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_no_auth_blocked(client, overlay_svc):
    resp = await client.post(
        "/api/document-overlays/records",
        json=_PAYLOAD_DOC_A,
    )
    assert resp.status_code == 403
