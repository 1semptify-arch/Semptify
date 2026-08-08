"""
Case Builder - Curated Packet Export
====================================

Builds a single ZIP export that curates documents, highlights, notes,
and footnotes from a case into a virtual folder.

ZIP layout:
  manifest.json              # case + document + overlay manifest
  clean/                     # original documents, unmodified
  marked/                    # each document with its annotation overlays:
                             #   - PDFs: original pages + appended annotation pages
                             #   - images: converted to PDF + annotation pages
                             #   - other: original file + sidecar _annotations.pdf
  summary/
    packet-summary.pdf       # printable summary of all annotations
    packet-summary.txt       # plain-text summary of all annotations

This implements option 3 requested by the product owner: both marked-up
and clean copies, plus a summary, in a single ZIP.
"""

import io
import json
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.models.unified_overlay_models import UnifiedOverlay
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager
from app.services.vault_upload_service import VaultDocument, get_vault_service

logger = logging.getLogger(__name__)


class PacketExportRequest(BaseModel):
    """Request body for curated packet export."""

    document_ids: list[str] = Field(
        default_factory=list,
        description="Specific vault IDs or safe_filenames to include. If empty, uses case evidence.",
    )
    include_clean: bool = Field(
        default=True,
        description="Include clean/ original copies.",
    )
    include_marked: bool = Field(
        default=True,
        description="Include marked/ copies with overlays.",
    )
    include_summary: bool = Field(
        default=True,
        description="Include summary/ report of all annotations.",
    )
    overlay_types: list[str] = Field(
        default_factory=lambda: [
            OverlayType.HIGHLIGHT.value,
            OverlayType.NOTE.value,
            OverlayType.FOOTNOTE.value,
        ],
        description="Which overlay types to include.",
    )


@dataclass
class _MarkedFile:
    name: str
    content: bytes


def _safe_pdf_text(text: Any) -> str:
    """Ensure text can be drawn by reportlab's default fonts (latin-1)."""
    if text is None:
        return ""
    s = str(text)
    # Replace characters outside latin-1 with a placeholder.
    return s.encode("latin-1", "replace").decode("latin-1")


def _sanitize_filename(name: str | None) -> str:
    """Make a filesystem-safe filename, preserving the last extension."""
    if not name:
        return "document"
    name = str(name).strip().replace("\\", "_").replace("/", "_")
    base, dot, ext = name.rpartition(".")
    if not dot or len(ext) > 20:
        # No sensible extension, keep whole name
        safe = re.sub(r"[^a-zA-Z0-9_.\-]", "_", name).strip("._")
        return safe or "document"
    safe_base = re.sub(r"[^a-zA-Z0-9_.\-]", "_", base).strip("._")
    safe_ext = re.sub(r"[^a-zA-Z0-9]", "_", ext).lower()
    return f"{safe_base}.{safe_ext}"


def _change_ext(filename: str, ext: str) -> str:
    base = Path(filename).stem
    return f"{base}{ext}"


def _sidecar_name(filename: str) -> str:
    base = Path(filename).stem
    return f"{base}_annotations.pdf"


async def _get_case_documents(
    case: dict[str, Any],
    user,
    request: PacketExportRequest,
) -> list[VaultDocument]:
    """Resolve VaultDocument objects for the requested export."""
    vault_service = get_vault_service()
    try:
        all_docs = await vault_service.get_user_documents(user.user_id)
    except Exception as e:
        logger.warning("Could not list vault documents for %s: %s", user.user_id, e)
        all_docs = []

    if request.document_ids:
        wanted = set(request.document_ids)
        return [d for d in all_docs if d.vault_id in wanted or d.safe_filename in wanted]

    by_path: dict[str, VaultDocument] = {}
    for d in all_docs:
        by_path[d.storage_path] = d
        by_path[d.safe_filename] = d
        by_path[d.vault_id] = d

    evidence = case.get("evidence") or []
    docs: list[VaultDocument] = []
    for ev in evidence:
        fp = ev.get("file_path") or ev.get("vault_path") or ev.get("document_id") or ev.get("path")
        if not fp:
            continue
        if fp in by_path:
            docs.append(by_path[fp])
            continue
        # Match by basename
        base = Path(fp).name
        if base in by_path:
            docs.append(by_path[base])
    return docs


async def _download_vault_document(doc: VaultDocument, user) -> bytes | None:
    """Download original document bytes from the user's storage."""
    vault_service = get_vault_service()
    if doc.storage_provider == "local":
        content = vault_service._local_read_file(doc.storage_path)
        if content:
            return content
        logger.warning("Could not read local document %s", doc.vault_id)
        return None

    try:
        storage = get_provider(doc.storage_provider, access_token=user.access_token)
    except Exception as e:
        logger.warning("Could not get storage provider for %s: %s", doc.vault_id, e)
        return None

    if doc.provider_file_id:
        try:
            return await storage.download_file(f"id:{doc.provider_file_id}")
        except Exception as exc:
            logger.debug("Provider file id download failed for %s: %s", doc.vault_id, exc)

    try:
        return await storage.download_file(doc.storage_path)
    except Exception as e:
        logger.warning("Could not download document %s: %s", doc.vault_id, e)
        return None


async def _fetch_overlays(
    doc: VaultDocument,
    user,
    wanted_types: list[OverlayType],
) -> list[UnifiedOverlay]:
    """Fetch annotation overlays for a document."""
    if doc.storage_provider == "local" or not wanted_types:
        return []

    try:
        storage = get_provider(doc.storage_provider, access_token=user.access_token)
    except Exception:
        return []

    manager = UnifiedOverlayManager(storage, user.user_id)
    response = await manager.get_overlays(document_id=doc.safe_filename)
    if not response or not response.success:
        return []
    return [o for o in response.overlays if o.overlay_type in wanted_types]


def _overlay_as_paragraphs(
    overlay: UnifiedOverlay,
    style_name: str = "Normal",
) -> list[Paragraph]:
    """Convert an overlay into reportlab Paragraphs for an annotation page."""
    styles = getSampleStyleSheet()
    base_style = styles.get(style_name, styles["Normal"])
    result = []

    otype = _safe_pdf_text(overlay.overlay_type.value)
    result.append(Paragraph(f"<b>{otype.upper()}</b>", base_style))

    payload = overlay.payload or {}
    if overlay.overlay_type == OverlayType.HIGHLIGHT:
        color = _safe_pdf_text(payload.get("color", "yellow"))
        rng = payload.get("range") or {}
        text = _safe_pdf_text(rng.get("text") or "")
        note = _safe_pdf_text(payload.get("note") or "")
        page = rng.get("page")
        if text:
            result.append(Paragraph(f"<b>Selected text:</b> {text}", base_style))
        if note:
            result.append(Paragraph(f"<b>Note:</b> {note}", base_style))
        if page:
            result.append(Paragraph(f"<b>Page:</b> {page}", base_style))
        if color:
            result.append(Paragraph(f"<b>Color:</b> {color}", base_style))
    elif overlay.overlay_type == OverlayType.NOTE:
        content = _safe_pdf_text(payload.get("content") or "")
        note_type = _safe_pdf_text(payload.get("note_type", "user"))
        priority = _safe_pdf_text(payload.get("priority", "normal"))
        tags = payload.get("tags") or []
        rng = payload.get("range") or {}
        if content:
            result.append(Paragraph(f"<b>Content:</b> {content}", base_style))
        if note_type:
            result.append(Paragraph(f"<b>Type:</b> {note_type}", base_style))
        if priority:
            result.append(Paragraph(f"<b>Priority:</b> {priority}", base_style))
        if tags:
            result.append(
                Paragraph(
                    f"<b>Tags:</b> {', '.join(_safe_pdf_text(t) for t in tags)}",
                    base_style,
                )
            )
        if rng.get("page"):
            result.append(Paragraph(f"<b>Page:</b> {rng['page']}", base_style))
    elif overlay.overlay_type == OverlayType.FOOTNOTE:
        number = payload.get("number")
        content = _safe_pdf_text(payload.get("content") or "")
        citation = _safe_pdf_text(payload.get("citation") or "")
        rng = payload.get("range") or {}
        text = _safe_pdf_text(rng.get("text") or "")
        if number is not None:
            result.append(Paragraph(f"<b>Footnote #{number}</b>", base_style))
        if text:
            result.append(Paragraph(f"<b>Reference text:</b> {text}", base_style))
        if content:
            result.append(Paragraph(f"<b>Content:</b> {content}", base_style))
        if citation:
            result.append(Paragraph(f"<b>Citation:</b> {citation}", base_style))
        if rng.get("page"):
            result.append(Paragraph(f"<b>Page:</b> {rng['page']}", base_style))

    created = _safe_pdf_text(overlay.created_at.isoformat() if overlay.created_at else "")
    if created:
        result.append(Paragraph(f"<i>Created: {created}</i>", styles["Italic"]))
    return result


def _build_annotation_pdf(
    doc: VaultDocument,
    overlays: list[UnifiedOverlay],
    doc_index: int,
    total: int,
) -> bytes:
    """Build a PDF page (or pages) describing the overlays for one document."""
    buf = io.BytesIO()
    doc_template = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    filename = _safe_pdf_text(doc.filename)
    story.append(Paragraph(f"Annotations for {filename}", styles["Heading2"]))
    story.append(Paragraph(f"Document {doc_index} of {total} in packet", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    if not overlays:
        story.append(Paragraph("No annotations for this document.", styles["Normal"]))
    else:
        for idx, overlay in enumerate(overlays, 1):
            story.append(Paragraph(f"Annotation {idx}", styles["Heading3"]))
            for para in _overlay_as_paragraphs(overlay):
                story.append(para)
            story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            "This page contains user highlights, notes, and footnotes. It does not modify the original document.",
            styles["Italic"],
        )
    )
    doc_template.build(story)
    return buf.getvalue()


def _build_summary_pdf(
    case: dict[str, Any],
    doc_entries: list[tuple[VaultDocument, bytes, list[UnifiedOverlay]]],
) -> bytes:
    """Build a summary PDF for the entire packet."""
    buf = io.BytesIO()
    doc_template = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph("Packet Annotation Summary", styles["Title"]))
    case_number = _safe_pdf_text(case.get("case_number") or case.get("case_id"))
    story.append(Paragraph(f"Case: {case_number}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {utc_now().isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    for doc, _content, overlays in doc_entries:
        filename = _safe_pdf_text(doc.filename)
        story.append(Paragraph(f"Document: {filename}", styles["Heading2"]))
        if not overlays:
            story.append(Paragraph("No annotations.", styles["Normal"]))
        else:
            for overlay in overlays:
                for para in _overlay_as_paragraphs(overlay):
                    story.append(para)
                story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            "This summary collects highlights, notes, and footnotes across all packet documents. "
            "It does not contain legal advice.",
            styles["Italic"],
        )
    )
    doc_template.build(story)
    return buf.getvalue()


def _build_summary_text(
    case: dict[str, Any],
    doc_entries: list[tuple[VaultDocument, bytes, list[UnifiedOverlay]]],
) -> bytes:
    """Build a plain-text summary for the entire packet."""
    lines = [
        "Packet Annotation Summary",
        "=" * 50,
        f"Case: {case.get('case_number') or case.get('case_id')}",
        f"Generated: {utc_now().isoformat()}",
        "",
    ]
    for doc, _content, overlays in doc_entries:
        lines.append(f"Document: {doc.filename}")
        if not overlays:
            lines.append("  No annotations.")
        else:
            for overlay in overlays:
                lines.append(f"  [{overlay.overlay_type.value}]")
                payload = overlay.payload or {}
                if overlay.overlay_type == OverlayType.HIGHLIGHT:
                    note = payload.get("note") or ""
                    text = (payload.get("range") or {}).get("text") or ""
                    if text:
                        lines.append(f"    Selected text: {text}")
                    if note:
                        lines.append(f"    Note: {note}")
                elif overlay.overlay_type == OverlayType.NOTE:
                    content = payload.get("content") or ""
                    if content:
                        lines.append(f"    Content: {content}")
                elif overlay.overlay_type == OverlayType.FOOTNOTE:
                    number = payload.get("number")
                    content = payload.get("content") or ""
                    citation = payload.get("citation") or ""
                    if number is not None:
                        lines.append(f"    Footnote #{number}")
                    if content:
                        lines.append(f"    Content: {content}")
                    if citation:
                        lines.append(f"    Citation: {citation}")
                lines.append("")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes | None:
    """Merge a list of PDF byte strings into one PDF."""
    if not pdf_bytes_list:
        return None
    try:
        from PyPDF2 import PdfMerger
    except ImportError:
        logger.warning("PyPDF2 not available; cannot merge PDFs")
        return None

    merger = PdfMerger()
    for pdf_bytes in pdf_bytes_list:
        try:
            merger.append(io.BytesIO(pdf_bytes))
        except Exception as e:
            logger.warning("Could not append PDF: %s", e)
    try:
        out = io.BytesIO()
        merger.write(out)
        out.seek(0)
        return out.getvalue()
    except Exception as e:
        logger.warning("Could not write merged PDF: %s", e)
        return None


def _image_to_pdf(image_bytes: bytes, mime_type: str) -> bytes | None:
    """Convert an image to a single-page PDF."""
    try:
        from PIL import Image as PILImage
    except ImportError:
        logger.warning("PIL not available; cannot convert image to PDF")
        return None
    try:
        pil_img = PILImage.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.warning("Could not open image (%s): %s", mime_type, e)
        return None

    # Convert to RGB if necessary (e.g. PNG with transparency)
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")

    page_width, page_height = letter
    available_w = page_width - 1.5 * inch
    available_h = page_height - 1.5 * inch
    img_w, img_h = pil_img.size
    if not img_w or not img_h:
        return None
    scale = min(available_w / img_w, available_h / img_h, 1.0)
    width = img_w * scale
    height = img_h * scale

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    try:
        # reportlab.platypus.Image accepts a PIL Image or a file path.
        img = Image(pil_img, width=width, height=height)
    except Exception as e:
        logger.warning("Could not create reportlab image: %s", e)
        return None

    story = [Spacer(1, 0.25 * inch), img]
    try:
        doc.build(story)
    except Exception as e:
        logger.warning("Could not build image PDF: %s", e)
        return None
    return buf.getvalue()


async def _build_marked_entries(
    doc: VaultDocument,
    content: bytes,
    overlays: list[UnifiedOverlay],
    doc_index: int,
    total: int,
) -> list[_MarkedFile]:
    """Create marked-up copy entries for one document."""
    base = _sanitize_filename(doc.filename) or f"doc-{doc.vault_id}"
    annotation_pdf = _build_annotation_pdf(doc, overlays, doc_index, total)

    if not overlays:
        # No annotations: marked copy is the same as clean copy.
        return [_MarkedFile(name=base, content=content)]

    mime = (doc.mime_type or "").lower()

    if mime == "application/pdf":
        merged = _merge_pdfs([content, annotation_pdf])
        if merged:
            return [_MarkedFile(name=base, content=merged)]

    if mime.startswith("image/"):
        image_pdf = _image_to_pdf(content, mime)
        if image_pdf:
            merged = _merge_pdfs([image_pdf, annotation_pdf])
            if merged:
                new_name = _change_ext(base, ".pdf")
                return [_MarkedFile(name=new_name, content=merged)]

    # Fallback: include original file plus a sidecar annotations PDF.
    sidecar = _sidecar_name(base)
    return [
        _MarkedFile(name=base, content=content),
        _MarkedFile(name=sidecar, content=annotation_pdf),
    ]


async def build_curated_packet_zip(
    case: dict[str, Any],
    user,
    request: PacketExportRequest,
) -> tuple[bytes, str]:
    """Build the curated packet ZIP and return (bytes, filename)."""
    if not request.include_clean and not request.include_marked and not request.include_summary:
        raise ValueError("At least one of include_clean, include_marked, or include_summary must be true")

    docs = await _get_case_documents(case, user, request)
    if not docs:
        raise ValueError("No documents found for packet export")

    try:
        wanted_types = [OverlayType(t) for t in request.overlay_types]
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid overlay type: {e}")

    doc_entries: list[tuple[VaultDocument, bytes, list[UnifiedOverlay]]] = []
    for doc in docs:
        content = await _download_vault_document(doc, user)
        if not content:
            continue
        overlays = await _fetch_overlays(doc, user, wanted_types)
        doc_entries.append((doc, content, overlays))

    if not doc_entries:
        raise ValueError("Could not download any documents for packet export")

    buf = io.BytesIO()
    used_names: set = set()
    manifest: list[dict[str, Any]] = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, (doc, content, overlays) in enumerate(doc_entries, 1):
            base_name = _sanitize_filename(doc.filename) or doc.vault_id
            if base_name in used_names:
                base, dot, ext = base_name.rpartition(".")
                base_name = f"{base}_{idx}{dot}{ext}" if dot else f"{base_name}_{idx}"
            used_names.add(base_name)

            if request.include_clean:
                zf.writestr(f"clean/{base_name}", content)

            if request.include_marked:
                marked_files = await _build_marked_entries(doc, content, overlays, idx, len(doc_entries))
                for mf in marked_files:
                    zf.writestr(f"marked/{mf.name}", mf.content)

            manifest.append(
                {
                    "vault_id": doc.vault_id,
                    "filename": doc.filename,
                    "safe_filename": doc.safe_filename,
                    "mime_type": doc.mime_type,
                    "storage_path": doc.storage_path,
                    "included_annotations": len(overlays),
                    "annotation_types": sorted({o.overlay_type.value for o in overlays}),
                }
            )

        if request.include_summary:
            zf.writestr("summary/packet-summary.pdf", _build_summary_pdf(case, doc_entries))
            zf.writestr("summary/packet-summary.txt", _build_summary_text(case, doc_entries))

        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "packet_type": "curated",
                    "case_id": case.get("case_id"),
                    "case_number": case.get("case_number"),
                    "generated_at": utc_now().isoformat(),
                    "user_id": user.user_id,
                    "include_clean": request.include_clean,
                    "include_marked": request.include_marked,
                    "include_summary": request.include_summary,
                    "overlay_types": [t.value for t in wanted_types],
                    "documents": manifest,
                },
                indent=2,
                default=str,
            ).encode("utf-8"),
        )

    filename = _sanitize_filename(case.get("case_number") or f"case-{case.get('case_id')}")
    return buf.getvalue(), f"packet-{filename}.zip"
