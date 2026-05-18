"""
Court Packet Export API
=======================
Generates court-ready document packets from Briefcase contents.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import io
import zipfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/court-packet", tags=["Court Packet"])

# Import briefcase data (shared storage)
try:
    from app.routers.briefcase import briefcase_data
except ImportError:
    briefcase_data = {
        "folders": {},
        "documents": {},
        "extractions": {},
        "highlights": {}
    }


# Import security for authentication
try:
    from app.core.security import require_user, StorageUser
    from fastapi import Depends
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False


def _get_processed_documents(user_id: str) -> List[Dict[str, Any]]:
    """Get processed documents from the unified upload pipeline."""
    try:
        from app.services.document_distributor import get_document_distributor
        distributor = get_document_distributor()
        return distributor.get_court_packet_documents(user_id)
    except Exception:
        return []


@router.get("/")
async def get_packet_status(request: Request) -> Dict[str, Any]:
    """
    Get current court packet status and contents summary.
    
    Includes documents from:
    - Briefcase manual uploads
    - Unified upload pipeline (automatically categorized)
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    # Count items from briefcase
    doc_count = len(briefcase_data.get("documents", {}))
    extraction_count = len(briefcase_data.get("extractions", {}))
    highlight_count = len(briefcase_data.get("highlights", {}))
    
    # Get processed documents from unified upload
    processed_docs = _get_processed_documents(user_id)
    
    # Categorize documents
    categories = {
        "evidence_photos": 0,
        "legal_documents": 0,
        "communications": 0,
        "financial": 0,
        "other": 0
    }
    
    starred_docs = []
    all_timeline_events = []
    all_action_items = []
    
    # Process briefcase documents
    for doc_id, doc in briefcase_data.get("documents", {}).items():
        cat = doc.get("category", "other")
        if cat in categories:
            categories[cat] += 1
        else:
            categories["other"] += 1
        
        if doc.get("starred"):
            starred_docs.append({
                "id": doc_id,
                "name": doc.get("name"),
                "type": doc.get("type")
            })
    
    # Process unified upload documents
    for doc in processed_docs:
        cat = doc.get("category", "other")
        if cat in categories:
            categories[cat] += 1
        else:
            categories["other"] += 1
        
        if doc.get("starred"):
            starred_docs.append({
                "id": doc.get("id"),
                "name": doc.get("name"),
                "type": doc.get("type"),
                "doc_type": doc.get("doc_type"),
                "registry_id": doc.get("registry_id"),
            })
        
        # Collect timeline events and action items
        all_timeline_events.extend(doc.get("timeline_events", []))
    
    total_doc_count = doc_count + len(processed_docs)
    
    return {
        "success": True,
        "packet_summary": {
            "total_documents": total_doc_count,
            "briefcase_documents": doc_count,
            "processed_documents": len(processed_docs),
            "total_extractions": extraction_count,
            "total_highlights": highlight_count,
            "categories": categories,
            "starred_documents": starred_docs,
            "timeline_events_count": len(all_timeline_events),
            "ready_for_export": total_doc_count > 0 or extraction_count > 0
        }
    }


@router.get("/documents")
async def get_packet_documents(request: Request) -> Dict[str, Any]:
    """
    Get all documents available for court packet.
    
    Returns documents from both:
    - Briefcase (manual uploads)
    - Unified upload pipeline (auto-processed)
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    # Get briefcase documents
    briefcase_docs = list(briefcase_data.get("documents", {}).values())
    
    # Get processed documents
    processed_docs = _get_processed_documents(user_id)
    
    return {
        "success": True,
        "documents": {
            "briefcase": briefcase_docs,
            "processed": processed_docs,
        },
        "total_count": len(briefcase_docs) + len(processed_docs),
    }


@router.get("/evidence")
async def get_packet_evidence(request: Request) -> Dict[str, Any]:
    """
    Get all evidence documents for court packet.
    
    Filters to documents categorized as evidence from unified upload.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    processed_docs = _get_processed_documents(user_id)
    evidence_docs = [d for d in processed_docs if d.get("is_evidence") or d.get("category") == "evidence_photos"]
    
    return {
        "success": True,
        "evidence": evidence_docs,
        "count": len(evidence_docs),
    }


@router.get("/legal-documents")
async def get_packet_legal_docs(request: Request) -> Dict[str, Any]:
    """
    Get all legal documents for court packet (notices, filings, etc.).
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    processed_docs = _get_processed_documents(user_id)
    legal_docs = [d for d in processed_docs if d.get("category") == "legal_documents"]
    
    return {
        "success": True,
        "legal_documents": legal_docs,
        "count": len(legal_docs),
    }


@router.get("/timeline")
async def get_packet_timeline(request: Request) -> Dict[str, Any]:
    """
    Get aggregated timeline events from all processed documents.
    
    Useful for creating a chronological summary for court.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    processed_docs = _get_processed_documents(user_id)
    
    all_events = []
    for doc in processed_docs:
        events = doc.get("timeline_events", [])
        for event in events:
            event["source_document"] = doc.get("name")
            event["source_doc_id"] = doc.get("id")
            all_events.append(event)
    
    # Sort by date if available
    all_events.sort(key=lambda x: x.get("date", ""), reverse=False)
    
    return {
        "success": True,
        "timeline_events": all_events,
        "count": len(all_events),
    }


@router.get("/checklist")
async def get_packet_checklist(request: Request) -> Dict[str, Any]:
    """
    Get checklist of recommended items for court packet.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    checklist = [
        {
            "category": "Essential Documents",
            "items": [
                {"name": "Eviction Notice/Complaint", "required": True, "help": "The document that started this case", "doc_types": ["eviction_notice", "notice_to_quit", "court_complaint"]},
                {"name": "Your Answer/Response", "required": True, "help": "Your written response to the complaint", "doc_types": ["court_filing", "motion"]},
                {"name": "Lease Agreement", "required": True, "help": "Your rental contract", "doc_types": ["lease", "lease_amendment"]},
                {"name": "Proof of Service", "required": False, "help": "If you served any documents", "doc_types": ["court_filing"]}
            ]
        },
        {
            "category": "Evidence",
            "items": [
                {"name": "Photos of Property Conditions", "required": False, "help": "Mold, damage, repairs needed", "doc_types": ["photo_evidence", "video_evidence"]},
                {"name": "Communication Records", "required": False, "help": "Texts, emails, letters with landlord", "doc_types": ["email_communication", "text_message", "letter"]},
                {"name": "Payment Records", "required": False, "help": "Receipts, bank statements, money orders", "doc_types": ["receipt", "payment_record", "bank_statement"]},
                {"name": "Witness Statements", "required": False, "help": "Written statements from witnesses", "doc_types": ["affidavit"]}
            ]
        },
        {
            "category": "Supporting Documents",
            "items": [
                {"name": "Timeline of Events", "required": False, "help": "Chronological summary of what happened", "doc_types": []},
                {"name": "Relevant Laws/Statutes", "required": False, "help": "Laws that support your case", "doc_types": []},
                {"name": "Inspection Reports", "required": False, "help": "City/county inspection reports", "doc_types": ["inspection_report"]},
                {"name": "Medical Records", "required": False, "help": "If health was affected by conditions", "doc_types": []}
            ]
        }
    ]
    
    # Get processed documents
    processed_docs = _get_processed_documents(user_id)
    processed_doc_types = set(d.get("doc_type") for d in processed_docs if d.get("doc_type"))
    
    # Check what user has from briefcase
    docs = briefcase_data.get("documents", {})
    has_items = set()
    
    for doc in docs.values():
        name_lower = doc.get("name", "").lower()
        if "eviction" in name_lower or "notice" in name_lower or "complaint" in name_lower:
            has_items.add("Eviction Notice/Complaint")
        if "answer" in name_lower or "response" in name_lower:
            has_items.add("Your Answer/Response")
        if "lease" in name_lower:
            has_items.add("Lease Agreement")
        if "photo" in name_lower or "image" in name_lower:
            has_items.add("Photos of Property Conditions")
        if "text" in name_lower or "email" in name_lower or "message" in name_lower:
            has_items.add("Communication Records")
        if "receipt" in name_lower or "payment" in name_lower:
            has_items.add("Payment Records")
    
    # Add status to checklist based on processed doc types
    for category in checklist:
        for item in category["items"]:
            # Check briefcase
            has_from_briefcase = item["name"] in has_items
            
            # Check processed documents by doc_type
            has_from_processed = bool(set(item.get("doc_types", [])) & processed_doc_types)
            
            item["has"] = has_from_briefcase or has_from_processed
            item["source"] = "processed" if has_from_processed else ("briefcase" if has_from_briefcase else None)
    
    # Calculate completion
    total_required = sum(1 for cat in checklist for item in cat["items"] if item["required"])
    has_required = sum(1 for cat in checklist for item in cat["items"] if item["required"] and item["has"])
    
    return {
        "success": True,
        "checklist": checklist,
        "completion": {
            "required_items": total_required,
            "has_required": has_required,
            "percentage": round((has_required / total_required * 100) if total_required > 0 else 0)
        }
    }


@router.post("/generate")
async def generate_court_packet(
    request: Request,
    include_highlights: bool = True,
    include_extractions: bool = True,
    include_index: bool = True,
    format: str = "zip"  # zip or pdf
) -> Dict[str, Any]:
    """
    Generate a court-ready document packet.
    
    Returns a downloadable ZIP file containing:
    - All starred/selected documents
    - Evidence index
    - Highlighted annotations summary
    - Extracted pages
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    try:
        # Get all items
        docs = briefcase_data.get("documents", {})
        extractions = briefcase_data.get("extractions", {}) if include_extractions else {}
        highlights = briefcase_data.get("highlights", {}) if include_highlights else {}
        
        if not docs and not extractions:
            return {
                "success": False,
                "error": "No documents to export. Add documents to your Briefcase first."
            }
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            # 1. Create Evidence Index
            if include_index:
                index_content = generate_evidence_index(docs, extractions, highlights)
                zf.writestr("00_EVIDENCE_INDEX.txt", index_content)
            
            # 2. Add documents
            doc_folder = "01_Documents/"
            for doc_id, doc in docs.items():
                # In real app, would include actual file content
                # For now, create placeholder with metadata
                doc_info = f"""Document: {doc.get('name', 'Unknown')}
Type: {doc.get('type', 'Unknown')}
Category: {doc.get('category', 'General')}
Date Added: {doc.get('created_at', 'Unknown')}
Starred: {'Yes' if doc.get('starred') else 'No'}

Notes:
{doc.get('notes', 'No notes')}
"""
                safe_name = doc.get('name', doc_id).replace('/', '_').replace('\\', '_')
                zf.writestr(f"{doc_folder}{safe_name}_info.txt", doc_info)
            
            # 3. Add extractions
            if extractions:
                extract_folder = "02_Extracted_Pages/"
                for ext_id, ext in extractions.items():
                    ext_info = f"""Extraction: {ext.get('filename', 'Unknown')}
Source PDF: {ext.get('source_pdf', 'Unknown')}
Pages: {ext.get('pages', 'Unknown')}
Extracted: {ext.get('created_at', 'Unknown')}
"""
                    zf.writestr(f"{extract_folder}{ext_id}_info.txt", ext_info)
            
            # 4. Add highlights summary
            if highlights:
                highlight_summary = generate_highlights_summary(highlights)
                zf.writestr("03_HIGHLIGHTS_SUMMARY.txt", highlight_summary)
            
            # 5. Add cover sheet
            cover = generate_cover_sheet(docs, extractions, highlights)
            zf.writestr("COURT_PACKET_COVER.txt", cover)
        
        # Save to temp location and return download info
        zip_buffer.seek(0)
        
        # In real implementation, would save to file system or cloud
        # For now, store in memory with ID
        packet_id = f"packet_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "success": True,
            "packet_id": packet_id,
            "contents": {
                "documents": len(docs),
                "extractions": len(extractions),
                "highlights": len(highlights),
                "includes_index": include_index
            },
            "download_url": f"/api/court-packet/download/{packet_id}",
            "message": "Court packet generated successfully!"
        }
        
    except Exception as e:
        logger.error(f"Error generating court packet: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def generate_evidence_index(docs: Dict, extractions: Dict, highlights: Dict) -> str:
    """Generate a text evidence index."""
    lines = [
        "=" * 60,
        "EVIDENCE INDEX",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "DOCUMENTS",
        "-" * 40,
    ]
    
    for i, (doc_id, doc) in enumerate(docs.items(), 1):
        lines.append(f"{i}. {doc.get('name', 'Unknown')}")
        lines.append(f"   Type: {doc.get('type', 'Unknown')}")
        lines.append(f"   Category: {doc.get('category', 'General')}")
        if doc.get('starred'):
            lines.append("   ★ STARRED - Key Evidence")
        lines.append("")
    
    if extractions:
        lines.extend([
            "",
            "EXTRACTED PAGES",
            "-" * 40,
        ])
        for i, (ext_id, ext) in enumerate(extractions.items(), 1):
            lines.append(f"{i}. {ext.get('filename', 'Unknown')}")
            lines.append(f"   From: {ext.get('source_pdf', 'Unknown')}")
            lines.append(f"   Pages: {ext.get('pages', 'Unknown')}")
            lines.append("")
    
    if highlights:
        lines.extend([
            "",
            f"ANNOTATIONS: {len(highlights)} highlighted items",
            "(See HIGHLIGHTS_SUMMARY.txt for details)",
            "",
        ])
    
    lines.extend([
        "=" * 60,
        "END OF INDEX",
        "=" * 60,
    ])
    
    return "\n".join(lines)


def generate_highlights_summary(highlights: Dict) -> str:
    """Generate highlights summary organized by color/type."""
    lines = [
        "=" * 60,
        "HIGHLIGHTS & ANNOTATIONS SUMMARY",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
    ]
    
    # Group by color
    by_color = {}
    color_labels = {
        "yellow": "🟡 KEY TERMS",
        "green": "🟢 DATES",
        "blue": "🔵 NAMES",
        "pink": "🟣 MONEY/AMOUNTS",
        "orange": "🟠 DEADLINES",
        "red": "🔴 VIOLATIONS"
    }
    
    for h_id, h in highlights.items():
        color = h.get("color", "yellow")
        if color not in by_color:
            by_color[color] = []
        by_color[color].append(h)
    
    for color, items in by_color.items():
        label = color_labels.get(color, color.upper())
        lines.append(f"\n{label}")
        lines.append("-" * 40)
        for item in items:
            lines.append(f"• {item.get('text', 'No text')}")
            if item.get('note'):
                lines.append(f"  Note: {item.get('note')}")
            lines.append(f"  Source: {item.get('pdf_name', 'Unknown')} (Page {item.get('page', '?')})")
            lines.append("")
    
    return "\n".join(lines)


def generate_cover_sheet(docs: Dict, extractions: Dict, highlights: Dict) -> str:
    """Generate cover sheet for court packet."""
    return f"""
╔══════════════════════════════════════════════════════════════╗
║                    COURT DOCUMENT PACKET                      ║
╚══════════════════════════════════════════════════════════════╝

Prepared by: Semptify Legal Defense Assistant
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTENTS SUMMARY
----------------
Documents:        {len(docs)}
Extracted Pages:  {len(extractions)}
Annotations:      {len(highlights)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO USE THIS PACKET
----------------------
1. Review the EVIDENCE_INDEX.txt for a complete list of contents
2. Documents are organized in numbered folders
3. HIGHLIGHTS_SUMMARY.txt contains all annotations by category
4. Present starred (★) items as key evidence

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT NOTES
---------------
• This packet was generated to assist with legal proceedings
• Verify all documents before presenting to the court
• Original documents should be available if requested
• Consult with legal counsel regarding proper presentation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated by Semptify - Your AI Legal Defense Assistant
https://semptify.com
"""


@router.get("/preview")
async def preview_packet(request: Request) -> Dict[str, Any]:
    """
    Preview what would be included in the court packet.
    """
    docs = briefcase_data.get("documents", {})
    extractions = briefcase_data.get("extractions", {})
    highlights = briefcase_data.get("highlights", {})
    
    preview = {
        "documents": [
            {
                "id": doc_id,
                "name": doc.get("name"),
                "type": doc.get("type"),
                "starred": doc.get("starred", False),
                "category": doc.get("category", "general")
            }
            for doc_id, doc in docs.items()
        ],
        "extractions": [
            {
                "id": ext_id,
                "filename": ext.get("filename"),
                "source": ext.get("source_pdf"),
                "pages": ext.get("pages")
            }
            for ext_id, ext in extractions.items()
        ],
        "highlights_by_color": {}
    }
    
    # Group highlights by color
    for h_id, h in highlights.items():
        color = h.get("color", "yellow")
        if color not in preview["highlights_by_color"]:
            preview["highlights_by_color"][color] = []
        preview["highlights_by_color"][color].append({
            "id": h_id,
            "text": h.get("text", "")[:100],  # Truncate
            "pdf": h.get("pdf_name"),
            "page": h.get("page")
        })
    
    return {
        "success": True,
        "preview": preview,
        "total_items": len(docs) + len(extractions) + len(highlights)
    }
