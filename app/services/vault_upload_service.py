# =============================================================================
# SSOT: app/services/vault_upload_service.py — CANONICAL UPLOAD SERVICE
# AI RULES — READ BEFORE EDITING:
#   1. This is the ONE upload handler. Never create vault_upload_service_v2.py
#      or any parallel upload service.
#   2. Put ALL implementation edits in _vault_upload_service_impl.py if using
#      the shim pattern; otherwise edit this file directly.
#   3. NEVER implement document upload logic in any router, module, or service
#      other than this file.
#   4. All folder paths come from app/core/vault_paths.py — never hardcode.
#   5. Gate marking is done by app/modules/onboarding/gates.py — never here.
# =============================================================================
"""
Vault Upload Service - Centralized Document Upload Handler

ALL document uploads from ANY module go through this service.
Documents are stored in the user's vault first, then modules access them from vault.

Flow:
1. Any module calls vault_upload_service.upload()
2. Document is stored in user's cloud storage vault (Semptify5.0/Vault/)
3. Document metadata is indexed in database for fast queries
4. Modules access documents via vault_id reference

This ensures:
- Single source of truth for all documents
- User owns their data in their cloud storage
- Modules can reference documents without storing duplicates
- Consistent security and certification across all uploads
- Metadata persists across server restarts (DB-backed)
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.id_gen import make_id
from app.core.config import get_settings
from app.core.utc import utc_now
from app.core.database import get_db_session
from app.core.vault_paths import CANONICAL_VAULT_FOLDERS, SEMPTIFY_ROOT, VAULT_ROOT, VAULT_DOCUMENTS, VAULT_CERTIFICATES
from app.core.overlay_types import OverlayType
from app.models.unified_overlay_models import CreateOverlayRequest
from app.models.models import VaultIndexDB, VaultUserIndexDB, VaultHashIndexDB
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Import storage provider
try:
    from app.services.storage import get_provider
    HAS_STORAGE = True
except ImportError:
    HAS_STORAGE = True
    logger.warning("Storage provider not available")

# Import document registry for auto-registration
try:
    from app.services.document_registry import get_document_registry
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False
    logger.info("Document registry not available, vault uploads will be uncertified")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class VaultDocument:
    """A document stored in user's vault.
    
    Every VaultDocument is automatically registered in the Document Registry
    upon upload, ensuring chain of custody and tamper-proof identification.
    A VaultDocument without registry_id is considered 'uncertified' and
    should not be processed by downstream modules.
    """
    vault_id: str  # Primary identifier (Semptify internal)
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
    provider_file_id: Optional[str] = None
    certificate_id: Optional[str] = None
    uploaded_at: Optional[str] = None
    # Registration - every vault doc auto-registers for chain of custody
    registry_id: Optional[str] = None  # SEM-YYYY-NNNNNN-XXXX format
    integrity_status: str = "unverified"  # verified, tampered, unverified
    # Processing state
    processed: bool = False
    extracted_data: Optional[dict] = None
    # Source tracking
    source_module: str = "direct"  # Which module initiated upload
    
    @property
    def is_certified(self) -> bool:
        """Check if document has completed registration and has chain of custody."""
        return self.registry_id is not None and self.integrity_status == "verified"
    
    @property
    def sem_id(self) -> str:
        """Get Semptify document ID (registry_id if available, else vault_id)."""
        return self.registry_id or self.vault_id
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "VaultDocument":
        return cls(**data)


# =============================================================================
# Vault Document Index (DB-backed with local cache for fast queries)
# =============================================================================

class VaultDocumentIndex:
    """DB-backed index of vault documents for fast queries without hitting cloud storage.
    
    Uses PostgreSQL as the source of truth with optional local disk cache.
    All writes go to DB first, then optionally to disk for redundancy.
    """

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
        # In-memory cache (loaded from DB on demand)
        self._documents: dict[str, VaultDocument] = {}
        self._loaded_from_db: set[str] = set()  # Track which vault_ids were loaded from DB
    
    def _doc_to_db_model(self, doc: VaultDocument) -> VaultIndexDB:
        """Convert VaultDocument to DB model."""
        return VaultIndexDB(
            vault_id=doc.vault_id,
            user_id=doc.user_id,
            filename=doc.filename,
            safe_filename=doc.safe_filename,
            sha256_hash=doc.sha256_hash,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            storage_path=doc.storage_path,
            provider_file_id=doc.provider_file_id,
            storage_provider=doc.storage_provider,
            document_type=doc.document_type,
            description=doc.description,
            tags=",".join(doc.tags) if doc.tags else None,
            certificate_id=doc.certificate_id,
            registry_id=doc.registry_id,
            integrity_status=doc.integrity_status,
            processed=doc.processed,
            extracted_data_json=json.dumps(doc.extracted_data) if doc.extracted_data else None,
            source_module=doc.source_module,
            uploaded_at=datetime.fromisoformat(doc.uploaded_at) if doc.uploaded_at else utc_now(),
            updated_at=utc_now(),
        )
    
    def _doc_from_db_model(self, db_doc: VaultIndexDB) -> VaultDocument:
        """Convert DB model to VaultDocument."""
        return VaultDocument(
            vault_id=db_doc.vault_id,
            user_id=db_doc.user_id,
            filename=db_doc.filename,
            safe_filename=db_doc.safe_filename,
            sha256_hash=db_doc.sha256_hash,
            file_size=db_doc.file_size,
            mime_type=db_doc.mime_type,
            document_type=db_doc.document_type,
            description=db_doc.description,
            tags=db_doc.tags.split(",") if db_doc.tags else [],
            storage_path=db_doc.storage_path,
            provider_file_id=db_doc.provider_file_id,
            storage_provider=db_doc.storage_provider,
            certificate_id=db_doc.certificate_id,
            uploaded_at=db_doc.uploaded_at.isoformat() if db_doc.uploaded_at else None,
            registry_id=db_doc.registry_id,
            integrity_status=db_doc.integrity_status,
            processed=db_doc.processed,
            extracted_data=json.loads(db_doc.extracted_data_json) if db_doc.extracted_data_json else None,
            source_module=db_doc.source_module,
        )
    
    async def _add_to_db(self, doc: VaultDocument) -> None:
        """Add document to database index."""
        try:
            from sqlalchemy import select
            async with get_db_session() as session:
                # Add to vault_index
                db_doc = self._doc_to_db_model(doc)
                await session.merge(db_doc)
                await session.flush()  # Ensure vault_index row exists before FK check
                
                # Add to user index
                user_idx = VaultUserIndexDB(
                    user_id=doc.user_id,
                    vault_id=doc.vault_id,
                    added_at=utc_now(),
                )
                await session.merge(user_idx)
                
                # Add/update hash index
                result = await session.execute(
                    select(VaultHashIndexDB).where(VaultHashIndexDB.sha256_hash == doc.sha256_hash)
                )
                hash_idx = result.scalar_one_or_none()
                if hash_idx:
                    hash_idx.ref_count += 1
                    hash_idx.vault_id = doc.vault_id  # Update to latest
                else:
                    hash_idx = VaultHashIndexDB(
                        sha256_hash=doc.sha256_hash,
                        vault_id=doc.vault_id,
                        user_id=doc.user_id,
                        ref_count=1,
                        created_at=utc_now(),
                    )
                    session.add(hash_idx)
                
                await session.commit()
                logger.debug("Document %s added to DB index", doc.vault_id)
        except Exception as e:
            logger.error("Failed to add document %s to DB index: %s", doc.vault_id, e)
            raise
    
    async def _get_from_db(self, vault_id: str) -> Optional[VaultDocument]:
        """Get document from database."""
        try:
            from sqlalchemy import select
            async with get_db_session() as session:
                result = await session.execute(
                    select(VaultIndexDB).where(VaultIndexDB.vault_id == vault_id)
                )
                db_doc = result.scalar_one_or_none()
                if db_doc:
                    return self._doc_from_db_model(db_doc)
                return None
        except Exception as e:
            logger.error("Failed to get document %s from DB: %s", vault_id, e)
            return None
    
    async def _get_by_hash_from_db(self, sha256_hash: str) -> Optional[VaultDocument]:
        """Find document by hash from database."""
        try:
            from sqlalchemy import select
            async with get_db_session() as session:
                result = await session.execute(
                    select(VaultHashIndexDB).where(VaultHashIndexDB.sha256_hash == sha256_hash)
                )
                hash_idx = result.scalar_one_or_none()
                if hash_idx:
                    return await self._get_from_db(hash_idx.vault_id)
                return None
        except Exception as e:
            logger.error("Failed to get document by hash from DB: %s", e)
            return None
    
    async def _get_user_docs_from_db(self, user_id: str, document_type: Optional[str] = None) -> list[VaultDocument]:
        """Get user's documents from database."""
        try:
            from sqlalchemy import select
            async with get_db_session() as session:
                result = await session.execute(
                    select(VaultIndexDB)
                    .where(VaultIndexDB.user_id == user_id)
                    .order_by(VaultIndexDB.uploaded_at.desc())
                )
                docs = result.scalars().all()
                vault_docs = [self._doc_from_db_model(d) for d in docs]
                if document_type:
                    vault_docs = [d for d in vault_docs if d.document_type == document_type]
                return vault_docs
        except Exception as e:
            logger.error("Failed to get user docs from DB: %s", e)
            return []
    
    async def _update_in_db(self, vault_id: str, **kwargs) -> None:
        """Update document in database."""
        try:
            from sqlalchemy import select
            async with get_db_session() as session:
                result = await session.execute(
                    select(VaultIndexDB).where(VaultIndexDB.vault_id == vault_id)
                )
                db_doc = result.scalar_one_or_none()
                if db_doc:
                    for key, value in kwargs.items():
                        if hasattr(db_doc, key):
                            setattr(db_doc, key, value)
                        elif key == "extracted_data":
                            db_doc.extracted_data_json = json.dumps(value) if value else None
                        elif key == "tags":
                            db_doc.tags = ",".join(value) if value else None
                    db_doc.updated_at = utc_now()
                    await session.commit()
                    logger.debug("Document %s updated in DB index", vault_id)
        except Exception as e:
            logger.error("Failed to update document %s in DB: %s", vault_id, e)
            raise
    
    def _legacy_load(self):
        """Load index from disk (legacy migration support)."""
        index_file = self.data_dir / "vault_index.json"
        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    data = json.load(f)
                for vault_id, doc_data in data.get("documents", {}).items():
                    doc = VaultDocument.from_dict(doc_data)
                    self._documents[vault_id] = doc
            except Exception as e:
                logger.error("Failed to load legacy vault index: %s", e)
    
    def _legacy_save(self):
        """Save index to disk (backup/redundancy)."""
        index_file = self.data_dir / "vault_index.json"
        data = {
            "documents": {vid: doc.to_dict() for vid, doc in self._documents.items()},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    async def add(self, doc: VaultDocument) -> None:
        """Add document to index (DB primary, disk backup)."""
        self._documents[doc.vault_id] = doc
        self._loaded_from_db.add(doc.vault_id)
        await self._add_to_db(doc)
        self._legacy_save()  # Redundant backup
    
    async def get(self, vault_id: str) -> Optional[VaultDocument]:
        """Get document by vault ID (from cache or DB)."""
        # Check cache first
        if vault_id in self._documents:
            return self._documents[vault_id]
        # Load from DB
        doc = await self._get_from_db(vault_id)
        if doc:
            self._documents[vault_id] = doc
            self._loaded_from_db.add(vault_id)
        return doc
    
    async def get_by_hash(self, sha256_hash: str) -> Optional[VaultDocument]:
        """Find document by hash (deduplication)."""
        # Check cache first
        for doc in self._documents.values():
            if doc.sha256_hash == sha256_hash:
                return doc
        # Load from DB
        return await self._get_by_hash_from_db(sha256_hash)
    
    async def get_user_documents(self, user_id: str, document_type: Optional[str] = None) -> list[VaultDocument]:
        """Get all documents for a user, optionally filtered by type."""
        return await self._get_user_docs_from_db(user_id, document_type)
    
    async def update(self, vault_id: str, **kwargs) -> Optional[VaultDocument]:
        """Update document metadata."""
        # Check immutable fields
        attempted_immutable = set(kwargs.keys()) & self.IMMUTABLE_FIELDS
        if attempted_immutable:
            fields = ", ".join(sorted(attempted_immutable))
            raise ValueError(f"Immutable vault fields cannot be modified: {fields}")
        
        # Update in DB
        await self._update_in_db(vault_id, **kwargs)
        
        # Update cache
        doc = self._documents.get(vault_id)
        if doc:
            for key, value in kwargs.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)
            self._legacy_save()
        return doc
    
    def delete(self, vault_id: str) -> bool:
        """Remove document from index (does not delete from storage)."""
        doc = self._documents.pop(vault_id, None)
        if doc:
            self._loaded_from_db.discard(vault_id)
            self._legacy_save()
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

    def _local_file_path(self, destination_path: str, filename: str) -> Path:
        """Resolve a local storage file path for testing or local provider support."""
        if not hasattr(self, "_local_dir") or self._local_dir is None:
            raise RuntimeError("local storage directory not configured")
        local_dir = Path(self._local_dir)
        relative_path = destination_path.strip("/").replace("\\", "/")
        file_path = local_dir / relative_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    async def _local_upload_file(
        self,
        file_content: bytes,
        destination_path: str,
        filename: str,
    ) -> None:
        path = self._local_file_path(destination_path, filename)
        path.write_bytes(file_content)

    def _local_read_file(self, storage_path: str) -> Optional[bytes]:
        if not hasattr(self, "_local_dir") or self._local_dir is None:
            return None
        file_path = Path(self._local_dir) / storage_path.strip("/")
        if not file_path.exists():
            return None
        return file_path.read_bytes()

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
        from app.core.path_utils import normalize_cloud_path
        try:
            for folder_path in CANONICAL_VAULT_FOLDERS:
                await storage.create_folder(normalize_cloud_path(folder_path))
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
        existing = await self.index.get_by_hash(sha256_hash)
        if existing and existing.user_id == user_id:
            if await self._verify_existing_document(existing, access_token):
                logger.info("Document already in vault: %s", existing.vault_id)
                return existing
            logger.warning(
                "Stale vault index entry detected for %s: storage file missing, uploading new copy",
                existing.vault_id,
            )
        
        # Generate IDs
        vault_id = make_id("doc")
        safe_filename = self._get_safe_filename(vault_id, filename)
        file_size = len(content)
        now = datetime.now(timezone.utc).isoformat()
        
        # Store document (returns storage path and provider file id)
        storage_path, provider_file_id = await self._store_document(
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
            provider_file_id=provider_file_id,
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
            provider_file_id=provider_file_id,
            storage_provider=storage_provider,
            certificate_id=certificate_id,
            uploaded_at=now,
            source_module=source_module,
        )
        
        # =========================================================================
        # AUTO-REGISTRATION: Every vault document gets registry entry for custody
        # =========================================================================
        if HAS_REGISTRY:
            try:
                registry = get_document_registry()
                from app.core.security import get_client_ip_from_request
                reg_doc = registry.register_document(
                    user_id=user_id,
                    content=content,
                    filename=filename,
                    mime_type=mime_type,
                    ip_address=None,  # Will be enriched by caller if available
                )
                doc.registry_id = reg_doc.document_id
                doc.integrity_status = reg_doc.integrity_status.value
                logger.info(f"✅ Document registered: {reg_doc.document_id} for vault {vault_id}")
            except Exception as e:
                logger.warning(f"Auto-registration failed for {vault_id}: {e}")
                # Document is still in vault, but uncertified - downstream modules
                # should check doc.is_certified before processing
        else:
            logger.warning(f"Registry unavailable - vault document {vault_id} is uncertified")
        
        # Add to index (now with registry info if available)
        await self.index.add(doc)

        # Overlays are created on-demand by the requesting process — NOT here.
        # Upload stores the document, certifies it, and indexes it. That is all.
        # Any module that needs an overlay calls UnifiedOverlayManager directly.

        logger.info("📁 Document uploaded to vault: %s (%s) via %s", vault_id, filename, source_module)
        
        # Emit event for other modules
        await self._emit_upload_event(doc)
        
        return doc
    
    async def _verify_existing_document(
        self,
        existing: VaultDocument,
        access_token: Optional[str],
    ) -> bool:
        """Verify that an existing indexed document still exists in storage."""
        if existing.storage_provider == "local":
            try:
                return self._local_read_file(existing.storage_path) is not None
            except Exception as exc:
                logger.warning(
                    "Existing local document verification failed for %s: %s",
                    existing.vault_id,
                    exc,
                )
                return False

        if not HAS_STORAGE or not access_token:
            logger.warning(
                "Cannot verify existing cloud document %s: missing storage access",
                existing.vault_id,
            )
            return False

        try:
            storage = get_provider(existing.storage_provider, access_token=access_token)
            return await storage.file_exists(existing.storage_path)
        except Exception as exc:
            logger.warning(
                "Existing cloud document verification failed for %s: %s",
                existing.vault_id,
                exc,
            )
            return False

    async def _store_document(
        self,
        user_id: str,
        safe_filename: str,
        content: bytes,
        mime_type: str,
        access_token: Optional[str],
        storage_provider: str,
    ) -> str:
        """Store document in user's connected cloud storage or local test storage."""

        if storage_provider == "local":
            await self._local_upload_file(
                file_content=content,
                destination_path=self.VAULT_FOLDER,
                filename=safe_filename,
            )
            return (f"{self.VAULT_FOLDER}/{safe_filename}", None)

        if not HAS_STORAGE:
            raise RuntimeError("storage provider unavailable")
        if not access_token:
            raise RuntimeError("missing storage access token")

        storage = get_provider(storage_provider, access_token=access_token)
        await self._ensure_folders(storage)
        storage_file = await storage.upload_file(
            file_content=content,
            destination_path=self.VAULT_FOLDER,
            filename=safe_filename,
            mime_type=mime_type,
        )
        # storage_file.path is the cloud path; storage_file.id is provider-specific file id
        return (f"{self.VAULT_FOLDER}/{safe_filename}", getattr(storage_file, "id", None))
    
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
        provider_file_id: Optional[str] = None,
    ) -> Optional[str]:
        """Create certification record for document."""
        certificate_id = make_id("cert")
        
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
            "provider_file_id": provider_file_id,
            "user_id": user_id,
            "version": "5.0",
            "platform": "Semptify Vault Service",
        }
        
        cert_content = json.dumps(certificate, indent=2).encode("utf-8")
        
        if storage_provider == "local":
            await self._local_upload_file(
                file_content=cert_content,
                destination_path=self.CERTS_FOLDER,
                filename=f"{certificate_id}.json",
            )
            return certificate_id

        if not HAS_STORAGE:
            raise RuntimeError("storage provider unavailable")
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
    
    async def get_document(self, vault_id: str) -> Optional[VaultDocument]:
        """Get document metadata by vault ID."""
        return await self.index.get(vault_id)
    
    async def get_user_documents(
        self,
        user_id: str,
        document_type: Optional[str] = None
    ) -> list[VaultDocument]:
        """Get all documents for a user."""
        return await self.index.get_user_documents(user_id, document_type)
    
    async def get_document_content(
        self,
        vault_id: str,
        access_token: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Get document content from storage.
        Modules call this to read document content from vault.
        """
        doc = await self.index.get(vault_id)
        if not doc:
            return None

        if doc.storage_provider == "local":
            return self._local_read_file(doc.storage_path)

        if not HAS_STORAGE or not access_token:
            logger.debug("Storage provider unavailable or missing access token for vault_id=%s", vault_id)
            return None

        storage = get_provider(doc.storage_provider, access_token=access_token)

        # Prefer provider file id if available — avoids fragile name-based lookups
        attempts = []
        if getattr(doc, "provider_file_id", None):
            fid = doc.provider_file_id
            attempts.append((f"id:{fid}", "by_id"))

        # Always try the recorded storage_path as fallback
        attempts.append((doc.storage_path, "by_path"))

        for path, why in attempts:
            try:
                result = await storage.download_file(path)
                if result:
                    logger.debug("Downloaded document %s via %s", vault_id, why)
                    return result
            except Exception as e:
                logger.warning("Download attempt failed for vault_id=%s path=%s (%s): %s", vault_id, path, why, e)

        logger.error("All download attempts failed for vault_id=%s storage_path=%s provider_file_id=%s", vault_id, doc.storage_path, getattr(doc, "provider_file_id", None))
        return None
    
    async def mark_processed(
        self,
        vault_id: str,
        extracted_data: Optional[dict] = None,
        access_token: Optional[str] = None,
        storage_provider: str = "google_drive",
    ) -> Optional[VaultDocument]:
        """Mark document as processed and store extracted data."""
        doc = await self.index.update(
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
        doc = await self.index.update(vault_id, document_type=document_type)
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


# =============================================================================
# Module Contracts — registered at import time, visible in contract browser
# =============================================================================
try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(FunctionGroupContract(
        module="vault",
        group_name="vault_upload",
        title="Document Vault Upload (SSOT)",
        description=(
            "CANONICAL upload handler. All document ingestion goes through VaultUploadService.upload(). "
            "Pipeline: validate → deduplicate (SHA256) → store to cloud → certificate → registry (get registry_id) → emit event. "
            "VAULT DOES NOT: create overlays, trigger intake, run analysis, or start workflows. "
            "Overlays are created on-demand by the requesting process. "
            "Intake/analysis is triggered by the caller after upload returns. "
            "No other service may implement upload logic."
        ),
        inputs=("user_id", "filename", "content", "mime_type", "access_token", "storage_provider"),
        outputs=("vault_id", "registry_id", "certificate_id", "provider_file_id", "storage_path"),
        dependencies=(
            "app.services.vault_upload_service",
            "app.core.vault_paths.VAULT_DOCUMENTS",
            "app.core.vault_paths.VAULT_CERTIFICATES",
        ),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="vault",
        group_name="vault_folders",
        title="Vault Folder Structure (SSOT)",
        description=(
            "All vault folder paths come from app/core/vault_paths.py. "
            "NEVER hardcode Semptify5.0/ paths. NEVER duplicate these constants."
        ),
        inputs=("user_id", "access_token", "provider"),
        outputs=("CANONICAL_VAULT_FOLDERS",),
        dependencies=("app.core.vault_paths",),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="vault",
        group_name="vault_init",
        title="Vault Initialization (Folder Creation)",
        description=(
            "Creates canonical vault folder structure in user cloud storage. "
            "Used by onboarding (Step 1). vault_initialized gate MUST only be "
            "marked by vault_verify() after ALL three onboarding steps pass — "
            "never by install_vault_for_user() or any intermediate step."
        ),
        inputs=("user_id", "access_token", "provider"),
        outputs=("folders_created", "activation_code"),
        dependencies=(
            "app.sdk.vault.client.VaultClient",
            "app.core.vault_paths.CANONICAL_VAULT_FOLDERS",
            "app.modules.onboarding.gates.mark_gate",
        ),
        deterministic=True,
    ))
except Exception:
    pass
