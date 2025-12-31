"""
🔄 User Cloud Sync - API Router
================================

Endpoints for syncing user data with their cloud storage.
All data is stored in the user's connected cloud (Google Drive, Dropbox, OneDrive).
Semptify stores NOTHING - we just orchestrate the sync.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.core.security import require_user, StorageUser
from app.services.user_cloud_sync import (
    UserCloudSync,
    UserProfile,
    CaseData,
    SyncStatus,
    QuickSyncData,
)

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["Cloud Sync"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ProfileUpdate(BaseModel):
    """Profile update request."""
    display_name: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    notifications: Optional[bool] = None
    auto_sync: Optional[bool] = None


class CaseUpdate(BaseModel):
    """Case update request."""
    case_number: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_address: Optional[str] = None
    landlord_name: Optional[str] = None
    landlord_address: Optional[str] = None
    property_address: Optional[str] = None
    notice_date: Optional[str] = None
    summons_date: Optional[str] = None
    hearing_date: Optional[str] = None
    answer_deadline: Optional[str] = None
    rent_amount: Optional[float] = None
    amount_owed: Optional[float] = None
    eviction_reason: Optional[str] = None
    defenses: Optional[list] = None
    notes: Optional[str] = None


class TimelineEventCreate(BaseModel):
    """Create timeline event."""
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: str
    is_evidence: bool = False


class CalendarEventCreate(BaseModel):
    """Create calendar event."""
    title: str
    event_type: str
    start_datetime: str
    end_datetime: Optional[str] = None
    is_critical: bool = False
    reminder_days: int = 3


class ImportRequest(BaseModel):
    """Import data request."""
    data: dict


class SyncResponse(BaseModel):
    """Sync status response."""
    status: str
    user_id: str
    synced_at: Optional[str] = None
    profile: Optional[dict] = None
    case_summary: Optional[dict] = None
    counts: Optional[dict] = None
    message: Optional[str] = None


# =============================================================================
# Storage Client Helper
# =============================================================================

class MockStorageClient:
    """Mock storage client for open/demo mode."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.provider_name = "demo_storage"
        self._data = {}
        self._folders = set()

    async def is_connected(self) -> bool:
        """Check if storage is connected - always True for mock."""
        return True

    async def read_file(self, path: str) -> Optional[str]:
        """Read file from mock storage."""
        return self._data.get(path)

    async def write_file(self, path: str, content: str) -> bool:
        """Write file to mock storage."""
        self._data[path] = content
        return True

    async def create_folder(self, path: str) -> bool:
        """Create folder in mock storage."""
        self._folders.add(path)
        return True

    async def create_folder_if_not_exists(self, path: str) -> bool:
        """Create folder if it doesn't exist."""
        self._folders.add(path)
        return True

    async def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return path in self._data
async def get_storage_client(user: StorageUser, db: AsyncSession, settings: Settings):
    """
    Get the appropriate storage client for the user's provider.
    This creates a client based on their OAuth tokens.
    
    NOTE: Even in open mode, we use REAL storage if user has connected.
    Mock storage is only used as fallback when no real connection exists.
    """
    from app.routers.storage import get_valid_session

    # Get a valid session with real storage provider
    session = await get_valid_session(db, user.user_id)
    
    # Require real storage connection - no mock fallback
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid storage session. Please reconnect your cloud storage."
        )

    provider = session.get("provider")
    access_token = session.get("access_token")

    if provider == "google_drive":
        from app.services.storage.google_drive import GoogleDriveProvider
        return GoogleDriveProvider(access_token)
    elif provider == "dropbox":
        from app.services.storage.dropbox import DropboxProvider
        return DropboxProvider(access_token)
    elif provider == "onedrive":
        from app.services.storage.onedrive import OneDriveProvider
        return OneDriveProvider(access_token)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown storage provider: {provider}"
        )


async def get_sync_service(
    user: StorageUser,
    db: AsyncSession,
    settings: Settings,
) -> UserCloudSync:
    """
    Get UserCloudSync service for current user.
    
    NOTE: This is a regular async function, NOT a FastAPI dependency.
    Endpoints must resolve user, db, and settings via Depends() and pass them.
    """
    storage = await get_storage_client(user, db, settings)
    return UserCloudSync(storage, user.user_id)
# =============================================================================
# Sync Endpoints
# =============================================================================

@router.get("/status", response_model=SyncResponse)
async def get_sync_status(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📊 Get current sync status.

    Returns the current sync state and summary of stored data.
    """
    try:
        sync = await get_sync_service(user, db, settings)        # Try to load cached data
        summary = QuickSyncData.from_sync(sync)

        return SyncResponse(
            status=sync.status.value,
            user_id=user.user_id,
            synced_at=datetime.now(timezone.utc).isoformat(),
            **summary,
        )
    except HTTPException:
        # No storage connected - return basic status
        return SyncResponse(
            status="disconnected",
            user_id=user.user_id,
            message="Connect cloud storage to enable sync",
        )
    except Exception as e:
        # Any other error - return disconnected status with error message
        logger.warning("Error getting sync status: %s", str(e))
        return SyncResponse(
            status="error",
            user_id=user.user_id,
            message=f"Sync service unavailable: {str(e)}",
        )
@router.post("/full", response_model=SyncResponse)
async def full_sync(
    background_tasks: BackgroundTasks,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    🔄 Perform full sync with cloud storage.

    Loads all data from user's cloud storage:
    - Profile settings
    - Case data
    - Timeline events
    - Calendar events
    - Document index
    """
    sync = await get_sync_service(user, db, settings)
    result = await sync.sync_all()
    
    return SyncResponse(
        status=result.get("status", "error"),
        user_id=user.user_id,
        synced_at=result.get("synced_at"),
        profile=result.get("profile"),
        case_summary={
            "case_number": result.get("case", {}).get("case_number") if result.get("case") else None,
        },
        counts={
            "timeline": result.get("timeline_count", 0),
            "calendar": result.get("calendar_count", 0),
            "documents": result.get("document_count", 0),
        },
        message="Full sync complete" if result.get("status") == "synced" else result.get("error"),
    )


# =============================================================================
# Profile Endpoints
# =============================================================================

@router.get("/profile")
async def get_profile(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    👤 Get user profile from cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    profile = await sync.get_or_create_profile()
    return profile.to_dict()


@router.put("/profile")
async def update_profile(
    update: ProfileUpdate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    ✏️ Update user profile in cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    profile = await sync.get_or_create_profile()
    
    # Apply updates
    for field, value in update.model_dump(exclude_none=True).items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    
    await sync.save_profile(profile)
    return profile.to_dict()


# =============================================================================
# Case Endpoints
# =============================================================================

@router.get("/case")
async def get_case(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📋 Get case data from cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    case = await sync.get_or_create_case()
    return case.to_dict()


@router.put("/case")
async def update_case(
    update: CaseUpdate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    ✏️ Update case data in cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    case = await sync.get_or_create_case()
    
    # Apply updates
    for field, value in update.model_dump(exclude_none=True).items():
        if hasattr(case, field):
            setattr(case, field, value)
    
    await sync.save_case(case)
    return case.to_dict()


# =============================================================================
# Timeline Endpoints (Cloud-backed)
# =============================================================================

@router.get("/timeline")
async def get_timeline(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📅 Get timeline events from cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    events = await sync.load_timeline()
    return {"events": events, "count": len(events)}


@router.post("/timeline")
async def add_timeline_event(
    event: TimelineEventCreate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    ➕ Add timeline event to cloud storage.
    """
    import uuid

    sync = await get_sync_service(user, db, settings)
    
    event_data = {
        "id": str(uuid.uuid4()),
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "event_date": event.event_date,
        "is_evidence": event.is_evidence,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await sync.add_timeline_event(event_data)
    return event_data


# =============================================================================
# Calendar Endpoints (Cloud-backed)
# =============================================================================

@router.get("/calendar")
async def get_calendar(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    🗓️ Get calendar events from cloud storage.
    """
    sync = await get_sync_service(user, db, settings)
    events = await sync.load_calendar()
    return {"events": events, "count": len(events)}


@router.post("/calendar")
async def add_calendar_event(
    event: CalendarEventCreate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    ➕ Add calendar event to cloud storage.
    """
    import uuid

    sync = await get_sync_service(user, db, settings)
    events = await sync.load_calendar()

    event_data = {
        "id": str(uuid.uuid4()),
        "title": event.title,
        "event_type": event.event_type,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "is_critical": event.is_critical,
        "reminder_days": event.reminder_days,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    events.append(event_data)
    await sync.save_calendar(events)
    return event_data


# =============================================================================
# Export/Import Endpoints
# =============================================================================

@router.get("/export")
async def export_all_data(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📤 Export all user data as JSON.

    Returns a complete backup that can be imported later or on another device.
    """
    sync = await get_sync_service(user, db, settings)
    await sync.sync_all()  # Ensure cache is populated
    return await sync.export_all()


@router.post("/import")
async def import_all_data(
    request: ImportRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📥 Import user data from JSON backup.

    Restores data from an export backup.
    """
    sync = await get_sync_service(user, db, settings)
    success = await sync.import_all(request.data)
    
    if success:
        return {"status": "imported", "message": "Data imported successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import data"
        )


# =============================================================================
# Document Endpoints
# =============================================================================

@router.get("/documents")
async def get_documents(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📄 Get document index from VAULT in cloud storage.
    All documents are now stored in .semptify/vault/
    """
    import json
    
    sync = await get_sync_service(user, db, settings)
    
    # Try to load from vault index first (new architecture)
    vault_folder = ".semptify/vault"
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        docs = vault_index.get("documents", [])
        return {
            "documents": docs,
            "count": len(docs),
            "source": "vault",
            "user_id": user.user_id
        }
    except Exception:
        pass
    
    # Fallback to legacy document index
    docs = await sync.load_document_index()
    return {"documents": docs, "count": len(docs), "source": "legacy"}


@router.get("/vault/index")
async def get_vault_index(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📋 Get the complete vault document index.
    Returns all documents stored in .semptify/vault/ with their metadata.
    """
    import json
    
    sync = await get_sync_service(user, db, settings)
    vault_folder = ".semptify/vault"
    
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        return {
            "success": True,
            "index": vault_index,
            "document_count": len(vault_index.get("documents", [])),
            "user_id": user.user_id,
        }
    except Exception as e:
        return {
            "success": False,
            "index": {"documents": [], "version": "1.0"},
            "document_count": 0,
            "user_id": user.user_id,
            "message": "No vault index found - upload documents to create one"
        }


@router.get("/vault/document/{document_id}")
async def get_vault_document(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📄 Get a specific document from vault by document ID.
    Returns the document metadata from the vault index.
    """
    import json
    
    sync = await get_sync_service(user, db, settings)
    vault_folder = ".semptify/vault"
    
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        
        for doc in vault_index.get("documents", []):
            if doc.get("document_id") == document_id:
                return {
                    "success": True,
                    "document": doc,
                    "user_id": user.user_id,
                }
        
        raise HTTPException(status_code=404, detail="Document not found in vault")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read vault: {str(e)}")


@router.get("/vault/document/{document_id}/content")
async def get_vault_document_content(
    document_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📥 Download document content from vault.
    Returns the raw file content for processing.
    """
    import json
    from fastapi.responses import Response
    
    sync = await get_sync_service(user, db, settings)
    vault_folder = ".semptify/vault"
    
    # Find document in index
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        
        doc_info = None
        for doc in vault_index.get("documents", []):
            if doc.get("document_id") == document_id:
                doc_info = doc
                break
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found in vault")
        
        # Download content
        storage_path = doc_info.get("storage_path", f"{vault_folder}/{document_id}")
        content = await sync.storage.download_file(storage_path)
        
        return Response(
            content=content,
            media_type=doc_info.get("mime_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{doc_info.get("original_filename", "document")}"',
                "X-Document-ID": document_id,
                "X-SHA256": doc_info.get("sha256", ""),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download: {str(e)}")


@router.patch("/vault/document/{document_id}")
async def update_vault_document(
    document_id: str,
    processed: Optional[bool] = None,
    registered: Optional[bool] = None,
    document_type: Optional[str] = None,
    tags: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📝 Update document metadata in vault index.
    Used by processing modules to update document status.
    """
    import json
    from datetime import datetime, timezone
    
    sync = await get_sync_service(user, db, settings)
    vault_folder = ".semptify/vault"
    
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        
        updated = False
        for doc in vault_index.get("documents", []):
            if doc.get("document_id") == document_id:
                if processed is not None:
                    doc["processed"] = processed
                if registered is not None:
                    doc["registered"] = registered
                if document_type is not None:
                    doc["document_type"] = document_type
                if tags is not None:
                    doc["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
                doc["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail="Document not found in vault")
        
        vault_index["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        await sync.storage.upload_file(
            f"{vault_folder}/index.json",
            json.dumps(vault_index, indent=2).encode("utf-8")
        )
        
        return {"success": True, "document_id": document_id, "message": "Document updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")


@router.post("/documents/upload")
async def upload_document_to_cloud(
    file: UploadFile = File(...),
    folder: str = Form(default="root"),
    tags: str = Form(default=""),
    notes: str = Form(default=""),
    document_type: str = Form(default=""),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    📤 Upload document directly to user's VAULT in cloud storage.
    
    All uploads go to .semptify/vault/ with document ID and user ID.
    This is the single source of truth for all documents.
    """
    import uuid
    import hashlib
    import json
    from datetime import datetime, timezone
    
    sync = await get_sync_service(user, db, settings)
    
    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"
    file_size = len(content)
    
    # Check size limit
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB"
        )
    
    # Generate document ID and compute hash
    document_id = str(uuid.uuid4())
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # Determine extension and safe filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    safe_filename = f"{document_id}.{ext}"
    
    # Detect mime type
    mime_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }
    mime_type = file.content_type or mime_types.get(ext, "application/octet-stream")
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    # Ensure vault folders exist
    vault_folder = ".semptify/vault"
    certs_folder = ".semptify/vault/certificates"
    index_folder = ".semptify/vault"
    
    try:
        await sync.storage.create_folder(".semptify")
        await sync.storage.create_folder(vault_folder)
        await sync.storage.create_folder(certs_folder)
    except Exception:
        pass  # Folders may already exist
    
    # Upload file to vault
    storage_path = f"{vault_folder}/{safe_filename}"
    try:
        await sync.storage.upload_file(storage_path, content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to vault: {str(e)}"
        )
    
    # Create certificate
    certificate_id = f"cert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{document_id[:8]}"
    certificate = {
        "certificate_id": certificate_id,
        "document_id": document_id,
        "user_id": user.user_id,
        "sha256": sha256_hash,
        "original_filename": filename,
        "file_size": file_size,
        "mime_type": mime_type,
        "document_type": document_type or "other",
        "description": notes,
        "tags": tag_list,
        "folder": folder,
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "storage_path": storage_path,
        "storage_provider": user.provider,
        "version": "5.0",
        "platform": "Semptify Vault",
    }
    
    # Upload certificate
    cert_content = json.dumps(certificate, indent=2).encode("utf-8")
    try:
        await sync.storage.upload_file(f"{certs_folder}/{certificate_id}.json", cert_content)
    except Exception:
        pass  # Certificate failed but file uploaded
    
    # Update vault index
    try:
        # Load existing index
        try:
            index_content = await sync.storage.download_file(f"{index_folder}/index.json")
            vault_index = json.loads(index_content.decode("utf-8"))
        except Exception:
            vault_index = {"documents": [], "version": "1.0"}
        
        # Add document to index
        vault_index["documents"].append({
            "document_id": document_id,
            "user_id": user.user_id,
            "filename": safe_filename,
            "original_filename": filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "sha256": sha256_hash,
            "document_type": document_type or "other",
            "tags": tag_list,
            "folder": folder,
            "storage_path": storage_path,
            "certificate_id": certificate_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "processed": False,
            "registered": False,
        })
        vault_index["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Save updated index
        await sync.storage.upload_file(
            f"{index_folder}/index.json",
            json.dumps(vault_index, indent=2).encode("utf-8")
        )
    except Exception as e:
        logger.warning(f"Failed to update vault index: {e}")
    
    logger.info(f"📤 Document uploaded to vault: {filename} -> {document_id}")
    
    return {
        "success": True,
        "document_id": document_id,
        "file_id": document_id,  # For backward compatibility
        "filename": safe_filename,
        "original_filename": filename,
        "size": file_size,
        "sha256": sha256_hash,
        "certificate_id": certificate_id,
        "storage_path": storage_path,
        "folder": folder,
        "user_id": user.user_id,
        "message": f"Document uploaded to vault"
    }


# =============================================================================
# Quick Connect Check
# =============================================================================

@router.get("/check")
async def check_storage_connection(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    🔌 Check if cloud storage is connected and accessible.

    Returns connection status without performing full sync.
    """
    try:
        sync = await get_sync_service(user, db, settings)
        connected = await sync.storage.is_connected()
        
        return {
            "connected": connected,
            "user_id": user.user_id,
            "provider": getattr(sync.storage, 'provider_name', 'unknown'),
            "message": "Storage connected" if connected else "Storage not accessible",
        }
    except HTTPException as e:
        return {
            "connected": False,
            "user_id": user.user_id,
            "provider": None,
            "message": e.detail,
        }
