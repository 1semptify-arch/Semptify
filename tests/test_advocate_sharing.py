"""Tests for tenant-controlled advocate sharing (legal UI epic, slice 2).

Under ONBOARDING SOLO there are no roles — an "advocate" is another tenant
identity that the tenant grants access to. These tests pin the consent +
scope contract:

- Mutual consent: link-request (tenant-initiated) is pending until the
  advocate accepts; intake (advocate-initiated) is pending until the
  tenant approves. Nothing is visible before acceptance.
- Scope: "all" shares the whole case file; "selected" shares only the
  picked documents — out-of-scope docs 404 identically to privileged
  docs (no existence oracle). share_timeline controls event visibility.
- Tenant control: scope can be narrowed mid-session (immediate 404 on
  the next request), access can be revoked, and my-access-log answers
  "who has seen my case".
- Privileged / work-product documents can never be selected for sharing.
"""

import asyncio
import importlib
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

adv_router = importlib.import_module("app.modules.advocate.router")
from app.models.models import (  # noqa: E402
    Base,
    Document,
    DocumentAccessLog,
    RelationshipType,
    User,
    UserRelationship,
)

HELPER = "GUhelper0001"  # the share recipient — just another tenant identity
TENANT = "GUtenant0001"
DOC_A = "doc-lease"
DOC_B = "doc-notice"
DOC_PRIV = "doc-privileged"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[
                    User.__table__,
                    UserRelationship.__table__,
                    Document.__table__,
                    DocumentAccessLog.__table__,
                ],
            )

    _run(_setup())
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def fake_db_session():
        async with factory() as s:
            yield s

    async def seed():
        async with factory() as db:
            db.add(User(id=HELPER, primary_provider="local", storage_user_id="hlp", default_role="user"))
            db.add(User(id=TENANT, primary_provider="local", storage_user_id="ten", default_role="user"))
            db.add(Document(
                id=DOC_A, user_id=TENANT, filename="lease.pdf",
                original_filename="lease.pdf", file_path="vault/lease.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="a" * 64,
            ))
            db.add(Document(
                id=DOC_B, user_id=TENANT, filename="notice.pdf",
                original_filename="notice.pdf", file_path="vault/notice.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="b" * 64,
            ))
            db.add(Document(
                id=DOC_PRIV, user_id=TENANT, filename="memo.pdf",
                original_filename="memo.pdf", file_path="vault/memo.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="c" * 64,
                is_privileged=True, attorney_id="GUatty1",
            ))
            await db.commit()

    _run(seed())

    monkeypatch.setattr(adv_router, "get_db_session", fake_db_session)
    monkeypatch.setattr(
        adv_router, "require_request_user_id", lambda request: request.state.test_user
    )

    async def fake_storage(tenant_user_id):
        class S:
            async def download_file(self, file_path):
                return b"bytes"

        return S()

    monkeypatch.setattr(adv_router, "_get_tenant_storage", fake_storage)

    app = FastAPI()
    app.include_router(adv_router.router)

    @app.middleware("http")
    async def set_user(request, call_next):
        request.state.test_user = request.headers.get("X-Test-User", TENANT)
        return await call_next(request)

    with TestClient(app) as c:
        c.factory = factory
        yield c


def _as(client_, user_id, method, url, **kw):
    return getattr(client_, method)(url, headers={"X-Test-User": user_id}, **kw)


def _rel(factory, from_id=HELPER, to_id=TENANT):
    async def q():
        async with factory() as db:
            return (
                await db.execute(
                    select(UserRelationship).where(
                        UserRelationship.from_user_id == from_id,
                        UserRelationship.to_user_id == to_id,
                    )
                )
            ).scalars().first()

    return _run(q())


def test_link_request_is_pending_until_advocate_accepts(client):
    r = _as(client, TENANT, "post", "/api/advocate/link-request", json={"advocate_user_id": HELPER})
    assert r.status_code == 200 and r.json()["pending"] is True

    # Advocate sees nothing yet — pending grants no access
    r = _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents")
    assert r.status_code == 403

    # Advocate sees the incoming request and accepts
    r = _as(client, HELPER, "get", "/api/advocate/requests")
    assert len(r.json()["incoming"]) == 1
    r = _as(client, HELPER, "post", f"/api/advocate/requests/{TENANT}/respond", json={"accept": True})
    assert r.json()["status"] == "active"

    # Now access works
    r = _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents")
    assert r.status_code == 200
    assert {d["id"] for d in r.json()["documents"]} == {DOC_A, DOC_B}


def test_advocate_decline_blocks_access(client):
    _as(client, TENANT, "post", "/api/advocate/link-request", json={"advocate_user_id": HELPER})
    r = _as(client, HELPER, "post", f"/api/advocate/requests/{TENANT}/respond", json={"accept": False})
    assert r.json()["status"] == "declined"
    r = _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents")
    assert r.status_code == 403


def test_selected_scope_hides_unshared_docs(client):
    r = _as(
        client, TENANT, "post", "/api/advocate/link-request",
        json={"advocate_user_id": HELPER, "share_all": False, "document_ids": [DOC_A]},
    )
    assert r.status_code == 200
    _as(client, HELPER, "post", f"/api/advocate/requests/{TENANT}/respond", json={"accept": True})

    r = _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents")
    assert [d["id"] for d in r.json()["documents"]] == [DOC_A]

    # Out-of-scope doc is 404 — identical to privileged/missing (no oracle)
    r = _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents/{DOC_B}/view")
    assert r.status_code == 404


def test_privileged_docs_can_never_be_selected(client):
    r = _as(
        client, TENANT, "post", "/api/advocate/link-request",
        json={"advocate_user_id": HELPER, "share_all": False, "document_ids": [DOC_PRIV]},
    )
    assert r.status_code == 400
    assert "privileged" in r.json()["detail"].lower()


def test_scope_update_narrows_mid_session(client):
    _as(client, TENANT, "post", "/api/advocate/link-request", json={"advocate_user_id": HELPER})
    _as(client, HELPER, "post", f"/api/advocate/requests/{TENANT}/respond", json={"accept": True})
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents/{DOC_B}/view").status_code == 200

    r = _as(
        client, TENANT, "put", f"/api/advocate/my-advocates/{HELPER}/scope",
        json={"share_all": False, "document_ids": [DOC_A]},
    )
    assert r.status_code == 200

    # Immediate effect — the very next request 404s
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents/{DOC_B}/view").status_code == 404
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents/{DOC_A}/view").status_code == 200


def test_intake_requires_tenant_approval(client):
    r = _as(client, HELPER, "post", "/api/advocate/intake", json={"tenant_user_id": TENANT})
    assert r.json()["status"] == "pending"

    # Pending advocate-initiated request grants nothing
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents").status_code == 403

    # Tenant sees it as incoming and approves
    r = _as(client, TENANT, "get", "/api/advocate/my-advocates")
    assert r.json()["advocates"][0]["status"] == "pending_incoming"
    r = _as(client, TENANT, "post", f"/api/advocate/my-advocates/{HELPER}/respond", json={"accept": True})
    assert r.json()["status"] == "active"
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents").status_code == 200


def test_tenant_decline_blocks_advocate(client):
    _as(client, HELPER, "post", "/api/advocate/intake", json={"tenant_user_id": TENANT})
    r = _as(client, TENANT, "post", f"/api/advocate/my-advocates/{HELPER}/respond", json={"accept": False})
    assert r.json()["status"] == "declined"
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents").status_code == 403


def test_link_request_unknown_id(client):
    """No role check — but the share target must be a real user."""
    r = _as(client, TENANT, "post", "/api/advocate/link-request", json={"advocate_user_id": "GUnobody"})
    assert r.status_code == 400


def test_revoke_and_access_log(client):
    _as(client, TENANT, "post", "/api/advocate/link-request", json={"advocate_user_id": HELPER})
    _as(client, HELPER, "post", f"/api/advocate/requests/{TENANT}/respond", json={"accept": True})
    _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents")

    r = _as(client, TENANT, "delete", f"/api/advocate/my-advocates/{HELPER}")
    assert r.status_code == 200
    assert _as(client, HELPER, "get", f"/api/advocate/clients/{TENANT}/documents").status_code == 403

    # Tenant's access log shows the whole story: request, accept, list, revoke
    r = _as(client, TENANT, "get", "/api/advocate/my-access-log")
    actions = {e["action"] for e in r.json()["entries"]}
    assert {"share_request", "share_accept", "list_documents", "revoke"} <= actions


def test_shareable_documents_marks_privileged(client):
    r = _as(client, TENANT, "get", "/api/advocate/my-shareable-documents")
    docs = {d["id"]: d for d in r.json()["documents"]}
    assert docs[DOC_A]["shareable"] is True
    assert docs[DOC_PRIV]["shareable"] is False
    assert docs[DOC_PRIV]["shareable_reason"]


def test_pending_relationship_never_in_my_advocates_as_active(client):
    _as(client, HELPER, "post", "/api/advocate/intake", json={"tenant_user_id": TENANT})
    r = _as(client, TENANT, "get", "/api/advocate/my-advocates")
    statuses = [a["status"] for a in r.json()["advocates"]]
    assert statuses == ["pending_incoming"]
