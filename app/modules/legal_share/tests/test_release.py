"""Legal Share — gated release + custody tests (matrix G9.1–G9.6).

Exercises release_service end-to-end against a real (in-memory sqlite) DB
for documents/document_access_logs/user_relationships, a FakeStorageProvider
for the tenant vault (overlays + artifact writes + original bytes), a fake
vault service for the vault_index identity space, and a stubbed TSA so the
run stays offline (the real stamp_document_hash falls back to HMAC the same
way when the TSA is unreachable).

Asserts the locked invariants: a release is always a NEW artifact, the
original bytes are never modified, artifact hash + timestamp + certificate
travel together, the legend ships inside the bundle, and a linked advocate's
attempt is denied AND logged — never silent.

Run: python -m pytest app/modules/legal_share/tests/test_release.py -v
"""

import hashlib
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.overlay_types import OverlayType
from app.core.user_context import StorageProvider, UserContext, UserRole
from app.core.vault_paths import VAULT_RELEASES
from app.models.unified_overlay_models import CreateOverlayRequest
from app.modules.legal_share import release_service
from app.services.unified_overlay_manager import UnifiedOverlayManager
from tests.test_unified_overlay_manager import FakeStorageProvider

OWNER_ID = "GUalice001"
ADVOCATE_ID = "AVdanny001"
STRANGER_ID = "GUstranger1"
VAULT_ID = "TEST-SL6-vault001"
DOC_TABLE_ID = "TEST-SL6-doc001"
FILE_PATH = "/Semptify/Vault/documents/TEST-SL6-lease001.pdf"
ORIGINAL = b"%PDF-1.4 synthetic TEST-SL6 release doc bytes"
ORIG_SHA = hashlib.sha256(ORIGINAL).hexdigest()


def _ctx(user_id: str = OWNER_ID, token: str = "tok-owner") -> UserContext:
    return UserContext(
        user_id=user_id,
        provider=StorageProvider.GOOGLE_DRIVE,
        storage_user_id=f"drv_{user_id}",
        access_token=token,
        role=UserRole.USER,
    )


def _vault_doc(vault_id: str = VAULT_ID, user_id: str = OWNER_ID):
    return SimpleNamespace(
        vault_id=vault_id,
        user_id=user_id,
        filename="lease.pdf",
        safe_filename="TEST-SL6-lease001.pdf",
        sha256_hash=ORIG_SHA,
        file_size=len(ORIGINAL),
        mime_type="application/pdf",
        storage_path=FILE_PATH,
        storage_provider="local",
        provider_file_id=None,
        uploaded_at="2026-11-10T12:00:00+00:00",
        registry_id="SEM-2026-000001-ABCD",
    )


class FakeVaultService:
    """Mimics VaultUploadService surface release_service calls."""

    def __init__(self, docs=(), contents=None):
        self._docs = {d.vault_id: d for d in docs}
        self._contents = dict(contents or {})

    async def get_document(self, vault_id):
        return self._docs.get(vault_id)

    async def get_user_documents(self, user_id, document_type=None):
        return [d for d in self._docs.values() if d.user_id == user_id]

    async def get_document_content(self, vault_id, access_token=None):
        return self._contents.get(vault_id)


@pytest.fixture
def storage(monkeypatch):
    """One FakeStorageProvider for the owner's vault."""
    fake = FakeStorageProvider()
    monkeypatch.setattr(
        release_service, "get_provider", lambda provider, access_token=None: fake
    )
    return fake


@pytest.fixture
def vault(monkeypatch):
    """Fake vault service — the vault_index identity space + byte reads."""
    fake = FakeVaultService(docs=[_vault_doc()], contents={VAULT_ID: ORIGINAL})
    monkeypatch.setattr(
        "app.services.vault_upload_service.get_vault_service", lambda: fake
    )
    return fake


@pytest.fixture(autouse=True)
def stub_tsa(monkeypatch):
    """Keep the run offline — same fallback shape a dead TSA produces."""
    import app.services.storage.tsa as tsa

    async def fake_stamp(document_hash, timestamp_iso, tsa_url=None):
        return tsa.TSAResult(
            timestamp_iso=timestamp_iso,
            document_hash=document_hash,
            token_b64="dGVzdC1obWFjLWZhbGxiYWNrLXRva2Vu",  # pragma: allowlist secret
            tsa_backed=False,
            tsa_url=None,
            error="test stub",
        )

    monkeypatch.setattr(tsa, "stamp_document_hash", fake_stamp)


async def _manager(user_id: str, storage) -> UnifiedOverlayManager:
    return UnifiedOverlayManager(storage, user_id)


@pytest.fixture
async def db_session(tmp_path, monkeypatch):
    """Real sqlite session — this module's tests dir has no parent conftest,
    so the DATABASE_URL + table setup lives here."""
    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    from app.core.config import get_settings
    from app.core.database import Base, close_db, get_db_session, get_engine

    get_settings.cache_clear()
    await close_db()
    from app.models import models  # noqa: F401 — register tables

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with get_db_session() as session:
        yield session
    await close_db()


def _user(user_id: str):
    from app.models.models import User

    return User(
        id=user_id,
        primary_provider="google_drive",
        storage_user_id=f"store-{user_id}",
    )


async def _seed_owner_and_doc(db_session, user_id=OWNER_ID):
    from app.models.models import Document

    db_session.add(_user(user_id))
    db_session.add(
        Document(
            id=DOC_TABLE_ID,
            user_id=user_id,
            filename="TEST-SL6-lease001.pdf",
            original_filename="lease.pdf",
            file_path=FILE_PATH,
            file_size=len(ORIGINAL),
            mime_type="application/pdf",
            sha256_hash=ORIG_SHA,
        )
    )
    await db_session.commit()


# =============================================================================
# DocRef resolution — both identity spaces
# =============================================================================


@pytest.mark.anyio
async def test_resolve_vault_document(storage, vault, db_session):
    ref = await release_service.resolve_document(_ctx(), VAULT_ID, db_session)
    assert ref is not None
    assert ref.canonical_id == VAULT_ID
    assert ref.owner_user_id == OWNER_ID
    assert ref.sha256_recorded == ORIG_SHA
    assert ref.storage_path == FILE_PATH


@pytest.mark.anyio
async def test_resolve_documents_table_correlates_vault(storage, vault, db_session):
    """A documents.id resolves AND picks up the vault identity via file_path."""
    await _seed_owner_and_doc(db_session)
    ref = await release_service.resolve_document(_ctx(), DOC_TABLE_ID, db_session)
    assert ref is not None
    assert ref.canonical_id == VAULT_ID  # vault doc wins — matched on file_path
    assert ref.documents_id == DOC_TABLE_ID
    assert VAULT_ID in release_service.all_doc_ids(ref)
    assert DOC_TABLE_ID in release_service.all_doc_ids(ref)


@pytest.mark.anyio
async def test_resolve_unknown_returns_none(storage, vault, db_session):
    assert await release_service.resolve_document(_ctx(), "nope", db_session) is None


# =============================================================================
# Legend + annotations snapshot
# =============================================================================


@pytest.mark.anyio
async def test_gather_legend_merges_document_key(storage, vault, db_session):
    user = _ctx()
    manager = await _manager(OWNER_ID, storage)
    await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.DOCUMENT_KEY,
            document_id=VAULT_ID,
            vault_path=FILE_PATH,
            payload={"colors": {"yellow": "The landlord said this"}},
        )
    )
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)
    legend = await release_service.gather_legend(user, ref)
    assert legend["is_default"] is False
    assert legend["colors"]["yellow"] == "The landlord said this"
    assert legend["colors"]["blue"] == "Date or deadline"  # default preserved


@pytest.mark.anyio
async def test_gather_legend_defaults_when_no_key(storage, vault, db_session):
    ref = await release_service.resolve_document(_ctx(), VAULT_ID, db_session)
    legend = await release_service.gather_legend(_ctx(), ref)
    assert legend["is_default"] is True
    assert legend["colors"]["yellow"] == "Key evidence"


# =============================================================================
# The gated release — G9.1, G9.2, G9.5
# =============================================================================


@pytest.mark.anyio
async def test_release_creates_new_artifact_original_untouched(storage, vault, db_session):
    """The release produces a NEW file; original bytes are never modified."""
    user = _ctx()
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)

    record = await release_service.release_document(user, ref, db_session)

    # Record carries artifact hash + timestamp + certificate together.
    assert record["release_id"].startswith("rls_")
    assert record["artifact_sha256"]
    assert record["released_at"]
    assert record["certificate"]["document_hash"] == ORIG_SHA
    assert record["certificate"]["signature"]
    assert record["certificate"]["tsa_token"]
    assert record["original_sha256"] == ORIG_SHA
    assert record["intake_sha256"] == ORIG_SHA
    assert record["hash_verified_against_intake"] is True
    assert record["original_intact_after_release"] is True

    # A NEW file exists under releases/ — not under the document's own path.
    assert record["artifact_path"].startswith(f"{VAULT_RELEASES}/{VAULT_ID}")
    artifact = await storage.download_file(record["artifact_path"])
    assert hashlib.sha256(artifact).hexdigest() == record["artifact_sha256"]

    # Original bytes in storage are untouched — bit-for-bit.
    assert vault._contents[VAULT_ID] == ORIGINAL

    # The bundle decodes: original bytes, certificate, legend, custody, manifest.
    with zipfile.ZipFile(io.BytesIO(artifact)) as zf:
        names = set(zf.namelist())
        assert "certificate.json" in names
        assert "legend.json" in names
        assert "overlays.json" in names
        assert "custody-log.json" in names
        assert "release.json" in names
        assert "README.txt" in names
        doc_entry = next(n for n in names if n.startswith("document/"))
        assert zf.read(doc_entry) == ORIGINAL
        cert = json.loads(zf.read("certificate.json"))
        assert cert["document_hash"] == ORIG_SHA
        manifest = json.loads(zf.read("release.json"))
        assert manifest["document"]["canonical_id"] == VAULT_ID
        legend = json.loads(zf.read("legend.json"))
        assert legend["colors"]["yellow"]


@pytest.mark.anyio
async def test_release_is_listed_and_downloadable(storage, vault, db_session):
    user = _ctx()
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)
    record = await release_service.release_document(user, ref, db_session)

    releases = await release_service.list_releases(user, ref)
    assert len(releases) == 1
    assert releases[0]["release_id"] == record["release_id"]
    assert releases[0]["artifact_sha256"] == record["artifact_sha256"]
    assert releases[0]["certificate"]["document_hash"] == ORIG_SHA

    found = await release_service.fetch_release_artifact(user, ref, record["release_id"])
    assert found is not None
    data, filename = found
    assert data[:4] == b"PK\x03\x04"
    assert filename.endswith(".zip")


# =============================================================================
# Custody log — G9.6
# =============================================================================


@pytest.mark.anyio
async def test_custody_log_chronological_and_covers_events(storage, vault, db_session):
    """Intake → access rows → release, in order, all in one exportable list."""
    from app.models.models import DocumentAccessLog

    await _seed_owner_and_doc(db_session)
    db_session.add(
        DocumentAccessLog(
            actor_user_id=ADVOCATE_ID,
            actor_role="advocate",
            tenant_user_id=OWNER_ID,
            document_id=VAULT_ID,
            action="view_document",
            outcome="ok",
            detail="advocate opened the document",
        )
    )
    db_session.add(
        DocumentAccessLog(
            actor_user_id=ADVOCATE_ID,
            actor_role="advocate",
            tenant_user_id=OWNER_ID,
            document_id=DOC_TABLE_ID,  # other identity space — must still match
            action="annotate",
            outcome="ok",
        )
    )
    await db_session.commit()

    user = _ctx()
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)
    record = await release_service.release_document(user, ref, db_session)

    events = await release_service.build_custody_log(user, ref, db_session)
    kinds = [e["event"] for e in events]
    assert kinds[0] == "intake"
    assert "view_document" in kinds
    assert "annotate" in kinds
    assert kinds[-1] == "release"
    timestamps = [e["timestamp"] for e in events]
    assert timestamps == sorted(timestamps)
    release_events = [e for e in events if e["event"] == "release"]
    assert record["release_id"] in release_events[0]["detail"]


# =============================================================================
# Ownership gate — G9.4 (advocate denial is explicit + logged, never silent)
# =============================================================================


@pytest.mark.anyio
async def test_linked_advocate_release_denied_and_logged(storage, vault, db_session):
    from fastapi import HTTPException

    from app.models.models import DocumentAccessLog, RelationshipType, UserRelationship
    from app.modules.legal_share import router

    db_session.add(_user(OWNER_ID))
    db_session.add(_user(ADVOCATE_ID))
    db_session.add(
        UserRelationship(
            from_user_id=ADVOCATE_ID,
            to_user_id=OWNER_ID,
            relationship_type=RelationshipType.ADVOCACY.value,
            is_active=True,
            context={"status": "active", "initiated_by": "tenant"},
        )
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await router._resolve_for_release(_ctx(ADVOCATE_ID), VAULT_ID, db_session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "release_denied"

    rows = (
        await db_session.execute(
            select(DocumentAccessLog).where(DocumentAccessLog.action == "release_denied")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].actor_user_id == ADVOCATE_ID
    assert rows[0].tenant_user_id == OWNER_ID
    assert rows[0].outcome == "denied"


@pytest.mark.anyio
async def test_stranger_release_404s_silently(storage, vault, db_session):
    """No relationship → same 404 as a nonexistent document. No oracle."""
    from fastapi import HTTPException

    from app.modules.legal_share import router

    db_session.add(_user(STRANGER_ID))
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await router._resolve_for_release(_ctx(STRANGER_ID), VAULT_ID, db_session)
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_owner_release_gate_passes(storage, vault, db_session):
    from app.modules.legal_share import router

    db_session.add(_user(OWNER_ID))
    await db_session.commit()

    ref = await router._resolve_for_release(_ctx(), VAULT_ID, db_session)
    assert ref.canonical_id == VAULT_ID


# =============================================================================
# Integrity surface — G9.5 (hash recorded at intake, recomputable any time)
# =============================================================================


@pytest.mark.anyio
async def test_integrity_status_recomputes_and_pairs_releases(storage, vault, db_session):
    user = _ctx()
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)
    record = await release_service.release_document(user, ref, db_session)

    status = await release_service.integrity_status(user, ref, db_session)
    assert status["intake_sha256"] == ORIG_SHA
    assert status["recomputed_sha256"] == ORIG_SHA
    assert status["matches_intake"] is True
    assert status["bytes_available"] is True
    assert len(status["releases"]) == 1
    rel = status["releases"][0]
    assert rel["artifact_sha256"] == record["artifact_sha256"]
    assert rel["released_at"] == record["released_at"]
    assert rel["certificate"]["document_hash"] == ORIG_SHA
    assert status["custody_log"]


@pytest.mark.anyio
async def test_integrity_flags_tampered_original(storage, vault, db_session):
    """If the stored bytes no longer match the intake hash, the surface says so."""
    vault._contents[VAULT_ID] = b"%PDF-1.4 TAMPERED bytes"
    user = _ctx()
    ref = await release_service.resolve_document(user, VAULT_ID, db_session)
    status = await release_service.integrity_status(user, ref, db_session)
    assert status["matches_intake"] is False
    assert status["recomputed_sha256"] != status["intake_sha256"]
