"""
Unified Overlay Manager
=======================

=============================================================================
SSOT — OVERLAYS ARE THE ONLY ACCESS MECHANISM
=============================================================================
The raw document file stored in the vault is IMMUTABLE and UNTOUCHED.
No Semptify process reads, parses, or modifies the raw file directly.

Every process that needs to work with a document — OCR, classification,
timeline extraction, letter generation, briefcase display, court packet
assembly — does so EXCLUSIVELY through overlays.

An overlay is a structured record stored in the user's cloud storage that
describes what was found in, extracted from, or annotated on a document.
The document itself is never touched after vault storage.

Rule: A document that has no overlay does not exist to Semptify processes.
Rule: A document that is uncertified (no registry_id) may not receive overlays.
Rule: All overlays are stored in the USER's cloud storage — never on our servers.

Overlay lifecycle:
  1. Vault stores raw file → issues vault_id + certificate
  2. Registry certifies → issues registry_id (sem_id)
  3. VAULT_UPLOAD_MANIFEST overlay created → document is now visible
  4. Downstream processes create additional overlays (extraction, classification, etc.)
  5. All reads go through overlay — raw file is never re-opened by Semptify
=============================================================================

Core Principle: Original documents NEVER get modified.
All mutations happen in overlay layers stored in user's cloud storage.
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from app.core.overlay_types import OverlayType, get_overlay_category
from app.core.vault_paths import (
    VAULT_OVERLAYS,
    VAULT_OVERLAY_REGISTRY,
    VAULT_OVERLAY_DOCUMENTS,
)
from app.models.unified_overlay_models import (
    UnifiedOverlay,
    CreateOverlayRequest,
    CreateOverlayResponse,
    GetOverlaysResponse,
    DocumentViewResponse,
)

logger = logging.getLogger(__name__)


class UnifiedOverlayManager:
    """
    Manages all overlay operations for a user.
    
    All methods are async and cloud-based. No local state is maintained.
    The user's cloud storage (Google Drive, Dropbox, etc.) is the single
    source of truth for overlay data.
    """
    
    def __init__(self, storage_provider, user_id: str):
        """
        Initialize overlay manager for a user.
        
        Args:
            storage_provider: Cloud storage adapter (GoogleDriveStorage, etc.)
            user_id: User identifier for ownership tracking
        """
        self.storage = storage_provider
        self.user_id = user_id
    
    # ==========================================================================
    # Core Operations
    # ==========================================================================
    
    async def create_overlay(self, request: CreateOverlayRequest) -> CreateOverlayResponse:
        """
        Create a new overlay in user's cloud storage.
        
        Args:
            request: Overlay creation request
            
        Returns:
            CreateOverlayResponse with overlay_id or error message
        """
        try:
            # Build overlay object
            overlay = UnifiedOverlay(
                overlay_type=request.overlay_type,
                document_id=request.document_id,
                vault_path=request.vault_path,
                created_by=self.user_id,
                payload=request.payload,
                metadata=request.metadata or {},
                ephemeral=request.ephemeral,
            )
            
            # Skip persistence for ephemeral overlays
            if overlay.ephemeral:
                return CreateOverlayResponse(
                    success=True,
                    overlay_id=overlay.overlay_id,
                    overlay_type=overlay.overlay_type,
                    message="Ephemeral overlay created (not persisted)",
                )
            
            # Ensure overlay folders exist
            await self._ensure_overlay_folders()
            
            # Compute hash for security chain
            overlay.overlay_hash = self._compute_hash(overlay)
            
            # Get previous overlay for chaining (if exists)
            prev_overlay = await self._get_latest_overlay(request.document_id)
            if prev_overlay:
                overlay.prev_overlay_hash = prev_overlay.overlay_hash
            
            # Save to cloud storage
            overlay_path = self._get_overlay_path(overlay.overlay_id)
            await self._save_overlay_to_cloud(overlay, overlay_path)
            
            # Update registry
            await self._update_registry(overlay)
            
            logger.info(
                f"Created overlay {overlay.overlay_id} "
                f"(type={overlay.overlay_type.value}, doc={request.document_id})"
            )
            
            return CreateOverlayResponse(
                success=True,
                overlay_id=overlay.overlay_id,
                overlay_type=overlay.overlay_type,
                message="Overlay created successfully",
            )
            
        except Exception as e:
            logger.error(f"Failed to create overlay: {e}", exc_info=True)
            return CreateOverlayResponse(
                success=False,
                message=f"Error creating overlay: {str(e)}",
            )
    
    async def get_overlays(
        self,
        document_id: Optional[str] = None,
        overlay_type: Optional[OverlayType] = None,
        category: Optional[str] = None,
        created_by: Optional[str] = None,
        include_ephemeral: bool = False,
    ) -> GetOverlaysResponse:
        """
        Query overlays from cloud storage.
        
        Returns overlays matching the specified filters.
        Ephemeral overlays are never returned unless include_ephemeral=True.
        """
        try:
            # Load from registry (more efficient than listing files)
            registry = await self._load_registry()
            overlays = []
            
            for overlay_data in registry.values():
                overlay = UnifiedOverlay(**overlay_data)
                
                # Apply filters
                if document_id and overlay.document_id != document_id:
                    continue
                if overlay_type and overlay.overlay_type != overlay_type:
                    continue
                if category and get_overlay_category(overlay.overlay_type) != category:
                    continue
                if created_by and overlay.created_by != created_by:
                    continue
                if overlay.ephemeral and not include_ephemeral:
                    continue
                
                overlays.append(overlay)
            
            # Sort by created_at (newest first)
            overlays.sort(key=lambda x: x.created_at, reverse=True)
            
            return GetOverlaysResponse(
                success=True,
                overlays=overlays,
                count=len(overlays),
                filters_applied={
                    "document_id": document_id,
                    "overlay_type": overlay_type.value if overlay_type else None,
                    "category": category,
                    "created_by": created_by,
                    "include_ephemeral": include_ephemeral,
                },
            )
            
        except Exception as e:
            logger.error(f"Failed to get overlays: {e}", exc_info=True)
            return GetOverlaysResponse(
                success=False,
                overlays=[],
                count=0,
                filters_applied={},
            )
    
    async def get_overlay(self, overlay_id: str) -> Optional[UnifiedOverlay]:
        """Get a single overlay by ID."""
        try:
            overlay_path = self._get_overlay_path(overlay_id)
            content = await self.storage.download_file(overlay_path)
            if not content:
                return None
            
            data = json.loads(content.decode("utf-8"))
            return UnifiedOverlay(**data)
            
        except Exception as e:
            logger.warning(f"Failed to load overlay {overlay_id}: {e}")
            return None
    
    async def update_overlay(
        self,
        overlay_id: str,
        payload: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Update an existing overlay.
        
        Note: Some fields are immutable (overlay_id, document_id, vault_path, created_by).
        Only payload and metadata can be updated.
        """
        try:
            overlay = await self.get_overlay(overlay_id)
            if not overlay:
                logger.warning(f"Overlay {overlay_id} not found for update")
                return False
            
            # Verify ownership
            if overlay.created_by != self.user_id:
                logger.warning(f"User {self.user_id} cannot update overlay owned by {overlay.created_by}")
                return False
            
            # Update fields
            if payload is not None:
                overlay.payload = payload
            if metadata is not None:
                overlay.metadata = {**overlay.metadata, **metadata}
            
            overlay.updated_at = datetime.utcnow()
            overlay.overlay_hash = self._compute_hash(overlay)
            
            # Save back to cloud
            overlay_path = self._get_overlay_path(overlay_id)
            await self._save_overlay_to_cloud(overlay, overlay_path)
            
            # Update registry
            await self._update_registry(overlay)
            
            logger.info(f"Updated overlay {overlay_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update overlay {overlay_id}: {e}", exc_info=True)
            return False
    
    async def delete_overlay(self, overlay_id: str) -> bool:
        """Delete an overlay from cloud storage."""
        try:
            overlay = await self.get_overlay(overlay_id)
            if not overlay:
                logger.warning(f"Overlay {overlay_id} not found for deletion")
                return False
            
            # Verify ownership
            if overlay.created_by != self.user_id:
                logger.warning(f"User {self.user_id} cannot delete overlay owned by {overlay.created_by}")
                return False
            
            # Delete from cloud
            overlay_path = self._get_overlay_path(overlay_id)
            await self.storage.delete_file(overlay_path)
            
            # Update registry
            await self._remove_from_registry(overlay_id)
            
            logger.info(f"Deleted overlay {overlay_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete overlay {overlay_id}: {e}", exc_info=True)
            return False
    
    # ==========================================================================
    # Document View Composition
    # ==========================================================================
    
    async def compose_document_view(
        self,
        document_id: str,
        overlay_ids: list[str],
        apply_redactions: bool = True,
    ) -> DocumentViewResponse:
        """
        Compose a view of a document with overlays applied.
        
        This is a query operation - no files are created. The result is a
        render specification that can be used to generate a view on-demand.
        """
        try:
            # Load document metadata
            overlays = []
            for overlay_id in overlay_ids:
                overlay = await self.get_overlay(overlay_id)
                if overlay and overlay.document_id == document_id:
                    overlays.append(overlay)
            
            # Sort overlays by type (redactions last if applying)
            if apply_redactions:
                overlays.sort(key=lambda x: 1 if get_overlay_category(x.overlay_type) == "redaction" else 0)
            
            # Build view specification
            view_spec = {
                "document_id": document_id,
                "original_path": overlays[0].vault_path if overlays else None,
                "overlays_applied": [o.overlay_id for o in overlays],
                "overlay_types": [o.overlay_type.value for o in overlays],
                "render_instructions": self._build_render_instructions(overlays),
            }
            
            return DocumentViewResponse(
                success=True,
                document_id=document_id,
                applied_overlays=[o.overlay_id for o in overlays],
                message="Document view composed successfully",
            )
            
        except Exception as e:
            logger.error(f"Failed to compose document view: {e}", exc_info=True)
            return DocumentViewResponse(
                success=False,
                document_id=document_id,
                applied_overlays=[],
                message=f"Error composing view: {str(e)}",
            )
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    async def _ensure_overlay_folders(self) -> None:
        """Ensure overlay folder structure exists in cloud storage."""
        try:
            await self.storage.create_folder(VAULT_OVERLAYS)
            await self.storage.create_folder(VAULT_OVERLAY_DOCUMENTS)
        except Exception as e:
            logger.debug(f"Folder creation skipped (may already exist): {e}")
    
    async def _load_registry(self) -> dict:
        """Load overlay registry from cloud storage."""
        try:
            content = await self.storage.download_file(VAULT_OVERLAY_REGISTRY)
            if not content:
                return {}
            return json.loads(content.decode("utf-8"))
        except Exception as e:
            logger.debug(f"Registry load failed (creating new): {e}")
            return {}
    
    async def _update_registry(self, overlay: UnifiedOverlay) -> None:
        """Update registry with new or modified overlay."""
        registry = await self._load_registry()
        registry[overlay.overlay_id] = overlay.dict()
        await self._save_registry(registry)
    
    async def _remove_from_registry(self, overlay_id: str) -> None:
        """Remove overlay from registry."""
        registry = await self._load_registry()
        if overlay_id in registry:
            del registry[overlay_id]
            await self._save_registry(registry)
    
    async def _save_registry(self, registry: dict) -> None:
        """Save registry to cloud storage."""
        content = json.dumps(registry, indent=2, default=str).encode("utf-8")
        await self.storage.upload_file(
            file_content=content,
            destination_path=VAULT_OVERLAYS,
            filename="registry.json",
            mime_type="application/json",
        )
    
    async def _save_overlay_to_cloud(self, overlay: UnifiedOverlay, path: str) -> None:
        """Save overlay JSON to cloud storage."""
        content = json.dumps(overlay.dict(), indent=2, default=str).encode("utf-8")
        await self.storage.upload_file(
            file_content=content,
            destination_path=VAULT_OVERLAY_DOCUMENTS,
            filename=f"{overlay.overlay_id}.json",
            mime_type="application/json",
        )
    
    def _get_overlay_path(self, overlay_id: str) -> str:
        """Get cloud storage path for an overlay file."""
        return f"{VAULT_OVERLAY_DOCUMENTS}/{overlay_id}.json"
    
    async def _get_latest_overlay(self, document_id: str) -> Optional[UnifiedOverlay]:
        """Get the most recent overlay for a document (for chaining)."""
        response = await self.get_overlays(document_id=document_id)
        if response.overlays:
            return response.overlays[0]  # Already sorted by created_at desc
        return None
    
    def _compute_hash(self, overlay: UnifiedOverlay) -> str:
        """Compute SHA-256 hash of overlay content for security chain."""
        # Exclude hash fields from hash computation
        data = overlay.dict(exclude={"overlay_hash", "prev_overlay_hash", "updated_at"})
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    
    def _build_render_instructions(self, overlays: list[UnifiedOverlay]) -> list[dict]:
        """Build render instructions from overlays."""
        instructions = []
        for overlay in overlays:
            instructions.append({
                "overlay_id": overlay.overlay_id,
                "type": overlay.overlay_type.value,
                "category": get_overlay_category(overlay.overlay_type),
                "payload": overlay.payload,
            })
        return instructions


# =============================================================================
# Factory Function
# =============================================================================

async def get_unified_overlay_manager(storage_provider, user_id: str) -> UnifiedOverlayManager:
    """Factory function to create overlay manager."""
    return UnifiedOverlayManager(storage_provider, user_id)
