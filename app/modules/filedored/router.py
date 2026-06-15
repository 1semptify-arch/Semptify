"""Filedored Router — Virtual document organization post-processing."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.filedored_service import process_uploaded_document, ensure_filedored_folders
from app.services.vault_upload_service import VaultUploadService
from app.services.unified_overlay_manager import get_unified_overlay_manager
from app.core.storage_factory import get_storage_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/filedored", tags=["Filedored"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ProcessRequest(BaseModel):
    """Request to process documents through filedored system."""
    vault_ids: Optional[List[str]] = None
    process_all: bool = False
    enable_ai: bool = False


class ProcessResponse(BaseModel):
    """Response from filedored processing."""
    processed: List[dict]
    errors: List[str]
    total: int


class FolderStatusResponse(BaseModel):
    """Response for folder status check."""
    status: str
    folders_created: List[str]
    folders_failed: List[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/process", response_model=ProcessResponse)
async def process_documents(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    user: StorageUser = Depends(require_user),
):
    """
    Process documents through filedored system.
    
    Can process specific documents by vault_id or all unprocessed documents.
    """
    processed = []
    errors = []
    
    try:
        # Get vault upload service
        vault_service = VaultUploadService()
        
        # Determine which documents to process
        if request.process_all:
            # Get all user documents
            documents = await vault_service.get_user_documents(user.user_id)
            vault_ids = [doc.vault_id for doc in documents]
        elif request.vault_ids:
            vault_ids = request.vault_ids
        else:
            raise HTTPException(status_code=400, detail="Either vault_ids or process_all must be specified")
        
        # Process each document
        for vault_id in vault_ids:
            try:
                # Get document details
                doc = await vault_service.get_document(vault_id, user.user_id)
                if not doc:
                    errors.append(f"Document {vault_id} not found")
                    continue
                
                # Process through filedored
                result = await process_uploaded_document(
                    vault_id=vault_id,
                    user_id=user.user_id,
                    filename=doc.filename,
                    content=await vault_service._get_document_content(doc),
                    sha256_hash=doc.sha256_hash,
                    enable_ai=request.enable_ai,
                )
                
                processed.append({
                    "vault_id": vault_id,
                    "filename": doc.filename,
                    "result": result,
                })
                
            except Exception as e:
                logger.error("Failed to process document %s: %s", vault_id, e)
                errors.append(f"Failed to process {vault_id}: {str(e)}")
        
        return ProcessResponse(
            processed=processed,
            errors=errors,
            total=len(vault_ids),
        )
        
    except Exception as e:
        logger.error("Filedored processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/folders/status", response_model=FolderStatusResponse)
async def check_folders(user: StorageUser = Depends(require_user)):
    """Check and ensure filedored folders exist in vault."""
    try:
        # Get storage provider
        storage_provider = await get_storage_provider(user.user_id)
        if not storage_provider:
            raise HTTPException(status_code=400, detail="No storage provider found")
        
        # Create vault client
        from app.sdk.vault.client import VaultClient
        from app.sdk.vault.folder_spec import TENANT_VAULT
        
        vault_client = VaultClient(
            provider=storage_provider,
            access_token=storage_provider.access_token,
            user_id=user.user_id,
            folder_spec=TENANT_VAULT,
        )
        
        # Ensure filedored folders
        result = await ensure_filedored_folders(vault_client)
        
        return FolderStatusResponse(
            status=result["status"],
            folders_created=result.get("folders_created", []),
            folders_failed=result.get("folders_failed", []),
        )
        
    except Exception as e:
        logger.error("Failed to check filedored folders: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browse/{folder:path}")
async def browse_folder(
    folder: str,
    user: StorageUser = Depends(require_user),
):
    """Browse documents in a filedored virtual folder."""
    try:
        # Get overlay manager
        storage_provider = await get_storage_provider(user.user_id)
        if not storage_provider:
            raise HTTPException(status_code=400, detail="No storage provider found")
        
        overlay_manager = get_unified_overlay_manager(storage_provider, user.user_id)
        
        # Query overlays for this folder
        from app.core.overlay_types import OverlayType
        from app.core.vault_paths import VAULT_FILEDORED
        
        # Build folder path
        if not folder.startswith(VAULT_FILEDORED):
            folder_path = f"{VAULT_FILEDORED}/{folder}"
        else:
            folder_path = folder
        
        # Get overlays in this folder
        overlays = await overlay_manager.get_overlays_by_path(
            overlay_type=OverlayType.FILEDORED,
            path_prefix=folder_path,
        )
        
        # Build response with document details
        documents = []
        for overlay in overlays:
            documents.append({
                "vault_id": overlay.document_id,
                "filename": overlay.payload.get("original_filename", "Unknown"),
                "overlay_path": overlay.overlay_path,
                "filedored_category": overlay.payload.get("filedored_category"),
                "ai_label": overlay.payload.get("ai_label"),
                "extension": overlay.payload.get("extension"),
                "created_at": overlay.created_at,
            })
        
        return {
            "folder": folder_path,
            "documents": documents,
            "count": len(documents),
        }
        
    except Exception as e:
        logger.error("Failed to browse folder %s: %s", folder, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders")
async def list_folders(user: StorageUser = Depends(require_user)):
    """List all filedored virtual folders and their document counts."""
    try:
        from app.core.overlay_types import OverlayType
        from app.core.vault_paths import (
            VAULT_FILEDORED_PDF,
            VAULT_FILEDORED_WORD,
            VAULT_FILEDORED_TEXT,
            VAULT_FILEDORED_SPREADS,
            VAULT_FILEDORED_PRESENTS,
            VAULT_FILEDORED_SCANS,
            VAULT_FILEDORED_DUPLICATES,
            VAULT_FILEDORED_OTHER,
            VAULT_FILEDORED_AI,
        )
        
        # Get storage provider and overlay manager
        storage_provider = await get_storage_provider(user.user_id)
        if not storage_provider:
            raise HTTPException(status_code=400, detail="No storage provider found")
        
        overlay_manager = get_unified_overlay_manager(storage_provider, user.user_id)
        
        # Define folders to check
        folders = {
            "Documents/PDF": VAULT_FILEDORED_PDF,
            "Documents/Word": VAULT_FILEDORED_WORD,
            "Documents/Text": VAULT_FILEDORED_TEXT,
            "Documents/Spreadsheets": VAULT_FILEDORED_SPREADS,
            "Documents/Presentations": VAULT_FILEDORED_PRESENTS,
            "Scans/Images": VAULT_FILEDORED_SCANS,
            "__DUPLICATES__": VAULT_FILEDORED_DUPLICATES,
            "__OTHER__": VAULT_FILEDORED_OTHER,
            "__AI_CLASSIFIED__": VAULT_FILEDORED_AI,
        }
        
        # Count documents in each folder
        folder_counts = {}
        for name, path in folders.items():
            overlays = await overlay_manager.get_overlays_by_path(
                overlay_type=OverlayType.FILEDORED,
                path_prefix=path,
            )
            folder_counts[name] = {
                "path": path,
                "count": len(overlays),
            }
        
        return {
            "folders": folder_counts,
            "total_processed": sum(f["count"] for f in folder_counts.values()),
        }
        
    except Exception as e:
        logger.error("Failed to list folders: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for filedored module."""
    return {"status": "healthy", "module": "filedored"}
