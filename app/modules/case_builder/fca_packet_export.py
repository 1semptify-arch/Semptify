"""FCA/Qui Tam readiness packet export.

Builds an attorney-review PDF and a ZIP bundle containing the PDF plus a JSON
case summary. Output is factual and chronological only. It does not conclude that
any claim exists or is viable, and it does not file anything.
"""

import io
import json
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.upl_guardrails import UPL_DISCLAIMER, UPL_REFERRAL_CONTACTS
from app.modules.case_builder.fca_service import calculate_readiness_score, get_referral_resources
from app.modules.case_builder.packet_export import _safe_pdf_text, _sanitize_filename

logger = logging.getLogger(__name__)


def _p(text: Any) -> str:
    """Safe paragraph text for the default reportlab font."""
    return _safe_pdf_text(text)


def _fmt_date(value: Any) -> str:
    """Format a date-ish value for the PDF."""
    if not value:
        return ""
    if isinstance(value, dict):
        return _fmt_date(value.get("date") or value.get("start_date") or value.get("end_date"))
    return _p(str(value))


def build_fca_readiness_pdf(case_data: dict, user_docs: list | None = None) -> bytes:
    """Build an attorney-review PDF for federal case readiness."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=54, leftMargin=54,
                            topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    story: list = []

    title = _p("Attorney Review Packet — Federal Case Readiness")
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.1 * inch))

    case_id = _p(case_data.get("case_id", ""))
    if case_id:
        story.append(Paragraph(f"Case ID: {case_id}", styles["Normal"]))

    created = _fmt_date(case_data.get("updated_at") or case_data.get("created_at"))
    if created:
        story.append(Paragraph(f"Prepared: {created}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # UPL disclaimer
    story.append(Paragraph(_p(UPL_DISCLAIMER), styles["Heading4"]))
    story.append(Paragraph(
        "This packet is an organized record of facts and documents. It is not legal advice and does not conclude that any claim exists or is viable. A qualified attorney must evaluate jurisdiction, materiality, scienter, causation, damages, deadlines, and other requirements.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # Case narrative
    narrative = _p(case_data.get("narrative", ""))
    if narrative:
        story.append(Paragraph("Case Summary", styles["Heading2"]))
        story.append(Paragraph(narrative, styles["Normal"]))
        story.append(Spacer(1, 0.15 * inch))

    harm = _p(case_data.get("harm_description", ""))
    if harm:
        story.append(Paragraph("Harm or Impact Described", styles["Heading2"]))
        story.append(Paragraph(harm, styles["Normal"]))
        story.append(Spacer(1, 0.15 * inch))

    # Readiness checklist with notes
    checklist = list(case_data.get("readiness_checklist", []))
    score = calculate_readiness_score(checklist)
    story.append(Paragraph("Readiness Checklist", styles["Heading2"]))
    story.append(Paragraph(f"Completion: {score}%", styles["Normal"]))
    story.append(Spacer(1, 0.1 * inch))

    if checklist:
        data = [["Framework", "Item", "Status", "Notes"]]
        for item in checklist:
            framework = _p(item.get("framework", ""))
            label = _p(item.get("label", ""))
            status = "Complete" if item.get("completed") else "Pending"
            notes = _p(item.get("notes", ""))
            data.append([framework, label, status, notes])

        table = Table(data, colWidths=[1.3 * inch, 2.5 * inch, 0.8 * inch, 1.8 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No readiness checklist items have been added.", styles["Normal"]))

    story.append(Spacer(1, 0.2 * inch))

    # Timeline
    timeline = list(case_data.get("timeline", []))
    if timeline:
        story.append(Paragraph("Chronology", styles["Heading2"]))
        data = [["Date", "Event", "Source"]]
        for event in timeline:
            date = _fmt_date(event)
            desc = _p(event.get("description") or event.get("event", ""))
            source = _p(event.get("source") or event.get("document_id", ""))
            data.append([date, desc, source])
        table = Table(data, colWidths=[1.3 * inch, 3.5 * inch, 1.2 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

    # Evidence index
    exhibit_refs = list(case_data.get("exhibit_refs", []))
    user_docs = user_docs or []
    if exhibit_refs or user_docs:
        story.append(Paragraph("Evidence Index", styles["Heading2"]))
        data = [["Vault ID", "Filename", "Hash"]]
        seen = set()
        for ref in exhibit_refs:
            seen.add(str(ref))
            data.append([_p(ref), "", ""])
        for doc in user_docs:
            if doc.vault_id in seen:
                continue
            data.append([_p(doc.vault_id), _p(doc.filename), _p(doc.sha256_hash)])
        table = Table(data, colWidths=[1.8 * inch, 3.0 * inch, 1.2 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

    # Referral resources
    story.append(Paragraph("Legal Help Resources", styles["Heading2"]))
    story.append(Paragraph("Share this list with your attorney. Semptify does not endorse any provider.", styles["Normal"]))
    story.append(Spacer(1, 0.1 * inch))

    for contact in UPL_REFERRAL_CONTACTS.values():
        text = f"<b>{_p(contact['name'])}</b><br/>Call: {_p(contact['phone'])}"
        if contact.get("url"):
            text += f"<br/>Web: {_p(contact['url'])}"
        text += f"<br/>{_p(contact['description'])}<br/>{_p(contact['hours'])}"
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.05 * inch))

    for resource in get_referral_resources():
        text = f"<b>{_p(resource['name'])}</b>"
        if resource.get("phone"):
            text += f"<br/>Call: {_p(resource['phone'])}"
        if resource.get("url"):
            text += f"<br/>Web: {_p(resource['url'])}"
        text += f"<br/>{_p(resource['description'])}"
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 0.05 * inch))

    # Attorney notes page
    story.append(Paragraph("Attorney Notes", styles["Heading2"]))
    for _ in range(8):
        story.append(Paragraph("______________________________________________________________", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    return buffer.getvalue()


def build_fca_readiness_zip(case_data: dict, user_docs: list | None = None) -> tuple[bytes, str]:
    """Build a ZIP with the PDF plus a JSON summary. Returns (bytes, filename)."""
    import zipfile

    user_docs = user_docs or []
    pdf_bytes = build_fca_readiness_pdf(case_data, user_docs)

    # Light JSON summary — no raw narrative beyond what is in the PDF
    summary = {
        "case_id": case_data.get("case_id"),
        "narrative_present": bool(case_data.get("narrative") and str(case_data.get("narrative")).strip()),
        "readiness_score": calculate_readiness_score(case_data.get("readiness_checklist", [])),
        "checklist_count": len(case_data.get("readiness_checklist", [])),
        "exhibit_count": len(case_data.get("exhibit_refs", [])),
        "document_count": len(user_docs),
        "disclaimer": UPL_DISCLAIMER,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("fca_readiness_summary.json", json.dumps(summary, indent=2, default=str))
        zf.writestr("fca_readiness_packet.pdf", pdf_bytes)

    case_id = _sanitize_filename(case_data.get("case_id", "case"))
    filename = f"fca-readiness-{case_id}.zip"
    return buffer.getvalue(), filename
