"""Tests for advocate document-access enforcement (legal UI epic, slice 1).

Covers the privilege boundary and audit trail on /api/advocate/* document
endpoints with a real SQLite database and a fake storage provider:

- Privileged + work-product documents are invisible to advocates (list AND
  direct access — a filtered doc must be indistinguishable from missing).
- Denied access attempts are logged to document_access_logs.
- Successful view/list/review actions are logged.
- View streams the tenant's bytes read-only through tenant storage.
"""

import importlib
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
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
from app.core.user_context import UserRole  # noqa: E402

ADVOCATE = "GUadvocate01"
TENANT = "GUtenant0001"
STRANGER = "GUstranger01"


class FakeStorage:
    def __init__(self, data: bytes):
        self.data = data

    async def download_file(self, file_path: str) -> bytes:
        return self.data


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

    import asyncio
    asyncio.get_event_loop().run_until_complete(_setup())

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def fake_db_session():
        async with factory() as s:
            yield s

    async def seed():
        async with factory() as db:
            db.add(User(id=ADVOCATE, primary_provider="google_drive", storage_user_id="adv-stor", default_role="advocate"))
            db.add(User(id=TENANT, primary_provider="local", storage_user_id="ten-stor", default_role="user"))
            db.add(User(id=STRANGER, primary_provider="local", storage_user_id="str-stor", default_role="user"))
            db.add(UserRelationship(
                from_user_id=ADVOCATE, to_user_id=TENANT,
                relationship_type=RelationshipType.ADVOCACY.value, is_active=True,
            ))
            db.add(Document(
                id="doc-public", user_id=TENANT, filename="lease.pdf",
                original_filename="lease.pdf", file_path="vault/lease.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="x" * 64,
            ))
            db.add(Document(
                id="doc-privileged", user_id=TENANT, filename="attorney_memo.pdf",
                original_filename="attorney_memo.pdf", file_path="vault/memo.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="y" * 64,
                is_privileged=True, attorney_id="GUatty1",
            ))
            db.add(Document(
                id="doc-workprod", user_id=TENANT, filename="strategy.pdf",
                original_filename="strategy.pdf", file_path="vault/strategy.pdf",
                file_size=4, mime_type="text/plain", sha256_hash="z" * 64,
                is_work_product=True, created_by_role="legal",
            ))
            await db.commit()

    asyncio.get_event_loop().run_until_complete(seed())

    monkeypatch.setattr(adv_router, "get_db_session", fake_db_session)
    monkeypatch.setattr(
        adv_router, "require_request_user_id", lambda request: request.state.test_user
    )
    monkeypatch.setattr(
        adv_router,
        "get_role_from_user_id",
        lambda uid: UserRole.ADVOCATE if uid == ADVOCATE else UserRole.TENANT,
    )
    monkeypatch.setattr(
        adv_router, "get_provider_from_user_id", lambda uid: "local"
    )

    async def fake_storage(tenant_user_id):
        return FakeStorage(b"file-bytes")

    monkeypatch.setattr(adv_router, "_get_tenant_storage", fake_storage)

    app = FastAPI()
    app.include_router(adv_router.router)

    @app.middleware("http")
    async def set_user(request, call_next):
        request.state.test_user = request.headers.get("X-Test-User", ADVOCATE)
        return await call_next(request)

    with TestClient(app) as c:
        c.factory = factory
        yield c


def _log_rows(factory):
    import asyncio

    async def q():
        from sqlalchemy import select
        async with factory() as db:
            return (await db.execute(select(DocumentAccessLog))).scalars().all()

    return asyncio.get_event_loop().run_until_complete(q())


def test_privileged_docs_hidden_from_list(client):
    r = client.get(f"/api/advocate/clients/{TENANT}/documents")
    assert r.status_code == 200
    ids = [d["id"] for d in r.json()["documents"]]
    assert ids == ["doc-public"]
    assert "doc-privileged" not in ids and "doc-workprod" not in ids


def test_privileged_doc_direct_access_is_404(client):
    """Filtered docs must be indistinguishable from missing — no oracle."""
    for doc_id in ("doc-privileged", "doc-workprod"):
        for verb in ("view", "overlays"):
            r = client.get(f"/api/advocate/clients/{TENANT}/documents/{doc_id}/{verb}")
            assert r.status_code == 404, (doc_id, verb)
        r = client.post(
            f"/api/advocate/clients/{TENANT}/documents/{doc_id}/annotate",
            json={"overlay_type": "NOTE", "payload": {"content": "x"}},
        )
        assert r.status_code == 404


def test_denied_access_is_logged(client):
    r = client.get(f"/api/advocate/clients/{STRANGER}/documents")
    assert r.status_code == 403
    rows = _log_rows(client.factory)
    denied = [x for x in rows if x.outcome == "denied"]
    assert len(denied) == 1
    assert denied[0].actor_user_id == ADVOCATE
    assert denied[0].tenant_user_id == STRANGER
    assert denied[0].action == "access_denied"


def test_view_streams_bytes_and_logs(client):
    r = client.get(f"/api/advocate/clients/{TENANT}/documents/doc-public/view")
    assert r.status_code == 200
    assert r.content == b"file-bytes"
    rows = _log_rows(client.factory)
    views = [x for x in rows if x.action == "view_document"]
    assert len(views) == 1
    assert views[0].document_id == "doc-public"
    assert views[0].actor_role == "advocate"


def test_review_and_list_are_logged(client):
    client.get(f"/api/advocate/clients/{TENANT}/documents")
    client.post(
        f"/api/advocate/clients/{TENANT}/documents/doc-public/review",
        json={"status": "reviewed", "notes": "ok"},
    )
    actions = {x.action for x in _log_rows(client.factory)}
    assert "list_documents" in actions
    assert "review" in actions


def test_revoked_link_blocks_access(client):
    import asyncio
    from sqlalchemy import select

    async def revoke():
        async with client.factory() as db:
            rel = (
                await db.execute(
                    select(UserRelationship).where(UserRelationship.from_user_id == ADVOCATE)
                )
            ).scalars().first()
            rel.is_active = False
            await db.commit()

    asyncio.get_event_loop().run_until_complete(revoke())
    r = client.get(f"/api/advocate/clients/{TENANT}/documents")
    assert r.status_code == 403
    assert any(x.outcome == "denied" for x in _log_rows(client.factory))
