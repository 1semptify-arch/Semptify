"""OCR-first document intake — extraction, proposal sessions, finalize.

Pipeline (intake-pipeline-chart-2026-09-19 + Brad's directive: every piece of
OCR-extracted information is reviewed by the user during intake):

    upload -> text-layer check FIRST (native PDF/DOCX skips OCR)
           -> OCRService extract (ephemeral, in-memory — ADR-0007 fallback)
           -> doc_type proposal
           -> EVERY field of the type's checklist proposed into the confirm
              loop — fields with no detected value still require review
           -> finalize writes documents + document_fields + verification_state
              + processed_document_count into vault.db in ONE mutate_remote
              call (per-field pull/push would blow the ~100s origin budget)

Sessions are ephemeral in-memory with a TTL — the ADR-0007 server fallback
is memory-only, so proposal content never persists on Semptify servers. A
restart mid-review loses the session; the documents row (unverified) and
the file itself stay in the vault, so intake can simply be re-run.
"""

from __future__ import annotations

import io
import logging
import re
import time
import zipfile
from dataclasses import dataclass, field

from app.core.document_types import DOCUMENT_TYPES, FieldDef
from app.core.id_gen import make_id
from app.core.utc import utc_now_iso
from app.sdk.vault.db import mutate_remote
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

SESSION_TTL_S = 45 * 60
_MEANINGFUL_WORD_FLOOR = 20

# verification_state rule (handoff's 4 states): all-yes -> verified;
# any edit -> in_review; any no -> mismatched (a rejected proposal is the
# "mismatch" the handoff says can be reopened at the exact field).
_STATE_VERIFIED = "verified"
_STATE_IN_REVIEW = "in_review"
_STATE_MISMATCHED = "mismatched"


# ---------------------------------------------------------------------------
# Text layer — native text skips OCR entirely (text_layer_first rule)
# ---------------------------------------------------------------------------


def _meaningful_words(text: str) -> int:
    return len([w for w in text.split() if len(w) > 2])


def extract_text_layer(file_bytes: bytes, filename: str) -> str | None:
    """Native text for PDF/DOCX, or None when the doc needs real OCR."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        try:
            try:
                import pypdf
            except ImportError:
                import PyPDF2 as pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
            return text if _meaningful_words(text) > _MEANINGFUL_WORD_FLOOR else None
        except Exception:
            return None
    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", "ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text)
            return text if _meaningful_words(text) > _MEANINGFUL_WORD_FLOOR else None
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Classification — naive keyword scoring over the document_types SSOT
# ---------------------------------------------------------------------------


def classify_doc_type(text: str) -> tuple[str, float]:
    """Best-fit doc_type key + rough confidence (0..1). 'other' is the floor."""
    hay = text.lower()
    best_key, best_score = "other", 0
    for key, defn in DOCUMENT_TYPES.items():
        if key == "other":
            continue
        tokens = set(re.findall(r"[a-z]{4,}", defn["label"].lower()))
        tokens |= set(re.findall(r"[a-z]{4,}", defn["description"].lower()))
        for f in defn["fields"]:
            tokens |= {t for t in re.findall(r"[a-z]{4,}", f["ocr_target"].lower()) if len(t) > 4}
        score = sum(1 for t in tokens if t in hay)
        if score > best_score:
            best_key, best_score = key, score
    confidence = min(1.0, best_score / 8.0) if best_score else 0.0
    return best_key, confidence


# ---------------------------------------------------------------------------
# Field proposals — one per checklist field, value may be None
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*,?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_CURRENCY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?|\b\d[\d,]*(?:\.\d{2})?\s*(?:dollars|usd)\b", re.IGNORECASE)
_SIGNATURE_RE = re.compile(r"\b(sign(ed|ature|s)?|executed|duly)\b", re.IGNORECASE)


def _near_keywords(text: str, ocr_target: str) -> list[tuple[int, int]]:
    """(start, end) spans of the text surrounding each ocr_target keyword hit."""
    hay = text.lower()
    spans = []
    for kw in re.split(r"[,/]", ocr_target.lower()):
        kw = kw.strip()
        if len(kw) < 3:
            continue
        idx = hay.find(kw)
        if idx >= 0:
            spans.append((max(0, idx - 150), min(len(text), idx + 150)))
    return spans


def _span_key(text: str, start: int, word_boxes: list | None) -> str:
    """Span reference for the viewer: word-box index for scanned docs,
    char offset for text-layer docs."""
    if word_boxes:
        token = text[start : start + 12].split()[0].strip(".,;:()\"'").lower() if text[start:].strip() else ""
        if token:
            for i, wb in enumerate(word_boxes):
                if wb.text.strip(".,;:()\"'").lower() == token:
                    return f"word:{wb.page}:{i}"
    return f"text:{start}"


def _extract_value(field: FieldDef, text: str, word_boxes: list | None) -> tuple[str | None, str | None]:
    """(proposed_value, source_span_key) for one checklist field."""
    windows = _near_keywords(text, field["ocr_target"])
    scopes = [text[s:e] for s, e in windows] or [text]
    offsets = windows or [(0, len(text))]

    ftype = field["field_type"]
    if ftype == "boolean":
        match = _SIGNATURE_RE.search(text)
        if match:
            return "yes", _span_key(text, match.start(), word_boxes)
        return None, None
    pattern = _DATE_RE if ftype == "date" else _CURRENCY_RE if ftype == "currency" else None
    if pattern:
        for scope, (off, _) in zip(scopes, offsets):
            match = pattern.search(scope)
            if match:
                return match.group(0).strip(), _span_key(text, off + match.start(), word_boxes)
        return None, None
    # text: first non-empty line inside the nearest keyword window
    for scope, (off, _) in zip(scopes, offsets):
        for line in scope.split("\n"):
            line = line.strip()
            if len(line) > 3:
                pos = text.find(line, off)
                return line[:200], _span_key(text, pos if pos >= 0 else off, word_boxes)
    return None, None


@dataclass
class FieldProposal:
    id: str
    name: str
    label: str
    field_type: str
    required: bool
    proposed_value: str | None
    source_span_key: str | None
    answer: str | None = None          # yes | no | edit — None until reviewed
    final_value: str | None = None     # edited value when answer == 'edit'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "field_type": self.field_type,
            "required": self.required,
            "proposed_value": self.proposed_value,
            "source_span_key": self.source_span_key,
            "answer": self.answer,
            "final_value": self.final_value,
        }


@dataclass
class IntakeSession:
    session_id: str
    user_id: str
    vault_id: str
    filename: str
    storage_ref: str
    doc_type: str
    doc_type_confidence: float
    has_text_layer: bool
    ocr_method: str
    fields: list[FieldProposal] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "vault_id": self.vault_id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "doc_type_confidence": self.doc_type_confidence,
            "has_text_layer": self.has_text_layer,
            "ocr_method": self.ocr_method,
            "fields": [f.to_dict() for f in self.fields],
            "fields_total": len(self.fields),
            "fields_answered": sum(1 for f in self.fields if f.answer),
        }


_SESSIONS: dict[str, IntakeSession] = {}


def _sweep_sessions() -> None:
    cutoff = time.time() - SESSION_TTL_S
    for sid in [s for s, v in _SESSIONS.items() if v.created_at < cutoff]:
        _SESSIONS.pop(sid, None)


def get_session(session_id: str) -> IntakeSession | None:
    _sweep_sessions()
    return _SESSIONS.get(session_id)


def build_session(
    *,
    user_id: str,
    vault_id: str,
    filename: str,
    storage_ref: str,
    text: str,
    word_boxes: list | None,
    has_text_layer: bool,
    ocr_method: str,
    doc_type: str | None = None,
) -> IntakeSession:
    """Create the confirm-loop session. Every checklist field becomes a
    proposal — detected or not — because every one gets user review."""
    key, confidence = classify_doc_type(text) if not doc_type else (doc_type, 1.0)
    defn = DOCUMENT_TYPES.get(key) or DOCUMENT_TYPES["other"]
    proposals = []
    for fdef in defn["fields"]:
        value, span = _extract_value(fdef, text, word_boxes)
        proposals.append(
            FieldProposal(
                id=make_id("fld"),
                name=fdef["name"],
                label=fdef["label"],
                field_type=fdef["field_type"],
                required=fdef["required"],
                proposed_value=value,
                source_span_key=span,
            )
        )
    session = IntakeSession(
        session_id=make_id("int"),
        user_id=user_id,
        vault_id=vault_id,
        filename=filename,
        storage_ref=storage_ref,
        doc_type=key,
        doc_type_confidence=confidence,
        has_text_layer=has_text_layer,
        ocr_method=ocr_method,
        fields=proposals,
    )
    _sweep_sessions()
    _SESSIONS[session.session_id] = session
    return session


async def start_intake(
    *,
    user_id: str,
    vault_id: str,
    filename: str,
    storage_ref: str,
    content: bytes,
    storage,
) -> IntakeSession:
    """Extract -> write the unverified documents row -> build the session."""
    text = extract_text_layer(content, filename)
    word_boxes = []
    if text is not None:
        has_text_layer, method = True, "text_layer"
    else:
        result = await ocr_service.extract_text(file_bytes=content, filename=filename)
        text = result.text or ""
        word_boxes = result.word_boxes
        has_text_layer, method = False, result.method

    now = utc_now_iso()
    session = build_session(
        user_id=user_id,
        vault_id=vault_id,
        filename=filename,
        storage_ref=storage_ref,
        text=text,
        word_boxes=word_boxes,
        has_text_layer=has_text_layer,
        ocr_method=method,
    )

    def _upsert_document(conn):
        exists = conn.execute(
            "SELECT id FROM documents WHERE id = ?", (vault_id,)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE documents SET has_text_layer = ?, updated_at = ? WHERE id = ?",
                (1 if has_text_layer else 0, now, vault_id),
            )
        else:
            conn.execute(
                "INSERT INTO documents (id, name, doc_type, verification_state,"
                " uploaded_at, storage_ref, has_text_layer, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    vault_id,
                    filename,
                    session.doc_type,
                    "unverified",
                    now,
                    storage_ref,
                    1 if has_text_layer else 0,
                    now,
                    now,
                ),
            )

    await mutate_remote(storage, _upsert_document)
    return session


def answer_field(
    session: IntakeSession, field_id: str, answer: str, value: str | None = None
) -> FieldProposal:
    """Record one review answer. answer: yes | no | edit (edit needs value)."""
    if answer not in ("yes", "no", "edit"):
        raise ValueError(f"invalid answer {answer!r}")
    target = next((f for f in session.fields if f.id == field_id), None)
    if target is None:
        raise KeyError(f"unknown field {field_id!r}")
    if answer == "edit":
        if not (value or "").strip():
            raise ValueError("edit answer requires a value")
        target.final_value = value.strip()
    target.answer = answer
    return target


def unanswered_fields(session: IntakeSession) -> list[FieldProposal]:
    return [f for f in session.fields if f.answer is None]


async def finalize(session: IntakeSession, storage, doc_type: str | None = None) -> dict:
    """Write all reviewed fields + verification state into vault.db.

    Refuses while any proposed field is unanswered — Brad's rule: every
    piece of OCR information is reviewed during intake, none lands silently.
    """
    pending = unanswered_fields(session)
    if pending:
        return {
            "success": False,
            "error": "unreviewed_fields",
            "unanswered": [f.id for f in pending],
        }

    answers = {f.answer for f in session.fields}
    if answers == {"yes"}:
        state = _STATE_VERIFIED
    elif "no" in answers:
        state = _STATE_MISMATCHED
    else:
        state = _STATE_IN_REVIEW

    final_type = doc_type or session.doc_type
    if final_type not in DOCUMENT_TYPES:
        final_type = "other"
    now = utc_now_iso()
    fields = session.fields

    def _write(conn):
        conn.execute("DELETE FROM document_fields WHERE document_id = ?", (session.vault_id,))
        for f in fields:
            value = f.final_value if f.answer == "edit" else f.proposed_value
            confirm = "edited" if f.answer == "edit" else f.answer
            conn.execute(
                "INSERT INTO document_fields (id, document_id, label, value,"
                " required, confirm_answer, source_span_key, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (f.id, session.vault_id, f.name, value, 1 if f.required else 0,
                 confirm, f.source_span_key, now, now),
            )
        conn.execute(
            "UPDATE documents SET verification_state = ?, doc_type = ?,"
            " updated_at = ? WHERE id = ?",
            (state, final_type, now, session.vault_id),
        )
        conn.execute(
            "UPDATE vault_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)"
            " WHERE key = 'processed_document_count'"
        )
        return state

    written_state = await mutate_remote(storage, _write)
    _SESSIONS.pop(session.session_id, None)
    return {
        "success": True,
        "vault_id": session.vault_id,
        "verification_state": written_state,
        "fields_written": len(fields),
    }
