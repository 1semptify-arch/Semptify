"""
DEPRECATED: Old Document Overlay System

⚠️ WARNING: This module is deprecated. Use `app/services/unified_overlay_manager.py` instead.

The unified overlay system provides:
- Cloud-only storage (no local files)
- Single source of truth for all overlay types
- Better integration with vault paths

Migration:
- Old: OverlayManager(storage, token) → creates overlays in Vault/.overlay/
- New: UnifiedOverlayManager(storage, user_id) → creates overlays in Vault/overlays/

This file will be removed in a future release.
"""

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.vault_paths import VAULT_OVERLAY, VAULT_OVERLAY_REGISTRY


@dataclass
class DocumentOverlay:
    """Metadata for a document overlay."""
    overlay_id: str
    original_id: str  # Reference to original document in Vault/documents/
    original_path: str  # Path in user's cloud storage
    overlay_path: str  # Path to working copy
    created_at: str
    document_type: str = "unknown"  # lease, notice, correspondence, evidence, etc.
    extracted_dates: list = None
    extracted_parties: list = None
    summary: str = ""
    status: str = "active"  # active, processing, error, archived
    
    def __post_init__(self):
        if self.extracted_dates is None:
            self.extracted_dates = []
        if self.extracted_parties is None:
            self.extracted_parties = []
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "DocumentOverlay":
        return cls(**data)


class OverlayManager:
    """
    Manages document overlays for safe processing.
    
    All Semptify features that need to read/modify document content
    must use overlays, never touch originals.
    """
    
    OVERLAY_FOLDER = VAULT_OVERLAY
    REGISTRY_FILE = VAULT_OVERLAY_REGISTRY
    
    def __init__(self, storage_provider, access_token: str):
        self.storage = storage_provider
        self.token = access_token
    
    async def create_overlay(self, original_id: str, original_path: str) -> DocumentOverlay:
        """
        Create an overlay for processing.
        
        1. Read original from Vault/documents/
        2. Copy to Vault/.overlay/
        3. Register overlay metadata
        4. Return overlay for processing
        """
        overlay_id = f"ovl_{original_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Copy original to overlay folder
        original_bytes = await self.storage.download_file(original_path)
        await self.storage.create_folder(self.OVERLAY_FOLDER)
        await self.storage.upload_file(
            file_content=original_bytes,
            destination_path=self.OVERLAY_FOLDER,
            filename=f"{overlay_id}.pdf",
            mime_type="application/pdf",
        )
        overlay_path = f"{self.OVERLAY_FOLDER}/{overlay_id}.pdf"
        
        # Create overlay record
        overlay = DocumentOverlay(
            overlay_id=overlay_id,
            original_id=original_id,
            original_path=original_path,
            overlay_path=overlay_path,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="active"
        )
        
        # Register overlay
        await self._register_overlay(overlay)
        
        return overlay
    
    async def get_overlay(self, overlay_id: str) -> Optional[DocumentOverlay]:
        """Get overlay by ID."""
        registry = await self._load_registry()
        if overlay_id in registry:
            return DocumentOverlay.from_dict(registry[overlay_id])
        return None
    
    async def update_overlay(self, overlay: DocumentOverlay):
        """Update overlay metadata after processing."""
        registry = await self._load_registry()
        registry[overlay.overlay_id] = overlay.to_dict()
        await self._save_registry(registry)
    
    async def list_overlays(self, original_id: str = None) -> list:
        """List all overlays, optionally filtered by original document."""
        registry = await self._load_registry()
        overlays = [DocumentOverlay.from_dict(d) for d in registry.values()]
        
        if original_id:
            overlays = [o for o in overlays if o.original_id == original_id]
        
        return overlays
    
    async def _load_registry(self) -> Dict[str, Any]:
        """Load overlay registry from storage."""
        try:
            raw = await self.storage.download_file(self.REGISTRY_FILE)
            if not raw:
                return {}
            registry = json.loads(raw.decode("utf-8"))
            if isinstance(registry, dict):
                return registry
            return {}
        except Exception:
            return {}
    
    async def _save_registry(self, registry: Dict[str, Any]):
        """Save overlay registry to storage."""
        await self.storage.create_folder(self.OVERLAY_FOLDER)
        payload = json.dumps(registry, ensure_ascii=True, indent=2).encode("utf-8")
        await self.storage.upload_file(
            file_content=payload,
            destination_path=self.OVERLAY_FOLDER,
            filename="registry.json",
            mime_type="application/json",
        )
    
    async def _register_overlay(self, overlay: DocumentOverlay):
        """Register new overlay in registry."""
        registry = await self._load_registry()
        registry[overlay.overlay_id] = overlay.to_dict()
        await self._save_registry(registry)
    
    async def get_processing_copy(self, overlay: DocumentOverlay) -> bytes:
        """
        Get the overlay file content for processing.
        
        This is the ONLY way features should access document content.
        Never read original directly.
        """
        return await self.storage.download_file(overlay.overlay_path)
    
    async def save_processing_result(self, overlay: DocumentOverlay, content: bytes):
        """
        Save modified content back to overlay.
        
        Original stays untouched. Only overlay is modified.
        """
        filename = overlay.overlay_path.split("/")[-1]
        destination_path = "/".join(overlay.overlay_path.split("/")[:-1])
        await self.storage.upload_file(
            file_content=content,
            destination_path=destination_path,
            filename=filename,
            mime_type="application/pdf",
        )


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_overlay_for_processing(original_id: str, original_path: str, 
                                         provider: str, access_token: str) -> DocumentOverlay:
    """
    Create an overlay for document processing.
    
    Usage:
        overlay = await create_overlay_for_processing(
            original_id="doc_123",
            original_path="Semptify5.0/Vault/documents/lease.pdf",
            provider="google_drive",
            access_token="..."
        )
        
        # Now process safely
        content = await overlay_manager.get_processing_copy(overlay)
        # ... extract dates, etc. ...
    """
    if provider == "google_drive":
        from app.services.storage.google_drive import GoogleDriveStorage
        storage = GoogleDriveStorage(access_token)
    else:
        raise ValueError(f"Provider {provider} not supported for overlays yet")
    
    manager = OverlayManager(storage, access_token)
    return await manager.create_overlay(original_id, original_path)
