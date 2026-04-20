"""
Document Vault Router (Cloud Storage Version)
Secure document upload to user's cloud storage with certification.

Semptify 5.0 Architecture:
- ALL DOCUMENTS GO TO VAULT FIRST
- Documents stored in USER's cloud storage (Google Drive, Dropbox, OneDrive)
- Modules access documents FROM the vault
- User must be authenticated via storage OAuth
- Certificates stored alongside documents in .semptify/vault/
"""

import hashlib
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.security import (
    require_user,
    rate_limit_dependency,
    StorageUser,
    issue_function_access_token,
)
from app.core.vault_paths import SEMPTIFY_ROOT, VAULT_ROOT, VAULT_DOCUMENTS, VAULT_CERTIFICATES
from app.services.storage import get_provider, StorageFile

# Import vault upload service - central document storage
try:
    from app.services.vault_upload_service import get_vault_service, VaultDocument
    HAS_VAULT_SERVICE = True
except ImportError:
    HAS_VAULT_SERVICE = False

# Import preview generation
try:
    from app.core.preview_generator import generate_document_thumbnail, generate_document_preview
    from app.core.job_processor import submit_thumbnail_generation_job
    HAS_PREVIEW_GENERATOR = True
except ImportError:
    HAS_PREVIEW_GENERATOR = False

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class DocumentMetadata(BaseModel):
    """Document metadata for upload."""
    document_type: Optional[str] = Field(None, description="Type: lease, notice, photo, receipt, other")
    description: Optional[str] = Field(None, description="Description of the document")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    event_date: Optional[str] = Field(None, description="Date related to this document (ISO format)")


class DocumentResponse(BaseModel):
    """Response after document upload."""
    id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    certificate_id: str
    uploaded_at: str
    document_type: Optional[str] = None
    storage_provider: str
    storage_path: str
    function_token: Optional[str] = None
    function_token_expires_at: Optional[str] = None
    function_token_reverify_in_seconds: Optional[int] = None


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: list[DocumentResponse]
    total: int
    storage_provider: str


class CertificateResponse(BaseModel):
    """Document certification details."""
    document_id: str
    sha256_hash: str
    certified_at: str
    original_filename: str
    file_size: int
    request_id: str
    storage_provider: str


# =============================================================================
# Constants
# =============================================================================

VAULT_FOLDER = VAULT_DOCUMENTS
CERTS_FOLDER = VAULT_CERTIFICATES


# =============================================================================
# Helper Functions
# =============================================================================

def compute_sha256(file_content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def is_allowed_extension(filename: str, settings: Settings) -> bool:
    """Check if file extension is allowed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.allowed_extensions_set


async def ensure_vault_folders(storage, provider_name: str) -> None:
    """Ensure vault folders exist in user's storage."""
    await storage.create_folder(SEMPTIFY_ROOT)
    await storage.create_folder(VAULT_ROOT)
    await storage.create_folder(VAULT_FOLDER)
    await storage.create_folder(CERTS_FOLDER)


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("vault-upload", window=60, max_requests=20))],
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a document to the user's cloud storage vault.

    The document is stored in the user's connected cloud storage (not on server):
    - File: .semptify/vault/{document_id}.{ext}
    - Certificate: .semptify/vault/certificates/cert_{document_id}.json
    
    Requires:
    - User authenticated via storage OAuth
    - access_token: Current access token for user's storage provider
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    if not is_allowed_extension(file.filename, settings):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {settings.allowed_extensions}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check size limit
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB",
        )

    # Generate IDs and hash
    document_id = str(uuid.uuid4())
    sha256_hash = compute_sha256(content)

    # Determine safe filename
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    safe_filename = f"{document_id}.{ext}"

    # Get storage provider for user
    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Ensure vault folders exist and upload file
    try:
        await ensure_vault_folders(storage, user.provider)

        # Upload file to user's storage
        storage_path = f"{VAULT_FOLDER}/{safe_filename}"
        await storage.upload_file(
            file_content=content,
            destination_path=VAULT_FOLDER,
            filename=safe_filename,
            mime_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        # Storage authentication or access errors
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "access" in error_msg.lower():
            raise HTTPException(status_code=401, detail=f"Storage authentication failed: {error_msg}")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise HTTPException(status_code=403, detail=f"Storage access denied: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"Storage error: {error_msg}")

    # Create certificate
    certificate_id = f"cert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{document_id[:8]}"
    certificate = {
        "certificate_id": certificate_id,
        "document_id": document_id,
        "sha256": sha256_hash,
        "original_filename": file.filename,
        "file_size": file_size,
        "mime_type": file.content_type or "application/octet-stream",
        "document_type": document_type,
        "description": description,
        "tags": tags.split(",") if tags else [],
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "storage_path": storage_path,
        "storage_provider": user.provider,
        "user_id": user.user_id,
        "version": "5.0",
        "platform": "Semptify FastAPI Cloud Storage",
    }

    # Upload certificate to user's storage
    cert_content = json.dumps(certificate, indent=2).encode("utf-8")
    try:
        await storage.upload_file(
            file_content=cert_content,
            destination_path=CERTS_FOLDER,
            filename=f"{certificate_id}.json",
            mime_type="application/json",
        )
    except Exception as e:
        # Certificate upload failed, but file was already uploaded
        # Log this but don't fail the request
        pass

    # Create overlay for safe processing (original never touched)
    overlay = None
    try:
        from app.services.document_overlay import OverlayManager
        overlay_manager = OverlayManager(storage, access_token)
        overlay = await overlay_manager.create_overlay(
            original_id=document_id,
            original_path=storage_path
        )
        # Store overlay ID in certificate for reference
        certificate["overlay_id"] = overlay.overlay_id
        
        # Auto-extract timeline events from document and persist to user's timeline storage
        try:
            from app.services.timeline_extraction import extract_timeline_from_upload
            provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
            timeline_events = await extract_timeline_from_upload(
                document_id=document_id,
                overlay_id=overlay.overlay_id,
                provider=provider_name,
                access_token=access_token,
            )
            certificate["timeline_events_extracted"] = len(timeline_events)
        except Exception as e:
            # Timeline extraction failed, but upload succeeded
            # Log and continue - can re-extract later
            certificate["timeline_events_extracted"] = 0
            
    except Exception as e:
        # Overlay creation failed, but document is safely stored
        # Log and continue - overlay can be created later
        overlay = None

    function_token = issue_function_access_token(
        user.user_id,
        context={
            "provider": user.provider,
            "reason": "vault_upload",
            "scopes": ["overlay:read", "overlay:write"],
            "document_ids": [document_id],
        },
    )

    # Generate preview and thumbnail (async, non-blocking)
    if HAS_PREVIEW_GENERATOR:
        try:
            # Submit thumbnail generation job
            from app.core.job_processor import submit_thumbnail_generation_job
            job_id = submit_thumbnail_generation_job(
                document_id=document_id,
                page_numbers=[1],  # Generate first page thumbnail
                user_id=user.user_id
            )
            logger.info(f"Submitted thumbnail generation job {job_id} for document {document_id}")
            
            # Also submit document analysis job
            from app.core.job_processor import submit_document_analysis_job
            analysis_job_id = submit_document_analysis_job(
                document_id=document_id,
                analysis_type="basic",
                user_id=user.user_id
            )
            logger.info(f"Submitted document analysis job {analysis_job_id} for document {document_id}")
            
        except Exception as e:
            logger.warning(f"Preview generation failed for {document_id}: {e}")

    # =============================================================================
    # TRIGGER MESH WORKFLOW BASED ON DOCUMENT TYPE
    # =============================================================================
    try:
        from app.core.positronic_mesh import positronic_mesh, WorkflowType
        import asyncio
        
        # Determine workflow type from document_type or content hints
        workflow_type = None
        trigger_context = {
            "document_id": document_id,
            "certificate_id": certificate_id,
            "filename": file.filename,
            "mime_type": file.content_type,
            "document_type": document_type,
            "overlay_id": overlay.overlay_id if overlay else None,
            "timeline_events_count": certificate.get("timeline_events_extracted", 0),
        }
        
        # Map document types to workflows
        if document_type in ("eviction_notice", "summons", "court_order"):
            workflow_type = WorkflowType.EVICTION_DEFENSE
        elif document_type in ("lease", "rental_agreement"):
            workflow_type = WorkflowType.LEASE_ANALYSIS
        elif document_type in ("hearing_notice", "motion", "evidence_list"):
            workflow_type = WorkflowType.COURT_PREP
        
        # Also check filename for hints if no explicit type
        if not workflow_type and file.filename:
            fname_lower = file.filename.lower()
            if any(word in fname_lower for word in ("evict", "notice", "summons", "quit")):
                workflow_type = WorkflowType.EVICTION_DEFENSE
            elif any(word in fname_lower for word in ("lease", "rental", "agreement")):
                workflow_type = WorkflowType.LEASE_ANALYSIS
            elif any(word in fname_lower for word in ("hearing", "court", "motion")):
                workflow_type = WorkflowType.COURT_PREP
        
        if workflow_type:
            # Start workflow async (non-blocking to response)
            asyncio.create_task(
                positronic_mesh.start_workflow(
                    workflow_type=workflow_type,
                    user_id=user.user_id,
                    trigger="document_upload",
                    initial_context=trigger_context,
                )
            )
            logger.info(f"🚀 Triggered {workflow_type.value} workflow for document {document_id}")
            certificate["mesh_workflow_triggered"] = workflow_type.value
        else:
            certificate["mesh_workflow_triggered"] = None
            
    except Exception as e:
        # Workflow trigger failed but upload succeeded - log and continue
        logger.warning(f"Mesh workflow trigger failed for {document_id}: {e}")
        certificate["mesh_workflow_triggered"] = "error"

    # Build response
    return DocumentResponse(
        id=document_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        sha256_hash=sha256_hash,
        certificate_id=certificate_id,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        document_type=document_type,
        storage_provider=user.provider,
        storage_path=storage_path,
        function_token=function_token["token"],
        function_token_expires_at=function_token["expires_at"],
        function_token_reverify_in_seconds=function_token["reverify_in_seconds"],
    )


@router.post(
    "/copy-from-sync",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("vault-copy", window=60, max_requests=20))],
)
async def copy_from_sync_to_vault(
    file_id: str = Form(..., description="File ID from cloud sync storage"),
    filename: str = Form(..., description="Original filename"),
    document_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    Copy a document from sync storage (.semptify/documents/) to vault (.semptify/vault/).
    
    This is used when the original File object is no longer available (e.g., after page refresh)
    but the document was already uploaded to cloud storage via the sync endpoint.
    """
    # Get storage provider for user
    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Try to download from sync documents folder
    sync_path = f".semptify/documents/{filename}"
    
    try:
        content = await storage.download_file(sync_path)
    except Exception as e:
        # Try alternative paths
        try:
            content = await storage.download_file(f".semptify/documents/{file_id}")
        except Exception:
            raise HTTPException(
                status_code=404, 
                detail=f"Could not find document in cloud storage. Path tried: {sync_path}"
            )
    
    if not content:
        raise HTTPException(status_code=404, detail="Document content is empty")
    
    file_size = len(content)
    
    # Check size limit
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB",
        )

    # Generate IDs and hash
    document_id = str(uuid.uuid4())
    sha256_hash = compute_sha256(content)

    # Determine safe filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    safe_filename = f"{document_id}.{ext}"
    
    # Detect mime type from extension
    mime_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }
    mime_type = mime_types.get(ext, "application/octet-stream")

    # Ensure vault folders exist and upload file
    try:
        await ensure_vault_folders(storage, user.provider)

        # Upload file to user's vault
        storage_path = f"{VAULT_FOLDER}/{safe_filename}"
        await storage.upload_file(
            file_content=content,
            destination_path=VAULT_FOLDER,
            filename=safe_filename,
            mime_type=mime_type,
        )
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "access" in error_msg.lower():
            raise HTTPException(status_code=401, detail=f"Storage authentication failed: {error_msg}")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise HTTPException(status_code=403, detail=f"Storage access denied: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"Storage error: {error_msg}")

    # Create certificate
    certificate_id = f"cert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{document_id[:8]}"
    certificate = {
        "certificate_id": certificate_id,
        "document_id": document_id,
        "sha256": sha256_hash,
        "original_filename": filename,
        "file_size": file_size,
        "mime_type": mime_type,
        "document_type": document_type,
        "description": description,
        "tags": tags.split(",") if tags else [],
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4()),
        "storage_path": storage_path,
        "storage_provider": user.provider,
        "user_id": user.user_id,
        "version": "5.0",
        "platform": "Semptify FastAPI Cloud Storage",
        "source": "copy-from-sync",
        "source_path": sync_path,
    }

    # Upload certificate to user's storage
    cert_content = json.dumps(certificate, indent=2).encode("utf-8")
    try:
        await storage.upload_file(
            file_content=cert_content,
            destination_path=CERTS_FOLDER,
            filename=f"{certificate_id}.json",
            mime_type="application/json",
        )
    except Exception:
        pass  # Certificate upload failed but file was uploaded

    function_token = issue_function_access_token(
        user.user_id,
        context={
            "provider": user.provider,
            "reason": "vault_copy_from_sync",
            "scopes": ["overlay:read", "overlay:write"],
            "document_ids": [document_id],
        },
    )

    return DocumentResponse(
        id=document_id,
        filename=safe_filename,
        original_filename=filename,
        file_size=file_size,
        mime_type=mime_type,
        sha256_hash=sha256_hash,
        certificate_id=certificate_id,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        document_type=document_type,
        storage_provider=user.provider,
        storage_path=storage_path,
        function_token=function_token["token"],
        function_token_expires_at=function_token["expires_at"],
        function_token_reverify_in_seconds=function_token["reverify_in_seconds"],
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    document_type: Optional[str] = None,
    access_token: str = None,
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    List all documents in the user's cloud storage vault.
    
    Reads certificates from .semptify/vault/certificates/ in user's storage.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    documents = []

    # List certificate files from user's storage
    try:
        cert_files = await storage.list_files(CERTS_FOLDER)
    except Exception:
        # Folder might not exist yet
        cert_files = []

    for cert_file in cert_files:
        if not cert_file.name.endswith(".json"):
            continue

        try:
            cert_content = await storage.download_file(f"{CERTS_FOLDER}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))

            # Filter by type if specified
            if document_type and cert.get("document_type") != document_type:
                continue

            documents.append(DocumentResponse(
                id=cert.get("document_id", ""),
                filename=f"{cert.get('document_id', '')}.{cert.get('original_filename', '').rsplit('.', 1)[-1]}",
                original_filename=cert.get("original_filename", ""),
                file_size=cert.get("file_size", 0),
                mime_type=cert.get("mime_type", "application/octet-stream"),
                sha256_hash=cert.get("sha256", ""),
                certificate_id=cert.get("certificate_id", ""),
                uploaded_at=cert.get("certified_at", ""),
                document_type=cert.get("document_type"),
                storage_provider=cert.get("storage_provider", user.provider),
                storage_path=cert.get("storage_path", ""),
            ))
        except Exception:
            continue

    # Sort by upload date, newest first
    documents.sort(key=lambda d: d.uploaded_at, reverse=True)

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
        storage_provider=user.provider,
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    access_token: str = None,
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    Download a document from the user's cloud storage vault.
    
    Returns the file content and original filename.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Find certificate to get file info
    cert_files = await storage.list_files(CERTS_FOLDER)
    target_cert = None

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{CERTS_FOLDER}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))
            if cert.get("document_id") == document_id:
                target_cert = cert
                break

    if not target_cert:
        raise HTTPException(status_code=404, detail="Document not found")

    # Download file from storage
    storage_path = target_cert.get("storage_path", "")
    if not storage_path:
        raise HTTPException(status_code=404, detail="Document path not found")

    file_content = await storage.download_file(storage_path)

    from fastapi.responses import Response
    return Response(
        content=file_content,
        media_type=target_cert.get("mime_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{target_cert.get("original_filename", "document")}"'
        },
    )


@router.get("/{document_id}/certificate", response_model=CertificateResponse)
async def get_certificate(
    document_id: str,
    access_token: str = None,
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    Get the certification details for a document.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Find certificate
    cert_files = await storage.list_files(CERTS_FOLDER)

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{CERTS_FOLDER}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))
            if cert.get("document_id") == document_id:
                return CertificateResponse(
                    document_id=cert.get("document_id", document_id),
                    sha256_hash=cert.get("sha256", ""),
                    certified_at=cert.get("certified_at", ""),
                    original_filename=cert.get("original_filename", ""),
                    file_size=cert.get("file_size", 0),
                    request_id=cert.get("request_id", ""),
                    storage_provider=cert.get("storage_provider", user.provider),
                )

    raise HTTPException(status_code=404, detail="Certificate not found")


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    access_token: str = None,
    user: StorageUser = Depends(require_user),
    settings: Settings = Depends(get_settings),
):
    """
    Delete a document from the user's cloud storage vault.
    Note: Certificates are kept for audit trail.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    try:
        storage = get_provider(user.provider, access_token=access_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Find certificate to get file path
    cert_files = await storage.list_files(CERTS_FOLDER)

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{CERTS_FOLDER}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))
            if cert.get("document_id") == document_id:
                storage_path = cert.get("storage_path", "")
                if storage_path:
                    await storage.delete_file(storage_path)
                    return

    raise HTTPException(status_code=404, detail="Document not found")


# =============================================================================
# Vault Service Endpoints - For modules to access documents
# =============================================================================

class VaultDocumentSummary(BaseModel):
    """Summary of a vault document."""
    vault_id: str
    filename: str
    document_type: Optional[str] = None
    file_size: int
    mime_type: str
    uploaded_at: str
    processed: bool = False
    source_module: str = "direct"
    in_vault: bool = True


class VaultListResponse(BaseModel):
    """List of vault documents."""
    documents: List[VaultDocumentSummary]
    total: int


@router.get("/all", response_model=VaultListResponse)
async def list_all_vault_documents(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    user: StorageUser = Depends(require_user),
):
    """
    List ALL documents in user's vault.
    
    This endpoint is for modules to discover available documents.
    Documents can be accessed by their vault_id.
    """
    if not HAS_VAULT_SERVICE:
        return VaultListResponse(documents=[], total=0)
    
    vault_service = get_vault_service()
    docs = vault_service.get_user_documents(user.user_id, document_type)
    
    summaries = [
        VaultDocumentSummary(
            vault_id=doc.vault_id,
            filename=doc.filename,
            document_type=doc.document_type,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            uploaded_at=doc.uploaded_at,
            processed=doc.processed,
            source_module=doc.source_module,
            in_vault=True,
        )
        for doc in docs
    ]
    
    return VaultListResponse(documents=summaries, total=len(summaries))


@router.get("/document/{vault_id}")
async def get_vault_document_metadata(
    vault_id: str,
    user: StorageUser = Depends(require_user),
):
    """
    Get metadata for a vault document by vault_id.
    
    Modules use this to get document details before processing.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    vault_service = get_vault_service()
    doc = vault_service.get_document(vault_id)
    
    if not doc or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc.to_dict()


@router.get("/document/{vault_id}/content")
async def get_vault_document_content(
    vault_id: str,
    access_token: Optional[str] = Query(None, description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
):
    """
    Get document content from vault.
    
    Modules call this to read document bytes for processing.
    Returns raw file content.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    vault_service = get_vault_service()
    doc = vault_service.get_document(vault_id)
    
    if not doc or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    content = await vault_service.get_document_content(vault_id, access_token)
    
    if not content:
        raise HTTPException(status_code=404, detail="Document content not available")
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={doc.filename}",
            "X-Vault-ID": vault_id,
        }
    )


@router.post("/document/{vault_id}/mark-processed")
async def mark_vault_document_processed(
    vault_id: str,
    extracted_data: Optional[dict] = None,
    document_type: Optional[str] = None,
    user: StorageUser = Depends(require_user),
):
    """
    Mark a vault document as processed by a module.
    
    Modules call this after processing to update vault metadata.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    vault_service = get_vault_service()
    doc = vault_service.get_document(vault_id)
    
    if not doc or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    vault_service.mark_processed(vault_id, extracted_data)
    
    if document_type:
        vault_service.update_document_type(vault_id, document_type)
    
    return {"success": True, "vault_id": vault_id, "processed": True}

# ============================================================================
# Persistent Vault Sidebar Endpoints
# ============================================================================

@router.get("/sidebar/files")
async def get_sidebar_files(
    user: StorageUser = Depends(require_user),
):
    """Get files for vault sidebar component"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    vault_service = get_vault_service()
    documents = vault_service.get_user_documents(user.user_id)
    
    # Convert to sidebar format
    files = []
    for doc in documents:
        files.append({
            "id": doc.vault_id,
            "name": doc.filename,
            "size": doc.size,
            "type": doc.mime_type,
            "category": _get_file_category(doc.filename),
            "uploaded_at": doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat(),
            "provider": doc.provider,
            "user_id": doc.user_id,
            "path": doc.vault_path,
            "tags": doc.tags or [],
            "metadata": {
                "source": "vault_upload",
                "original_filename": doc.filename,
                "upload_timestamp": doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat()
            }
        })
    
    return JSONResponse({
        "success": True,
        "message": f"Retrieved {len(files)} files for sidebar",
        "files": files
    })

@router.post("/sidebar/upload")
async def sidebar_upload(
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    user: StorageUser = Depends(require_user),
):
    """Handle upload from vault sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    try:
        # Parse metadata
        metadata_dict = json.loads(metadata)
        source = metadata_dict.get('source', 'vault_sidebar')
        
        # Process uploaded files
        uploaded_files = []
        upload_errors = []
        
        for i, uploaded_file in enumerate(files):
            try:
                # Read file content
                file_content = await uploaded_file.read()
                
                # Validate file
                from app.core.file_validator import validate_upload_file
                validation_result = validate_upload_file(file_content, uploaded_file.filename, uploaded_file.size)
                
                if not validation_result.is_valid:
                    # Log validation failure
                    from app.core.audit_logger import log_security_event
                    log_security_event(
                        user_id=user.user_id,
                        event_type="file_validation_failure",
                        details={
                            "filename": uploaded_file.filename,
                            "validation_error": validation_result.error_message,
                            "security_risk": validation_result.security_risk
                        },
                        ip_address=request.client.host if hasattr(request, 'client') else "unknown",
                        user_agent=request.headers.get("user-agent", "unknown")
                    )
                    
                    upload_errors.append({
                        "filename": uploaded_file.filename,
                        "error": validation_result.error_message,
                        "security_risk": validation_result.security_risk,
                        "recommended_action": validation_result.recommended_action
                    })
                    continue
                
                # Create vault document
                vault_id = f"vault_{datetime.utcnow().timestamp()}_{i}"
                
                # Store via vault service
                vault_service = get_vault_service()
                doc = VaultDocument(
                    vault_id=vault_id,
                    filename=uploaded_file.filename,
                    size=uploaded_file.size,
                    mime_type=validation_result.mime_type or uploaded_file.content_type or 'application/octet-stream',
                    user_id=user.user_id,
                    provider=vault_service.get_user_provider(user.user_id),
                    vault_path=f"/vault/{uploaded_file.filename}",
                    tags=[],
                    created_at=datetime.utcnow()
                )
                
                # Store document
                vault_service.store_document(doc, file_content)
                
                # Log successful upload
                from app.core.audit_logger import log_document_upload
                log_document_upload(
                    user_id=user.user_id,
                    document_id=vault_id,
                    filename=uploaded_file.filename,
                    file_size=uploaded_file.size,
                    file_type=validation_result.file_type,
                    ip_address=request.client.host if hasattr(request, 'client') else "unknown",
                    user_agent=request.headers.get("user-agent", "unknown")
                )
                
                uploaded_files.append({
                    "id": vault_id,
                    "name": uploaded_file.filename,
                    "size": uploaded_file.size,
                    "type": doc.mime_type,
                    "category": _get_file_category(uploaded_file.filename),
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "provider": vault_service.get_user_provider(user.user_id),
                    "user_id": user.user_id,
                    "path": f"/vault/{uploaded_file.filename}",
                    "tags": [],
                    "metadata": {
                        "source": source,
                        "original_filename": uploaded_file.filename,
                        "upload_timestamp": datetime.utcnow().isoformat()
                    }
                })
                
                logger.info(f"Vault sidebar upload: {vault_id} for user {user.user_id}")
                
            except Exception as e:
                error_msg = f"Failed to process {uploaded_file.filename}: {str(e)}"
                upload_errors.append(error_msg)
                logger.error(error_msg)
        
        # Return response
        response_data = {
            "success": True,
            "message": f"Uploaded {len(uploaded_files)} files to vault",
            "files": uploaded_files
        }
        
        if upload_errors:
            response_data["errors"] = upload_errors
            response_data["message"] = f"Uploaded {len(uploaded_files)} files with {len(upload_errors)} errors"
        
        return JSONResponse(response_data)
        
    except json.JSONDecodeError:
        return JSONResponse({
            "success": False,
            "message": "Invalid metadata format",
            "files": []
        })
    except Exception as e:
        logger.error(f"Error in vault sidebar upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload to vault")

@router.get("/sidebar/stats")
async def get_sidebar_stats(
    user: StorageUser = Depends(require_user),
):
    """Get vault statistics for sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    vault_service = get_vault_service()
    documents = vault_service.get_user_documents(user.user_id)
    
    total_files = len(documents)
    total_size = sum(doc.size for doc in documents)
    
    # Count by category
    categories = {
        'all': total_files,
        'documents': len([doc for doc in documents if _get_file_category(doc.filename) == 'documents']),
        'images': len([doc for doc in documents if _get_file_category(doc.filename) == 'images']),
        'audio': len([doc for doc in documents if _get_file_category(doc.filename) == 'audio']),
        'video': len([doc for doc in documents if _get_file_category(doc.filename) == 'video'])
    }
    
    # Calculate storage usage (assuming 1GB limit)
    storage_limit = 1024 * 1024 * 1024  # 1GB in bytes
    storage_used = (total_size / storage_limit) * 100
    
    return JSONResponse({
        "success": True,
        "message": "Vault statistics retrieved",
        "stats": {
            "total_files": total_files,
            "total_size": total_size,
            "categories": categories,
            "storage_used": storage_used,
            "storage_limit": storage_limit
        }
    })

@router.get("/sidebar/search")
async def sidebar_search(
    query: str,
    user: StorageUser = Depends(require_user),
):
    """Search vault files for sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")
    
    if not query.strip():
        return JSONResponse({
            "success": False,
            "message": "Search query required",
            "files": []
        })
    
    vault_service = get_vault_service()
    documents = vault_service.get_user_documents(user.user_id)
    query_lower = query.lower()
    
    filtered_docs = [
        doc for doc in documents 
        if query_lower in doc.filename.lower() or 
           any(query_lower in tag.lower() for tag in (doc.tags or []))
    ]
    
    # Convert to sidebar format
    filtered_files = []
    for doc in filtered_docs:
        filtered_files.append({
            "id": doc.vault_id,
            "name": doc.filename,
            "size": doc.size,
            "type": doc.mime_type,
            "category": _get_file_category(doc.filename),
            "uploaded_at": doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat(),
            "provider": doc.provider,
            "user_id": doc.user_id,
            "path": doc.vault_path,
            "tags": doc.tags or [],
            "metadata": {
                "source": "vault_upload",
                "original_filename": doc.filename,
                "upload_timestamp": doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat()
            }
        })
    
    return JSONResponse({
        "success": True,
        "message": f"Found {len(filtered_files)} files matching '{query}'",
        "files": filtered_files
    })

def _get_file_category(filename: str) -> str:
    """Determine file category from filename"""
    from pathlib import Path
    extension = Path(filename).suffix.lower()
    
    document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'}
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac'}
    video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv'}
    
    if extension in document_extensions:
        return 'documents'
    elif extension in image_extensions:
        return 'images'
    elif extension in audio_extensions:
        return 'audio'
    elif extension in video_extensions:
        return 'video'
    else:
        return 'other'
