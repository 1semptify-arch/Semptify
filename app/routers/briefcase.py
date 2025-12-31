"""
Briefcase Router - Document & Folder Organization System
A digital briefcase for organizing legal documents, evidence, and case files

SECURITY: All endpoints require authenticated user with connected storage.
All documents are stored in user's cloud (Google Drive/Dropbox/OneDrive).
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import os
import io
import json
import hashlib
import base64
import zipfile
import uuid
import logging

from app.core.security import require_user, StorageUser
from app.core.database import get_db
from app.core.config import get_settings, Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/briefcase", tags=["Briefcase"])


# =============================================================================
# Cloud Sync Integration
# =============================================================================

async def get_cloud_sync(user: StorageUser, db: AsyncSession, settings: Settings):
    """Get UserCloudSync service for the user's cloud storage."""
    from app.routers.cloud_sync import get_sync_service
    return await get_sync_service(user, db, settings)


# =============================================================================
# Default Folder Structure
# =============================================================================

DEFAULT_FOLDERS = {
    "root": {
        "id": "root",
        "name": "My Briefcase",
        "parent_id": None,
        "color": "#4ade80",
        "icon": "briefcase"
    },
    "extracted": {
        "id": "extracted",
        "name": "📄 Extracted Pages",
        "parent_id": "root",
        "color": "#f59e0b",
        "icon": "file-export",
        "system": True
    },
    "highlights": {
        "id": "highlights",
        "name": "🖍️ Highlights & Notes",
        "parent_id": "root",
        "color": "#ec4899",
        "icon": "highlighter",
        "system": True
    },
    "evidence": {
        "id": "evidence",
        "name": "📸 Evidence",
        "parent_id": "root",
        "color": "#ef4444",
        "icon": "gavel",
        "system": True
    },
    "court": {
        "id": "court",
        "name": "⚖️ Court Documents",
        "parent_id": "root",
        "color": "#8b5cf6",
        "icon": "scale",
        "system": True
    },
    "correspondence": {
        "id": "correspondence",
        "name": "📧 Correspondence",
        "parent_id": "root",
        "color": "#06b6d4",
        "icon": "envelope",
        "system": True
    }
}

DEFAULT_TAGS = ["Important", "Evidence", "Lease", "Notice", "Court", "Correspondence", "Financial", "Photos", "Urgent"]


# =============================================================================
# Pydantic Models
# =============================================================================

class FolderCreate(BaseModel):
    name: str
    parent_id: str = "root"
    color: Optional[str] = "#3b82f6"
    icon: Optional[str] = "folder"

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    starred: Optional[bool] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_file_type(ext: str) -> str:
    """Determine file type category from extension"""
    types = {
        ".pdf": "pdf",
        ".doc": "word", ".docx": "word",
        ".xls": "excel", ".xlsx": "excel",
        ".ppt": "powerpoint", ".pptx": "powerpoint",
        ".txt": "text", ".md": "text", ".rtf": "text",
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image", ".webp": "image",
        ".mp3": "audio", ".wav": "audio", ".m4a": "audio",
        ".mp4": "video", ".mov": "video", ".avi": "video",
        ".zip": "archive", ".rar": "archive", ".7z": "archive",
        ".html": "web", ".htm": "web",
        ".json": "data", ".xml": "data", ".csv": "data"
    }
    return types.get(ext.lower(), "other")


def get_breadcrumb(folder_id: str) -> List[Dict]:
    """Build breadcrumb path from root to folder."""
    breadcrumb = []
    current_id = folder_id
    
    while current_id and current_id in DEFAULT_FOLDERS:
        folder = DEFAULT_FOLDERS[current_id]
        breadcrumb.insert(0, {"id": folder["id"], "name": folder["name"]})
        current_id = folder.get("parent_id")
    
    return breadcrumb


# =============================================================================
# Main Briefcase Endpoints
# =============================================================================

@router.get("/")
async def get_briefcase(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Get entire briefcase structure - loads from USER'S CLOUD STORAGE.
    
    Returns folders and documents from user's connected cloud storage.
    """
    try:
        sync = await get_cloud_sync(user, db, settings)
        documents = await sync.load_document_index()
    except HTTPException:
        # No storage connected yet
        documents = []
    except Exception as e:
        logger.warning(f"Error loading documents: {e}")
        documents = []
    
    return {
        "user_id": user.user_id,
        "folders": list(DEFAULT_FOLDERS.values()),
        "documents": documents,
        "tags": DEFAULT_TAGS,
        "stats": {
            "total_folders": len(DEFAULT_FOLDERS),
            "total_documents": len(documents),
            "total_size": sum(d.get("size", 0) for d in documents),
            "starred_count": sum(1 for d in documents if d.get("starred"))
        },
        "storage": "cloud"
    }


@router.get("/processed")
async def get_processed_documents(
    user: StorageUser = Depends(require_user),
):
    """
    Get all processed documents from the unified upload pipeline.
    
    These are documents that have been:
    - Uploaded via /api/documents/upload
    - Fully processed (OCR, classification, analysis)
    - Automatically organized into folders
    
    Returns documents formatted for briefcase display.
    """
    try:
        from app.services.document_distributor import get_document_distributor
        distributor = get_document_distributor()
        documents = distributor.get_briefcase_documents(user.user_id)
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents),
            "source": "unified_upload_pipeline"
        }
    except ImportError:
        return {
            "success": False,
            "documents": [],
            "count": 0,
            "message": "Document distributor not available"
        }
    except Exception as e:
        logger.warning(f"Error getting processed documents: {e}")
        return {
            "success": False,
            "documents": [],
            "count": 0,
            "message": str(e)
        }


@router.get("/folder/{folder_id}")
async def get_folder_contents(
    folder_id: str, 
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get contents of a specific folder - loads from cloud storage."""
    if folder_id not in DEFAULT_FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = DEFAULT_FOLDERS[folder_id]
    
    try:
        sync = await get_cloud_sync(user, db, settings)
        all_documents = await sync.load_document_index()
    except HTTPException:
        all_documents = []
    except Exception as e:
        logger.warning(f"Error loading documents: {e}")
        all_documents = []
    
    # Also include processed documents from unified upload
    try:
        from app.services.document_distributor import get_document_distributor
        distributor = get_document_distributor()
        processed_docs = distributor.get_briefcase_documents(user.user_id)
        # Filter to this folder
        processed_in_folder = [d for d in processed_docs if d.get("folder_id", "root") == folder_id]
        all_documents.extend(processed_in_folder)
    except Exception:
        pass  # Distributor not available
    
    # Get subfolders
    subfolders = [f for f in DEFAULT_FOLDERS.values() if f.get("parent_id") == folder_id]
    
    # Get documents in this folder
    documents = [d for d in all_documents if d.get("folder_id", "root") == folder_id]
    
    # Get breadcrumb path
    breadcrumb = get_breadcrumb(folder_id)
    
    return {
        "folder": folder,
        "subfolders": subfolders,
        "documents": documents,
        "breadcrumb": breadcrumb,
        "stats": {
            "document_count": len(documents),
            "subfolder_count": len(subfolders),
            "total_size": sum(d.get("size", 0) for d in documents)
        }
    }


# =============================================================================
# Document Upload & Management
# =============================================================================

@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    folder_id: str = Form(default="root"),
    tags: str = Form(default=""),
    notes: str = Form(default=""),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a document to the briefcase - saves to USER'S CLOUD STORAGE.
    
    Documents are stored in user's Google Drive/Dropbox/OneDrive under:
    .semptify/documents/[filename]
    """
    sync = await get_cloud_sync(user, db, settings)
    
    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"
    
    # Generate document ID and hash
    doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) & 0xFFFFFF:06x}"
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    
    # Determine file type
    ext = os.path.splitext(filename)[1].lower()
    file_type = get_file_type(ext)
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Build metadata
    metadata = {
        "doc_id": doc_id,
        "folder_id": folder_id,
        "type": file_type,
        "extension": ext,
        "mime_type": file.content_type,
        "hash": file_hash,
        "tags": tag_list,
        "notes": notes,
        "starred": False,
        "user_id": user.user_id,
    }
    
    # Upload to cloud storage
    cloud_file_id = await sync.upload_document(filename, content, metadata)
    
    if not cloud_file_id:
        raise HTTPException(
            status_code=500, 
            detail="Failed to upload document to cloud storage"
        )
    
    logger.info(f"📤 Document uploaded to cloud: {filename} -> {cloud_file_id}")
    
    # Build response
    doc_response = {
        "id": doc_id,
        "cloud_id": cloud_file_id,
        "name": filename,
        "folder_id": folder_id,
        "size": len(content),
        "type": file_type,
        "extension": ext,
        "mime_type": file.content_type,
        "hash": file_hash,
        "tags": tag_list,
        "notes": notes,
        "starred": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user.user_id,
    }
    
    return {"success": True, "document": doc_response, "storage": "cloud"}


@router.get("/document/{doc_id}")
async def get_document(
    doc_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get document metadata from cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc = next((d for d in documents if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc


@router.get("/document/{doc_id}/download")
async def download_document(
    doc_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Download a document from cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc = next((d for d in documents if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get the cloud file ID
    cloud_id = doc.get("cloud_id") or doc.get("file_id")
    if not cloud_id:
        raise HTTPException(status_code=404, detail="Document has no cloud reference")
    
    # Download from cloud
    content = await sync.download_document(cloud_id)
    if not content:
        raise HTTPException(status_code=404, detail="Could not download document from cloud")
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename={doc.get('name', 'document')}"}
    )


@router.get("/document/{doc_id}/preview")
async def preview_document(
    doc_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get document content for preview (base64 encoded)."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc = next((d for d in documents if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get the cloud file ID
    cloud_id = doc.get("cloud_id") or doc.get("file_id")
    if not cloud_id:
        raise HTTPException(status_code=404, detail="Document has no cloud reference")
    
    # Download from cloud
    content = await sync.download_document(cloud_id)
    if not content:
        raise HTTPException(status_code=404, detail="Could not download document from cloud")
    
    # Encode as base64
    b64_content = base64.b64encode(content).decode('utf-8')
    mime_type = doc.get("mime_type", "application/octet-stream")
    
    return {
        "id": doc_id,
        "name": doc.get("name", "document"),
        "type": doc.get("type", "other"),
        "mime_type": mime_type,
        "content": f"data:{mime_type};base64,{b64_content}"
    }


@router.put("/document/{doc_id}")
async def update_document(
    doc_id: str,
    update: DocumentUpdate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Update document metadata in cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc_index = next((i for i, d in enumerate(documents) if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if doc_index is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[doc_index]
    
    # Apply updates
    if update.name is not None:
        doc["name"] = update.name
    if update.folder_id is not None:
        if update.folder_id not in DEFAULT_FOLDERS:
            raise HTTPException(status_code=404, detail="Target folder not found")
        doc["folder_id"] = update.folder_id
    if update.tags is not None:
        doc["tags"] = update.tags
    if update.notes is not None:
        doc["notes"] = update.notes
    if update.starred is not None:
        doc["starred"] = update.starred
    
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Save updated index back to cloud
    documents[doc_index] = doc
    await sync.save_document_index(documents)
    
    return {"success": True, "document": doc}


@router.delete("/document/{doc_id}")
async def delete_document(
    doc_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Delete a document from cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc = next((d for d in documents if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from cloud
    cloud_id = doc.get("cloud_id") or doc.get("file_id")
    if cloud_id:
        try:
            await sync.delete_document(cloud_id)
        except Exception as e:
            logger.warning(f"Could not delete cloud file: {e}")
    
    # Remove from index
    documents = [d for d in documents if d.get("doc_id") != doc_id and d.get("id") != doc_id]
    await sync.save_document_index(documents)
    
    return {"success": True, "message": "Document deleted"}


@router.post("/document/{doc_id}/move")
async def move_document(
    doc_id: str,
    folder_id: str = Form(...),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Move document to another folder."""
    if folder_id not in DEFAULT_FOLDERS:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    doc_index = next((i for i, d in enumerate(documents) if d.get("doc_id") == doc_id or d.get("id") == doc_id), None)
    if doc_index is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    documents[doc_index]["folder_id"] = folder_id
    documents[doc_index]["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await sync.save_document_index(documents)
    
    return {"success": True, "message": "Document moved", "document": documents[doc_index]}


# =============================================================================
# Search & Filter
# =============================================================================

@router.get("/search")
async def search_documents(
    q: str,
    folder_id: Optional[str] = None,
    tags: Optional[str] = None,
    file_type: Optional[str] = None,
    starred: Optional[bool] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Search documents in cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    results = []
    query = q.lower()
    tag_filter = [t.strip() for t in tags.split(",")] if tags else []
    
    for doc in documents:
        # Text search
        if query:
            name_match = query in doc.get("name", "").lower()
            notes_match = query in doc.get("notes", "").lower()
            tag_match = any(query in t.lower() for t in doc.get("tags", []))
            if not (name_match or notes_match or tag_match):
                continue
        
        # Folder filter
        if folder_id and doc.get("folder_id", "root") != folder_id:
            continue
        
        # Tag filter
        if tag_filter:
            if not any(t in doc.get("tags", []) for t in tag_filter):
                continue
        
        # File type filter
        if file_type and doc.get("type") != file_type:
            continue
        
        # Starred filter
        if starred is not None and doc.get("starred") != starred:
            continue
        
        results.append(doc)
    
    return {"results": results, "count": len(results), "query": q}


@router.get("/starred")
async def get_starred_documents(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get all starred documents from cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    starred = [d for d in documents if d.get("starred")]
    return {"documents": starred, "count": len(starred)}


@router.get("/recent")
async def get_recent_documents(
    limit: int = 10,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get recently added/updated documents from cloud storage."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    # Sort by updated_at or created_at
    docs = sorted(documents, key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
    
    return {"documents": docs[:limit], "count": len(docs[:limit])}


# =============================================================================
# Tags
# =============================================================================

@router.get("/tags")
async def get_all_tags(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get all available tags (default + used)."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    # Collect all tags from documents
    all_tags = set(DEFAULT_TAGS)
    for doc in documents:
        all_tags.update(doc.get("tags", []))
    
    return {"tags": sorted(list(all_tags))}


# =============================================================================
# Statistics
# =============================================================================

@router.get("/stats")
async def get_briefcase_stats(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Get detailed briefcase statistics."""
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()

    # Type distribution
    type_counts = {}
    for doc in documents:
        t = doc.get("type", "other")
        type_counts[t] = type_counts.get(t, 0) + 1

    # Tag distribution
    tag_counts = {}
    for doc in documents:
        for tag in doc.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Folder sizes
    folder_sizes = {}
    folder_counts = {}
    for doc in documents:
        fid = doc.get("folder_id", "root")
        folder_sizes[fid] = folder_sizes.get(fid, 0) + doc.get("size", 0)
        folder_counts[fid] = folder_counts.get(fid, 0) + 1

    return {
        "total_folders": len(DEFAULT_FOLDERS),
        "total_documents": len(documents),
        "total_size": sum(d.get("size", 0) for d in documents),
        "starred_count": sum(1 for d in documents if d.get("starred")),
        "type_distribution": type_counts,
        "tag_distribution": tag_counts,
        "folder_sizes": folder_sizes,
        "folder_counts": folder_counts,
        "storage": "cloud"
    }


# =============================================================================
# Export
# =============================================================================

@router.post("/export")
async def export_folder(
    folder_id: str = Form(default="root"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Export folder as ZIP file (downloads all documents from cloud)."""
    if folder_id not in DEFAULT_FOLDERS:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    # Filter documents in this folder
    folder_docs = [d for d in documents if d.get("folder_id", "root") == folder_id]
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for doc in folder_docs:
            cloud_id = doc.get("cloud_id") or doc.get("file_id")
            if cloud_id:
                try:
                    content = await sync.download_document(cloud_id)
                    if content:
                        zip_file.writestr(doc.get("name", "unknown"), content)
                except Exception as e:
                    logger.warning(f"Could not download {doc.get('name')}: {e}")
    
    zip_buffer.seek(0)
    folder_name = DEFAULT_FOLDERS[folder_id]["name"]
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={folder_name}.zip"}
    )


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/bulk/move")
async def bulk_move_documents(
    request: Request,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Move multiple documents to a folder."""
    data = await request.json()
    doc_ids = data.get("doc_ids", [])
    target_folder = data.get("folder_id", "root")
    
    if target_folder not in DEFAULT_FOLDERS:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    moved = 0
    for doc in documents:
        if doc.get("doc_id") in doc_ids or doc.get("id") in doc_ids:
            doc["folder_id"] = target_folder
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            moved += 1
    
    await sync.save_document_index(documents)
    
    return {"success": True, "moved": moved}


@router.post("/bulk/tag")
async def bulk_tag_documents(
    request: Request,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Add tags to multiple documents."""
    data = await request.json()
    doc_ids = data.get("doc_ids", [])
    tags_to_add = data.get("tags", [])
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    tagged = 0
    for doc in documents:
        if doc.get("doc_id") in doc_ids or doc.get("id") in doc_ids:
            existing_tags = set(doc.get("tags", []))
            existing_tags.update(tags_to_add)
            doc["tags"] = list(existing_tags)
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            tagged += 1
    
    await sync.save_document_index(documents)
    
    return {"success": True, "tagged": tagged}


@router.post("/bulk/delete")
async def bulk_delete_documents(
    request: Request,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Delete multiple documents."""
    data = await request.json()
    doc_ids = data.get("doc_ids", [])
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    deleted = 0
    remaining = []
    
    for doc in documents:
        if doc.get("doc_id") in doc_ids or doc.get("id") in doc_ids:
            # Delete from cloud
            cloud_id = doc.get("cloud_id") or doc.get("file_id")
            if cloud_id:
                try:
                    await sync.delete_document(cloud_id)
                except Exception as e:
                    logger.warning(f"Could not delete cloud file: {e}")
            deleted += 1
        else:
            remaining.append(doc)
    
    await sync.save_document_index(remaining)
    
    return {"success": True, "deleted": deleted}


@router.post("/bulk/star")
async def bulk_star_documents(
    request: Request,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Star/unstar multiple documents."""
    data = await request.json()
    doc_ids = data.get("doc_ids", [])
    starred = data.get("starred", True)
    
    sync = await get_cloud_sync(user, db, settings)
    documents = await sync.load_document_index()
    
    updated = 0
    for doc in documents:
        if doc.get("doc_id") in doc_ids or doc.get("id") in doc_ids:
            doc["starred"] = starred
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
    
    await sync.save_document_index(documents)
    
    return {"success": True, "updated": updated, "starred": starred}
