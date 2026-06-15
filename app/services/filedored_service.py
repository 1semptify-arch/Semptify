"""Filedored Vault Post-Processing Service — overlay-based sorting, dedup, AI classification."""
import logging
from typing import Optional
from datetime import datetime, timezone

from app.core.vault_paths import (
    VAULT_FILEDORED,
    VAULT_FILEDORED_PDF,
    VAULT_FILEDORED_WORD,
    VAULT_FILEDORED_TEXT,
    VAULT_FILEDORED_SPREADS,
    VAULT_FILEDORED_PRESENTS,
    VAULT_FILEDORED_SCANS,
    VAULT_FILEDORED_DUPLICATES,
    VAULT_FILEDORED_OTHER,
    VAULT_FILEDORED_AI,
    VAULT_FILEDORED_AI_LEASE,
    VAULT_FILEDORED_AI_NOTICE,
    VAULT_FILEDORED_AI_EVIDENCE,
    VAULT_FILEDORED_AI_PHOTO,
    VAULT_FILEDORED_AI_INVOICE,
    VAULT_FILEDORED_AI_COMM,
    VAULT_FILEDORED_AI_UNKNOWN,
)
from app.core.overlay_types import OverlayType
from app.models.unified_overlay_models import CreateOverlayRequest

logger = logging.getLogger(__name__)

DOCUMENT_EXTENSIONS = {
    "pdf": VAULT_FILEDORED_PDF,
    "doc": VAULT_FILEDORED_WORD,
    "docx": VAULT_FILEDORED_WORD,
    "txt": VAULT_FILEDORED_TEXT,
    "rtf": VAULT_FILEDORED_TEXT,
    "xls": VAULT_FILEDORED_SPREADS,
    "xlsx": VAULT_FILEDORED_SPREADS,
    "ppt": VAULT_FILEDORED_PRESENTS,
    "pptx": VAULT_FILEDORED_PRESENTS,
    "jpg": VAULT_FILEDORED_SCANS,
    "jpeg": VAULT_FILEDORED_SCANS,
    "png": VAULT_FILEDORED_SCANS,
}

AI_CLASSIFICATION_MAP = {
    "lease": VAULT_FILEDORED_AI_LEASE,
    "notice": VAULT_FILEDORED_AI_NOTICE,
    "evidence": VAULT_FILEDORED_AI_EVIDENCE,
    "photo": VAULT_FILEDORED_AI_PHOTO,
    "invoice": VAULT_FILEDORED_AI_INVOICE,
    "communication": VAULT_FILEDORED_AI_COMM,
    "unknown": VAULT_FILEDORED_AI_UNKNOWN,
}


def ai_classify_document(vault_id: str, content: bytes, filename: str) -> str:
    """
    AI classification hook.
    Expected return values: lease, notice, evidence, photo, invoice, communication, unknown
    
    Integration points:
    - SWE 1.6: Replace this function with SWE 1.6 API call
    - Local model: Replace with local model inference
    - External API: Replace with external classification service
    """
    # TODO: Integrate with SWE 1.6 or local model
    # Example SWE 1.6 integration:
    # from app.services.swe16_client import classify_document
    # return classify_document(content, filename)
    
    # Example local model integration:
    # from app.services.local_classifier import predict
    # return predict(content, filename)
    
    return "unknown"


async def process_uploaded_document(
    vault_id: str,
    user_id: str,
    filename: str,
    content: bytes,
    sha256_hash: str,
    enable_ai: bool = False,
    overlay_manager=None,
) -> dict:
    """
    Post-process an uploaded document through filedored system using overlays.
    
    Instead of moving files, creates overlay references that organize documents
    into the filedored folder structure virtually.
    
    Returns dict with:
        - status: "sorted", "ai_classified", "skipped", "error"
        - overlay_path: virtual path in filedored structure
        - ai_label: if AI classification was used
    """
    if overlay_manager is None:
        from app.services.unified_overlay_manager import get_unified_overlay_manager
        overlay_manager = get_unified_overlay_manager()
    
    try:
        # AI classification (optional)
        if enable_ai:
            label = ai_classify_document(vault_id, content, filename)
            if label != "unknown":
                target_path = AI_CLASSIFICATION_MAP.get(label, VAULT_FILEDORED_AI_UNKNOWN)
                overlay_data = {
                    "original_vault_id": vault_id,
                    "filedored_category": label,
                    "classification_method": "ai",
                    "classified_at": datetime.now(timezone.utc).isoformat(),
                }
                
                overlay_req = CreateOverlayRequest(
                    vault_id=vault_id,
                    user_id=user_id,
                    overlay_type=OverlayType.FILEDORED,
                    overlay_path=target_path,
                    overlay_data=overlay_data,
                )
                
                await overlay_manager.create_overlay(overlay_req)
                
                return {
                    "status": "ai_classified",
                    "overlay_path": target_path,
                    "ai_label": label,
                }
        
        # Extension-based routing
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        target_path = DOCUMENT_EXTENSIONS.get(ext, VAULT_FILEDORED_OTHER)
        
        overlay_data = {
            "original_vault_id": vault_id,
            "filedored_category": "extension_based",
            "file_extension": ext,
            "sorted_at": datetime.now(timezone.utc).isoformat(),
        }
        
        overlay_req = CreateOverlayRequest(
            vault_id=vault_id,
            user_id=user_id,
            overlay_type=OverlayType.FILEDORED,
            overlay_path=target_path,
            overlay_data=overlay_data,
        )
        
        await overlay_manager.create_overlay(overlay_req)
        
        return {
            "status": "sorted",
            "overlay_path": target_path,
            "extension": ext,
        }
        
    except Exception as e:
        logger.error("Filedored processing failed for %s: %s", vault_id, e)
        return {
            "status": "error",
            "error": str(e),
        }


async def ensure_filedored_folders(vault_client) -> dict:
    """
    Ensure all filedored folders exist in the vault.
    Returns dict with folder creation status.
    """
    from app.sdk.vault.folder_spec import VaultFolderSpec
    
    filedored_spec = VaultFolderSpec(
        name="filedored",
        folders=[
            VAULT_FILEDORED,
            VAULT_FILEDORED_PDF,
            VAULT_FILEDORED_WORD,
            VAULT_FILEDORED_TEXT,
            VAULT_FILEDORED_SPREADS,
            VAULT_FILEDORED_PRESENTS,
            VAULT_FILEDORED_SCANS,
            VAULT_FILEDORED_DUPLICATES,
            VAULT_FILEDORED_OTHER,
            VAULT_FILEDORED_AI,
            VAULT_FILEDORED_AI_LEASE,
            VAULT_FILEDORED_AI_NOTICE,
            VAULT_FILEDORED_AI_EVIDENCE,
            VAULT_FILEDORED_AI_PHOTO,
            VAULT_FILEDORED_AI_INVOICE,
            VAULT_FILEDORED_AI_COMM,
            VAULT_FILEDORED_AI_UNKNOWN,
        ],
    )
    
    result = await vault_client.create_folders(filedored_spec)
    return {
        "status": "complete" if result.all_ok else "partial",
        "folders_created": result.created_folders,
        "folders_failed": result.failed_folders,
    }
