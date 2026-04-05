"""
Document Intake API Router

Provides endpoints for:
- Document upload and intake
- Processing status tracking
- Extraction results retrieval
- Issue detection results
- Batch processing
- Vault-based processing (documents from cloud storage)

ALL UPLOADS GO TO VAULT FIRST - modules access from vault.
"""

import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel
from typing import Optional

from app.core.security import get_user_id, require_user, StorageUser
from app.core.config import get_settings, Settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.document_intake import (
    get_intake_engine,
    DocumentType,
    IntakeStatus,
    IssueSeverity,
    LanguageCode,
)
from app.core.event_bus import event_bus, EventType as BusEventType

logger = logging.getLogger(__name__)

# Import vault upload service - ALL uploads go through here first
try:
    from app.services.vault_upload_service import get_vault_service
    HAS_VAULT_SERVICE = True
except ImportError:
    HAS_VAULT_SERVICE = False

# Import flow orchestrator for complete pipeline
try:
    from app.services.document_flow_orchestrator import DocumentFlowOrchestrator
    FLOW_AVAILABLE = True
except ImportError:
    FLOW_AVAILABLE = False

# Import notarization service for tamper-proof documentation
try:
    from app.services.document_notarization import get_notarization_service
    HAS_NOTARIZATION = True
except ImportError:
    HAS_NOTARIZATION = False
    logger.warning("Notarization service not available")


router = APIRouter(prefix="/api/intake", tags=["Document Intake"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class IntakeStatusResponse(BaseModel):
    """Processing status response."""
    id: str
    status: str
    status_message: str
    progress_percent: int


class ExtractedDateResponse(BaseModel):
    """Extracted date response."""
    date: str
    label: str
    confidence: float
    source_text: str
    is_deadline: bool
    days_until: Optional[int] = None


class ExtractedPartyResponse(BaseModel):
    """Extracted party response."""
    name: str
    role: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    confidence: float


class ExtractedAmountResponse(BaseModel):
    """Extracted amount response."""
    amount: float
    label: str
    currency: str
    period: Optional[str] = None
    confidence: float
    source_text: str


class DetectedIssueResponse(BaseModel):
    """Detected issue response."""
    issue_id: str
    severity: str
    title: str
    description: str
    affected_text: Optional[str] = None
    legal_basis: Optional[str] = None
    recommended_action: Optional[str] = None
    deadline: Optional[str] = None
    related_laws: list[str] = []


class ExtractionResultResponse(BaseModel):
    """Complete extraction result response."""
    doc_type: str
    doc_type_confidence: float
    language: str
    page_count: int
    word_count: int
    summary: str
    key_points: list[str]
    dates: list[ExtractedDateResponse]
    parties: list[ExtractedPartyResponse]
    amounts: list[ExtractedAmountResponse]
    issues: list[DetectedIssueResponse]
    extracted_at: str


class IntakeDocumentResponse(BaseModel):
    """Complete intake document response."""
    id: str
    user_id: str
    filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    status_message: str
    progress_percent: int
    extraction: Optional[ExtractionResultResponse] = None
    uploaded_at: str
    processed_at: Optional[str] = None


class UploadResponse(BaseModel):
    """Upload response."""
    id: str
    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    """Batch upload response."""
    uploaded: list[UploadResponse]
    failed: list[dict]
    total_uploaded: int
    total_failed: int


# =============================================================================
# NOTARIZATION MODELS
# =============================================================================

class NotarizationResponse(BaseModel):
    """Notarization record response."""
    notarization_id: str
    document_id: str
    file_hash: str
    file_size: int
    original_filename: str
    notarized_at: str
    certificate_hash: Optional[str]
    status: str
    storage_path: str
    storage_provider: str
    registry_id: Optional[str] = None


class NotarizationVerificationResponse(BaseModel):
    """Notarization verification result."""
    status: str
    verified: bool
    notarization_id: str
    document_id: str
    file_hash: str
    file_size: int
    original_filename: str
    notarized_at: str
    storage_location: str
    content_verified: Optional[bool] = None
    content_status: Optional[str] = None
    registry_status: Optional[str] = None
    error: Optional[str] = None


class ChainOfCustodyEvent(BaseModel):
    """Single event in chain of custody."""
    event: str
    timestamp: str
    actor: str
    action: str
    hash: Optional[str] = None
    location: Optional[str] = None


class ChainOfCustodyResponse(BaseModel):
    """Complete chain of custody."""
    notarization_id: str
    events: list[ChainOfCustodyEvent]


# =============================================================================
# UPLOAD ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(..., description="User ID for the document owner"),
    username: str = Form("unknown", description="Username for notarization"),
    access_token: Optional[str] = Form(None, description="Storage provider access token"),
    storage_provider: str = Form("local", description="Storage provider"),
    description: Optional[str] = Form(None, description="Document description"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """
    Upload a document for intake processing with notarization.
    
    COMPLETE FLOW:
    1. Notarize receipt (tamper-proof record with hash)
    2. Store in user's vault (cloud or local)
    3. Register in system (Document Registry)
    4. Queue for processing
    
    Returns status with notarization proof.
    """
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(content) > 25 * 1024 * 1024:  # 25MB limit
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    
    # STEP 0: Notarize the upload
    notarization = None
    notarization_id = None
    if HAS_NOTARIZATION:
        try:
            notarization_service = await get_notarization_service()
            tags_list = [t.strip() for t in tags.split(",")] if tags else []
            
            notarization = await notarization_service.notarize_upload(
                file_content=content,
                filename=file.filename or "unknown",
                user_id=user_id,
                username=username,
                storage_path="",  # Will be set after vault upload
                storage_provider=storage_provider,
                document_type=None,
                description=description,
                tags=tags_list,
                upload_method="web",
                upload_context={
                    "original_filename": file.filename,
                    "mime_type": file.content_type,
                },
            )
            notarization_id = notarization.notarization_id
            logger.info(f"✓ Document notarized: {notarization_id}")
        except Exception as e:
            logger.warning(f"Notarization failed (non-blocking): {e}")
    
    # STEP 1: Upload to vault first
    vault_id = None
    if HAS_VAULT_SERVICE:
        try:
            vault_service = get_vault_service()
            vault_doc = await vault_service.upload(
                user_id=user_id,
                filename=file.filename or "unknown",
                content=content,
                mime_type=file.content_type or "application/octet-stream",
                source_module="intake",
                access_token=access_token,
                storage_provider=storage_provider,
            )
            vault_id = vault_doc.vault_id
            
            # Update notarization with actual storage path
            if notarization and HAS_NOTARIZATION:
                try:
                    notarization.storage_path = vault_doc.storage_path
                    logger.info(f"📁 Document stored in vault: {vault_id}")
                except Exception as e:
                    logger.debug(f"Could not update notarization storage path: {e}")
        except Exception as e:
            logger.warning("Vault upload failed: %s", e)
    
    # STEP 2: Intake the document for processing (in background, don't wait)
    engine = get_intake_engine()
    try:
        doc = await engine.intake_document(
            user_id=user_id,
            file_content=content,
            filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            vault_id=vault_id,  # Pass vault reference
        )
        logger.info(f"📋 Document registered: {doc.id}")
    except Exception as e:
        logger.error(f"Intake failed: {e}")
        doc = None
    
    return UploadResponse(
        id=doc.id if doc else "",
        filename=file.filename or "unknown",
        status="notarized" if notarization else "received",
        message=(
            f"✓ Document notarized and stored in vault ({vault_id or 'local'}). "
            f"Notarization: {notarization_id}. "
            f"Use /status/{doc.id if doc else 'pending'} to check processing."
        ),
    )


class AutoProcessResponse(BaseModel):
    """Response for auto-processed upload."""
    id: str
    filename: str
    status: str
    doc_type: str
    message: str
    vault_id: Optional[str] = None
    extracted_data: dict = {}
    timeline_events: int = 0
    issues_found: int = 0


@router.post("/upload/auto", response_model=AutoProcessResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    user_id: str = Form(..., description="User ID"),
    username: str = Form("unknown", description="Username for notarization"),
    access_token: Optional[str] = Form(None, description="Storage provider access token"),
    storage_provider: str = Form("local", description="Storage provider"),
    description: Optional[str] = Form(None, description="Document description"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
):
    """
    Upload and automatically process a document (complete pipeline).
    
    COMPLETE FLOW:
    1. Notarize receipt (tamper-proof record with hash)
    2. Store in user's vault (cloud or local)
    3. OCR/text extraction (auto-detects if image/scan)
    4. Document type classification (summons, lease, notice, etc.)
    5. Data extraction (dates, amounts, parties)
    6. Timeline event creation
    7. FormData hub update
    8. Issue detection & chain of custody tracking
    9. UI refresh via WebSocket
    
    Returns complete processing result in one call.
    """
    engine = get_intake_engine()
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    
    # STEP 0a: Notarize the upload first
    notarization = None
    notarization_id = None
    if HAS_NOTARIZATION:
        try:
            notarization_service = await get_notarization_service()
            tags_list = [t.strip() for t in tags.split(",")] if tags else []
            
            notarization = await notarization_service.notarize_upload(
                file_content=content,
                filename=file.filename or "unknown",
                user_id=user_id,
                username=username,
                storage_path="",  # Will be updated after vault upload
                storage_provider=storage_provider,
                description=description,
                tags=tags_list,
                upload_method="web_auto",
                upload_context={
                    "auto_processing": True,
                    "original_filename": file.filename,
                    "mime_type": file.content_type,
                },
            )
            notarization_id = notarization.notarization_id
            logger.info(f"✓ Document notarized: {notarization_id}")
        except Exception as e:
            logger.warning(f"Notarization failed (non-blocking): {e}")
    
    # STEP 0b: Upload to vault first
    vault_id = None
    if HAS_VAULT_SERVICE:
        try:
            vault_service = get_vault_service()
            vault_doc = await vault_service.upload(
                user_id=user_id,
                filename=file.filename or "unknown",
                content=content,
                mime_type=file.content_type or "application/octet-stream",
                source_module="intake_auto",
                access_token=access_token,
                storage_provider=storage_provider,
            )
            vault_id = vault_doc.vault_id
            
            # Update notarization with storage path
            if notarization and HAS_NOTARIZATION:
                try:
                    notarization.storage_path = vault_doc.storage_path
                except Exception:
                    pass
            
            logger.info(f"📁 Document stored in vault: {vault_id}")
        except Exception as e:
            logger.warning("Vault upload failed: %s", e)
    
    # Step 1: Intake the document
    doc = await engine.intake_document(
        user_id=user_id,
        file_content=content,
        filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        vault_id=vault_id,
    )
    logger.info(f"📋 Document intake complete: {doc.id}")
    
    # Step 2: Process (extract text, classify, analyze)
    try:
        doc = await engine.process_document(doc.id)
        logger.info(f"✓ Document processing complete: {doc.id}")
    except Exception as e:
        logger.error("Processing failed: %s", e)
        return AutoProcessResponse(
            id=doc.id,
            filename=doc.filename,
            status="error",
            doc_type="unknown",
            message=f"Processing failed: {str(e)}",
            vault_id=vault_id,
        )
    
    # Step 3: Run full flow orchestration for complete pipeline
    flow_result = {}
    if FLOW_AVAILABLE:
        try:
            orchestrator = DocumentFlowOrchestrator()
            flow_result = await orchestrator.process_document_complete(
                doc_id=doc.id,
                user_id=user_id,
                notarization_id=notarization_id,  # Pass notarization for chain of custody
            )
            logger.info(f"✓ Flow orchestration complete: {len(flow_result.get('stages', {}))} stages")
        except Exception as flow_err:
            logger.warning("Flow orchestration partial: %s", flow_err)
    
    # Update vault with extracted data
    if HAS_VAULT_SERVICE and vault_id and doc.extraction:
        try:
            vault_service = get_vault_service()
            vault_service.mark_processed(
                vault_id=vault_id,
                extracted_data={
                    "doc_type": doc.doc_type.value if doc.doc_type else None,
                    "summary": doc.extraction.summary if doc.extraction else None,
                }
            )
            if doc.doc_type:
                vault_service.update_document_type(vault_id, doc.doc_type.value)
        except Exception as e:
            logger.warning("Vault update failed: %s", e)
    
    # Publish completion event
    await event_bus.publish(
        BusEventType.DOCUMENT_PROCESSED,
        {
            "doc_id": doc.id,
            "vault_id": vault_id,
            "user_id": user_id,
            "notarization_id": notarization_id,
            "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
            "filename": doc.filename,
        },
        user_id=user_id,
    )
    
    # Build response
    extracted_data = {}
    if doc.extraction:
        extracted_data = {
            "dates": len(doc.extraction.dates) if doc.extraction.dates else 0,
            "parties": len(doc.extraction.parties) if doc.extraction.parties else 0,
            "amounts": len(doc.extraction.amounts) if doc.extraction.amounts else 0,
            "summary": doc.extraction.summary[:200] if doc.extraction.summary else "",
        }
    
    return AutoProcessResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value if doc.status else "complete",
        doc_type=doc.doc_type.value if doc.doc_type else "unknown",
        message=(
            f"✓ Document stored, notarized ({notarization_id}), "
            f"and processed successfully in vault ({vault_id or 'local'})"
        ),
        vault_id=vault_id,
        extracted_data=extracted_data,
        timeline_events=flow_result.get("stages", {}).get("events", {}).get("count", 0),
        issues_found=len(doc.extraction.issues) if doc.extraction and doc.extraction.issues else 0,
    )


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    user_id: str = Form(...),
):
    """
    Upload multiple documents at once.
    
    Returns status for each file.
    """
    engine = get_intake_engine()
    
    uploaded = []
    failed = []
    
    for file in files:
        try:
            content = await file.read()
            
            if len(content) == 0:
                failed.append({"filename": file.filename, "error": "Empty file"})
                continue
            
            if len(content) > 25 * 1024 * 1024:
                failed.append({"filename": file.filename, "error": "File too large"})
                continue
            
            doc = await engine.intake_document(
                user_id=user_id,
                file_content=content,
                filename=file.filename or "unknown",
                mime_type=file.content_type or "application/octet-stream",
            )
            
            uploaded.append(UploadResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.status.value,
                message="Document received",
            ))
            
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})
    
    return BatchUploadResponse(
        uploaded=uploaded,
        failed=failed,
        total_uploaded=len(uploaded),
        total_failed=len(failed),
    )


# =============================================================================
# PROCESSING ENDPOINTS
# =============================================================================

@router.post("/process/vault/{doc_id}", response_model=AutoProcessResponse)
async def process_document_from_vault(
    doc_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Process a document stored in vault.
    
    This endpoint:
    1. Downloads document content from vault
    2. Runs the full processing pipeline
    3. Updates vault index with processed status
    
    Use this for documents uploaded directly to vault.
    """
    import json
    
    from app.routers.cloud_sync import get_sync_service
    
    sync = await get_sync_service(user, db, settings)
    vault_folder = ".semptify/vault"
    
    # Get document info from vault index
    try:
        index_content = await sync.storage.download_file(f"{vault_folder}/index.json")
        vault_index = json.loads(index_content.decode("utf-8"))
        
        doc_info = None
        for doc in vault_index.get("documents", []):
            if doc.get("document_id") == doc_id:
                doc_info = doc
                break
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found in vault")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read vault index: {str(e)}") from e
    
    # Download document content
    try:
        storage_path = doc_info.get("storage_path", f"{vault_folder}/{doc_id}")
        content = await sync.storage.download_file(storage_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download document: {str(e)}") from e
    
    # Process with intake engine
    engine = get_intake_engine()
    
    try:
        # Intake the document with vault content
        intake_doc = await engine.intake_document(
            user_id=user.user_id,
            file_content=content,
            filename=doc_info.get("original_filename", "document"),
            mime_type=doc_info.get("mime_type", "application/octet-stream"),
        )
        
        # Process
        intake_doc = await engine.process_document(intake_doc.id)
        
        # Run flow orchestration if available
        if FLOW_AVAILABLE:
            try:
                orchestrator = DocumentFlowOrchestrator()
                await orchestrator.process_document_complete(
                    doc_id=intake_doc.id,
                    user_id=user.user_id,
                )
            except Exception as flow_err:
                logger.warning(f"Flow orchestration warning: {flow_err}")
        
        # Update vault index with processed status
        try:
            from datetime import datetime, timezone
            for doc in vault_index.get("documents", []):
                if doc.get("document_id") == doc_id:
                    doc["processed"] = True
                    doc["processed_at"] = datetime.now(timezone.utc).isoformat()
                    doc["intake_id"] = intake_doc.id
                    if intake_doc.doc_type:
                        doc["document_type"] = intake_doc.doc_type.value
                    break
            
            vault_index["last_updated"] = datetime.now(timezone.utc).isoformat()
            await sync.storage.upload_file(
                f"{vault_folder}/index.json",
                json.dumps(vault_index, indent=2).encode("utf-8")
            )
        except Exception as idx_err:
            logger.warning("Failed to update vault index: %s", idx_err)
        
        # Build response
        extracted_data = {}
        if intake_doc.extraction:
            extracted_data = {
                "dates": len(intake_doc.extraction.dates) if intake_doc.extraction.dates else 0,
                "parties": len(intake_doc.extraction.parties) if intake_doc.extraction.parties else 0,
                "amounts": len(intake_doc.extraction.amounts) if intake_doc.extraction.amounts else 0,
                "summary": intake_doc.extraction.summary[:200] if intake_doc.extraction.summary else "",
            }
        
        return AutoProcessResponse(
            id=doc_id,  # Return vault document ID
            filename=doc_info.get("original_filename", "document"),
            status=intake_doc.status.value if intake_doc.status else "complete",
            doc_type=intake_doc.doc_type.value if intake_doc.doc_type else "unknown",
            message="Document processed successfully from vault",
            extracted_data=extracted_data,
            timeline_events=0,
            issues_found=len(intake_doc.extraction.issues) if intake_doc.extraction and intake_doc.extraction.issues else 0,
        )
        
    except Exception as e:
        logger.error(f"Vault document processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process/{doc_id}", response_model=IntakeDocumentResponse)
async def process_document(doc_id: str, user_id: str = Depends(get_user_id)):
    """
    Process an uploaded document.
    
    This runs the full pipeline:
    1. Validation
    2. Text extraction (OCR if needed)
    3. Content analysis & document type detection
    4. Issue detection
    5. Timeline event creation
    6. FormData hub update
    7. UI refresh via WebSocket
    
    Returns the complete extraction result.
    """
    engine = get_intake_engine()
    
    doc = engine.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status == IntakeStatus.COMPLETE:
        # Already processed, return existing result
        return _doc_to_response(doc)
    
    try:
        # Run basic processing first
        doc = await engine.process_document(doc_id)
        
        # Run full flow orchestration if available
        if FLOW_AVAILABLE:
            try:
                orchestrator = DocumentFlowOrchestrator()
                flow_result = await orchestrator.process_document_complete(
                    doc_id=doc_id,
                    user_id=user_id,
                )
                # Attach flow result to response
                if flow_result.get("status") == "complete":
                    await event_bus.publish(
                        BusEventType.DOCUMENT_PROCESSED,
                        {
                            "doc_id": doc_id,
                            "user_id": user_id,
                            "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
                            "flow_stages": list(flow_result.get("stages", {}).keys()),
                        },
                        user_id=user_id,
                    )
            except Exception as flow_err:
                # Log but don't fail - basic processing succeeded
                logger.warning("Flow orchestration warning: %s", flow_err)
        
        return _doc_to_response(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}") from e


@router.get("/status/{doc_id}", response_model=IntakeStatusResponse)
async def get_processing_status(doc_id: str):
    """
    Get the current processing status of a document.
    
    Use this to poll for completion during async processing.
    """
    engine = get_intake_engine()
    status = engine.get_processing_status(doc_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return IntakeStatusResponse(**status)


# =============================================================================
# RETRIEVAL ENDPOINTS
# =============================================================================

@router.get("/documents", response_model=list[IntakeDocumentResponse])
async def list_documents(
    user_id: str = Depends(get_user_id),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    List all documents for a user.
    
    Optionally filter by processing status.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    if status:
        try:
            status_filter = IntakeStatus(status)
            docs = [d for d in docs if d.status == status_filter]
        except ValueError:
            pass
    
    return [_doc_to_response(d) for d in docs]


@router.get("/documents/{doc_id}", response_model=IntakeDocumentResponse)
async def get_document(doc_id: str):
    """
    Get a specific document with all extraction results.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return _doc_to_response(doc)


@router.get("/documents/{doc_id}/issues", response_model=list[DetectedIssueResponse])
async def get_document_issues(doc_id: str):
    """
    Get only the detected issues for a document.
    
    Useful for displaying alerts/warnings to the user.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        DetectedIssueResponse(
            issue_id=i.issue_id,
            severity=i.severity.value,
            title=i.title,
            description=i.description,
            affected_text=i.affected_text,
            legal_basis=i.legal_basis,
            recommended_action=i.recommended_action,
            deadline=i.deadline.isoformat() if i.deadline else None,
            related_laws=i.related_laws,
        )
        for i in doc.extraction.issues
    ]


@router.get("/documents/{doc_id}/dates", response_model=list[ExtractedDateResponse])
async def get_document_dates(doc_id: str):
    """
    Get only the extracted dates for a document.
    
    Includes deadline detection and days-until calculation.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedDateResponse(
            date=d.date.isoformat(),
            label=d.label,
            confidence=d.confidence,
            source_text=d.source_text,
            is_deadline=d.is_deadline,
            days_until=d.days_until,
        )
        for d in doc.extraction.dates
    ]


@router.get("/documents/{doc_id}/amounts", response_model=list[ExtractedAmountResponse])
async def get_document_amounts(doc_id: str):
    """
    Get only the extracted monetary amounts for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedAmountResponse(
            amount=a.amount,
            label=a.label,
            currency=a.currency,
            period=a.period,
            confidence=a.confidence,
            source_text=a.source_text,
        )
        for a in doc.extraction.amounts
    ]


@router.get("/documents/{doc_id}/parties", response_model=list[ExtractedPartyResponse])
async def get_document_parties(doc_id: str):
    """
    Get only the extracted parties for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedPartyResponse(
            name=p.name,
            role=p.role,
            address=p.address,
            phone=p.phone,
            email=p.email,
            confidence=p.confidence,
        )
        for p in doc.extraction.parties
    ]


@router.get("/documents/{doc_id}/text")
async def get_document_text(doc_id: str):
    """
    Get the full extracted text for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return {
        "id": doc_id,
        "filename": doc.filename,
        "text": doc.extraction.full_text,
        "word_count": doc.extraction.word_count,
        "language": doc.extraction.language.value,
    }


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/issues/critical")
async def get_critical_issues(user_id: str = Depends(get_user_id)):
    """
    Get all CRITICAL issues across all user's documents.
    
    These require immediate attention.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    critical_issues = []
    for doc in docs:
        if doc.extraction:
            for issue in doc.extraction.issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    critical_issues.append({
                        "document_id": doc.id,
                        "document_name": doc.filename,
                        "issue": DetectedIssueResponse(
                            issue_id=issue.issue_id,
                            severity=issue.severity.value,
                            title=issue.title,
                            description=issue.description,
                            affected_text=issue.affected_text,
                            legal_basis=issue.legal_basis,
                            recommended_action=issue.recommended_action,
                            deadline=issue.deadline.isoformat() if issue.deadline else None,
                            related_laws=issue.related_laws,
                        ),
                    })
    
    return {
        "total_critical": len(critical_issues),
        "issues": critical_issues,
    }


@router.get("/deadlines/upcoming")
async def get_upcoming_deadlines(
    user_id: str = Depends(get_user_id),
    days: int = Query(14, description="Number of days to look ahead"),
):
    """
    Get all upcoming deadlines across user's documents.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    deadlines = []
    for doc in docs:
        if doc.extraction:
            for date in doc.extraction.dates:
                if date.is_deadline and date.days_until is not None:
                    if 0 <= date.days_until <= days:
                        deadlines.append({
                            "document_id": doc.id,
                            "document_name": doc.filename,
                            "date": date.date.isoformat(),
                            "label": date.label,
                            "days_until": date.days_until,
                            "source_text": date.source_text,
                        })
    
    # Sort by days until deadline
    deadlines.sort(key=lambda x: x["days_until"])
    
    return {
        "total_deadlines": len(deadlines),
        "deadlines": deadlines,
    }


@router.get("/summary")
async def get_user_intake_summary(user_id: str = Depends(get_user_id)):
    """
    Get a summary of all intake documents for a user.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    by_status = {}
    by_type = {}
    total_issues = 0
    critical_issues = 0
    
    for doc in docs:
        # Count by status
        status = doc.status.value
        by_status[status] = by_status.get(status, 0) + 1
        
        # Count by type and issues
        if doc.extraction:
            doc_type = doc.extraction.doc_type.value
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
            
            total_issues += len(doc.extraction.issues)
            critical_issues += sum(
                1 for i in doc.extraction.issues 
                if i.severity == IssueSeverity.CRITICAL
            )
    
    return {
        "total_documents": len(docs),
        "by_status": by_status,
        "by_type": by_type,
        "total_issues_detected": total_issues,
        "critical_issues": critical_issues,
    }


# =============================================================================
# NOTARIZATION & VERIFICATION ENDPOINTS
# =============================================================================

@router.get("/notarization/{notarization_id}", response_model=NotarizationVerificationResponse)
async def verify_notarization(
    notarization_id: str,
):
    """
    Verify a document notarization record.
    
    Checks:
    - Notarization record integrity
    - Document hash validity
    - Storage location
    - Registry status (if registered)
    
    Returns verification status and details.
    """
    if not HAS_NOTARIZATION:
        raise HTTPException(
            status_code=503,
            detail="Notarization service not available"
        )
    
    try:
        notarization_service = await get_notarization_service()
        result = await notarization_service.verify_notarization(notarization_id)
        
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Notarization not found")
        
        return NotarizationVerificationResponse(
            status=result.get("status", "unknown"),
            verified=result.get("verified", False),
            notarization_id=result.get("notarization_id", notarization_id),
            document_id=result.get("document_id", ""),
            file_hash=result.get("file_hash", ""),
            file_size=result.get("file_size", 0),
            original_filename=result.get("original_filename", ""),
            notarized_at=result.get("notarized_at", ""),
            storage_location=result.get("storage_location", ""),
            content_verified=result.get("content_verified"),
            content_status=result.get("content_status"),
            registry_status=result.get("registry_status"),
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Notarization verification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.get("/notarization/{notarization_id}/chain-of-custody", response_model=ChainOfCustodyResponse)
async def get_notarization_chain_of_custody(
    notarization_id: str,
):
    """
    Get complete chain of custody for a notarized document.
    
    Shows:
    - Document upload (with hash and timestamp)
    - Registry registrations
    - Processing events
    - Modifications/supersedes
    - Archive status
    
    Useful for legal proceedings to prove document authenticity.
    """
    if not HAS_NOTARIZATION:
        raise HTTPException(
            status_code=503,
            detail="Notarization service not available"
        )
    
    try:
        notarization_service = await get_notarization_service()
        chain = await notarization_service.create_chain_of_custody(notarization_id)
        
        if not chain:
            raise HTTPException(
                status_code=404,
                detail=f"Notarization {notarization_id} not found"
            )
        
        # Convert to response format
        events = [
            ChainOfCustodyEvent(
                event=evt.get("event", "unknown"),
                timestamp=evt.get("timestamp", ""),
                actor=evt.get("actor", "system"),
                action=evt.get("action", ""),
                hash=evt.get("hash"),
                location=evt.get("location"),
            )
            for evt in chain
        ]
        
        return ChainOfCustodyResponse(
            notarization_id=notarization_id,
            events=events,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chain of custody retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chain of custody: {str(e)}"
        )


# =============================================================================
# ENUM ENDPOINTS (for frontend)
# =============================================================================

@router.get("/enums/document-types")
async def get_document_types():
    """Get all document types."""
    return [{"value": t.value, "name": t.name} for t in DocumentType]


@router.get("/enums/intake-statuses")
async def get_intake_statuses():
    """Get all intake statuses."""
    return [{"value": s.value, "name": s.name} for s in IntakeStatus]


@router.get("/enums/issue-severities")
async def get_issue_severities():
    """Get all issue severity levels."""
    return [{"value": s.value, "name": s.name} for s in IssueSeverity]


@router.get("/enums/languages")
async def get_languages():
    """Get supported languages."""
    return [{"value": l.value, "name": l.name} for l in LanguageCode]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _doc_to_response(doc) -> IntakeDocumentResponse:
    """Convert IntakeDocument to response model."""
    extraction_response = None
    
    if doc.extraction:
        ext = doc.extraction
        extraction_response = ExtractionResultResponse(
            doc_type=ext.doc_type.value,
            doc_type_confidence=ext.doc_type_confidence,
            language=ext.language.value,
            page_count=ext.page_count,
            word_count=ext.word_count,
            summary=ext.summary,
            key_points=ext.key_points,
            dates=[
                ExtractedDateResponse(
                    date=d.date.isoformat(),
                    label=d.label,
                    confidence=d.confidence,
                    source_text=d.source_text,
                    is_deadline=d.is_deadline,
                    days_until=d.days_until,
                )
                for d in ext.dates
            ],
            parties=[
                ExtractedPartyResponse(
                    name=p.name,
                    role=p.role,
                    address=p.address,
                    phone=p.phone,
                    email=p.email,
                    confidence=p.confidence,
                )
                for p in ext.parties
            ],
            amounts=[
                ExtractedAmountResponse(
                    amount=a.amount,
                    label=a.label,
                    currency=a.currency,
                    period=a.period,
                    confidence=a.confidence,
                    source_text=a.source_text,
                )
                for a in ext.amounts
            ],
            issues=[
                DetectedIssueResponse(
                    issue_id=i.issue_id,
                    severity=i.severity.value,
                    title=i.title,
                    description=i.description,
                    affected_text=i.affected_text,
                    legal_basis=i.legal_basis,
                    recommended_action=i.recommended_action,
                    deadline=i.deadline.isoformat() if i.deadline else None,
                    related_laws=i.related_laws,
                )
                for i in ext.issues
            ],
            extracted_at=ext.extracted_at.isoformat(),
        )
    
    return IntakeDocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status.value,
        status_message=doc.status_message,
        progress_percent=doc.progress_percent,
        extraction=extraction_response,
        uploaded_at=doc.uploaded_at.isoformat(),
        processed_at=doc.processed_at.isoformat() if doc.processed_at else None,
    )
