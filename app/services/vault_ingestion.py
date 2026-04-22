"""
ALL-IN-ONE Unified Evidence Vault — Ingestion Service

This service enforces the data contract and three-timestamp model for all
vault item ingestion. It is the single source of truth for vault item creation,
ensuring metadata preservation and complete audit trails.

Function Group: vault_ingestion
Purpose: Ingest evidence into unified vault with data contract enforcement.

Data Contract Rules (NON-NEGOTIABLE):
- Never discard metadata
- Never flatten metadata
- Never overwrite timestamps
- Preserve nested JSON
- If unknown → set null

Three-Timestamp Model (NON-NEGOTIABLE):
- event_time: Factual time of event occurrence
- record_time: When evidence was created/recorded
- semptify_entry_time: When added to Semptify system (auto-set)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_DOCUMENTS
from app.models.models import VaultItem, Incident, VaultAuditLog

VAULT_INGESTION_FUNCTION_GROUP = "vault_ingestion"

# Register module contract
register_function_group(
    FunctionGroupContract(
        module="vault",
        group_name=VAULT_INGESTION_FUNCTION_GROUP,
        title="Vault Ingestion Service",
        description="Ingest evidence into unified vault with data contract enforcement and three-timestamp model.",
        inputs=(
            "user_id",
            "item_type",
            "event_time",
            "record_time",
            "metadata",
        ),
        outputs=(
            "item_id",
            "audit_log_id",
        ),
        dependencies=(
            "VaultItem model",
            "VaultAuditLog model",
            "PostgreSQL JSONB",
        ),
        deterministic=True,
    )
)


@dataclass
class IngestionRequest:
    """
    Standardized ingestion request following the data contract.
    
    All fields must be provided; use None for unknown values.
    """
    user_id: str
    item_type: str  # lease, notice, photo, email, audio, etc.
    
    # THREE TIMESTAMPS (REQUIRED)
    event_time: datetime  # Factual time of event
    record_time: datetime  # When evidence created
    # semptify_entry_time is auto-set by service
    
    # Metadata (REQUIRED - never null, empty dict minimum)
    metadata: dict[str, Any]
    
    # Optional classification
    folder: Optional[str] = None
    tags: Optional[list[str]] = None
    related_incident_id: Optional[int] = None
    source: Optional[str] = None
    severity: Optional[str] = None  # critical, high, normal, low
    status: Optional[str] = None  # pending, verified, disputed, archived
    
    # Optional content
    file_path: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    
    # Rich metadata
    location_data: Optional[dict[str, Any]] = None


@dataclass
class IngestionResult:
    """Result of vault item ingestion."""
    success: bool
    item_id: Optional[int] = None
    audit_log_id: Optional[int] = None
    error_message: Optional[str] = None
    item: Optional[VaultItem] = None


class VaultIngestionError(Exception):
    """Raised when vault ingestion fails due to contract violations."""
    pass


class VaultIngestionService:
    """
    Service for ingesting evidence into the unified vault.
    
    Enforces:
    - Data contract compliance
    - Three-timestamp model
    - Complete audit logging
    - Metadata preservation
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _validate_request(self, request: IngestionRequest) -> None:
        """
        Validate ingestion request against data contract.
        
        Raises:
            VaultIngestionError: If request violates data contract.
        """
        errors: list[str] = []
        
        # Required fields
        if not request.user_id:
            errors.append("user_id is required")
        if not request.item_type:
            errors.append("item_type is required")
        
        # Three timestamps required
        if not request.event_time:
            errors.append("event_time is required (three-timestamp model)")
        if not request.record_time:
            errors.append("record_time is required (three-timestamp model)")
        
        # Metadata must not be None (empty dict is acceptable)
        if request.metadata is None:
            errors.append("metadata cannot be None (use empty dict if no metadata)")
        
        # Validate timestamp logic
        if request.event_time and request.record_time:
            # Event time should generally not be after record time
            # (Record is when evidence was created, event is when it happened)
            if request.event_time > request.record_time:
                errors.append(
                    f"event_time ({request.event_time}) cannot be after "
                    f"record_time ({request.record_time})"
                )
        
        if errors:
            raise VaultIngestionError(
                f"Data contract violations: {'; '.join(errors)}"
            )
    
    def _preserve_metadata(self, raw_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Preserve all metadata without flattening or discarding.
        
        Rules:
        - Never discard metadata
        - Never flatten metadata
        - Preserve nested JSON
        - Convert unserializable values to strings
        """
        def make_serializable(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            elif isinstance(obj, (datetime,)):
                return obj.isoformat()
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif obj is None:
                return None
            else:
                # Convert unknown types to string representation
                return str(obj)
        
        return make_serializable(raw_metadata)
    
    async def ingest(
        self,
        request: IngestionRequest,
        action_context: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest a new vault item with full data contract enforcement.
        
        Args:
            request: IngestionRequest with complete data contract fields
            action_context: Context for audit log (API endpoint, job name, etc.)
        
        Returns:
            IngestionResult with item_id and audit_log_id on success
        """
        try:
            # Validate against data contract
            self._validate_request(request)
            
            # Prepare metadata (preserve everything)
            preserved_metadata = self._preserve_metadata(request.metadata)
            
            # Ensure timezone-aware timestamps
            event_time = self._ensure_timezone(request.event_time)
            record_time = self._ensure_timezone(request.record_time)
            semptify_entry_time = utc_now()
            
            # Create vault item
            vault_item = VaultItem(
                user_id=request.user_id,
                
                # Three timestamps (NON-NEGOTIABLE)
                event_time=event_time,
                record_time=record_time,
                semptify_entry_time=semptify_entry_time,
                
                # Classification
                item_type=request.item_type,
                folder=request.folder,
                tags=request.tags or [],
                
                # Relationships & Context
                related_incident_id=request.related_incident_id,
                source=request.source or "ingestion_service",
                severity=request.severity or "normal",
                status=request.status or "pending",
                
                # Rich metadata
                location_data=request.location_data,
                metadata=preserved_metadata,
                
                # Content
                file_path=request.file_path,
                title=request.title,
                summary=request.summary,
                
                # Timestamps
                created_at=semptify_entry_time,
                updated_at=semptify_entry_time,
            )
            
            self.db.add(vault_item)
            await self.db.flush()  # Get item_id
            
            # Create audit log entry
            audit_log = VaultAuditLog(
                item_id=vault_item.item_id,
                user_id=request.user_id,
                action="create",
                action_context=action_context or "vault_ingestion_service",
                before_state=None,  # New item, no before state
                after_state={
                    "item_id": vault_item.item_id,
                    "item_type": request.item_type,
                    "event_time": event_time.isoformat(),
                    "record_time": record_time.isoformat(),
                    "semptify_entry_time": semptify_entry_time.isoformat(),
                    "metadata_keys": list(preserved_metadata.keys()),
                },
                timestamp=semptify_entry_time,
            )
            
            self.db.add(audit_log)
            await self.db.flush()
            
            return IngestionResult(
                success=True,
                item_id=vault_item.item_id,
                audit_log_id=audit_log.log_id,
                item=vault_item,
            )
            
        except VaultIngestionError as e:
            return IngestionResult(
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                error_message=f"Unexpected ingestion error: {type(e).__name__}: {str(e)}",
            )
    
    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware (UTC if none specified)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    async def update_item(
        self,
        item_id: int,
        user_id: str,
        updates: dict[str, Any],
        action_context: Optional[str] = None,
    ) -> IngestionResult:
        """
        Update existing vault item with audit logging.
        
        Args:
            item_id: ID of item to update
            user_id: User performing the update
            updates: Dict of field updates
            action_context: Context for audit log
        
        Returns:
            IngestionResult with updated item
        """
        try:
            # Fetch existing item
            result = await self.db.execute(
                select(VaultItem).where(
                    VaultItem.item_id == item_id,
                    VaultItem.user_id == user_id,
                )
            )
            item = result.scalar_one_or_none()
            
            if not item:
                return IngestionResult(
                    success=False,
                    error_message=f"Vault item {item_id} not found for user {user_id}",
                )
            
            # Capture before state
            before_state = {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "event_time": item.event_time.isoformat(),
                "record_time": item.record_time.isoformat(),
                "semptify_entry_time": item.semptify_entry_time.isoformat(),
                "folder": item.folder,
                "tags": item.tags,
                "severity": item.severity,
                "status": item.status,
                "title": item.title,
                "summary": item.summary,
            }
            
            # Apply updates (protecting immutable fields)
            immutable_fields = {
                'item_id', 'user_id', 'event_time', 'record_time',
                'semptify_entry_time', 'created_at',
            }
            
            for field, value in updates.items():
                if field in immutable_fields:
                    continue  # Skip immutable fields
                if hasattr(item, field):
                    setattr(item, field, value)
            
            item.updated_at = utc_now()
            await self.db.flush()
            
            # Capture after state
            after_state = {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "event_time": item.event_time.isoformat(),
                "record_time": item.record_time.isoformat(),
                "semptify_entry_time": item.semptify_entry_time.isoformat(),
                "folder": item.folder,
                "tags": item.tags,
                "severity": item.severity,
                "status": item.status,
                "title": item.title,
                "summary": item.summary,
            }
            
            # Create audit log
            audit_log = VaultAuditLog(
                item_id=item.item_id,
                user_id=user_id,
                action="update",
                action_context=action_context or "vault_ingestion_service.update",
                before_state=before_state,
                after_state=after_state,
                timestamp=utc_now(),
            )
            self.db.add(audit_log)
            await self.db.flush()
            
            return IngestionResult(
                success=True,
                item_id=item.item_id,
                audit_log_id=audit_log.log_id,
                item=item,
            )
            
        except Exception as e:
            return IngestionResult(
                success=False,
                error_message=f"Update error: {type(e).__name__}: {str(e)}",
            )
    
    async def delete_item(
        self,
        item_id: int,
        user_id: str,
        action_context: Optional[str] = None,
    ) -> IngestionResult:
        """
        Delete vault item with audit logging (soft delete not implemented yet).
        
        Args:
            item_id: ID of item to delete
            user_id: User performing the deletion
            action_context: Context for audit log
        
        Returns:
            IngestionResult
        """
        try:
            result = await self.db.execute(
                select(VaultItem).where(
                    VaultItem.item_id == item_id,
                    VaultItem.user_id == user_id,
                )
            )
            item = result.scalar_one_or_none()
            
            if not item:
                return IngestionResult(
                    success=False,
                    error_message=f"Vault item {item_id} not found for user {user_id}",
                )
            
            # Capture before state
            before_state = {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "title": item.title,
                "metadata_keys": list(item.metadata.keys()) if item.metadata else [],
            }
            
            # Create audit log before deletion
            audit_log = VaultAuditLog(
                item_id=item.item_id,
                user_id=user_id,
                action="delete",
                action_context=action_context or "vault_ingestion_service.delete",
                before_state=before_state,
                after_state=None,
                timestamp=utc_now(),
            )
            self.db.add(audit_log)
            
            # Delete item (cascades to audit_logs via FK)
            await self.db.delete(item)
            await self.db.flush()
            
            return IngestionResult(
                success=True,
                item_id=item_id,
                audit_log_id=audit_log.log_id,
            )
            
        except Exception as e:
            return IngestionResult(
                success=False,
                error_message=f"Delete error: {type(e).__name__}: {str(e)}",
            )


# Convenience functions for direct use
async def ingest_vault_item(
    db: AsyncSession,
    user_id: str,
    item_type: str,
    event_time: datetime,
    record_time: datetime,
    metadata: dict[str, Any],
    **kwargs: Any,
) -> IngestionResult:
    """
    Convenience function to ingest a vault item.
    
    Example:
        result = await ingest_vault_item(
            db=db,
            user_id="abc123",
            item_type="notice",
            event_time=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
            record_time=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
            metadata={
                "notice_type": "pay_or_quit",
                "amount_due": 1500.00,
                "landlord": "ABC Management",
            },
            title="3-Day Pay or Quit Notice",
            severity="critical",
        )
    """
    service = VaultIngestionService(db)
    request = IngestionRequest(
        user_id=user_id,
        item_type=item_type,
        event_time=event_time,
        record_time=record_time,
        metadata=metadata,
        **kwargs,
    )
    return await service.ingest(request)
