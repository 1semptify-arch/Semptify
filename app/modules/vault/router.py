"""
Document Vault Router (Cloud Storage Version)
Secure document storage, retrieval, and certification.

=============================================================================
SSOT — VAULT RESPONSIBILITIES
=============================================================================
The vault STORES and SERVES documents. It does NOT intake them from the UI.

UI uploads:   POST /api/intake/upload/auto   (intake.py is the ONE door in)
Vault reads:  GET  /api/vault/documents      (list tenant's stored documents)
Vault fetch:  GET  /api/vault/download/{id}  (retrieve a specific document)

The POST /upload endpoint in this router is for INTERNAL/SERVICE use only.
It is called by VaultUploadService — never directly from the tenant UI.
If you are building a UI upload form, point it at /api/intake/upload/auto.

Storage:
- Documents stored in USER's cloud storage (Google Drive, Dropbox, OneDrive)
- Certificates stored alongside documents in .semptify/vault/certificates/
- User must be authenticated via storage OAuth before any vault operation
=============================================================================
"""
# Migrated from app/routers/vault.py into the vault SDK module.
# All imports remain absolute since vault is a CORE module.

import hashlib
import json
import logging
from datetime import datetime
from importlib.util import find_spec

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import require_capability
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.id_gen import make_id
from app.core.request_utils import raise_for_storage_error
from app.core.security import (
    StorageUser,
    issue_function_access_token,
    rate_limit_dependency,
    yellow_access,
)
from app.core.utc import utc_now
from app.core.vault_paths import (
    CANONICAL_VAULT_FOLDERS,
    VAULT_CERTIFICATES,
    VAULT_DOCUMENTS,
)
from app.models.models import Incident, VaultItem
from app.services.storage import get_provider

# Import vault upload service - central document storage
try:
    from app.services.vault_upload_service import get_vault_service

    HAS_VAULT_SERVICE = True
except ImportError:
    HAS_VAULT_SERVICE = False

# Import preview generation
HAS_PREVIEW_GENERATOR = (
    find_spec("app.core.job_processor") is not None and find_spec("app.core.preview_generator") is not None
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_capability("app.modules.vault.router"))])


# =============================================================================
# Schemas
# =============================================================================


class DocumentMetadata(BaseModel):
    """Document metadata for upload."""

    document_type: str | None = Field(None, description="Type: lease, notice, photo, receipt, other")
    description: str | None = Field(None, description="Description of the document")
    tags: str | None = Field(None, description="Comma-separated tags")
    event_date: str | None = Field(None, description="Date related to this document (ISO format)")


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
    document_type: str | None = None
    storage_provider: str
    storage_path: str
    function_token: str | None = None
    function_token_expires_at: str | None = None
    function_token_reverify_in_seconds: int | None = None


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


# =============================================================================
# Helper Functions
# =============================================================================


def compute_sha256(file_content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def is_allowed_extension(filename: str, settings: Settings) -> bool:
    """Check if file extension is allowed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in {e.strip().lower() for e in settings.allowed_extensions.split(",")}


async def ensure_vault_folders(storage, provider_name: str) -> None:
    """Ensure the full canonical vault folder structure exists in user's storage."""
    for folder_path in CANONICAL_VAULT_FOLDERS:
        await storage.create_folder(folder_path)


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
    document_type: str | None = Form(None),
    description: str | None = Form(None),
    tags: str | None = Form(None),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(yellow_access),
    settings: Settings = Depends(get_settings),
):
    """
    Upload a document to the user's cloud storage vault.

    SSOT: All uploads go through VaultUploadService — one pipeline, one index,
    one certificate, one registry entry, one event bus. Never call storage
    directly for document uploads.

    Requires:
    - User authenticated via storage OAuth
    - access_token: Current access token for user's storage provider
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=503, detail="Vault service unavailable")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    if not is_allowed_extension(file.filename, settings):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {settings.allowed_extensions}",
        )

    content = await file.read()
    file_size = len(content)

    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.max_upload_size_mb}MB",
        )

    # Resolve real access token
    real_token = access_token
    if not real_token or real_token == "auto":
        real_token = getattr(user, "access_token", None)
    if not real_token or real_token in ("auto", "no-token"):
        try:
            from app.core.oauth_token_manager import get_valid_token_for_user

            real_token = get_valid_token_for_user(user.user_id) or real_token
        except ImportError:
            # Token manager unavailable, will use provided token
            pass
    if not real_token or real_token in ("auto", "no-token"):
        raise HTTPException(
            status_code=401,
            detail="Storage session expired. Please reconnect your storage.",
        )

    provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)

    try:
        vault_service = get_vault_service()
        vault_doc = await vault_service.upload(
            user_id=user.user_id,
            filename=file.filename,
            content=content,
            mime_type=file.content_type or "application/octet-stream",
            document_type=document_type,
            description=description,
            tags=tags.split(",") if tags else [],
            source_module="vault_router",
            access_token=real_token,
            storage_provider=provider_name,
        )
    except Exception as e:
        raise_for_storage_error(e, default_detail="Upload failed")

    function_token = issue_function_access_token(
        user.user_id,
        context={
            "provider": user.provider,
            "reason": "vault_upload",
            "scopes": ["overlay:read", "overlay:write"],
            "document_ids": [vault_doc.vault_id],
        },
    )

    return DocumentResponse(
        id=vault_doc.vault_id,
        filename=vault_doc.safe_filename or vault_doc.vault_id,
        original_filename=vault_doc.filename,
        file_size=vault_doc.file_size,
        mime_type=vault_doc.mime_type,
        sha256_hash=vault_doc.sha256_hash,
        certificate_id=vault_doc.certificate_id or "",
        uploaded_at=(
            vault_doc.uploaded_at.isoformat() if hasattr(vault_doc.uploaded_at, "isoformat") else vault_doc.uploaded_at
        )
        if vault_doc.uploaded_at
        else utc_now().isoformat(),
        document_type=vault_doc.document_type,
        storage_provider=provider_name,
        storage_path=vault_doc.storage_path or "",
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
    document_type: str | None = Form(None),
    description: str | None = Form(None),
    tags: str | None = Form(None),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(yellow_access),
    settings: Settings = Depends(get_settings),
):
    """
    Copy a document from sync storage (Semptify5.0/Vault/documents/) to vault.

    This is used when the original File object is no longer available (e.g., after page refresh)
    but the document was already uploaded to cloud storage via the sync endpoint.
    """
    # Resolve real access token (form field may be "auto" placeholder from JS)
    real_token = access_token
    if not real_token or real_token == "auto":
        real_token = getattr(user, "access_token", None)
    if not real_token or real_token in ("auto", "no-token"):
        try:
            from app.core.oauth_token_manager import get_valid_token_for_user

            real_token = get_valid_token_for_user(user.user_id) or real_token
        except ImportError:
            # Token manager unavailable, will use provided token
            pass
    if not real_token or real_token in ("auto", "no-token"):
        raise HTTPException(
            status_code=401,
            detail="Storage session expired. Please reconnect your storage.",
        )

    # Get storage provider for user
    try:
        storage = get_provider(user.provider, access_token=real_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Try to download from vault documents folder
    sync_path = f"{VAULT_DOCUMENTS}/{filename}"

    try:
        content = await storage.download_file(sync_path)
    except Exception:
        # Try alternative path by file_id
        try:
            # Try provider file id (id:<file_id>) first, then path fallback
            try:
                content = await storage.download_file(f"id:{file_id}")
            except Exception:
                content = await storage.download_file(f"{VAULT_DOCUMENTS}/{file_id}")
        except Exception:
            raise HTTPException(
                status_code=404, detail=f"Could not find document in cloud storage. Path tried: {sync_path}"
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
    document_id = make_id("doc")
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
        storage_path = f"{VAULT_DOCUMENTS}/{safe_filename}"
        await storage.upload_file(
            file_content=content,
            destination_path=VAULT_DOCUMENTS,
            filename=safe_filename,
            mime_type=mime_type,
        )
    except Exception as e:
        raise_for_storage_error(e)

    # Create certificate
    certificate_id = make_id("cert")
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
        "certified_at": utc_now().isoformat(),
        "request_id": make_id("req"),
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
            destination_path=VAULT_CERTIFICATES,
            filename=f"{certificate_id}.json",
            mime_type="application/json",
        )
    except Exception as e:
        logger.warning(f"Certificate upload failed for {document_id}: {e}")

    # Create overlay for safe processing (original never touched)
    overlay_id = None
    try:
        from app.core.overlay_types import OverlayType
        from app.models.unified_overlay_models import CreateOverlayRequest
        from app.services.unified_overlay_manager import UnifiedOverlayManager

        overlay_mgr = UnifiedOverlayManager(storage, user.user_id)
        overlay_resp = await overlay_mgr.create_overlay(
            CreateOverlayRequest(
                overlay_type=OverlayType.VAULT_UPLOAD_MANIFEST,
                document_id=document_id,
                vault_path=storage_path,
                payload={
                    "original_filename": filename,
                    "mime_type": mime_type,
                    "file_size_bytes": file_size,
                    "content_hash": sha256_hash,
                    "storage_provider": user.provider,
                    "source_path": sync_path,
                },
            )
        )
        if overlay_resp.success:
            overlay_id = overlay_resp.overlay_id
        certificate["overlay_id"] = overlay_id

        try:
            from app.services.timeline_extraction import extract_timeline_from_upload

            provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
            timeline_events = await extract_timeline_from_upload(
                document_id=document_id,
                overlay_id=overlay_id,
                provider=provider_name,
                access_token=real_token,  # Use resolved token
            )
            certificate["timeline_events_extracted"] = len(timeline_events)
        except Exception as e:
            logger.warning(f"Timeline extraction failed for {document_id} (copy-from-sync): {e}")
            certificate["timeline_events_extracted"] = 0

    except Exception as e:
        logger.warning(f"Overlay creation failed for {document_id} (copy-from-sync): {e}")

    # Trigger mesh workflow based on document type (mirrors main upload path)
    try:
        import asyncio

        from app.core.positronic_mesh import WorkflowType, positronic_mesh

        workflow_type = None
        trigger_context = {
            "document_id": document_id,
            "certificate_id": certificate_id,
            "filename": filename,
            "mime_type": mime_type,
            "document_type": document_type,
            "overlay_id": overlay_id,
            "timeline_events_count": certificate.get("timeline_events_extracted", 0),
            "source": "copy-from-sync",
        }

        if document_type in ("eviction_notice", "summons", "court_order"):
            workflow_type = WorkflowType.EVICTION_DEFENSE
        elif document_type in ("lease", "rental_agreement"):
            workflow_type = WorkflowType.LEASE_ANALYSIS
        elif document_type in ("hearing_notice", "motion", "evidence_list"):
            workflow_type = WorkflowType.COURT_PREP

        if not workflow_type and filename:
            fname_lower = filename.lower()
            if any(word in fname_lower for word in ("evict", "notice", "summons", "quit")):
                workflow_type = WorkflowType.EVICTION_DEFENSE
            elif any(word in fname_lower for word in ("lease", "rental", "agreement")):
                workflow_type = WorkflowType.LEASE_ANALYSIS
            elif any(word in fname_lower for word in ("hearing", "court", "motion")):
                workflow_type = WorkflowType.COURT_PREP

        if workflow_type:
            asyncio.create_task(
                positronic_mesh.start_workflow(
                    workflow_type=workflow_type,
                    user_id=user.user_id,
                    trigger="copy_from_sync",
                    initial_context=trigger_context,
                )
            )
            logger.info(f"Triggered {workflow_type.value} workflow for {document_id} (copy-from-sync)")
            certificate["mesh_workflow_triggered"] = workflow_type.value
        else:
            certificate["mesh_workflow_triggered"] = None

    except Exception as e:
        logger.warning(f"Mesh workflow trigger failed for {document_id} (copy-from-sync): {e}")
        certificate["mesh_workflow_triggered"] = "error"

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
        uploaded_at=utc_now().isoformat(),
        document_type=document_type,
        storage_provider=user.provider,
        storage_path=storage_path,
        function_token=function_token["token"],
        function_token_expires_at=function_token["expires_at"],
        function_token_reverify_in_seconds=function_token["reverify_in_seconds"],
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    document_type: str | None = None,
    access_token: str = None,
    user: StorageUser = Depends(yellow_access),
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
        cert_files = await storage.list_files(VAULT_CERTIFICATES)
    except Exception:
        # Folder might not exist yet
        cert_files = []

    for cert_file in cert_files:
        if not cert_file.name.endswith(".json"):
            continue

        try:
            cert_content = await storage.download_file(f"{VAULT_CERTIFICATES}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))

            # Filter by type if specified
            if document_type and cert.get("document_type") != document_type:
                continue

            documents.append(
                DocumentResponse(
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
                )
            )
        except Exception as exc:
            logger.debug("Skipping invalid vault certificate: %s", exc)
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
    user: StorageUser = Depends(yellow_access),
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
    cert_files = await storage.list_files(VAULT_CERTIFICATES)
    target_cert = None

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{VAULT_CERTIFICATES}/{cert_file.name}")
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

    # Prefer provider-specific file id if present in certificate
    provider_file_id = target_cert.get("provider_file_id")
    file_content = None
    if provider_file_id:
        try:
            file_content = await storage.download_file(f"id:{provider_file_id}")
        except Exception:
            file_content = None

    if not file_content:
        file_content = await storage.download_file(storage_path)

    from fastapi.responses import Response

    return Response(
        content=file_content,
        media_type=target_cert.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{target_cert.get("original_filename", "document")}"'},
    )


@router.get("/{document_id}/certificate", response_model=CertificateResponse)
async def get_certificate(
    document_id: str,
    access_token: str = None,
    user: StorageUser = Depends(yellow_access),
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
    cert_files = await storage.list_files(VAULT_CERTIFICATES)

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{VAULT_CERTIFICATES}/{cert_file.name}")
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
    user: StorageUser = Depends(yellow_access),
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
    cert_files = await storage.list_files(VAULT_CERTIFICATES)

    for cert_file in cert_files:
        if document_id[:8] in cert_file.name:
            cert_content = await storage.download_file(f"{VAULT_CERTIFICATES}/{cert_file.name}")
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
    document_type: str | None = None
    file_size: int
    mime_type: str
    uploaded_at: str
    processed: bool = False
    source_module: str = "direct"
    in_vault: bool = True


class VaultListResponse(BaseModel):
    """List of vault documents."""

    documents: list[VaultDocumentSummary]
    total: int


@router.get("/all", response_model=VaultListResponse)
async def list_all_vault_documents(
    document_type: str | None = Query(None, description="Filter by document type"),
    user: StorageUser = Depends(yellow_access),
):
    """
    List ALL documents in user's vault.

    This endpoint is for modules to discover available documents.
    Documents can be accessed by their vault_id.
    """
    if not HAS_VAULT_SERVICE:
        return VaultListResponse(documents=[], total=0)

    vault_service = get_vault_service()
    docs = await vault_service.get_user_documents(user.user_id, document_type)

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
    user: StorageUser = Depends(yellow_access),
):
    """
    Get metadata for a vault document by vault_id.

    Modules use this to get document details before processing.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    vault_service = get_vault_service()
    doc = await vault_service.get_document(vault_id)

    if not doc or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc.to_dict()


@router.get("/document/{vault_id}/content")
async def get_vault_document_content(
    vault_id: str,
    access_token: str | None = Query(None, description="Storage provider access token"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Get document content from vault.

    Modules call this to read document bytes for processing.
    Returns raw file content.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    vault_service = get_vault_service()
    doc = await vault_service.get_document(vault_id)

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
        },
    )


@router.post("/document/{vault_id}/mark-processed")
async def mark_vault_document_processed(
    vault_id: str,
    extracted_data: dict | None = None,
    document_type: str | None = None,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(yellow_access),
):
    """
    Mark a vault document as processed by a module.

    Modules call this after processing to update vault metadata.
    Creates unified overlay records in user's cloud storage.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    vault_service = get_vault_service()
    doc = await vault_service.get_document(vault_id)

    if not doc or doc.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_provider = user.provider if hasattr(user, "provider") else "google_drive"

    await vault_service.mark_processed(
        vault_id,
        extracted_data,
        access_token=access_token,
        storage_provider=storage_provider,
    )

    if document_type:
        await vault_service.update_document_type(
            vault_id,
            document_type,
            access_token=access_token,
            storage_provider=storage_provider,
        )

    return {"success": True, "vault_id": vault_id, "processed": True}


# ============================================================================
# Persistent Vault Sidebar Endpoints
# ============================================================================


@router.get("/sidebar/files")
async def get_sidebar_files(
    user: StorageUser = Depends(yellow_access),
):
    """Get files for vault sidebar component"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    vault_service = get_vault_service()
    documents = await vault_service.get_user_documents(user.user_id)

    # Convert to sidebar format
    files = []
    for doc in documents:
        uploaded_at = doc.uploaded_at if isinstance(doc.uploaded_at, str) else doc.uploaded_at.isoformat()
        files.append(
            {
                "id": doc.vault_id,
                "name": doc.filename,
                "size": doc.file_size,
                "type": doc.mime_type,
                "category": _get_file_category(doc.filename),
                "uploaded_at": uploaded_at,
                "provider": doc.storage_provider,
                "user_id": doc.user_id,
                "path": doc.storage_path,
                "tags": doc.tags or [],
                "metadata": {
                    "source": "vault_upload",
                    "original_filename": doc.filename,
                    "upload_timestamp": uploaded_at,
                },
            }
        )

    return JSONResponse({"success": True, "message": f"Retrieved {len(files)} files for sidebar", "files": files})


@router.post("/sidebar/upload")
async def sidebar_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    metadata: str = Form(...),
    user: StorageUser = Depends(yellow_access),
):
    """Handle upload from vault sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    try:
        # Parse metadata
        metadata_dict = json.loads(metadata)
        source = metadata_dict.get("source", "vault_sidebar")

        # Process uploaded files
        uploaded_files = []
        upload_errors = []

        for _i, uploaded_file in enumerate(files):
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
                            "security_risk": validation_result.security_risk,
                        },
                        ip_address=request.client.host if hasattr(request, "client") else "unknown",
                        user_agent=request.headers.get("user-agent", "unknown"),
                    )

                    upload_errors.append(
                        {
                            "filename": uploaded_file.filename,
                            "error": validation_result.error_message,
                            "security_risk": validation_result.security_risk,
                            "recommended_action": validation_result.recommended_action,
                        }
                    )
                    continue

                # Route through certified upload path so SHA-256, cert,
                # overlay, timeline extraction, and mesh workflow all fire.
                # Using already-read file_content (NOT re-reading from uploaded_file)
                access_token_val = metadata_dict.get("access_token") or getattr(user, "access_token", None)

                # Resolve real access token with fallback chain
                real_token = access_token_val
                if not real_token or real_token == "auto":
                    real_token = getattr(user, "access_token", None)
                if not real_token or real_token in ("auto", "no-token"):
                    try:
                        from app.core.oauth_token_manager import get_valid_token_for_user

                        real_token = get_valid_token_for_user(user.user_id) or real_token
                    except ImportError:
                        pass
                if not real_token or real_token in ("auto", "no-token"):
                    raise HTTPException(
                        status_code=401,
                        detail="Storage session expired. Please reconnect your storage.",
                    )

                # Generate document ID and hash from already-read content
                document_id = make_id("doc")
                sha256_hash = compute_sha256(file_content)
                ext = uploaded_file.filename.rsplit(".", 1)[-1].lower() if "." in uploaded_file.filename else "bin"
                safe_filename = f"{document_id}.{ext}"

                # Get storage provider
                try:
                    storage = get_provider(user.provider, access_token=real_token)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

                # Ensure vault folders and upload file
                try:
                    await ensure_vault_folders(storage, user.provider)
                    storage_path = f"{VAULT_DOCUMENTS}/{safe_filename}"
                    await storage.upload_file(
                        file_content=file_content,
                        destination_path=VAULT_DOCUMENTS,
                        filename=safe_filename,
                        mime_type=uploaded_file.content_type or "application/octet-stream",
                    )
                except Exception as e:
                    raise_for_storage_error(e)

                # Create and upload certificate
                certificate_id = make_id("cert")
                certificate = {
                    "certificate_id": certificate_id,
                    "document_id": document_id,
                    "sha256": sha256_hash,
                    "original_filename": uploaded_file.filename,
                    "file_size": len(file_content),
                    "mime_type": uploaded_file.content_type or "application/octet-stream",
                    "document_type": metadata_dict.get("document_type"),
                    "description": metadata_dict.get("description"),
                    "tags": [],
                    "certified_at": utc_now().isoformat(),
                    "request_id": make_id("req"),
                    "storage_path": storage_path,
                    "storage_provider": user.provider,
                    "user_id": user.user_id,
                    "version": "5.0",
                    "platform": "Semptify FastAPI Cloud Storage",
                }

                cert_content = json.dumps(certificate, indent=2).encode("utf-8")
                try:
                    await storage.upload_file(
                        file_content=cert_content,
                        destination_path=VAULT_CERTIFICATES,
                        filename=f"{certificate_id}.json",
                        mime_type="application/json",
                    )
                except Exception as e:
                    logger.warning(f"Certificate upload failed for {document_id}: {e}")

                # Create overlay
                overlay_id = None
                try:
                    from app.core.overlay_types import OverlayType
                    from app.models.unified_overlay_models import CreateOverlayRequest
                    from app.services.unified_overlay_manager import UnifiedOverlayManager

                    overlay_mgr = UnifiedOverlayManager(storage, user.user_id)
                    overlay_resp = await overlay_mgr.create_overlay(
                        CreateOverlayRequest(
                            overlay_type=OverlayType.VAULT_UPLOAD_MANIFEST,
                            document_id=document_id,
                            vault_path=storage_path,
                            payload={
                                "original_filename": uploaded_file.filename,
                                "mime_type": uploaded_file.content_type or "application/octet-stream",
                                "file_size_bytes": len(file_content),
                                "content_hash": sha256_hash,
                                "storage_provider": user.provider,
                            },
                        )
                    )
                    if overlay_resp.success:
                        overlay_id = overlay_resp.overlay_id
                    certificate["overlay_id"] = overlay_id

                    # Timeline extraction using resolved real_token (NOT access_token_val)
                    try:
                        from app.services.timeline_extraction import extract_timeline_from_upload

                        provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
                        timeline_events = await extract_timeline_from_upload(
                            document_id=document_id,
                            overlay_id=overlay_id,
                            provider=provider_name,
                            access_token=real_token,
                        )
                        certificate["timeline_events_extracted"] = len(timeline_events)
                    except Exception:
                        certificate["timeline_events_extracted"] = 0
                except Exception as e:
                    logger.warning(f"Overlay creation failed for {document_id}: {e}")

                # Issue function token
                issue_function_access_token(
                    user.user_id,
                    context={
                        "provider": user.provider,
                        "reason": "vault_upload",
                        "scopes": ["overlay:read", "overlay:write"],
                        "document_ids": [document_id],
                    },
                )

                vault_id = document_id

                # Log successful upload
                from app.core.audit_logger import log_document_upload

                log_document_upload(
                    user_id=user.user_id,
                    document_id=vault_id,
                    filename=uploaded_file.filename,
                    file_size=len(file_content),
                    file_type=validation_result.file_type,
                    ip_address=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent", "unknown"),
                )

                # Build file entry from inline upload results
                uploaded_at = certificate["certified_at"]
                mime_type = uploaded_file.content_type or "application/octet-stream"

                uploaded_files.append(
                    {
                        "id": vault_id,
                        "name": uploaded_file.filename,
                        "size": len(file_content),
                        "type": mime_type,
                        "category": _get_file_category(uploaded_file.filename),
                        "uploaded_at": uploaded_at,
                        "certificate_id": certificate_id,
                        "sha256": sha256_hash,
                        "user_id": user.user_id,
                        "path": storage_path,
                        "tags": [],
                        "metadata": {
                            "source": source,
                            "original_filename": uploaded_file.filename,
                            "upload_timestamp": uploaded_at,
                        },
                    }
                )

                logger.info(f"Vault sidebar upload (certified): {vault_id} for user {user.user_id}")

            except Exception as e:
                import traceback

                error_detail = {
                    "filename": uploaded_file.filename,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()[:2000],  # Truncated for response size
                }
                upload_errors.append(error_detail)
                logger.error(f"Vault sidebar upload error for {uploaded_file.filename}: {error_detail}")

        # Return response
        response_data = {
            "success": True,
            "message": f"Uploaded {len(uploaded_files)} files to vault",
            "files": uploaded_files,
        }

        if upload_errors:
            response_data["errors"] = upload_errors
            response_data["message"] = f"Uploaded {len(uploaded_files)} files with {len(upload_errors)} errors"

            # Check for auth errors - return 401 for auto-redirect
            auth_error_types = {"token_expired", "storage_required", "authentication_required"}
            auth_errors = [e for e in upload_errors if e.get("error_type") in auth_error_types]
            if auth_errors:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": auth_errors[0].get("error_type"),
                        "message": auth_errors[0].get("error_message", "Storage session expired"),
                        "redirect_url": "/storage/reconnect?return_to=/vault",
                        "needs_reconnect": True,
                    },
                )

        return JSONResponse(response_data)

    except json.JSONDecodeError:
        return JSONResponse({"success": False, "message": "Invalid metadata format", "files": []})
    except Exception as e:
        import traceback

        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()[:3000],  # Truncated for proxy limits
            "endpoint": "sidebar_upload",
        }
        logger.error(f"Error in vault sidebar upload: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/sidebar/stats")
async def get_sidebar_stats(
    user: StorageUser = Depends(yellow_access),
):
    """Get vault statistics for sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    vault_service = get_vault_service()
    documents = await vault_service.get_user_documents(user.user_id)

    total_files = len(documents)
    total_size = sum(doc.file_size for doc in documents)

    # Count by category
    categories = {
        "all": total_files,
        "documents": len([doc for doc in documents if _get_file_category(doc.filename) == "documents"]),
        "images": len([doc for doc in documents if _get_file_category(doc.filename) == "images"]),
        "audio": len([doc for doc in documents if _get_file_category(doc.filename) == "audio"]),
        "video": len([doc for doc in documents if _get_file_category(doc.filename) == "video"]),
    }

    # Calculate storage usage (assuming 1GB limit)
    storage_limit = 1024 * 1024 * 1024  # 1GB in bytes
    storage_used = (total_size / storage_limit) * 100

    return JSONResponse(
        {
            "success": True,
            "message": "Vault statistics retrieved",
            "stats": {
                "total_files": total_files,
                "total_size": total_size,
                "categories": categories,
                "storage_used": storage_used,
                "storage_limit": storage_limit,
            },
        }
    )


@router.get("/sidebar/search")
async def sidebar_search(
    query: str,
    user: StorageUser = Depends(yellow_access),
):
    """Search vault files for sidebar"""
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=404, detail="Vault service not available")

    if not query.strip():
        return JSONResponse({"success": False, "message": "Search query required", "files": []})

    vault_service = get_vault_service()
    documents = await vault_service.get_user_documents(user.user_id)
    query_lower = query.lower()

    filtered_docs = [
        doc
        for doc in documents
        if query_lower in doc.filename.lower() or any(query_lower in tag.lower() for tag in (doc.tags or []))
    ]

    # Convert to sidebar format
    filtered_files = []
    for doc in filtered_docs:
        uploaded_at = doc.uploaded_at if isinstance(doc.uploaded_at, str) else doc.uploaded_at.isoformat()
        filtered_files.append(
            {
                "id": doc.vault_id,
                "name": doc.filename,
                "size": doc.file_size,
                "type": doc.mime_type,
                "category": _get_file_category(doc.filename),
                "uploaded_at": uploaded_at,
                "provider": doc.storage_provider,
                "user_id": doc.user_id,
                "path": doc.storage_path,
                "tags": doc.tags or [],
                "metadata": {
                    "source": "vault_upload",
                    "original_filename": doc.filename,
                    "upload_timestamp": uploaded_at,
                },
            }
        )

    return JSONResponse(
        {"success": True, "message": f"Found {len(filtered_files)} files matching '{query}'", "files": filtered_files}
    )


def _get_file_category(filename: str) -> str:
    """Determine file category from filename"""
    from pathlib import Path

    extension = Path(filename).suffix.lower()

    document_extensions = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"}
    audio_extensions = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
    video_extensions = {".mp4", ".avi", ".mov", ".wmv", ".flv"}

    if extension in document_extensions:
        return "documents"
    elif extension in image_extensions:
        return "images"
    elif extension in audio_extensions:
        return "audio"
    elif extension in video_extensions:
        return "video"
    else:
        return "other"


# =============================================================================
# Vault Setup Endpoints — REMOVED 2026-07-02
# =============================================================================
# /api/vault/status, /api/vault/init, /api/vault/verify used to be defined here,
# duplicating the canonical onboarding vault-setup flow. Verified via grep across
# all .html/.js files and tests that nothing ever called these three endpoints —
# every live caller uses /onboarding/api/vault/status, /init, /security, /verify
# (see app/modules/onboarding/router.py). Removed to enforce a single entry
# point into vault setup, per SSOT ("one way in").
#
# ensure_vault_folders() below is still used directly by document upload
# endpoints in this file as a defensive folder-existence check — that usage
# is unrelated to vault *setup* and was left in place.


# =============================================================================
# Incident Endpoints (migrated from vault_all_in_one.router)
# =============================================================================


class IncidentCreateRequest(BaseModel):
    """Request model for creating an incident."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    incident_type: str | None = Field(None, description="habitability, discrimination, eviction, etc.")
    severity: str | None = Field(None, description="critical, high, normal, low")
    incident_metadata: dict | None = None


class IncidentResponse(BaseModel):
    """Response model for an incident."""

    incident_id: int
    user_id: str
    title: str
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    incident_type: str | None = None
    severity: str | None = None
    incident_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    class Config:
        from_attributes = True


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    request: IncidentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(yellow_access),
):
    """Create a new incident/case for organizing related evidence."""
    incident = Incident(
        user_id=user.user_id,
        title=request.title,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        incident_type=request.incident_type,
        severity=request.severity,
        incident_metadata=request.incident_metadata,
        status="active",
    )

    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    return IncidentResponse.model_validate(incident)


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    status: str | None = Query(None, description="Filter by status"),
    incident_type: str | None = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(yellow_access),
):
    """List all incidents for the user."""
    query = select(Incident).where(Incident.user_id == user.user_id)

    if status:
        query = query.where(Incident.status == status)
    if incident_type:
        query = query.where(Incident.incident_type == incident_type)

    query = query.order_by(Incident.created_at.desc())

    result = await db.execute(query)
    incidents = result.scalars().all()

    response_incidents = []
    for incident in incidents:
        count_result = await db.execute(
            select(func.count()).select_from(VaultItem).where(VaultItem.related_incident_id == incident.incident_id)
        )
        item_count = count_result.scalar() or 0

        resp = IncidentResponse.model_validate(incident)
        resp.item_count = item_count
        response_incidents.append(resp)

    return response_incidents


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(yellow_access),
):
    """Get a single incident with item count."""
    result = await db.execute(
        select(Incident).where(
            Incident.incident_id == incident_id,
            Incident.user_id == user.user_id,
        )
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    count_result = await db.execute(
        select(func.count()).select_from(VaultItem).where(VaultItem.related_incident_id == incident_id)
    )
    item_count = count_result.scalar() or 0

    resp = IncidentResponse.model_validate(incident)
    resp.item_count = item_count
    return resp


@router.get("/incidents/{incident_id}/items", response_model=list[DocumentResponse])
async def get_incident_items(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(yellow_access),
):
    """Get all vault items linked to a specific incident."""
    result = await db.execute(
        select(Incident).where(
            Incident.incident_id == incident_id,
            Incident.user_id == user.user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    items_result = await db.execute(
        select(VaultItem).where(
            VaultItem.user_id == user.user_id,
            VaultItem.related_incident_id == incident_id,
        )
    )
    items = items_result.scalars().all()

    return [DocumentResponse.model_validate(item) for item in items]


# =============================================================================
# Export — "Export my case" (download all vault documents as a ZIP)
# =============================================================================


@router.get("/export")
async def export_vault_zip(
    user: StorageUser = Depends(yellow_access),
    settings: Settings = Depends(get_settings),
):
    """
    Export all vault documents as a single ZIP archive.

    Combines every document in the user's vault with a manifest.json
    listing metadata (filename, date, size, type, vault_id).
    Streams the ZIP to the browser for download.
    """
    import io
    import zipfile

    from fastapi.responses import StreamingResponse

    # Resolve access token via the same fallback chain as download endpoint
    real_token = getattr(user, "access_token", None)
    if not real_token or real_token in ("auto", "no-token", None):
        try:
            from app.core.oauth_token_manager import get_valid_token_for_user

            real_token = get_valid_token_for_user(user.user_id) or real_token
        except ImportError:
            # Token manager unavailable, will use provided token
            pass
    if not real_token or real_token in ("auto", "no-token", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Storage access token required. Reconnect your storage.",
        )

    try:
        storage = get_provider(user.provider, access_token=real_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Gather all certificates to find document metadata + storage paths
    try:
        cert_files = await storage.list_files(VAULT_CERTIFICATES)
    except Exception as e:
        logger.error(f"export: failed to list certificates: {e}")
        raise HTTPException(status_code=500, detail="Could not list vault documents.")

    certificates = []
    for cert_file in cert_files:
        if not cert_file.name.lower().endswith(".json"):
            continue
        try:
            cert_content = await storage.download_file(f"{VAULT_CERTIFICATES}/{cert_file.name}")
            cert = json.loads(cert_content.decode("utf-8"))
            certificates.append(cert)
        except Exception as e:
            logger.warning(f"export: skipping cert {cert_file.name}: {e}")
            continue

    if not certificates:
        raise HTTPException(status_code=404, detail="No documents found in vault to export.")

    # Sort by uploaded_at descending (newest first)
    certificates.sort(key=lambda c: c.get("uploaded_at", ""), reverse=True)

    # Build the ZIP in memory, then stream it
    buf = io.BytesIO()
    manifest = []
    used_names = {}

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in certificates:
            doc_id = cert.get("document_id", "unknown")
            original_name = cert.get("original_filename") or cert.get("filename") or doc_id
            storage_path = cert.get("storage_path", "")
            mime_type = cert.get("mime_type", "application/octet-stream")
            uploaded_at = cert.get("uploaded_at", "")
            file_size = cert.get("file_size", 0)

            # De-duplicate filename inside the zip
            safe_name = original_name.replace("/", "_").replace("\\", "_")
            if safe_name in used_names:
                used_names[safe_name] += 1
                base, dot, ext = safe_name.rpartition(".")
                safe_name = (
                    f"{base}_{used_names[safe_name]}{dot}{ext}" if dot else f"{safe_name}_{used_names[safe_name]}"
                )
            else:
                used_names[safe_name] = 0

            # Download the file bytes
            file_bytes = None
            provider_file_id = cert.get("provider_file_id")
            if provider_file_id:
                try:
                    file_bytes = await storage.download_file(f"id:{provider_file_id}")
                except Exception:
                    file_bytes = None
            if not file_bytes and storage_path:
                try:
                    file_bytes = await storage.download_file(storage_path)
                except Exception as e:
                    logger.warning(f"export: could not download {doc_id}: {e}")
                    file_bytes = None

            if file_bytes:
                zf.writestr(safe_name, file_bytes)
                manifest.append(
                    {
                        "filename": safe_name,
                        "original_filename": original_name,
                        "document_id": doc_id,
                        "mime_type": mime_type,
                        "uploaded_at": uploaded_at,
                        "file_size": file_size if file_size else len(file_bytes),
                        "status": "included",
                    }
                )
            else:
                manifest.append(
                    {
                        "filename": safe_name,
                        "original_filename": original_name,
                        "document_id": doc_id,
                        "mime_type": mime_type,
                        "uploaded_at": uploaded_at,
                        "file_size": file_size,
                        "status": "failed_to_download",
                    }
                )

        manifest_bytes = json.dumps(
            {
                "exported_at": utc_now().isoformat(),
                "user_id": user.user_id,
                "total_documents": len(certificates),
                "included": sum(1 for m in manifest if m["status"] == "included"),
                "failed": sum(1 for m in manifest if m["status"] == "failed_to_download"),
                "documents": manifest,
            },
            indent=2,
        ).encode("utf-8")
        zf.writestr("manifest.json", manifest_bytes)

    buf.seek(0)
    zip_bytes = buf.getvalue()

    async def streamer():
        chunk_size = 64 * 1024
        offset = 0
        while offset < len(zip_bytes):
            chunk = zip_bytes[offset : offset + chunk_size]
            offset += chunk_size
            yield chunk

    zip_filename = f"semptify-my-case-{utc_now().strftime('%Y-%m-%d')}.zip"

    return StreamingResponse(
        streamer(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "Content-Length": str(len(zip_bytes)),
            "X-Export-Count": str(len(certificates)),
        },
    )
