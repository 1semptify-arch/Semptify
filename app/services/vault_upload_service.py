"""
Vault Upload Service - Centralized Document Upload Handler

ALL document uploads from ANY module go through this service.
Documents are stored in the user's vault first, then modules access them from vault.

Flow:
1. Any module calls vault_upload_service.upload()
2. Document is stored in user's cloud storage vault (Semptify5.0/Vault/)
3. Document metadata is indexed locally for fast queries
4. Modules access documents via vault_id reference

This ensures:
- Single source of truth for all documents
- User owns their data in their cloud storage
- Modules can reference documents without storing duplicates
- Consistent security and certification across all uploads
"""

import hashlib
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.config import get_settings
from app.core.vault_paths import SEMPTIFY_ROOT, VAULT_ROOT, VAULT_DOCUMENTS, VAULT_CERTIFICATES
from app.core.overlay_types import OverlayType
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Import storage provider
try:
    from app.services.storage import get_provider
    HAS_STORAGE = True
except ImportError:
    HAS_STORAGE = False
    logger.warning("Storage provider not available")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class VaultDocument:
    """A document stored in user's vault."""
    vault_id: str  # Primary identifier
    user_id: str
    filename: str  # Original filename
    safe_filename: str  # Safe filename in vault (uuid.ext)
    sha256_hash: str
    file_size: int
    mime_type: str
    document_type: Optional[str]  # lease, notice, photo, etc.
    description: Optional[str]
    tags: list[str]
    storage_path: str  # Path in cloud storage
    storage_provider: str  # google_drive, dropbox, onedrive, local
    certificate_id: Optional[str]
    uploaded_at: str
    # Processing state
    processed: bool = False
    extracted_data: Optional[dict] = None
    # Source tracking
    source_module: str = "direct"  # Which module initiated upload
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "VaultDocument":
        return cls(**data)


# =============================================================================
# Vault Document Index (Local cache for fast queries)
# =============================================================================

class VaultDocumentIndex:
    """Local index of vault documents for fast queries without hitting cloud storage."""

    IMMUTABLE_FIELDS = {
        "vault_id",
        "user_id",
        "filename",
        "safe_filename",
        "sha256_hash",
        "file_size",
        "mime_type",
        "storage_path",
        "storage_provider",
        "certificate_id",
        "uploaded_at",
    }
    
    def __init__(self, data_dir: str = "data/vault_index"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._documents: dict[str, VaultDocument] = {}
        self._user_index: dict[str, list[str]] = {}  # user_id -> [vault_ids]
        self._hash_index: dict[str, str] = {}  # sha256 -> vault_id (dedup)
        self._load()
    
    def _load(self):
        """Load index from disk."""
        index_file = self.data_dir / "vault_index.json"
        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    data = json.load(f)
                for vault_id, doc_data in data.get("documents", {}).items():
                    doc = VaultDocument.from_dict(doc_data)
                    self._documents[vault_id] = doc
                    # Build user index
                    if doc.user_id not in self._user_index:
                        self._user_index[doc.user_id] = []
                    self._user_index[doc.user_id].append(vault_id)
                    # Build hash index
                    self._hash_index[doc.sha256_hash] = vault_id
            except Exception as e:
                logger.error("Failed to load vault index: %s", e)
    
    def _save(self):
        """Save index to disk."""
        index_file = self.data_dir / "vault_index.json"
        data = {
            "documents": {vid: doc.to_dict() for vid, doc in self._documents.items()},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def add(self, doc: VaultDocument) -> None:
        """Add document to index."""
        self._documents[doc.vault_id] = doc
        if doc.user_id not in self._user_index:
            self._user_index[doc.user_id] = []
        self._user_index[doc.user_id].append(doc.vault_id)
        self._hash_index[doc.sha256_hash] = doc.vault_id
        self._save()
    
    def get(self, vault_id: str) -> Optional[VaultDocument]:
        """Get document by vault ID."""
        return self._documents.get(vault_id)
    
    def get_by_hash(self, sha256_hash: str) -> Optional[VaultDocument]:
        """Find document by hash (deduplication)."""
        vault_id = self._hash_index.get(sha256_hash)
        return self._documents.get(vault_id) if vault_id else None
    
    def get_user_documents(self, user_id: str, document_type: Optional[str] = None) -> list[VaultDocument]:
        """Get all documents for a user, optionally filtered by type."""
        vault_ids = self._user_index.get(user_id, [])
        docs = [self._documents[vid] for vid in vault_ids if vid in self._documents]
        if document_type:
            docs = [d for d in docs if d.document_type == document_type]
        return docs
    
    def update(self, vault_id: str, **kwargs) -> Optional[VaultDocument]:
        """Update document metadata."""
        doc = self._documents.get(vault_id)
        if doc:
            attempted_immutable = set(kwargs.keys()) & self.IMMUTABLE_FIELDS
            if attempted_immutable:
                fields = ", ".join(sorted(attempted_immutable))
                raise ValueError(f"Immutable vault fields cannot be modified: {fields}")
            for key, value in kwargs.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)
            self._save()
        return doc
    
    def delete(self, vault_id: str) -> bool:
        """Remove document from index (does not delete from storage)."""
        doc = self._documents.pop(vault_id, None)
        if doc:
            if doc.user_id in self._user_index:
                self._user_index[doc.user_id] = [
                    vid for vid in self._user_index[doc.user_id] if vid != vault_id
                ]
            self._hash_index.pop(doc.sha256_hash, None)
            self._save()
            return True
        return False


# =============================================================================
# Vault Upload Service
# =============================================================================

class VaultUploadService:
    """
    Centralized service for all document uploads.
    Routes uploads to user's vault, then modules access from there.
    """
    
    VAULT_ROOT_FOLDER = VAULT_ROOT
    VAULT_FOLDER = VAULT_DOCUMENTS
    CERTS_FOLDER = VAULT_CERTIFICATES
    
    def __init__(self):
        self.index = VaultDocumentIndex()
    
    def _compute_sha256(self, content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _get_safe_filename(self, vault_id: str, original_filename: str) -> str:
        """Generate safe filename for storage."""
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
        return f"{vault_id}.{ext}"

    def _validate_upload_input(self, filename: str, content: bytes, mime_type: str) -> None:
        """Validate upload size and extension before storing immutable artifacts."""
        if not filename or not filename.strip():
            raise ValueError("filename is required")
        if not content:
            raise ValueError("file content cannot be empty")

        settings = get_settings()
        max_size_bytes = int(settings.max_upload_size_mb) * 1024 * 1024
        if len(content) > max_size_bytes:
            raise ValueError(f"file too large: max {settings.max_upload_size_mb}MB")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed_extensions = {
            item.strip().lower()
            for item in str(settings.allowed_extensions).split(",")
            if item.strip()
        }
        if ext and ext not in allowed_extensions:
            raise ValueError(f"file extension not allowed: {ext}")
        if not mime_type:
            raise ValueError("mime_type is required")

    async def _create_unified_overlay(
        self,
        doc: VaultDocument,
        overlay_type: OverlayType,
        payload: dict,
        metadata: dict | None = None,
        access_token: str | None = None,
        storage_provider: str = "google_drive",
    ) -> None:
        """
        Create cloud-only overlay record using unified overlay manager.
        
        All overlays are stored in user's cloud storage, not locally.
        """
        try:
            if not HAS_STORAGE or not access_token:
                logger.debug("Storage unavailable, skipping overlay creation for %s", doc.vault_id)
                return

            storage = get_provider(storage_provider, access_token=access_token)
            manager = await get_unified_overlay_manager(storage, doc.user_id)

            request = CreateOverlayRequest(
                overlay_type=overlay_type,
                document_id=doc.safe_filename,
                vault_path=doc.storage_path,
                payload=payload,
                metadata=metadata or {},
                ephemeral=False,
            )

            result = await manager.create_overlay(request)
            if result.success:
                logger.debug("Created %s overlay for %s: %s", overlay_type.value, doc.vault_id, result.overlay_id)
            else:
                logger.warning("Failed to create overlay for %s: %s", doc.vault_id, result.message)

        except Exception as ex:
            logger.debug("Overlay creation skipped for %s: %s", doc.vault_id, ex)
    
    async def _ensure_folders(self, storage) -> None:
        """Ensure vault folders exist in storage."""
        try:
            await storage.create_folder("Semptify5.0")
            await storage.create_folder(self.VAULT_ROOT_FOLDER)
            await storage.create_folder(self.VAULT_FOLDER)
            await storage.create_folder(self.CERTS_FOLDER)
        except Exception as e:
            logger.warning("Could not create folders: %s", e)
    
    async def upload(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
        document_type: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        source_module: str = "direct",
        access_token: Optional[str] = None,
        storage_provider: str = "local",
    ) -> VaultDocument:
        """
        Upload a document to user's vault.
        
        This is THE method all modules should call to store documents.
        
        Args:
            user_id: User ID
            filename: Original filename
            content: File content bytes
            mime_type: MIME type
            document_type: Type of document (lease, notice, photo, etc.)
            description: Optional description
            tags: Optional tags list
            source_module: Which module initiated upload (intake, briefcase, etc.)
            access_token: Cloud storage access token (if using cloud storage)
            storage_provider: Storage provider (google_drive, dropbox, onedrive, local)
        
        Returns:
            VaultDocument with vault_id and storage details
        """
        self._validate_upload_input(filename=filename, content=content, mime_type=mime_type)

        # Compute hash for deduplication
        sha256_hash = self._compute_sha256(content)
        
        # Check for duplicate
        existing = self.index.get_by_hash(sha256_hash)
        if existing and existing.user_id == user_id:
            logger.info("Document already in vault: %s", existing.vault_id)
            return existing
        
        # Generate IDs
        vault_id = str(uuid.uuid4())
        safe_filename = self._get_safe_filename(vault_id, filename)
        file_size = len(content)
        now = datetime.now(timezone.utc).isoformat()
        
        # Store document
        storage_path = await self._store_document(
            user_id=user_id,
            safe_filename=safe_filename,
            content=content,
            mime_type=mime_type,
            access_token=access_token,
            storage_provider=storage_provider,
        )
        
        # Create certificate
        certificate_id = await self._create_certificate(
            vault_id=vault_id,
            user_id=user_id,
            original_filename=filename,
            sha256_hash=sha256_hash,
            file_size=file_size,
            mime_type=mime_type,
            document_type=document_type,
            storage_path=storage_path,
            storage_provider=storage_provider,
            access_token=access_token,
        )
        
        # Create vault document record
        doc = VaultDocument(
            vault_id=vault_id,
            user_id=user_id,
            filename=filename,
            safe_filename=safe_filename,
            sha256_hash=sha256_hash,
            file_size=file_size,
            mime_type=mime_type,
            document_type=document_type,
            description=description,
            tags=tags or [],
            storage_path=storage_path,
            storage_provider=storage_provider,
            certificate_id=certificate_id,
            uploaded_at=now,
            source_module=source_module,
        )
        
        # Add to index
        self.index.add(doc)

        await self._create_unified_overlay(
            doc,
            overlay_type=OverlayType.VAULT_UPLOAD_MANIFEST,
            payload={
                "sha256_hash": doc.sha256_hash,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "storage_path": doc.storage_path,
                "certificate_id": doc.certificate_id,
                "source_module": doc.source_module,
            },
            metadata={"stage": "upload"},
            access_token=access_token,
            storage_provider=storage_provider,
        )
        
        logger.info("📁 Document uploaded to vault: %s (%s) via %s", vault_id, filename, source_module)
        
        # Emit event for other modules
        await self._emit_upload_event(doc)
        
        return doc
    
    async def _store_document(
        self,
        user_id: str,
        safe_filename: str,
        content: bytes,
        mime_type: str,
        access_token: Optional[str],
        storage_provider: str,
    ) -> str:
        """Store document in user's connected cloud storage only."""

        if not HAS_STORAGE:
            raise RuntimeError("storage provider unavailable")
        if storage_provider == "local":
            raise RuntimeError("local storage is disabled for vault uploads")
        if not access_token:
            raise RuntimeError("missing storage access token")

        storage = get_provider(storage_provider, access_token=access_token)
        await self._ensure_folders(storage)
        await storage.upload_file(
            file_content=content,
            destination_path=self.VAULT_FOLDER,
            filename=safe_filename,
            mime_type=mime_type,
        )
        return f"{self.VAULT_FOLDER}/{safe_filename}"
    
    async def _create_certificate(
        self,
        vault_id: str,
        user_id: str,
        original_filename: str,
        sha256_hash: str,
        file_size: int,
        mime_type: str,
        document_type: Optional[str],
        storage_path: str,
        storage_provider: str,
        access_token: Optional[str],
    ) -> Optional[str]:
        """Create certification record for document."""
        certificate_id = f"cert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{vault_id[:8]}"
        
        certificate = {
            "certificate_id": certificate_id,
            "vault_id": vault_id,
            "sha256": sha256_hash,
            "original_filename": original_filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "document_type": document_type,
            "certified_at": datetime.now(timezone.utc).isoformat(),
            "storage_path": storage_path,
            "storage_provider": storage_provider,
            "user_id": user_id,
            "version": "5.0",
            "platform": "Semptify Vault Service",
        }
        
        cert_content = json.dumps(certificate, indent=2).encode("utf-8")
        
        if not HAS_STORAGE:
            raise RuntimeError("storage provider unavailable")
        if storage_provider == "local":
            raise RuntimeError("local storage is disabled for certificates")
        if not access_token:
            raise RuntimeError("missing storage access token")

        storage = get_provider(storage_provider, access_token=access_token)
        await storage.upload_file(
            file_content=cert_content,
            destination_path=self.CERTS_FOLDER,
            filename=f"{certificate_id}.json",
            mime_type="application/json",
        )
        return certificate_id
    
    async def _emit_upload_event(self, doc: VaultDocument) -> None:
        """Emit event for document upload so other modules can react."""
        try:
            from app.core.event_bus import event_bus, EventType
            await event_bus.publish(
                EventType.DOCUMENT_ADDED,
                {
                    "vault_id": doc.vault_id,
                    "user_id": doc.user_id,
                    "filename": doc.filename,
                    "document_type": doc.document_type,
                    "storage_path": doc.storage_path,
                    "source_module": doc.source_module,
                },
                user_id=doc.user_id,
            )
        except Exception as e:
            logger.debug("Event emission failed: %s", e)
    
    # =========================================================================
    # Document Access Methods (for modules to use)
    # =========================================================================
    
    def get_document(self, vault_id: str) -> Optional[VaultDocument]:
        """Get document metadata by vault ID."""
        return self.index.get(vault_id)
    
    def get_user_documents(
        self,
        user_id: str,
        document_type: Optional[str] = None
    ) -> list[VaultDocument]:
        """Get all documents for a user."""
        return self.index.get_user_documents(user_id, document_type)
    
    async def get_document_content(
        self,
        vault_id: str,
        access_token: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Get document content from storage.
        Modules call this to read document content from vault.
        """
        doc = self.index.get(vault_id)
        if not doc:
            return None
        
        if not HAS_STORAGE:
            return None
        if doc.storage_provider == "local" or not access_token:
            return None

        try:
            storage = get_provider(doc.storage_provider, access_token=access_token)
            result = await storage.download_file(doc.storage_path)
            if result:
                return result
        except Exception as e:
            logger.warning("Cloud download failed: %s", e)

        return None
    
    async def mark_processed(
        self,
        vault_id: str,
        extracted_data: Optional[dict] = None,
        access_token: Optional[str] = None,
        storage_provider: str = "google_drive",
    ) -> Optional[VaultDocument]:
        """Mark document as processed and store extracted data."""
        doc = self.index.update(
            vault_id,
            processed=True,
            extracted_data=extracted_data
        )
        if doc and extracted_data is not None:
            await self._create_unified_overlay(
                doc,
                overlay_type=OverlayType.DOCUMENT_EXTRACTION,
                payload={"extracted_data": extracted_data},
                metadata={"stage": "extraction"},
                access_token=access_token,
                storage_provider=storage_provider,
            )
        return doc
    
    async def update_document_type(
        self,
        vault_id: str,
        document_type: str,
        access_token: Optional[str] = None,
        storage_provider: str = "google_drive",
    ) -> Optional[VaultDocument]:
        """Update document type after classification."""
        doc = self.index.update(vault_id, document_type=document_type)
        if doc:
            await self._create_unified_overlay(
                doc,
                overlay_type=OverlayType.DOCUMENT_CLASSIFICATION,
                payload={"document_type": document_type},
                metadata={"stage": "classification"},
                access_token=access_token,
                storage_provider=storage_provider,
            )
        return doc


# =============================================================================
# Module-level singleton
# =============================================================================

_vault_service: Optional[VaultUploadService] = None


# Global service instance
_vault_service: Optional[VaultUploadService] = None


def get_vault_service() -> VaultUploadService:
    """Get or create the vault upload service singleton."""
    if _vault_service is None:
        # Use global assignment instead of global statement
        globals()['_vault_service'] = VaultUploadService()
    return _vault_service
