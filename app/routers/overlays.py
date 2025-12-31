"""
📝 Document Overlays Router
============================

Non-destructive overlay system for document annotations, highlights,
notes, footnotes, and edits. Original vault documents stay untouched.

Overlay Structure:
- .semptify/vault/overlays/{document_id}.json

Each overlay contains:
- highlights: Text selections with colors
- notes: Text notes attached to positions
- footnotes: Numbered annotations with references
- edits: Suggested text changes (tracked changes)
- processing: AI processing results
- metadata: Timestamps, version info
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
import logging

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.core.security import require_user, StorageUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overlays", tags=["Document Overlays"])


# =============================================================================
# Pydantic Models
# =============================================================================

class TextRange(BaseModel):
    """Position reference in document."""
    start_offset: int
    end_offset: int
    text: Optional[str] = None  # Selected text (for verification)
    page: Optional[int] = None  # For PDFs
    paragraph: Optional[int] = None  # For text documents
    line: Optional[int] = None


class Highlight(BaseModel):
    """Text highlight."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    range: TextRange
    color: str = "yellow"  # yellow, green, blue, pink, red
    note: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: Optional[str] = None


class Note(BaseModel):
    """Standalone note attached to position."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    range: Optional[TextRange] = None  # Position in document
    content: str
    note_type: str = "user"  # user, ai, system, legal
    priority: str = "normal"  # low, normal, high, critical
    tags: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: Optional[str] = None
    resolved: bool = False


class Footnote(BaseModel):
    """Numbered footnote annotation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    range: TextRange  # Where footnote marker appears
    content: str
    citation: Optional[str] = None  # Legal citation if applicable
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: Optional[str] = None


class Edit(BaseModel):
    """Tracked edit/change."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    range: TextRange
    original_text: str
    new_text: str
    edit_type: str = "replace"  # insert, delete, replace
    reason: Optional[str] = None
    status: str = "pending"  # pending, accepted, rejected
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: Optional[str] = None


class ProcessingResult(BaseModel):
    """AI processing results stored in overlay."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module_name: str
    module_version: Optional[str] = None
    results: dict = {}  # Module-specific results
    suggestions: List[str] = []
    warnings: List[str] = []
    confidence: Optional[float] = None
    processed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    processing_time_ms: Optional[int] = None


class DocumentOverlay(BaseModel):
    """Complete overlay for a document."""
    document_id: str
    user_id: str
    version: str = "1.0"
    highlights: List[Highlight] = []
    notes: List[Note] = []
    footnotes: List[Footnote] = []
    edits: List[Edit] = []
    processing: List[ProcessingResult] = []
    metadata: dict = {}
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Request Models
# =============================================================================

class AddHighlightRequest(BaseModel):
    range: TextRange
    color: str = "yellow"
    note: Optional[str] = None


class AddNoteRequest(BaseModel):
    range: Optional[TextRange] = None
    content: str
    note_type: str = "user"
    priority: str = "normal"
    tags: List[str] = []


class AddFootnoteRequest(BaseModel):
    range: TextRange
    content: str
    citation: Optional[str] = None


class AddEditRequest(BaseModel):
    range: TextRange
    original_text: str
    new_text: str
    edit_type: str = "replace"
    reason: Optional[str] = None


class AddProcessingResultRequest(BaseModel):
    module_name: str
    module_version: Optional[str] = None
    results: dict = {}
    suggestions: List[str] = []
    warnings: List[str] = []
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_storage_client(user: StorageUser, db: AsyncSession, settings: Settings):
    """Get the storage client for overlay operations."""
    from app.routers.cloud_sync import get_storage_client as get_cloud_storage
    return await get_cloud_storage(user, db, settings)


async def load_overlay(storage, document_id: str, user_id: str) -> DocumentOverlay:
    """Load overlay from storage, creating if doesn't exist."""
    overlay_path = f".semptify/vault/overlays/{document_id}.json"
    
    try:
        content = await storage.download_file(overlay_path)
        data = json.loads(content.decode("utf-8"))
        return DocumentOverlay(**data)
    except Exception:
        # Create new overlay
        return DocumentOverlay(
            document_id=document_id,
            user_id=user_id,
        )


async def save_overlay(storage, overlay: DocumentOverlay) -> bool:
    """Save overlay to storage."""
    overlay_path = f".semptify/vault/overlays/{overlay.document_id}.json"
    
    # Ensure folder exists
    try:
        await storage.create_folder(".semptify/vault/overlays")
    except Exception:
        pass
    
    # Update timestamp
    overlay.updated_at = datetime.now(timezone.utc).isoformat()
    
    # Save
    content = overlay.model_dump_json(indent=2).encode("utf-8")
    await storage.upload_file(overlay_path, content)
    return True


# =============================================================================
# Overlay Endpoints
# =============================================================================

@router.get("/{document_id}")
async def get_overlay(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📋 Get complete overlay for a document.
    
    Returns all highlights, notes, footnotes, edits, and processing results.
    """
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    return {
        "success": True,
        "overlay": overlay.model_dump(),
        "stats": {
            "highlights": len(overlay.highlights),
            "notes": len(overlay.notes),
            "footnotes": len(overlay.footnotes),
            "edits": len(overlay.edits),
            "processing_runs": len(overlay.processing),
        }
    }


@router.delete("/{document_id}")
async def delete_overlay(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    🗑️ Delete overlay for a document.
    
    Removes all annotations but keeps original document intact.
    """
    storage = await get_storage_client(user, db, settings)
    overlay_path = f".semptify/vault/overlays/{document_id}.json"
    
    try:
        await storage.delete_file(overlay_path)
        return {"success": True, "message": "Overlay deleted"}
    except Exception as e:
        return {"success": False, "message": f"No overlay found: {e}"}


# =============================================================================
# Highlight Endpoints
# =============================================================================

@router.get("/{document_id}/highlights")
async def get_highlights(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📌 Get all highlights for a document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    return {
        "success": True,
        "document_id": document_id,
        "highlights": [h.model_dump() for h in overlay.highlights],
        "count": len(overlay.highlights),
    }


@router.post("/{document_id}/highlights")
async def add_highlight(
    document_id: str,
    request: AddHighlightRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """✨ Add highlight to document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    highlight = Highlight(
        range=request.range,
        color=request.color,
        note=request.note,
        created_by=user.user_id,
    )
    
    overlay.highlights.append(highlight)
    await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "highlight": highlight.model_dump(),
        "total_highlights": len(overlay.highlights),
    }


@router.delete("/{document_id}/highlights/{highlight_id}")
async def delete_highlight(
    document_id: str,
    highlight_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """🗑️ Delete highlight from document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    original_count = len(overlay.highlights)
    overlay.highlights = [h for h in overlay.highlights if h.id != highlight_id]
    
    if len(overlay.highlights) == original_count:
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    await save_overlay(storage, overlay)
    
    return {"success": True, "message": "Highlight deleted"}


# =============================================================================
# Notes Endpoints
# =============================================================================

@router.get("/{document_id}/notes")
async def get_notes(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📝 Get all notes for a document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    return {
        "success": True,
        "document_id": document_id,
        "notes": [n.model_dump() for n in overlay.notes],
        "count": len(overlay.notes),
    }


@router.post("/{document_id}/notes")
async def add_note(
    document_id: str,
    request: AddNoteRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """➕ Add note to document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    note = Note(
        range=request.range,
        content=request.content,
        note_type=request.note_type,
        priority=request.priority,
        tags=request.tags,
        created_by=user.user_id,
    )
    
    overlay.notes.append(note)
    await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "note": note.model_dump(),
        "total_notes": len(overlay.notes),
    }


@router.patch("/{document_id}/notes/{note_id}")
async def update_note(
    document_id: str,
    note_id: str,
    content: Optional[str] = None,
    resolved: Optional[bool] = None,
    priority: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """✏️ Update note."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    for note in overlay.notes:
        if note.id == note_id:
            if content is not None:
                note.content = content
            if resolved is not None:
                note.resolved = resolved
            if priority is not None:
                note.priority = priority
            
            await save_overlay(storage, overlay)
            return {"success": True, "note": note.model_dump()}
    
    raise HTTPException(status_code=404, detail="Note not found")


@router.delete("/{document_id}/notes/{note_id}")
async def delete_note(
    document_id: str,
    note_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """🗑️ Delete note from document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    original_count = len(overlay.notes)
    overlay.notes = [n for n in overlay.notes if n.id != note_id]
    
    if len(overlay.notes) == original_count:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await save_overlay(storage, overlay)
    
    return {"success": True, "message": "Note deleted"}


# =============================================================================
# Footnotes Endpoints
# =============================================================================

@router.get("/{document_id}/footnotes")
async def get_footnotes(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📖 Get all footnotes for a document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    return {
        "success": True,
        "document_id": document_id,
        "footnotes": [f.model_dump() for f in overlay.footnotes],
        "count": len(overlay.footnotes),
    }


@router.post("/{document_id}/footnotes")
async def add_footnote(
    document_id: str,
    request: AddFootnoteRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📎 Add footnote to document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    # Auto-number footnotes
    next_number = max([f.number for f in overlay.footnotes], default=0) + 1
    
    footnote = Footnote(
        number=next_number,
        range=request.range,
        content=request.content,
        citation=request.citation,
        created_by=user.user_id,
    )
    
    overlay.footnotes.append(footnote)
    await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "footnote": footnote.model_dump(),
        "total_footnotes": len(overlay.footnotes),
    }


@router.delete("/{document_id}/footnotes/{footnote_id}")
async def delete_footnote(
    document_id: str,
    footnote_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """🗑️ Delete footnote from document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    original_count = len(overlay.footnotes)
    overlay.footnotes = [f for f in overlay.footnotes if f.id != footnote_id]
    
    if len(overlay.footnotes) == original_count:
        raise HTTPException(status_code=404, detail="Footnote not found")
    
    # Renumber remaining footnotes
    for i, fn in enumerate(sorted(overlay.footnotes, key=lambda x: x.range.start_offset), 1):
        fn.number = i
    
    await save_overlay(storage, overlay)
    
    return {"success": True, "message": "Footnote deleted"}


# =============================================================================
# Edits (Track Changes) Endpoints
# =============================================================================

@router.get("/{document_id}/edits")
async def get_edits(
    document_id: str,
    status_filter: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📝 Get all tracked edits for a document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    edits = overlay.edits
    if status_filter:
        edits = [e for e in edits if e.status == status_filter]
    
    return {
        "success": True,
        "document_id": document_id,
        "edits": [e.model_dump() for e in edits],
        "count": len(edits),
        "pending": len([e for e in overlay.edits if e.status == "pending"]),
        "accepted": len([e for e in overlay.edits if e.status == "accepted"]),
        "rejected": len([e for e in overlay.edits if e.status == "rejected"]),
    }


@router.post("/{document_id}/edits")
async def add_edit(
    document_id: str,
    request: AddEditRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """✏️ Add tracked edit to document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    edit = Edit(
        range=request.range,
        original_text=request.original_text,
        new_text=request.new_text,
        edit_type=request.edit_type,
        reason=request.reason,
        created_by=user.user_id,
    )
    
    overlay.edits.append(edit)
    await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "edit": edit.model_dump(),
        "total_edits": len(overlay.edits),
    }


@router.patch("/{document_id}/edits/{edit_id}")
async def update_edit_status(
    document_id: str,
    edit_id: str,
    status: str,  # pending, accepted, rejected
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """✅ Accept or reject a tracked edit."""
    if status not in ["pending", "accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    for edit in overlay.edits:
        if edit.id == edit_id:
            edit.status = status
            await save_overlay(storage, overlay)
            return {"success": True, "edit": edit.model_dump()}
    
    raise HTTPException(status_code=404, detail="Edit not found")


@router.delete("/{document_id}/edits/{edit_id}")
async def delete_edit(
    document_id: str,
    edit_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """🗑️ Delete tracked edit from document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    original_count = len(overlay.edits)
    overlay.edits = [e for e in overlay.edits if e.id != edit_id]
    
    if len(overlay.edits) == original_count:
        raise HTTPException(status_code=404, detail="Edit not found")
    
    await save_overlay(storage, overlay)
    
    return {"success": True, "message": "Edit deleted"}


# =============================================================================
# Processing Results Endpoints
# =============================================================================

@router.get("/{document_id}/processing")
async def get_processing_results(
    document_id: str,
    module_name: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """🧠 Get AI processing results for a document."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    results = overlay.processing
    if module_name:
        results = [r for r in results if r.module_name == module_name]
    
    return {
        "success": True,
        "document_id": document_id,
        "processing": [r.model_dump() for r in results],
        "count": len(results),
        "modules_run": list(set(r.module_name for r in overlay.processing)),
    }


@router.post("/{document_id}/processing")
async def add_processing_result(
    document_id: str,
    request: AddProcessingResultRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📊 Store AI processing result in overlay."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    result = ProcessingResult(
        module_name=request.module_name,
        module_version=request.module_version,
        results=request.results,
        suggestions=request.suggestions,
        warnings=request.warnings,
        confidence=request.confidence,
        processing_time_ms=request.processing_time_ms,
    )
    
    overlay.processing.append(result)
    await save_overlay(storage, overlay)
    
    logger.info(f"📊 Processing result stored: {request.module_name} -> {document_id}")
    
    return {
        "success": True,
        "result": result.model_dump(),
        "total_processing_runs": len(overlay.processing),
    }


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/{document_id}/bulk")
async def bulk_add_annotations(
    document_id: str,
    highlights: List[AddHighlightRequest] = [],
    notes: List[AddNoteRequest] = [],
    footnotes: List[AddFootnoteRequest] = [],
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📦 Bulk add multiple annotations at once."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    added = {"highlights": 0, "notes": 0, "footnotes": 0}
    
    for h in highlights:
        overlay.highlights.append(Highlight(
            range=h.range,
            color=h.color,
            note=h.note,
            created_by=user.user_id,
        ))
        added["highlights"] += 1
    
    for n in notes:
        overlay.notes.append(Note(
            range=n.range,
            content=n.content,
            note_type=n.note_type,
            priority=n.priority,
            tags=n.tags,
            created_by=user.user_id,
        ))
        added["notes"] += 1
    
    next_fn_number = max([f.number for f in overlay.footnotes], default=0)
    for fn in footnotes:
        next_fn_number += 1
        overlay.footnotes.append(Footnote(
            number=next_fn_number,
            range=fn.range,
            content=fn.content,
            citation=fn.citation,
            created_by=user.user_id,
        ))
        added["footnotes"] += 1
    
    await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "added": added,
        "totals": {
            "highlights": len(overlay.highlights),
            "notes": len(overlay.notes),
            "footnotes": len(overlay.footnotes),
        }
    }


@router.get("/{document_id}/export")
async def export_overlay(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📤 Export overlay as JSON for backup or transfer."""
    storage = await get_storage_client(user, db, settings)
    overlay = await load_overlay(storage, document_id, user.user_id)
    
    return {
        "success": True,
        "document_id": document_id,
        "export": overlay.model_dump(),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{document_id}/import")
async def import_overlay(
    document_id: str,
    overlay_data: dict,
    merge: bool = True,  # If True, merge with existing; if False, replace
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """📥 Import overlay from JSON."""
    storage = await get_storage_client(user, db, settings)
    
    if merge:
        existing = await load_overlay(storage, document_id, user.user_id)
        
        # Merge each list
        if "highlights" in overlay_data:
            for h in overlay_data["highlights"]:
                existing.highlights.append(Highlight(**h))
        if "notes" in overlay_data:
            for n in overlay_data["notes"]:
                existing.notes.append(Note(**n))
        if "footnotes" in overlay_data:
            for f in overlay_data["footnotes"]:
                existing.footnotes.append(Footnote(**f))
        if "edits" in overlay_data:
            for e in overlay_data["edits"]:
                existing.edits.append(Edit(**e))
        if "processing" in overlay_data:
            for p in overlay_data["processing"]:
                existing.processing.append(ProcessingResult(**p))
        
        await save_overlay(storage, existing)
        overlay = existing
    else:
        # Replace entirely
        overlay_data["document_id"] = document_id
        overlay_data["user_id"] = user.user_id
        overlay = DocumentOverlay(**overlay_data)
        await save_overlay(storage, overlay)
    
    return {
        "success": True,
        "document_id": document_id,
        "mode": "merged" if merge else "replaced",
        "stats": {
            "highlights": len(overlay.highlights),
            "notes": len(overlay.notes),
            "footnotes": len(overlay.footnotes),
            "edits": len(overlay.edits),
            "processing_runs": len(overlay.processing),
        }
    }
