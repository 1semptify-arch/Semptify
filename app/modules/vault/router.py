"""
Document Vault Router (Cloud Storage Version)
Secure document storage, retrieval, and certification.

=============================================================================
SSOT — VAULT INGRESS
=============================================================================
ALL document uploads go through VaultUploadService.upload() — the single
source of truth for document ingestion.

Upload paths:
- Onboarding: POST /onboarding/api/vault/verify (marks onboarding gates)
- Sidebar:    POST /api/vault/sidebar/upload (uses VaultUploadService)
- Documents:  POST /upload (documents router, uses VaultUploadService)

VaultUploadService handles:
- Storage in user's cloud (Google Drive, Dropbox, OneDrive)
- Certificate generation
- Registry entry (SEM-YYYY-NNNNNN-XXXX)
- Event bus emission
- Overlay creation
- Timeline extraction

Vault router endpoints:
- GET  /api/vault/documents      (list tenant's stored documents)
- GET  /api/vault/download/{id}  (retrieve a specific document)
- POST /api/vault/sidebar/upload (sidebar upload via VaultUploadService)
=============================================================================
"""
# Migrated from app/routers/vault.py into the vault SDK module.
# All imports remain absolute since vault is a CORE module.

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from app.core.utc import utc_now
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import make_id
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import (
    yellow_access,
    require_user,
    rate_limit_dependency,
    StorageUser,
    issue_function_access_token,
)
from app.core.vault_paths import (
    CANONICAL_VAULT_FOLDERS,
    SEMPTIFY_ROOT,
    VAULT_ROOT,
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
    VAULT_TIMELINE,
    VAULT_OVERLAYS,
    VAULT_OVERLAY_DOCUMENTS,
    VAULT_OVERLAY_QUERIES,
    VAULT_OVERLAYS_FORMS,
    VAULT_OVERLAY_REDACTIONS,
    SYSTEM_FOLDER,
    AUTH_FOLDER,
    VAULT_FOLDER,
)
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
    from app.core.job_processor import submit_thumbnail_generation_job, submit_document_analysis_job
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
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("vault-upload", window=60, max_requests=20))],
)
async def upload_document(
    request: Request,
    files: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user: StorageUser = Depends(yellow_access),
    settings: Settings = Depends(get_settings),
):
    """
    Upload one or more documents to the user's cloud storage vault.

    SSOT: The single entry point for ALL vault document uploads.
    Handles UI uploads (vault portal) and programmatic uploads identically.

    Accepts:
    - files: one or more files
    - metadata: optional JSON string with document_type, description, tags, source
    - document_type / description / tags: optional form fields (override metadata)

    Returns JSON with uploaded file entries and any errors.
    """
    if not HAS_VAULT_SERVICE:
        raise HTTPException(status_code=503, detail="Vault service unavailable")

    # Parse optional metadata JSON (from UI portal)
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    # Form fields override metadata dict
    doc_type = document_type or metadata_dict.get("document_type")
    doc_description = description or metadata_dict.get("description")
    doc_tags = tags.split(",") if tags else metadata_dict.get("tags", [])
    source = metadata_dict.get("source", "vault_upload")

    # Resolve access token with fallback chain
    access_token_val = metadata_dict.get("access_token") or getattr(user, "access_token", None)
    real_token = access_token_val
    if not real_token or real_token in ("auto", "no-token"):
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

    provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
    vault_service = get_vault_service()
    uploaded_files = []
    upload_errors = []

    for uploaded_file in files:
        try:
            file_content = await uploaded_file.read()

            # Security validation with audit logging
            from app.core.file_validator import validate_upload_file
            validation_result = validate_upload_file(file_content, uploaded_file.filename, uploaded_file.size)
            if not validation_result.is_valid:
                from app.core.audit_logger import log_security_event
                log_security_event(
                    user_id=user.user_id,
                    event_type="file_validation_failure",
                    details={
                        "filename": uploaded_file.filename,
                        "validation_error": validation_result.error_message,
                        "security_risk": validation_result.security_risk,
                    },
                    ip_address=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent", "unknown"),
                )
                upload_errors.append({
                    "filename": uploaded_file.filename,
                    "error": validation_result.error_message,
                    "security_risk": validation_result.security_risk,
                    "recommended_action": validation_result.recommended_action,
                })
                continue

            # VaultUploadService — the ONE door into the vault
            vault_doc = await vault_service.upload(
                user_id=user.user_id,
                filename=uploaded_file.filename,
                content=file_content,
                mime_type=uploaded_file.content_type or "application/octet-stream",
                document_type=doc_type,
                description=doc_description,
                tags=doc_tags,
                source_module=source,
                access_token=real_token,
                storage_provider=provider_name,
            )

            # Timeline extraction (secondary, non-blocking)
            timeline_events = []
            try:
                from app.services.timeline_extraction import extract_timeline_from_upload
                timeline_events = await extract_timeline_from_upload(
                    document_id=vault_doc.vault_id,
                    overlay_id=vault_doc.overlay_id if hasattr(vault_doc, "overlay_id") else None,
                    provider=provider_name,
                    access_token=real_token,
                )
                logger.info(f"Timeline: {len(timeline_events)} events for {vault_doc.vault_id}")
            except Exception as e:
                logger.warning(f"Timeline extraction failed for {vault_doc.vault_id}: {e}")

            # Document extraction + classification overlays (secondary, non-blocking)
            try:
                from app.services.document_intake import DocumentClassifier, DataExtractor
                from app.services.unified_overlay_manager import get_unified_overlay_manager
                from app.models.unified_overlay_models import CreateOverlayRequest
                from app.core.overlay_types import OverlayType
                from app.services.storage import get_provider as get_storage_provider

                text = ""
                try:
                    from app.services.document_intake import IntakeService
                    _intake = IntakeService()
                    text = await _intake._extract_text(
                        file_content, uploaded_file.content_type or "application/octet-stream", uploaded_file.filename
                    )
                except Exception:
                    pass

                if text and real_token:
                    storage_prov = get_storage_provider(provider_name, access_token=real_token)
                    ovl_mgr = await get_unified_overlay_manager(storage_prov, user.user_id)

                    doc_type, type_confidence = DocumentClassifier.classify(text, uploaded_file.filename)
                    dates = DataExtractor.extract_dates(text)
                    amounts = DataExtractor.extract_amounts(text)
                    parties = DataExtractor.extract_parties(text, doc_type)

                    # DOCUMENT_EXTRACTION overlay
                    await ovl_mgr.create_overlay(CreateOverlayRequest(
                        overlay_type=OverlayType.DOCUMENT_EXTRACTION,
                        document_id=vault_doc.vault_id,
                        vault_path=vault_doc.storage_path,
                        payload={
                            "extracted_dates": dates,
                            "extracted_parties": parties,
                            "extracted_amounts": amounts,
                            "key_terms": [],
                            "confidence_score": type_confidence,
                            "extraction_model": "text_parse",
                        },
                        metadata={"source_module": source, "filename": uploaded_file.filename},
                    ))

                    # DOCUMENT_CLASSIFICATION overlay
                    await ovl_mgr.create_overlay(CreateOverlayRequest(
                        overlay_type=OverlayType.DOCUMENT_CLASSIFICATION,
                        document_id=vault_doc.vault_id,
                        vault_path=vault_doc.storage_path,
                        payload={
                            "document_type": doc_type.value if hasattr(doc_type, "value") else str(doc_type),
                            "confidence_score": type_confidence,
                            "classification_model": "text_parse",
                            "alternative_types": [],
                        },
                        metadata={"source_module": source, "filename": uploaded_file.filename},
                    ))
                    logger.info("Extraction overlays created for %s (type=%s)", vault_doc.vault_id, doc_type)
            except Exception as e:
                logger.warning("Extraction overlay creation failed for %s: %s", vault_doc.vault_id, e)

            # Auto-sync timeline events to calendar (secondary, non-blocking)
            if timeline_events:
                try:
                    from app.services.calendar_service import CalendarService
                    from app.models.models import CalendarEvent as CalendarEventModel
                    from app.core.database import get_db_session
                    from app.core.id_gen import make_id as _make_id
                    from app.core.utc import utc_now as _utc_now
                    from datetime import datetime, timezone

                    cal_service = CalendarService()
                    cal_events = await cal_service.generate_events_from_timeline(
                        [e if isinstance(e, dict) else (e.__dict__ if hasattr(e, "__dict__") else {}) for e in timeline_events]
                    )

                    if cal_events:
                        async with get_db_session() as _db:
                            from sqlalchemy import select as _select
                            existing_titles_q = await _db.execute(
                                _select(CalendarEventModel.title).where(
                                    CalendarEventModel.user_id == user.user_id
                                )
                            )
                            existing_titles = {r[0] for r in existing_titles_q.fetchall()}

                            added = 0
                            for ce in cal_events:
                                if ce.title in existing_titles:
                                    continue
                                start_dt = datetime.combine(ce.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                                _db.add(CalendarEventModel(
                                    id=_make_id("cal"),
                                    user_id=user.user_id,
                                    title=ce.title,
                                    description=ce.description,
                                    start_datetime=start_dt,
                                    end_datetime=None,
                                    all_day=True,
                                    event_type=ce.event_type.value,
                                    is_critical=ce.event_type.value in ("court_hearing", "notice_deadline"),
                                    reminder_days=ce.reminders[0] // 1440 if ce.reminders else 1,
                                    created_at=_utc_now(),
                                ))
                                added += 1
                            await _db.commit()
                        logger.info("Auto-synced %d calendar events from timeline for %s", added, vault_doc.vault_id)
                except Exception as e:
                    logger.warning("Calendar auto-sync failed for %s: %s", vault_doc.vault_id, e)

            # Issue function token for downstream access
            function_token = issue_function_access_token(
                user.user_id,
                context={
                    "provider": user.provider,
                    "reason": "vault_upload",
                    "scopes": ["overlay:read", "overlay:write"],
                    "document_ids": [vault_doc.vault_id],
                },
            )

            # Audit log
            from app.core.audit_logger import log_document_upload
            log_document_upload(
                user_id=user.user_id,
                document_id=vault_doc.vault_id,
                filename=uploaded_file.filename,
                file_size=len(file_content),
                file_type=validation_result.file_type,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )

            # Fire DOCUMENT_ADDED → timeline subscriber creates TimelineEvent row
            try:
                from app.core.event_bus import notify_document_added
                asyncio.create_task(notify_document_added(
                    doc_id=vault_doc.vault_id,
                    filename=uploaded_file.filename,
                    user_id=user.user_id,
                ))
            except Exception as _ev_err:
                logger.debug("Event bus notify skipped: %s", _ev_err)

            uploaded_at = vault_doc.uploaded_at.isoformat() if hasattr(vault_doc.uploaded_at, "isoformat") else str(vault_doc.uploaded_at)

            uploaded_files.append({
                "id": vault_doc.vault_id,
                "name": uploaded_file.filename,
                "size": len(file_content),
                "type": uploaded_file.content_type or "application/octet-stream",
                "category": _get_file_category(uploaded_file.filename),
                "uploaded_at": uploaded_at,
                "certificate_id": vault_doc.certificate_id,
                "sha256": vault_doc.sha256_hash,
                "user_id": user.user_id,
                "path": vault_doc.storage_path,
                "tags": vault_doc.tags or [],
                "function_token": function_token["token"],
                "metadata": {
                    "source": source,
                    "original_filename": uploaded_file.filename,
                    "upload_timestamp": uploaded_at,
                    "registry_id": vault_doc.registry_id,
                },
            })

            logger.info(f"Vault upload (SSOT): {vault_doc.vault_id} for user {user.user_id}")

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            upload_errors.append({
                "filename": uploaded_file.filename,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()[:2000],
            })
            logger.error(f"Vault upload error for {uploaded_file.filename}: {e}")

    response_data = {
        "success": True,
        "message": f"Uploaded {len(uploaded_files)} file(s) to vault",
        "files": uploaded_files,
    }

    if upload_errors:
        response_data["errors"] = upload_errors
        response_data["message"] = f"Uploaded {len(uploaded_files)} file(s) with {len(upload_errors)} error(s)"

        # Return 401 if any auth errors for auto-redirect
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
    except Exception as e:
        # Try alternative path by file_id
        try:
            # Try provider file id (id:<file_id>) first, then path fallback
            try:
                content = await storage.download_file(f"id:{file_id}")
            except Exception:
                content = await storage.download_file(f"{VAULT_DOCUMENTS}/{file_id}")
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
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "access" in error_msg.lower():
            raise HTTPException(status_code=401, detail=f"Storage authentication failed: {error_msg}")
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise HTTPException(status_code=403, detail=f"Storage access denied: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"Storage error: {error_msg}")

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
        "certified_at": datetime.now(timezone.utc).isoformat(),
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
        from app.services.unified_overlay_manager import UnifiedOverlayManager
        from app.models.unified_overlay_models import CreateOverlayRequest
        from app.core.overlay_types import OverlayType
        overlay_mgr = UnifiedOverlayManager(storage, user.user_id)
        overlay_resp = await overlay_mgr.create_overlay(CreateOverlayRequest(
            overlay_type=OverlayType.VAULT_UPLOAD_MANIFEST,
            document_id=document_id,
            vault_path=storage_path,
            payload={
                "original_filename": original_filename,
                "mime_type": mime_type,
                "file_size_bytes": file_size,
                "content_hash": sha256_hash,
                "storage_provider": user.provider,
                "source_path": sync_path,
            },
        ))
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
        from app.core.positronic_mesh import positronic_mesh, WorkflowType
        import asyncio

        workflow_type = None
        trigger_context = {
            "document_id": document_id,
            "certificate_id": certificate_id,
            "filename": filename,
            "mime_type": mime_type,
            "document_type": document_type,
            "overlay_id": overlay.overlay_id if overlay else None,
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
        headers={
            "Content-Disposition": f'attachment; filename="{target_cert.get("original_filename", "document")}"'
        },
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
    access_token: Optional[str] = Query(None, description="Storage provider access token"),
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
        }
    )


@router.post("/document/{vault_id}/mark-processed")
async def mark_vault_document_processed(
    vault_id: str,
    extracted_data: Optional[dict] = None,
    document_type: Optional[str] = None,
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
    
    storage_provider = user.provider if hasattr(user, 'provider') else 'google_drive'
    
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
        files.append({
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
                "upload_timestamp": uploaded_at
            }
        })
    
    return JSONResponse({
        "success": True,
        "message": f"Retrieved {len(files)} files for sidebar",
        "files": files
    })

@router.post("/sidebar/upload")
async def sidebar_upload_redirect(
    request: Request,
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    user: StorageUser = Depends(yellow_access),
):
    """Deprecated — redirects to unified /upload endpoint."""
    return JSONResponse(
        status_code=308,
        content={"detail": "Use POST /api/vault/upload instead"},
        headers={"Location": "/api/vault/upload"},
    )



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
    user: StorageUser = Depends(yellow_access),
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
    documents = await vault_service.get_user_documents(user.user_id)
    query_lower = query.lower()
    
    filtered_docs = [
        doc for doc in documents 
        if query_lower in doc.filename.lower() or 
           any(query_lower in tag.lower() for tag in (doc.tags or []))
    ]
    
    # Convert to sidebar format
    filtered_files = []
    for doc in filtered_docs:
        uploaded_at = doc.uploaded_at if isinstance(doc.uploaded_at, str) else doc.uploaded_at.isoformat()
        filtered_files.append({
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
                "upload_timestamp": uploaded_at
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


# =============================================================================
# Vault Setup Endpoints (used by /onboarding/vault-setup page)
# =============================================================================

@router.get("/status")
async def vault_status(user: StorageUser = Depends(yellow_access)):
    """Check that the user is authenticated and has a storage provider configured."""
    return {"ok": True, "user_id": user.user_id[:6] + "***", "provider": str(getattr(user, "provider", "unknown"))}


@router.post("/init")
async def vault_init(user: StorageUser = Depends(yellow_access), db: AsyncSession = Depends(get_db)):
    """
    Create the Semptify vault folder structure in the user's cloud storage.
    Called once during onboarding vault-setup Step 1. Idempotent — safe to call again.

    SSOT RULE: This endpoint creates folders ONLY.
    vault_initialized gate is NOT marked here.
    It is marked by POST /onboarding/api/vault/verify (Step 3) only after:
      1. Folders created (this step)
      2. Token backup written (Step 2)
      3. Live write/read probe passed + document uploaded through pipeline
    """
    try:
        from app.core.oauth_token_manager import get_valid_token_for_user as _get_token
    except ImportError:
        def _get_token(uid: str):  # type: ignore[misc]
            return None

    access_token = getattr(user, "access_token", None) or _get_token(user.user_id)
    if not access_token or access_token == "no-token":
        raise HTTPException(
            status_code=401,
            detail={"error": "no_token", "message": "Storage token missing — please reconnect your storage."},
        )

    try:
        storage = get_provider(user.provider, access_token=access_token)
        await ensure_vault_folders(storage, user.provider)
        logger.info("Vault folders created for user=%s — awaiting Steps 2+3 to mark gate", user.user_id[:6] + "***")
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "folder_init_failed", "message": str(exc)},
        )

    return {"ok": True, "message": "Vault folders created", "provider": user.provider.value if hasattr(user.provider, 'value') else str(user.provider)}


@router.get("/verify")
async def vault_verify(user: StorageUser = Depends(yellow_access)):
    """
    Verify that the vault folder structure is accessible in the user's cloud storage.
    Called after /init to confirm everything is ready.
    """
    try:
        from app.core.oauth_token_manager import get_valid_token_for_user as _get_token
    except ImportError:
        def _get_token(uid: str):  # type: ignore[misc]
            return None

    access_token = getattr(user, "access_token", None) or _get_token(user.user_id)
    if not access_token or access_token == "no-token":
        raise HTTPException(
            status_code=401,
            detail={"error": "no_token", "message": "Storage token missing — please reconnect your storage."},
        )

    try:
        storage = get_provider(user.provider, access_token=access_token)
        await ensure_vault_folders(storage, user.provider)
        items = await storage.list_files(VAULT_ROOT)
        if items is None:
            raise RuntimeError("Vault root folder not accessible after init")
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "vault_verify_failed", "message": str(exc)},
        )

    return {"ok": True, "message": "Vault verified and accessible"}
