"""Regression tests for the FEMS upload path traversal + tenant isolation fix.

Covers:
- A multipart filename containing ``../`` is reduced to its basename and the
  upload lands inside the FEMS inbox, never outside it.
- FEMS documents/cases/quarantine are scoped to their owner: user B cannot
  list or fetch user A's rows.
"""

import importlib
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.modules.fems.config as fems_config
import app.modules.fems.ingest as fems_ingest
from app.modules.fems.models import Base

fems_router = importlib.import_module("app.modules.fems.router")


@pytest.fixture
async def db_session(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    quarantine = tmp_path / "quarantine"
    monkeypatch.setattr(fems_config, "FEMS_INBOX_DIR", inbox)
    monkeypatch.setattr(fems_config, "FEMS_QUARANTINE_DIR", quarantine)
    monkeypatch.setattr(fems_router, "FEMS_INBOX_DIR", inbox)
    monkeypatch.setattr(fems_ingest, "FEMS_QUARANTINE_DIR", quarantine)
    monkeypatch.setattr(fems_router, "FEMS_INBOX_DIR", inbox)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _user(user_id: str):
    return SimpleNamespace(user_id=user_id)


async def test_traversal_filename_lands_inside_inbox(db_session, tmp_path):
    """`../x.txt` must not escape the inbox — it is written as `x.txt`."""
    upload = UploadFile(file=BytesIO(b"evidence"), filename="../../../etc/x.txt")

    result = await fems_router.upload_file(file=upload, case_id=None, db=db_session, user=_user("GUalice001"))

    assert result["status"] == "ingested"
    inbox = tmp_path / "inbox"
    assert (inbox / "x.txt").is_file()
    assert not (tmp_path / "x.txt").exists()


async def test_upload_rejects_blank_filename(db_session):
    upload = UploadFile(file=BytesIO(b"x"), filename="..")
    with pytest.raises(Exception) as exc:
        await fems_router.upload_file(file=upload, case_id=None, db=db_session, user=_user("GUalice001"))
    assert getattr(exc.value, "status_code", None) == 400


async def test_owner_isolation_list_and_get(db_session):
    """User B cannot list or fetch user A's FEMS documents."""
    upload = UploadFile(file=BytesIO(b"alice evidence"), filename="alice.txt")
    await fems_router.upload_file(file=upload, case_id=None, db=db_session, user=_user("GUalice001"))

    docs_b = await fems_router.list_documents(case_id=None, db=db_session, user=_user("GUbob00001"))
    assert docs_b == []

    docs_a = await fems_router.list_documents(case_id=None, db=db_session, user=_user("GUalice001"))
    assert len(docs_a) == 1

    with pytest.raises(Exception) as exc:
        await fems_router.get_document(doc_id=docs_a[0]["id"], db=db_session, user=_user("GUbob00001"))
    assert getattr(exc.value, "status_code", None) == 404
