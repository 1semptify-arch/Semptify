"""
Document Notarization Service

Provides tamper-proof documentation of document reception, storage, and processing.
Creates timestamped, certified records that prove:
- Document received and authenticated
- Original content hash
- Storage location
- Chain of custody
- Processing history

Uses the document registry for integrity verification.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from app.services.document_registry import (
        DocumentRegistry,
        RegistryStatus,
        VerificationStatus,
    )
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False
    logger.warning("Document Registry not available")


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NotarizationRecord:
    """
    Notarization of a document upload event.
    
    Proves:
    - Document received at specific time
    - Content not tampered with (via hash)
    - Original filename and metadata
    - Who uploaded it (user_id)
    - Where it's stored
    """
    notarization_id: str  # Unique identifier (SEM-NOT-XXXXX)
    document_id: str  # Vault or system document ID
    user_id: str
    username: str
    
    # Content verification
    file_hash: str  # SHA-256 of original file
    file_size: int  # Original file size in bytes
    mime_type: str  # Original MIME type
    
    # Metadata
    original_filename: str  # Original uploaded filename
    document_type: Optional[str]  # lease, notice, photo, etc.
    description: Optional[str]
    tags: List[str]
    
    # Location
    storage_path: str  # Where stored in vault
    storage_provider: str  # google_drive, dropbox, onedrive, local
    
    # Timestamp & Source
    notarized_at: str  # ISO 8601 timestamp
    notarized_by: str  # System that created notarization
    ip_address: Optional[str]  # IP of uploader
    user_agent: Optional[str]  # Browser/client info
    
    # Status
    status: str  # notarized, verified, registered, processing
    
    # Chain of custody
    registry_id: Optional[str] = None  # Reference to document registry
    certificate_hash: Optional[str] = None  # Hash of this notarization itself
    
    # Metadata tracking
    upload_method: str = "web"  # web, api, file_picker, etc.
    upload_context: Optional[Dict[str, Any]] = None  # additional context
    
    def to_dict(self) -> dict:
        data = asdict(self)
        if self.upload_context:
            data["upload_context"] = json.dumps(self.upload_context)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "NotarizationRecord":
        if isinstance(data.get("upload_context"), str):
            data["upload_context"] = json.loads(data["upload_context"])
        return cls(**data)
    
    def get_notarization_hash(self) -> str:
        """Generate hash of this notarization record for integrity verification."""
        hashable = {
            "notarization_id": self.notarization_id,
            "document_id": self.document_id,
            "file_hash": self.file_hash,
            "notarized_at": self.notarized_at,
            "storage_path": self.storage_path,
        }
        content = json.dumps(hashable, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class DocumentNotarization:
    """Complete notarization event with verification results."""
    notarization: NotarizationRecord
    verification_status: str  # verified, tampered, pending
    registry_status: Optional[str]  # Original, Copy, Superseded, etc.
    created_at: datetime
    verified_at: Optional[datetime] = None


# =============================================================================
# Notarization Service
# =============================================================================

class DocumentNotarizationService:
    """
    Service for creating and verifying document notarizations.
    
    Usage:
    ```python
    service = DocumentNotarizationService()
    
    # On upload
    notarization = await service.notarize_upload(
        file_content=file_bytes,
        filename="lease.pdf",
        user_id="user_123",
        storage_path="/path/in/vault",
        document_type="lease"
    )
    
    # Later verification
    status = await service.verify_notarization(notarization_id)
    ```
    """
    
    def __init__(self):
        self.registry = DocumentRegistry() if HAS_REGISTRY else None
        self._notarizations: Dict[str, NotarizationRecord] = {}  # Memory cache
    
    async def notarize_upload(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        username: str,
        storage_path: str,
        storage_provider: str,
        document_type: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        upload_method: str = "web",
        upload_context: Optional[Dict[str, Any]] = None,
    ) -> NotarizationRecord:
        """
        Create a notarization record for an uploaded document.
        
        This proves:
        - Document received at specific time
        - Content integrity (via hash)
        - Original metadata
        - Storage location
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            user_id: User ID who uploaded
            username: Username for human readability
            storage_path: Where document is stored in vault
            storage_provider: Which cloud provider (google_drive, etc.)
            document_type: Document classification
            description: User description of document
            tags: User tags/labels
            ip_address: IP address of uploader
            user_agent: Browser/client information
            upload_method: How document was uploaded
            upload_context: Additional context about upload
            
        Returns:
            NotarizationRecord with all metadata and hashes
        """
        # Generate unique identifiers
        notarization_id = self._generate_notarization_id()
        document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)
        
        # Determine MIME type
        mime_type = self._detect_mime_type(filename)
        
        # Create notarization record
        notarization = NotarizationRecord(
            notarization_id=notarization_id,
            document_id=document_id,
            user_id=user_id,
            username=username,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            original_filename=filename,
            document_type=document_type,
            description=description,
            tags=tags or [],
            storage_path=storage_path,
            storage_provider=storage_provider,
            notarized_at=datetime.now(timezone.utc).isoformat(),
            notarized_by="DocumentNotarizationService",
            ip_address=ip_address,
            user_agent=user_agent,
            status="notarized",
            upload_method=upload_method,
            upload_context=upload_context,
        )
        
        # Calculate notarization hash
        notarization.certificate_hash = notarization.get_notarization_hash()
        
        # Register in document registry if available
        if self.registry and HAS_REGISTRY:
            try:
                registry_result = await self.registry.register_document(
                    filename=filename,
                    content_hash=file_hash,
                    document_type=document_type,
                    source="upload",
                    metadata={
                        "notarization_id": notarization_id,
                        "user_id": user_id,
                        "upload_method": upload_method,
                    }
                )
                notarization.registry_id = registry_result.get("registry_id")
                notarization.status = "registered"
                logger.info(
                    f"Document {document_id} registered in registry: {notarization.registry_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to register document in registry: {e}")
        
        # Cache in memory
        self._notarizations[notarization_id] = notarization
        
        logger.info(
            f"✓ Document notarized: {notarization_id} "
            f"({filename} from {username}, {file_size} bytes)"
        )
        
        return notarization
    
    async def verify_notarization(
        self,
        notarization_id: str,
        file_content: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Verify a notarization record.
        
        Checks:
        - Notarization record exists
        - Hash is valid (self-verification)
        - If file provided, verify content matches original hash
        - Registry status if registered
        
        Returns:
            Verification result with status and details
        """
        # Get notarization
        if notarization_id not in self._notarizations:
            return {
                "status": "not_found",
                "verified": False,
                "error": f"Notarization {notarization_id} not found",
            }
        
        notarization = self._notarizations[notarization_id]
        
        # Verify notarization hash
        expected_hash = notarization.get_notarization_hash()
        if notarization.certificate_hash != expected_hash:
            return {
                "status": "tampered",
                "verified": False,
                "error": "Notarization record hash mismatch - record may be tampered",
                "expected_hash": expected_hash,
                "actual_hash": notarization.certificate_hash,
            }
        
        result = {
            "status": "verified",
            "verified": True,
            "notarization_id": notarization_id,
            "document_id": notarization.document_id,
            "notarized_at": notarization.notarized_at,
            "file_hash": notarization.file_hash,
            "file_size": notarization.file_size,
            "original_filename": notarization.original_filename,
            "storage_location": f"{notarization.storage_provider}:{notarization.storage_path}",
        }
        
        # If file content provided, verify it matches
        if file_content is not None:
            content_hash = hashlib.sha256(file_content).hexdigest()
            if content_hash != notarization.file_hash:
                result["content_status"] = "tampered"
                result["content_verified"] = False
                result["error"] = "File content does not match original hash"
            else:
                result["content_status"] = "verified"
                result["content_verified"] = True
        
        # Check registry status
        if notarization.registry_id and self.registry:
            try:
                registry_status = await self.registry.get_document_status(
                    notarization.registry_id
                )
                result["registry_status"] = registry_status
            except Exception as e:
                logger.warning(f"Failed to check registry status: {e}")
        
        return result
    
    async def create_chain_of_custody(
        self,
        notarization_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get complete chain of custody for a document from notarization and registry.
        
        Returns list of events showing:
        - Document upload (notarization)
        - Registrations/copies
        - Modifications/supersedes
        - Processing events
        """
        if notarization_id not in self._notarizations:
            return []
        
        notarization = self._notarizations[notarization_id]
        chain = [
            {
                "event": "upload",
                "timestamp": notarization.notarized_at,
                "actor": notarization.username,
                "action": f"Uploaded {notarization.original_filename}",
                "hash": notarization.file_hash,
                "location": f"{notarization.storage_provider}:{notarization.storage_path}",
            }
        ]
        
        # Get registry chain if available
        if notarization.registry_id and self.registry:
            try:
                registry_chain = await self.registry.get_chain_of_custody(
                    notarization.registry_id
                )
                chain.extend(registry_chain)
            except Exception as e:
                logger.warning(f"Failed to get registry chain: {e}")
        
        return chain
    
    def _generate_notarization_id(self) -> str:
        """Generate unique notarization ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:8].upper()
        return f"SEM-NOT-{timestamp}-{random_suffix}"
    
    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"


# =============================================================================
# Singleton Instance
# =============================================================================

_notarization_service: Optional[DocumentNotarizationService] = None


async def get_notarization_service() -> DocumentNotarizationService:
    """Get or create notarization service singleton."""
    global _notarization_service
    if _notarization_service is None:
        _notarization_service = DocumentNotarizationService()
    return _notarization_service
