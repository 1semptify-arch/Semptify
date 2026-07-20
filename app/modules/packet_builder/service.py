"""Packet Builder Service

Unifies the case-builder attorney intake packet export and the briefcase folder
ZIP export into one curated-export feature. Supports overlay and clean modes,
zip and pdf output formats, and persists packet definitions as overlay queries.
"""

import io
import json
import logging
import re
import zipfile
from html import escape
from typing import Any

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.models.models import Incident
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.unified_overlay_manager import get_unified_overlay_manager
from app.services.vault_upload_service import get_vault_service

logger = logging.getLogger(__name__)

_PACKET_STORE: dict[str, dict[str, Any]] = {}


def _safe_text(value: Any) -> str:
    """Convert a value to an XML-escaped string safe for reportlab Paragraph."""
    if value is None:
        return ""
    return escape(str(value))


def _sanitize_filename(value: Any) -> str:
    """Sanitize a value for use in a downloaded filename."""
    if value is None:
        return ""
    text = re.sub(r"[^\w\-. ]", "_", str(value)).strip()
    text = re.sub(r"\s+", "_", text)
    return text or "packet"


def _overlay_to_dict(overlay: Any) -> dict[str, Any]:
    """Serialize a UnifiedOverlay to a plain dict."""
    if hasattr(overlay, "model_dump"):
        return overlay.model_dump(mode="json")
    return overlay.dict()


async def _get_overlay_manager(user_id: str) -> Any:
    """Build an overlay manager for the user, or None if storage is unavailable."""
    try:
        from app.core.oauth_token_manager import get_valid_token_for_user
        from app.core.user_id import get_provider_from_user_id
        from app.services.storage import get_provider
    except ImportError:
        return None

    token = get_valid_token_for_user(user_id)
    provider_code = get_provider_from_user_id(user_id)
    if not token or not provider_code or provider_code.lower() == "local":
        return None

    try:
        storage = get_provider(provider_code, access_token=token)
        return await get_unified_overlay_manager(storage, user_id)
    except Exception as exc:
        logger.warning("Packet builder overlay manager unavailable for %s: %s", user_id[:6], exc)
        return None


async def _load_case(case_id: str, user_id: str) -> dict[str, Any] | None:
    """Load a case from the DB, enforcing user ownership."""
    try:
        case_id_int = int(case_id)
    except ValueError:
        return None

    try:
        from sqlalchemy import select

        from app.core.database import get_db_session

        async with get_db_session() as session:
            row = await session.execute(
                select(Incident).where(
                    Incident.incident_id == case_id_int,
                    Incident.user_id == user_id,
                )
            )
            incident = row.scalar_one_or_none()
            if not incident:
                return None
            data = dict(incident.incident_metadata or {})
            data["case_id"] = str(incident.incident_id)
            data["user_id"] = incident.user_id
            return data
    except Exception as exc:
        logger.error("Failed to load case %s: %s", case_id, exc)
        return None


async def _find_vault_document(user_id: str, reference: str, vault_service: Any) -> Any:
    """Resolve a vault document from a vault_id, storage_path, or filename."""
    doc = await vault_service.get_document(reference)
    if doc and getattr(doc, "user_id", None) == user_id:
        return doc

    try:
        user_docs = await vault_service.get_user_documents(user_id)
    except Exception as exc:
        logger.warning("Failed to list user documents for %s: %s", user_id[:6], exc)
        return None

    for candidate in user_docs:
        if candidate.user_id != user_id:
            continue
        if (
            candidate.storage_path == reference
            or candidate.filename == reference
            or candidate.safe_filename == reference
        ):
            return candidate
    return None


async def _resolve_source_documents(
    user_id: str,
    vault_ids: list[str],
    case_id: str | None,
    folder_id: str | None,
) -> list[Any]:
    """Resolve the list of vault documents to include in the packet."""
    vault_service = get_vault_service()
    references: list[str] = []

    if case_id:
        case = await _load_case(case_id, user_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        for evidence in case.get("evidence", []):
            if isinstance(evidence, dict):
                file_path = evidence.get("file_path")
                if file_path:
                    references.append(str(file_path))
    elif folder_id:
        from app.modules.briefcase.router import briefcase_data

        if folder_id not in briefcase_data["folders"]:
            raise ValueError(f"Folder {folder_id} not found")
        docs = [doc for doc in briefcase_data["documents"].values() if doc.get("folder_id") == folder_id]
        for doc in docs:
            vault_id = doc.get("vault_id")
            if vault_id:
                references.append(str(vault_id))
    else:
        references = list(vault_ids)

    seen: set[str] = set()
    documents: list[Any] = []
    for reference in references:
        if reference in seen:
            continue
        seen.add(reference)
        doc = await _find_vault_document(user_id, reference, vault_service)
        if doc:
            documents.append(doc)
        else:
            logger.warning("Packet builder could not resolve reference: %s", reference)

    return documents


async def _fetch_document_overlays(
    overlay_manager: Any,
    doc: Any,
    include_highlights: bool,
    include_notes: bool,
    include_footnotes: bool,
) -> dict[str, list[Any]]:
    """Fetch and filter overlays for a single document."""
    if overlay_manager is None:
        return {"annotations": [], "metadata": []}

    try:
        response = await overlay_manager.get_overlays(document_id=doc.safe_filename)
    except Exception as exc:
        logger.warning("Failed to fetch overlays for %s: %s", doc.safe_filename, exc)
        return {"annotations": [], "metadata": []}

    annotations: list[Any] = []
    metadata: list[Any] = []
    for overlay in response.overlays:
        overlay_type = overlay.overlay_type
        if overlay_type in (
            OverlayType.VAULT_UPLOAD_MANIFEST,
            OverlayType.DOCUMENT_EXTRACTION,
        ):
            metadata.append(overlay)
            continue
        if (
            overlay_type == OverlayType.HIGHLIGHT
            and include_highlights
            or overlay_type == OverlayType.NOTE
            and include_notes
            or overlay_type == OverlayType.FOOTNOTE
            and include_footnotes
            or overlay_type == OverlayType.TRACKED_EDIT
            and include_notes
        ):
            annotations.append(overlay)

    return {"annotations": annotations, "metadata": metadata}


def _build_packet_spec(
    packet_id: str,
    name: str | None,
    user_id: str,
    mode: str,
    include_highlights: bool,
    include_notes: bool,
    include_footnotes: bool,
    source: dict[str, Any],
    documents: list[Any],
    document_overlays: list[dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Assemble the canonical packet definition dict."""
    doc_specs = [
        {
            "label": f"doc_{index + 1}",
            "vault_id": doc.vault_id,
            "filename": doc.filename,
            "safe_filename": doc.safe_filename,
            "mime_type": doc.mime_type,
            "storage_path": doc.storage_path,
        }
        for index, doc in enumerate(documents)
    ]

    return {
        "packet_id": packet_id,
        "name": name or f"packet_{packet_id}",
        "user_id": user_id,
        "mode": mode,
        "include_highlights": include_highlights,
        "include_notes": include_notes,
        "include_footnotes": include_footnotes,
        "source": source,
        "documents": doc_specs,
        "document_overlays": document_overlays,
        "created_at": utc_now().isoformat(),
        "item_count": len(documents),
    }


async def _store_packet_spec(spec: dict[str, Any], overlay_manager: Any | None = None) -> None:
    """Persist the packet spec as a query overlay, or fall back to in-memory."""
    packet_id = spec["packet_id"]
    if overlay_manager is None:
        overlay_manager = await _get_overlay_manager(spec["user_id"])

    if overlay_manager is None:
        _PACKET_STORE[packet_id] = spec
        return

    overlay_type = (
        OverlayType.COURT_PACKET_QUERY if spec["source"].get("case_id") else OverlayType.EVIDENCE_BUNDLE_QUERY
    )

    try:
        request = CreateOverlayRequest(
            overlay_type=overlay_type,
            document_id=packet_id,
            vault_path=f"/packet/{packet_id}",
            payload=spec,
            metadata={"mode": spec["mode"], "user_id": spec["user_id"]},
        )
        await overlay_manager.create_overlay(request)
    except Exception as exc:
        logger.warning("Failed to persist packet %s as overlay: %s", packet_id, exc)
        _PACKET_STORE[packet_id] = spec


async def _load_packet_spec(packet_id: str, user_id: str) -> dict[str, Any] | None:
    """Load a packet spec from overlay storage or in-memory fallback."""
    overlay_manager = await _get_overlay_manager(user_id)
    if overlay_manager is not None:
        try:
            response = await overlay_manager.get_overlays(document_id=packet_id)
            for overlay in response.overlays:
                if overlay.overlay_type in (
                    OverlayType.COURT_PACKET_QUERY,
                    OverlayType.EVIDENCE_BUNDLE_QUERY,
                ):
                    payload = overlay.payload
                    if isinstance(payload, dict) and payload.get("packet_id") == packet_id:
                        return payload
        except Exception as exc:
            logger.warning("Failed to load packet %s from overlay: %s", packet_id, exc)

    return _PACKET_STORE.get(packet_id)


async def _get_document_bytes(user_id: str, doc: Any) -> bytes | None:
    """Download the original bytes for a vault document."""
    vault_service = get_vault_service()
    token: str | None = None
    try:
        from app.core.oauth_token_manager import get_valid_token_for_user

        token = get_valid_token_for_user(user_id)
    except Exception as exc:
        logger.debug("No token for document download: %s", exc)

    try:
        content = await vault_service.get_document_content(doc.vault_id, access_token=token)
        if content:
            return content
    except Exception as exc:
        logger.warning("Failed to download vault document %s: %s", doc.vault_id, exc)

    return None


def _annotation_text(annotation: dict[str, Any]) -> str:
    """Render an annotation dict as a short human-readable string."""
    payload = annotation.get("payload", {}) or {}
    ann_type = annotation.get("overlay_type", "annotation")
    if ann_type == "highlight":
        return payload.get("note") or payload.get("range", {}).get("text", "")
    if ann_type == "note":
        return payload.get("content", "")
    if ann_type == "footnote":
        return f"{payload.get('number', '')}: {payload.get('content', '')}"
    if ann_type == "tracked_edit":
        return f"{payload.get('original_text', '')} -> {payload.get('new_text', '')}"
    return ""


def _render_summary_pdf_fallback(spec: dict[str, Any]) -> bytes:
    """Minimal fallback PDF when reportlab is unavailable."""
    text = json.dumps(spec, indent=2, ensure_ascii=True, default=str)
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = [f"({line}) Tj 0 -12 Td" for line in escaped.split("\n")]
    stream = "\n".join(lines)
    stream_bytes = (f"BT /F1 8 Tf 72 720 Td\n{stream}\nET\n").encode("latin-1", errors="replace")
    header = (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n"
    ).encode("latin-1")
    footer = (
        "\nendstream\nendobj\n"
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n"
        "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    ).encode("latin-1")
    return header + stream_bytes + footer


def _render_summary_pdf(spec: dict[str, Any]) -> bytes:
    """Render a packet spec as a reportlab summary PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        return _render_summary_pdf_fallback(spec)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=_safe_text(spec.get("name", "Packet Summary")),
        author="Semptify",
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph("Packet Summary", styles["Title"]))
    story.append(Paragraph(f"Generated: {_safe_text(spec.get('created_at', ''))}", styles["Normal"]))
    story.append(Paragraph(f"Mode: {_safe_text(spec.get('mode', ''))}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Document Index", styles["Heading2"]))
    doc_rows = [["Label", "Filename", "Type"]]
    for doc_spec in spec.get("documents", []):
        doc_rows.append(
            [
                _safe_text(doc_spec.get("label")),
                _safe_text(doc_spec.get("filename")),
                _safe_text(doc_spec.get("mime_type")),
            ]
        )
    if len(doc_rows) > 1:
        table = Table(doc_rows, colWidths=[1 * inch, 4 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No documents.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    for index, doc_spec in enumerate(spec.get("documents", [])):
        label = doc_spec.get("label", f"doc_{index + 1}")
        overlays = spec.get("document_overlays", [])[index] if index < len(spec.get("document_overlays", [])) else {}
        annotations = overlays.get("annotations", []) or []
        metadata = overlays.get("metadata", []) or []

        story.append(
            Paragraph(
                f"Document {label}: {_safe_text(doc_spec.get('filename'))}",
                styles["Heading3"],
            )
        )
        for meta in metadata:
            payload = meta.get("payload", {}) or {}
            meta_type = meta.get("overlay_type", "")
            if meta_type == "vault_upload_manifest":
                story.append(
                    Paragraph(
                        f"Original filename: {_safe_text(payload.get('original_filename'))}",
                        styles["Normal"],
                    )
                )
            elif meta_type == "document_extraction":
                terms = payload.get("key_terms", []) or []
                story.append(
                    Paragraph(
                        f"Extracted terms: {_safe_text(', '.join(str(t) for t in terms))}",
                        styles["Normal"],
                    )
                )

        if annotations:
            ann_rows = [["Type", "Content"]]
            for annotation in annotations:
                ann_rows.append(
                    [
                        _safe_text(annotation.get("overlay_type", "")),
                        _safe_text(_annotation_text(annotation)),
                    ]
                )
            table = Table(ann_rows, colWidths=[1.2 * inch, 5.3 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)
        else:
            story.append(Paragraph("No annotations.", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
    return buf.getvalue()


def _build_index_text(spec: dict[str, Any]) -> str:
    """Build a plain-text index for the packet."""
    lines = [
        "Packet Index",
        "=" * 60,
        f"Name: {spec.get('name', '')}",
        f"Mode: {spec.get('mode', '')}",
        f"Generated: {spec.get('created_at', '')}",
        f"Documents: {len(spec.get('documents', []))}",
        "",
    ]
    for index, doc_spec in enumerate(spec.get("documents", [])):
        label = doc_spec.get("label", f"doc_{index + 1}")
        overlays = spec.get("document_overlays", [])[index] if index < len(spec.get("document_overlays", [])) else {}
        annotations = overlays.get("annotations", []) or []
        lines.append(f"{label}: {doc_spec.get('filename', '')}")
        lines.append(f"  Safe filename: {doc_spec.get('safe_filename', '')}")
        lines.append(f"  MIME type: {doc_spec.get('mime_type', '')}")
        if annotations:
            lines.append("  Annotations:")
            for annotation in annotations:
                ann_type = annotation.get("overlay_type", "annotation")
                text = _annotation_text(annotation)
                lines.append(f"    [{ann_type}] {text}")
        else:
            lines.append("  No annotations.")
        lines.append("")
    return "\n".join(lines)


async def _build_zip(spec: dict[str, Any], mode: str) -> bytes:
    """Build the curated ZIP archive for the requested mode."""
    user_id = spec["user_id"]
    vault_service = get_vault_service()
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "packet.json",
            (json.dumps(spec, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8"),
        )

        for index, doc_spec in enumerate(spec.get("documents", [])):
            doc = await vault_service.get_document(doc_spec["vault_id"])
            if not doc:
                continue
            content = await _get_document_bytes(user_id, doc)
            if content is None:
                continue
            label = doc_spec.get("label", f"doc_{index + 1}")
            zip_file.writestr(
                f"documents/{label}_{doc.safe_filename}",
                content,
            )

            if mode == "overlay":
                overlays = (
                    spec.get("document_overlays", [])[index] if index < len(spec.get("document_overlays", [])) else {}
                )
                annotations = overlays.get("annotations", []) or []
                sidecar = json.dumps(annotations, indent=2, ensure_ascii=False, default=str)
                zip_file.writestr(f"annotations/{label}.json", sidecar.encode("utf-8"))

        if mode == "clean":
            zip_file.writestr("summary.pdf", _render_summary_pdf(spec))
            zip_file.writestr("index.txt", _build_index_text(spec).encode("utf-8"))

    return buf.getvalue()


async def build_packet(
    user_id: str,
    name: str | None,
    vault_ids: list[str],
    case_id: str | None,
    folder_id: str | None,
    mode: str,
    include_highlights: bool,
    include_notes: bool,
    include_footnotes: bool,
) -> dict[str, Any]:
    """Build a packet and persist its definition."""
    overlay_manager = await _get_overlay_manager(user_id)
    documents = await _resolve_source_documents(user_id, vault_ids, case_id, folder_id)
    if not documents:
        raise ValueError("No documents resolved for packet")

    document_overlays: list[dict[str, list[dict[str, Any]]]] = []
    for doc in documents:
        overlays = await _fetch_document_overlays(
            overlay_manager,
            doc,
            include_highlights,
            include_notes,
            include_footnotes,
        )
        document_overlays.append(
            {
                "annotations": [_overlay_to_dict(o) for o in overlays["annotations"]],
                "metadata": [_overlay_to_dict(o) for o in overlays["metadata"]],
            }
        )

    source = {
        "case_id": case_id,
        "folder_id": folder_id,
        "vault_ids": list(vault_ids),
    }
    packet_id = make_id("pkt")
    spec = _build_packet_spec(
        packet_id=packet_id,
        name=name,
        user_id=user_id,
        mode=mode,
        include_highlights=include_highlights,
        include_notes=include_notes,
        include_footnotes=include_footnotes,
        source=source,
        documents=documents,
        document_overlays=document_overlays,
    )

    await _store_packet_spec(spec, overlay_manager)

    return {"packet_id": packet_id, "item_count": len(documents)}


async def get_packet_metadata(packet_id: str, user_id: str) -> dict[str, Any] | None:
    """Return sanitized metadata for a packet."""
    spec = await _load_packet_spec(packet_id, user_id)
    if not spec:
        return None

    return {
        "packet_id": spec["packet_id"],
        "name": spec.get("name"),
        "mode": spec.get("mode"),
        "item_count": spec.get("item_count", 0),
        "created_at": spec.get("created_at"),
        "source": spec.get("source"),
        "documents": [
            {
                "label": d.get("label"),
                "filename": d.get("filename"),
                "mime_type": d.get("mime_type"),
            }
            for d in spec.get("documents", [])
        ],
    }


async def download_packet(
    packet_id: str,
    user_id: str,
    output_format: str,
    mode: str | None,
) -> tuple[bytes, str, str] | None:
    """Generate a packet download artifact (zip or pdf)."""
    spec = await _load_packet_spec(packet_id, user_id)
    if not spec:
        return None

    if output_format not in ("zip", "pdf"):
        raise ValueError("format must be zip or pdf")

    effective_mode = mode or spec.get("mode", "overlay")
    if effective_mode not in ("overlay", "clean"):
        raise ValueError("mode must be overlay or clean")

    name = _sanitize_filename(spec.get("name"))
    if output_format == "pdf":
        pdf_bytes = _render_summary_pdf(spec)
        filename = f"{name}-summary.pdf"
        return pdf_bytes, filename, "application/pdf"

    zip_bytes = await _build_zip(spec, effective_mode)
    filename = f"{name}-{effective_mode}.zip"
    return zip_bytes, filename, "application/zip"
