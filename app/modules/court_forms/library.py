"""
Court Forms Library — JSON-driven dynamic form rendering.

Loads form definitions from ``app/modules/court_forms/data/forms_library.json``
and renders Minnesota-compliant court documents through the existing
``CourtFormGenerator`` PDF pipeline.

This file is intentionally additive. Existing ``app/modules/court_forms/service.py``
remains the canonical generator; this module only provides the dynamic catalog
and a generic renderer that ``CourtFormGenerator`` can fall back to.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Data models
# =============================================================================


class CourtFormField(BaseModel):
    """One fillable field in a court form."""

    field_id: str
    label: str = ""
    type: str = "text"  # text | long_text | date | checkbox | checkbox_group | signature
    required: bool = False
    options: list[str] = Field(default_factory=list)


class CourtForm(BaseModel):
    """Canonical Minnesota court form definition."""

    form_id: str
    title: str
    category: str
    case_type: str
    jurisdiction: str = "Minnesota District Court"
    division: str = "Statewide"
    official_url: str | None = None
    format: str = "PDF"
    is_packet: bool = False
    required_fields: list[CourtFormField] = Field(default_factory=list)
    court_rules: list[str] = Field(default_factory=list)
    signature_required: bool = True
    related_forms: list[str] = Field(default_factory=list)


# =============================================================================
# Library loading
# =============================================================================


_LIBRARY_PATH = Path(__file__).parent / "data" / "forms_library.json"
_LIBRARY: dict[str, CourtForm] | None = None


def _load_library() -> dict[str, CourtForm]:
    """Lazy-load the JSON form library."""
    global _LIBRARY
    if _LIBRARY is not None:
        return _LIBRARY

    _LIBRARY = {}
    if not _LIBRARY_PATH.exists():
        logger.warning("Court forms library not found: %s", _LIBRARY_PATH)
        return _LIBRARY

    try:
        data = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
        for raw in data.get("forms", []):
            try:
                form = CourtForm.model_validate(raw)
                _LIBRARY[form.form_id] = form
            except Exception as exc:
                logger.warning("Skipping invalid form %s: %s", raw.get("form_id"), exc)
    except Exception as exc:
        logger.error("Failed to load court forms library: %s", exc)

    return _LIBRARY


def list_forms() -> list[dict[str, Any]]:
    """Return a summary list of every form in the library."""
    library = _load_library()
    return [
        {
            "form_id": form.form_id,
            "title": form.title,
            "category": form.category,
            "case_type": form.case_type,
            "jurisdiction": form.jurisdiction,
            "signature_required": form.signature_required,
            "related_forms": form.related_forms,
            "official_url": form.official_url,
        }
        for form in library.values()
    ]


def get_form(form_id: str) -> CourtForm | None:
    """Get a single form definition by ID."""
    return _load_library().get(form_id)


def validate_field_values(form_id: str, field_values: dict[str, Any]) -> list[dict[str, str]]:
    """Return a list of required fields that are missing or empty."""
    form = get_form(form_id)
    if not form:
        return []

    missing: list[dict[str, str]] = []
    for field in form.required_fields:
        if not field.required:
            continue
        value = field_values.get(field.field_id)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append({"field_id": field.field_id, "label": field.label})
    return missing


# =============================================================================
# Rendering
# =============================================================================


CAPTION_FIELDS = {
    "caption_court_name",
    "caption_county",
    "caption_judicial_district",
    "case_number",
    "caption_plaintiff",
    "caption_defendant",
}

COURT_DOCUMENT_CSS = """
@page {
    size: letter;
    margin: 0;
    @frame content_frame {
        left: 1in;
        width: 6.5in;
        top: 1in;
        height: 8.5in;
    }
    @frame footer_frame {
        -pdf-frame-content: footer_content;
        left: 1in;
        width: 6.5in;
        top: 9.7in;
        height: 0.3in;
    }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #000;
}
.court-header {
    text-align: center;
    margin-bottom: 24pt;
    border-bottom: 2px solid #000;
    padding-bottom: 12pt;
}
.court-info {
    font-weight: bold;
    margin-bottom: 8pt;
}
.case-info {
    font-size: 10pt;
    margin-top: 8pt;
}
.document-title {
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    text-transform: uppercase;
    margin: 24pt 0;
}
.case-caption {
    margin: 24pt 0;
    padding: 12pt;
    border: 1px solid #ccc;
    overflow: hidden;
}
.case-caption .case-number {
    float: right;
    font-weight: bold;
}
.case-caption .party {
    margin: 8pt 0;
}
.section {
    margin: 18pt 0;
}
.section-title {
    font-size: 12pt;
    font-weight: bold;
    text-transform: uppercase;
    margin-bottom: 8pt;
}
.content p, .content li {
    margin-bottom: 8pt;
}
.numbered-paragraphs p {
    margin-left: 0;
    text-indent: 0;
    margin-bottom: 6pt;
}
.paragraph-number {
    display: inline-block;
    width: 24pt;
    font-weight: bold;
}
.signature {
    margin-top: 48pt;
}
.signature-line {
    border-top: 1px solid #000;
    width: 250px;
    margin-top: 3em;
}
.filing-info {
    margin-top: 24pt;
    padding-top: 12pt;
    border-top: 1px solid #ccc;
    font-size: 10pt;
}
.footer_content {
    text-align: center;
    font-size: 11pt;
}
"""


def _format_date(value: Any) -> str:
    """Normalize a date value into a readable string."""
    if isinstance(value, (datetime, date)):
        return value.strftime("%B %d, %Y")
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%B %d, %Y")
            except ValueError:
                continue
    return str(value)


def _should_number_paragraphs(field: CourtFormField, form: CourtForm) -> bool:
    """Affidavits and Rule 60.02 grounds/facts should be numbered."""
    if "affidavit" in field.field_id.lower():
        return True
    if form.case_type == "Rule 60.02 Motion to Vacate" and field.field_id in {
        "supporting_facts",
        "duress_grounds",
        "misrepresentation_grounds",
        "violation_grounds",
    }:
        return True
    return False


def _render_field_html(field: CourtFormField, value: Any, form: CourtForm) -> str:
    """Render a single field as a document section."""
    if value is None:
        value = ""

    if field.type == "date" and value:
        value = _format_date(value)

    if field.type == "long_text":
        text = str(value)
        paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [""]
        if _should_number_paragraphs(field, form):
            items = "".join(
                f'<p><span class="paragraph-number">{i}.</span> {p}</p>'
                for i, p in enumerate(paragraphs, 1)
            )
        else:
            items = "".join(f"<p>{p}</p>" for p in paragraphs)
        return f'<div class="section"><div class="section-title">{field.label}</div><div class="content">{items}</div></div>'

    if field.type == "checkbox_group" and isinstance(value, list):
        options = value or field.options
        list_items = "".join(f"<li>{opt}</li>" for opt in options)
        return f'<div class="section"><div class="section-title">{field.label}</div><ul class="content">{list_items}</ul></div>'

    if field.type == "checkbox":
        checked = "Yes" if value else "No"
        return f'<div class="section"><div class="section-title">{field.label}</div><p>{checked}</p></div>'

    if field.type == "signature":
        return (
            f'<div class="section">'
            f'<div class="section-title">{field.label}</div>'
            f'<p>{value}</p>'
            f'<div class="signature-line"></div>'
            f"</div>"
        )

    return f'<div class="section"><div class="section-title">{field.label}</div><p>{value}</p></div>'


def render_dynamic_form_html(form_id: str, field_values: dict[str, Any]) -> str:
    """Render a complete court form as an HTML string."""
    form = get_form(form_id)
    if not form:
        raise ValueError(f"Unknown court form: {form_id}")

    # Caption values
    court_name = field_values.get("caption_court_name", "DISTRICT COURT")
    county = field_values.get("caption_county", "[COUNTY]")
    judicial_district = field_values.get("caption_judicial_district", "")
    case_number = field_values.get("case_number", "[CASE NUMBER]")
    plaintiff = field_values.get("caption_plaintiff", "[PLAINTIFF]")
    defendant = field_values.get("caption_defendant", "[DEFENDANT]")

    caption_html = f"""
    <div class="case-caption">
        <div class="case-number">Case No: {case_number}</div>
        <div class="party"><strong>{plaintiff}</strong>, Plaintiff</div>
        <div class="party" style="padding-left: 2em;">vs.</div>
        <div class="party"><strong>{defendant}</strong>, Defendant</div>
    </div>
    """

    district_line = f"<div>Judicial District: {judicial_district}</div>" if judicial_district else ""

    body_html = ""
    signature_parts: list[str] = []
    for field in form.required_fields:
        if field.field_id in CAPTION_FIELDS:
            continue

        value = field_values.get(field.field_id, "")

        # Auto-fill common defaults
        if field.field_id == "signature_name" and not value:
            value = field_values.get("affiant_name", field_values.get("caption_defendant", ""))
        if field.field_id == "signature_date" and not value:
            value = utc_now().strftime("%B %d, %Y")

        if field.field_id in {
            "signature_name",
            "signature_date",
            "signature_address",
            "signature_phone",
            "signature_email",
        }:
            if field.field_id == "signature_name":
                signature_parts.append(f"<p>{value}</p>")
            elif field.field_id == "signature_date":
                signature_parts.append(f"<p>Date: {value}</p>")
            else:
                signature_parts.append(f"<p>{value}</p>")
            continue

        body_html += _render_field_html(field, value, form)

    if signature_parts:
        signature_block = (
            '<div class="signature">'
            + '<div class="signature-line"></div>'
            + "".join(signature_parts)
            + "</div>"
        )
    else:
        signature_block = ""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{form.title}</title>
    <style>{COURT_DOCUMENT_CSS}</style>
</head>
<body>
    <div class="court-header">
        <div class="court-info">STATE OF MINNESOTA</div>
        <div>{court_name}</div>
        <div>{county} COUNTY</div>
        {district_line}
    </div>
    {caption_html}
    <h1 class="document-title">{form.title}</h1>
    {body_html}
    {signature_block}
    <div id="footer_content" class="footer_content">Page <pdf:pagenumber example="00"></pdf:pagenumber></div>
</body>
</html>"""


# =============================================================================
# Packet assembly
# =============================================================================


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """Merge a list of PDF byte streams into a single PDF."""
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except Exception as exc:
        logger.warning("PyPDF2 not available for packet merge: %s", exc)
        return b""

    writer = PdfWriter()
    for pdf in pdf_bytes_list:
        try:
            reader = PdfReader(BytesIO(pdf))
            for page in reader.pages:
                writer.add_page(page)
        except Exception as exc:
            logger.warning("Skipping PDF in packet merge: %s", exc)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
