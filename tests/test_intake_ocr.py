"""OCR-first intake — text-layer detect, classify, proposals, session, finalize."""

import io
import sqlite3
import zipfile

import pytest

from app.core.document_types import DOCUMENT_TYPES
from app.core.vault_paths import VAULT_DB_FILE
from app.sdk.vault import db as vault_db
from app.services import intake_ocr, intake_segmentation
from app.services.ocr_service import WordBox


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
# Pass 0 — segmentation, ranking, staged extraction
# ---------------------------------------------------------------------------


def test_segment_text_blocks_char_spans():
    regions = intake_segmentation.segment(LEASE_TEXT, None, True)
    assert len(regions) >= 3
    assert all(r.char_span for r in regions)
    # Spans tile the document without overlap and keep order.
    spans = sorted(r.char_span for r in regions)
    assert spans[0][0] == 0
    for (a_end, _), (b_start, _) in zip(spans, spans[1:]):
        assert b_start >= a_end


def test_segment_word_boxes_clusters_lines():
    boxes = [
        WordBox("Lease", 10, 10, 40, 10, page=0),
        WordBox("Agreement", 60, 10, 60, 10, page=0),
        WordBox("Rent", 10, 60, 30, 10, page=0),   # big gap -> new block
        WordBox("$1,250", 50, 60, 50, 10, page=0),
    ]
    regions = intake_segmentation.segment("", boxes, False)
    assert len(regions) == 2
    first = regions[0]
    assert first.bbox == {"left": 10, "top": 10, "width": 110, "height": 10}
    assert first.word_indices == [0, 1]
    assert "Agreement" in first.text


def test_rank_regions_passes_and_manual_review():
    regions = [
        intake_segmentation.Region(
            region_id="r1", label="b1",
            text="Monthly Rent: $1,250.00 due on the first of each month.",
        ),
        intake_segmentation.Region(region_id="r2", label="b2", text="zz qx vwf tplm"),
    ]
    intake_segmentation.rank_regions(regions, DOCUMENT_TYPES["lease"])
    assert regions[0].confidence > 0
    assert regions[0].pass_number == 1
    assert regions[1].pass_number == intake_segmentation.PASS_CAP
    intake_segmentation.finalize_region_status(regions)
    # Signaled data but nothing resolved -> flagged for a look.
    assert regions[0].status == "manual_review"
    # Zero signal was never a data candidate -> settles quietly, no flag.
    assert regions[1].status == "no_data"


def test_build_session_tags_region_provenance():
    session = _fresh_session()
    attributed = [f for f in session.fields if f.region_id]
    assert attributed  # at least one proposal came out of a region
    for f in attributed:
        assert 1 <= f.pass_number <= intake_segmentation.PASS_CAP
        region = next(r for r in session.regions if r.region_id == f.region_id)
        assert f.name in region.field_names
        assert region.status == "resolved"


def test_pending_session_lifecycle():
    session = intake_ocr.create_pending_session(
        user_id="u1", vault_id="docX", filename="scan.png", storage_ref="ref"
    )
    assert session.status == "processing"
    assert session.to_dict()["status"] == "processing"
    assert intake_ocr.get_session(session.session_id) is session


@pytest.mark.anyio
async def test_pipeline_marks_ready_with_regions():
    storage = FakeStorageProvider()
    await _seed_vault(storage)
    session = intake_ocr.create_pending_session(
        user_id="u1",
        vault_id="doc1",
        filename="lease.docx",
        storage_ref="Semptify5.0/Vault/documents/lease.docx",
    )
    await intake_ocr.run_intake_pipeline(
        session, _docx_bytes(LEASE_TEXT), storage
    )
    assert session.status == "ready"
    assert session.doc_type == "lease"
    assert session.regions
    assert session.fields
    # overlay creation is attempted explicitly — FakeStorage may not support
    # the overlay folders, but the session must record the outcome either way.
    assert session.overlay_status in ("created", "error")


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
    assert vault_db.schema_version(conn) == 2
    assert conn.execute("SELECT COUNT(*) FROM document_fields").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    # 'court_summons' (DC taxonomy, not in the handoff's 8) is now legal.
    conn.execute(
        "INSERT INTO documents (id, name, doc_type, uploaded_at, storage_ref,"
        " created_at, updated_at) VALUES ('d2','y','court_summons','t','r','t','t')"
    )
    conn.commit()
    vault_db.checkpoint_and_close(conn)


# ---------------------------------------------------------------------------
# Finalize -> doc-index sync (DC list/checklist mirror)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_finalize_syncs_doc_index(monkeypatch):
    """After finalize, _sync_doc_index mirrors type/status/field state onto
    the server-side index record the doc list and checklist read."""
    import json

    from app.modules.document_center import intake_router
    import app.services.vault_upload_service as vus

    storage = FakeStorageProvider()
    await _seed_vault(storage)
    await _seed_doc_row(storage)
    session = _fresh_session()
    for f in session.fields:
        f.answer = "yes"
    session.fields[0].answer = "edit"
    session.fields[0].final_value = "corrected-value"
    result = await intake_ocr.finalize(session, storage)
    assert result["success"] is True
    assert result["verification_state"] == "in_review"

    updates: dict = {}

    class _FakeIndex:
        async def update(self, vault_id, **kwargs):
            updates[vault_id] = kwargs
            return None

    class _FakeDoc:
        review_state_json = json.dumps({"field_confirm_state": {"old_field": "confirmed"}})

    class _FakeSvc:
        index = _FakeIndex()

        async def get_document(self, vault_id):
            return _FakeDoc()

    monkeypatch.setattr(vus, "get_vault_service", lambda: _FakeSvc())

    await intake_router._sync_doc_index(session, None, result)

    assert updates[session.vault_id]["processed"] is True
    assert updates[session.vault_id]["document_type"] == session.doc_type
    state = json.loads(updates[session.vault_id]["review_state_json"])
    assert state["manual_status"] == "review"  # in_review -> review
    first = session.fields[0]
    assert state["field_confirm_state"][first.name] == "corrected"
    assert state["field_confirm_state"][first.name + "_value"] == "corrected-value"
    assert state["field_confirm_state"][session.fields[1].name] == "confirmed"
    assert state["field_confirm_state"]["old_field"] == "confirmed"  # merge keeps prior state
