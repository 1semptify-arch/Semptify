"""OCR-first intake — text-layer detect, classify, proposals, session, finalize."""

import io
import sqlite3
import zipfile

import pytest

from app.core.vault_paths import VAULT_DB_FILE
from app.sdk.vault import db as vault_db
from app.services import intake_ocr


class FakeStorageProvider:
    """Dict-backed storage — files keyed by full path."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.uploads = 0

    async def file_exists(self, path: str) -> bool:
        return path in self.files

    async def download_file(self, path: str) -> bytes:
        return self.files[path]

    async def upload_file(self, file_content, destination_path, filename, mime_type=None):
        self.files[f"{destination_path}/{filename}"] = file_content
        self.uploads += 1
        return None

    async def delete_file(self, path: str) -> bool:
        return self.files.pop(path, None) is not None

    async def create_folder(self, path: str) -> bool:
        return True


LEASE_TEXT = """
RESIDENTIAL LEASE AGREEMENT

This Lease Agreement is made between Landlord: Acme Properties LLC and
Tenant: Jane Renter, for the premises located at 123 Main Street, Apt 4,
Minneapolis, MN 55401.

Term: commencing January 1, 2026 and ending December 31, 2026.
Monthly Rent: $1,250.00 due on the first of each month.
Security Deposit: $1,250.00 payable at signing.

Signed: ____________________    Signed: ____________________
Landlord                        Tenant
"""


def _docx_bytes(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", f"<w:document><w:p><w:t>{text}</w:t></w:p></w:document>")
    return buf.getvalue()


def _fresh_session() -> intake_ocr.IntakeSession:
    return intake_ocr.build_session(
        user_id="u1",
        vault_id="doc1",
        filename="lease.pdf",
        storage_ref="ref",
        text=LEASE_TEXT,
        word_boxes=None,
        has_text_layer=True,
        ocr_method="text_layer",
        doc_type="lease",
    )


def _open_remote(storage) -> sqlite3.Connection:
    path = vault_db.Path(vault_db.tempfile.mkdtemp()) / "v.db"
    path.write_bytes(storage.files[VAULT_DB_FILE])
    return vault_db.open_local(path)


async def _seed_vault(storage):
    await vault_db.ensure_remote(storage)


async def _seed_doc_row(storage, vault_id="doc1"):
    await vault_db.mutate_remote(
        storage,
        lambda conn: conn.execute(
            "INSERT INTO documents (id, name, doc_type, verification_state,"
            " uploaded_at, storage_ref, created_at, updated_at)"
            f" VALUES ('{vault_id}','lease.docx','lease','unverified','t','r','t','t')"
        ),
    )


# ---------------------------------------------------------------------------
# Text layer / classification / proposals
# ---------------------------------------------------------------------------

def test_text_layer_detects_docx():
    text = intake_ocr.extract_text_layer(_docx_bytes(LEASE_TEXT), "lease.docx")
    assert text is not None
    assert "Monthly Rent" in text


def test_text_layer_none_for_images():
    assert intake_ocr.extract_text_layer(b"\x89PNGfake", "scan.png") is None


def test_classify_lease_text():
    key, confidence = intake_ocr.classify_doc_type(LEASE_TEXT)
    assert key == "lease"
    assert confidence > 0


def test_session_proposes_every_checklist_field():
    session = _fresh_session()
    assert session.doc_type == "lease"
    assert len(session.fields) == 10  # every lease checklist field — reviewed or not
    names = {f.name for f in session.fields}
    assert {"landlord_name", "monthly_rent", "signatures_present"} <= names
    rent = next(f for f in session.fields if f.name == "monthly_rent")
    assert rent.proposed_value and "$1,250" in rent.proposed_value
    assert rent.source_span_key
    # Brad's rule: nothing is pre-answered
    assert all(f.answer is None for f in session.fields)


# ---------------------------------------------------------------------------
# Answer rules
# ---------------------------------------------------------------------------

def test_answer_edit_requires_value():
    session = _fresh_session()
    with pytest.raises(ValueError):
        intake_ocr.answer_field(session, session.fields[0].id, "edit")


@pytest.mark.anyio
async def test_finalize_refuses_unreviewed():
    storage = FakeStorageProvider()
    session = _fresh_session()
    result = await intake_ocr.finalize(session, storage)
    assert result["success"] is False
    assert len(result["unanswered"]) == 10


# ---------------------------------------------------------------------------
# End-to-end: start -> answer -> finalize lands in vault.db
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_full_intake_lands_verified():
    storage = FakeStorageProvider()
    await _seed_vault(storage)
    session = await intake_ocr.start_intake(
        user_id="u1",
        vault_id="doc1",
        filename="lease.docx",
        storage_ref="Semptify5.0/Vault/documents/lease.docx",
        content=_docx_bytes(LEASE_TEXT),
        storage=storage,
    )
    assert session.has_text_layer is True
    assert session.ocr_method == "text_layer"

    for f in session.fields:
        intake_ocr.answer_field(session, f.id, "yes")
    result = await intake_ocr.finalize(session, storage)
    assert result["success"] is True
    assert result["verification_state"] == "verified"

    conn = _open_remote(storage)
    doc = conn.execute("SELECT * FROM documents WHERE id='doc1'").fetchone()
    assert doc is not None
    fields = conn.execute(
        "SELECT label, confirm_answer FROM document_fields WHERE document_id='doc1'"
    ).fetchall()
    assert len(fields) == 10
    assert all(a == "yes" for _, a in fields)
    count = conn.execute(
        "SELECT value FROM vault_meta WHERE key='processed_document_count'"
    ).fetchone()[0]
    assert count == "1"
    state = conn.execute(
        "SELECT verification_state, has_text_layer FROM documents WHERE id='doc1'"
    ).fetchone()
    assert state == ("verified", 1)
    vault_db.checkpoint_and_close(conn)


@pytest.mark.anyio
async def test_finalize_edit_gives_in_review():
    storage = FakeStorageProvider()
    await _seed_vault(storage)
    await _seed_doc_row(storage)
    session = _fresh_session()
    for i, f in enumerate(session.fields):
        if i == 0:
            intake_ocr.answer_field(session, f.id, "edit", "Corrected Name LLC")
        else:
            intake_ocr.answer_field(session, f.id, "yes")
    result = await intake_ocr.finalize(session, storage)
    assert result["verification_state"] == "in_review"
    conn = _open_remote(storage)
    row = conn.execute(
        "SELECT value, confirm_answer FROM document_fields WHERE document_id='doc1' AND label=?",
        (session.fields[0].name,),
    ).fetchone()
    assert row == ("Corrected Name LLC", "edited")
    vault_db.checkpoint_and_close(conn)


@pytest.mark.anyio
async def test_finalize_no_gives_mismatched():
    storage = FakeStorageProvider()
    await _seed_vault(storage)
    await _seed_doc_row(storage)
    session = _fresh_session()
    for i, f in enumerate(session.fields):
        intake_ocr.answer_field(session, f.id, "no" if i == 0 else "yes")
    result = await intake_ocr.finalize(session, storage)
    assert result["verification_state"] == "mismatched"


# ---------------------------------------------------------------------------
# Migration 0002 — doc-type union rebuild keeps child rows
# ---------------------------------------------------------------------------

def test_migration_0002_rebuilds_documents_preserving_children(tmp_path, monkeypatch):
    # Build a genuine v1 file: migrations dir limited to 0001.
    migdir = tmp_path / "migrations"
    migdir.mkdir()
    real = vault_db.MIGRATIONS_DIR
    (migdir / "0001_initial.sql").write_text(
        (real / "0001_initial.sql").read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(vault_db, "MIGRATIONS_DIR", migdir)
    path = tmp_path / "vault.db"
    conn = vault_db.open_local(path)
    assert vault_db.schema_version(conn) == 1
    # A v1-legal doc_type plus a child row the rebuild must preserve.
    conn.execute(
        "INSERT INTO documents (id, name, doc_type, uploaded_at, storage_ref,"
        " created_at, updated_at) VALUES ('d1','x','lease','t','r','t','t')"
    )
    conn.execute(
        "INSERT INTO document_fields (id, document_id, label, created_at, updated_at)"
        " VALUES ('f1','d1','x','t','t')"
    )
    conn.commit()
    vault_db.checkpoint_and_close(conn)

    # Restore the real migrations dir: reopening runs 0002 on the v1 file.
    monkeypatch.setattr(vault_db, "MIGRATIONS_DIR", real)
    conn = vault_db.open_local(path)
    assert vault_db.schema_version(conn) == 3
    assert conn.execute("SELECT COUNT(*) FROM document_fields").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    # 'court_summons' (DC taxonomy, not in the handoff's 8) is now legal.
    conn.execute(
        "INSERT INTO documents (id, name, doc_type, uploaded_at, storage_ref,"
        " created_at, updated_at) VALUES ('d2','y','court_summons','t','r','t','t')"
    )
    conn.commit()
    vault_db.checkpoint_and_close(conn)
