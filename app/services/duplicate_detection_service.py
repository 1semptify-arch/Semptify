"""Duplicate Detection Service — Cross-vault duplicate identification via overlays."""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.models.unified_overlay_models import CreateOverlayRequest

logger = logging.getLogger(__name__)


async def detect_duplicates(
    user_id: str,
    vault_id: str,
    sha256_hash: str,
    filename: str,
    overlay_manager=None,
) -> dict:
    """
    Detect duplicates across user's vault using overlay system.
    
    Returns dict with:
        - is_duplicate: bool
        - original_vault_id: str (if duplicate)
        - duplicate_count: int (total duplicates for this hash)
    """
    if overlay_manager is None:
        from app.services.unified_overlay_manager import get_unified_overlay_manager
        from app.core.storage_factory import get_storage_provider
        
        storage_provider = await get_storage_provider(user_id)
        if not storage_provider:
            return {"is_duplicate": False, "error": "No storage provider"}
        
        overlay_manager = get_unified_overlay_manager(storage_provider, user_id)
    
    try:
        # Query for existing duplicate detection overlays with same hash
        existing_overlays = await overlay_manager.get_overlays_by_type(
            overlay_type=OverlayType.DUPLICATE_DETECTION
        )
        
        # Check if any overlay has the same hash
        for overlay in existing_overlays:
            if overlay.payload.get("sha256_hash") == sha256_hash:
                # Found a duplicate
                original_vault_id = overlay.payload.get("original_vault_id")
                duplicate_count = overlay.payload.get("duplicate_count", 1)
                
                # Create new duplicate overlay linking to original
                duplicate_overlay = CreateOverlayRequest(
                    vault_id=vault_id,
                    user_id=user_id,
                    overlay_type=OverlayType.DUPLICATE_DETECTION,
                    overlay_path="duplicates",
                    overlay_data={
                        "is_duplicate": True,
                        "original_vault_id": original_vault_id,
                        "duplicate_vault_id": vault_id,
                        "sha256_hash": sha256_hash,
                        "filename": filename,
                        "duplicate_count": duplicate_count + 1,
                        "detected_at": utc_now().isoformat(),
                    },
                )
                
                await overlay_manager.create_overlay(duplicate_overlay)
                
                # Update original overlay with new count
                original_overlay_data = overlay.payload.copy()
                original_overlay_data["duplicate_count"] = duplicate_count + 1
                original_overlay_data["last_duplicate_detected"] = utc_now().isoformat()
                
                # Note: In a real implementation, you'd update the existing overlay
                # For now, we'll create a new overlay with updated info
                update_overlay = CreateOverlayRequest(
                    vault_id=original_vault_id,
                    user_id=user_id,
                    overlay_type=OverlayType.DUPLICATE_DETECTION,
                    overlay_path="duplicates/original",
                    overlay_data=original_overlay_data,
                )
                
                await overlay_manager.create_overlay(update_overlay)
                
                logger.info(f"Duplicate detected: {vault_id} matches {original_vault_id}")
                
                return {
                    "is_duplicate": True,
                    "original_vault_id": original_vault_id,
                    "duplicate_count": duplicate_count + 1,
                }
        
        # No duplicate found - create original record
        original_overlay = CreateOverlayRequest(
            vault_id=vault_id,
            user_id=user_id,
            overlay_type=OverlayType.DUPLICATE_DETECTION,
            overlay_path="duplicates/original",
            overlay_data={
                "is_duplicate": False,
                "original_vault_id": vault_id,
                "sha256_hash": sha256_hash,
                "filename": filename,
                "duplicate_count": 1,
                "created_at": utc_now().isoformat(),
            },
        )
        
        await overlay_manager.create_overlay(original_overlay)
        
        return {
            "is_duplicate": False,
            "original_vault_id": vault_id,
            "duplicate_count": 1,
        }
        
    except Exception as e:
        logger.error("Duplicate detection failed for %s: %s", vault_id, e)
        return {
            "is_duplicate": False,
            "error": str(e),
        }


async def get_all_duplicates(user_id: str, overlay_manager=None) -> List[dict]:
    """
    Get all duplicate groups for a user.
    
    Returns list of duplicate groups, each containing:
        - sha256_hash
        - original_vault_id
        - duplicate_count
        - duplicates: list of duplicate vault_ids
    """
    if overlay_manager is None:
        from app.services.unified_overlay_manager import get_unified_overlay_manager
        from app.core.storage_factory import get_storage_provider
        
        storage_provider = await get_storage_provider(user_id)
        if not storage_provider:
            return []
        
        overlay_manager = get_unified_overlay_manager(storage_provider, user_id)
    
    try:
        # Get all duplicate detection overlays
        overlays = await overlay_manager.get_overlays_by_type(
            overlay_type=OverlayType.DUPLICATE_DETECTION
        )
        
        # Group by hash
        hash_groups: Dict[str, List[dict]] = {}
        
        for overlay in overlays:
            hash_val = overlay.payload.get("sha256_hash")
            if hash_val:
                if hash_val not in hash_groups:
                    hash_groups[hash_val] = []
                hash_groups[hash_val].append({
                    "vault_id": overlay.vault_id,
                    "filename": overlay.payload.get("filename"),
                    "is_duplicate": overlay.payload.get("is_duplicate", False),
                    "created_at": overlay.payload.get("created_at"),
                })
        
        # Build duplicate groups list
        duplicate_groups = []
        for hash_val, documents in hash_groups.items():
            if len(documents) > 1:  # Only include actual duplicates
                original = next((d for d in documents if not d.get("is_duplicate")), documents[0])
                duplicates = [d for d in documents if d.get("is_duplicate")]
                
                duplicate_groups.append({
                    "sha256_hash": hash_val,
                    "original_vault_id": original["vault_id"],
                    "original_filename": original["filename"],
                    "duplicate_count": len(documents),
                    "duplicates": duplicates,
                })
        
        return duplicate_groups
        
    except Exception as e:
        logger.error("Failed to get duplicates for user %s: %s", user_id, e)
        return []
