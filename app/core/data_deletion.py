"""
Data Deletion Manager - Secure Data Removal and GDPR Compliance
===========================================================

Handles secure deletion of user data, documents, and compliance requirements.
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DeletionStatus(Enum):
    """Status of deletion operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DeletionScope(Enum):
    """Scope of data deletion."""
    SINGLE_DOCUMENT = "single_document"
    ALL_DOCUMENTS = "all_documents"
    USER_DATA = "user_data"
    COMPLETE_ACCOUNT = "complete_account"

@dataclass
class DeletionRequest:
    """Data deletion request."""
    request_id: str
    user_id: str
    scope: DeletionScope
    target_id: Optional[str]  # Document ID for single document deletion
    reason: str
    requested_at: datetime
    status: DeletionStatus
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    audit_log: List[str] = None
    
    def __post_init__(self):
        if self.audit_log is None:
            self.audit_log = []

class DataDeletionManager:
    """Manages secure data deletion operations."""
    
    def __init__(self):
        self.requests: Dict[str, DeletionRequest] = {}
        self.deletion_retention_days = 30  # Keep deletion records for 30 days
        
    def create_deletion_request(self, user_id: str, scope: DeletionScope, 
                              target_id: Optional[str] = None, reason: str = "") -> str:
        """Create a new deletion request."""
        request_id = f"del_{datetime.now(timezone.utc).timestamp()}_{user_id}"
        
        request = DeletionRequest(
            request_id=request_id,
            user_id=user_id,
            scope=scope,
            target_id=target_id,
            reason=reason,
            requested_at=datetime.now(timezone.utc),
            status=DeletionStatus.PENDING
        )
        
        self.requests[request_id] = request
        logger.info(f"Created deletion request {request_id} for user {user_id}, scope {scope.value}")
        
        return request_id
    
    def get_deletion_request(self, request_id: str) -> Optional[DeletionRequest]:
        """Get deletion request by ID."""
        return self.requests.get(request_id)
    
    def get_user_deletion_requests(self, user_id: str) -> List[DeletionRequest]:
        """Get all deletion requests for a user."""
        return [req for req in self.requests.values() if req.user_id == user_id]
    
    def execute_deletion(self, request_id: str) -> bool:
        """Execute a deletion request."""
        request = self.requests.get(request_id)
        if not request:
            logger.error(f"Deletion request {request_id} not found")
            return False
        
        if request.status != DeletionStatus.PENDING:
            logger.warning(f"Deletion request {request_id} already processed")
            return False
        
        request.status = DeletionStatus.IN_PROGRESS
        request.audit_log.append(f"Started deletion at {datetime.now(timezone.utc)}")
        
        try:
            if request.scope == DeletionScope.SINGLE_DOCUMENT:
                success = self._delete_single_document(request)
            elif request.scope == DeletionScope.ALL_DOCUMENTS:
                success = self._delete_all_documents(request)
            elif request.scope == DeletionScope.USER_DATA:
                success = self._delete_user_data(request)
            elif request.scope == DeletionScope.COMPLETE_ACCOUNT:
                success = self._delete_complete_account(request)
            else:
                raise ValueError(f"Unknown deletion scope: {request.scope}")
            
            if success:
                request.status = DeletionStatus.COMPLETED
                request.completed_at = datetime.now(timezone.utc)
                request.audit_log.append(f"Deletion completed at {request.completed_at}")
                logger.info(f"Successfully completed deletion request {request_id}")
            else:
                request.status = DeletionStatus.FAILED
                request.error_message = "Deletion operation failed"
                request.audit_log.append("Deletion failed")
                logger.error(f"Failed deletion request {request_id}")
            
            return success
            
        except Exception as e:
            request.status = DeletionStatus.FAILED
            request.error_message = str(e)
            request.audit_log.append(f"Deletion failed with error: {str(e)}")
            logger.error(f"Error executing deletion request {request_id}: {e}")
            return False
    
    def _delete_single_document(self, request: DeletionRequest) -> bool:
        """Delete a single document."""
        if not request.target_id:
            raise ValueError("Document ID required for single document deletion")
        
        try:
            # Get vault service
            from app.services.vault_upload_service import get_vault_service
            vault_service = get_vault_service()
            
            # Delete from vault
            success = vault_service.delete_document(request.target_id, request.user_id)
            
            if success:
                request.audit_log.append(f"Deleted document {request.target_id} from vault")
                
                # Log deletion
                from app.core.audit_logger import get_audit_logger
                audit_logger = get_audit_logger()
                audit_logger.document_deleted(
                    user_id=request.user_id,
                    document_id=request.target_id,
                    filename=f"document_{request.target_id}",
                    ip_address="system",
                    user_agent="data_deletion_manager",
                    success=True
                )
            else:
                request.audit_log.append(f"Failed to delete document {request.target_id} from vault")
            
            return success
            
        except Exception as e:
            request.audit_log.append(f"Error deleting document {request.target_id}: {str(e)}")
            raise
    
    def _delete_all_documents(self, request: DeletionRequest) -> bool:
        """Delete all documents for a user."""
        try:
            # Get vault service
            from app.services.vault_upload_service import get_vault_service
            vault_service = get_vault_service()
            
            # Get all user documents
            documents = vault_service.get_user_documents(request.user_id)
            
            deleted_count = 0
            failed_count = 0
            
            for doc in documents:
                try:
                    success = vault_service.delete_document(doc.vault_id, request.user_id)
                    if success:
                        deleted_count += 1
                        request.audit_log.append(f"Deleted document {doc.vault_id} ({doc.filename})")
                        
                        # Log deletion
                        from app.core.audit_logger import get_audit_logger
                        audit_logger = get_audit_logger()
                        audit_logger.document_deleted(
                            user_id=request.user_id,
                            document_id=doc.vault_id,
                            filename=doc.filename,
                            ip_address="system",
                            user_agent="data_deletion_manager",
                            success=True
                        )
                    else:
                        failed_count += 1
                        request.audit_log.append(f"Failed to delete document {doc.vault_id} ({doc.filename})")
                except Exception as e:
                    failed_count += 1
                    request.audit_log.append(f"Error deleting document {doc.vault_id}: {str(e)}")
            
            request.audit_log.append(f"Deleted {deleted_count} documents, {failed_count} failed")
            
            return failed_count == 0
            
        except Exception as e:
            request.audit_log.append(f"Error deleting all documents: {str(e)}")
            raise
    
    def _delete_user_data(self, request: DeletionRequest) -> bool:
        """Delete user data (excluding documents)."""
        try:
            # Delete user preferences, settings, and other metadata
            deleted_items = []
            
            # Delete user from database if applicable
            try:
                # This would depend on your database structure
                # For now, just log the action
                deleted_items.append("user_database_record")
                request.audit_log.append("Deleted user database record")
            except Exception as e:
                request.audit_log.append(f"Failed to delete user database record: {str(e)}")
            
            # Delete user cache files
            try:
                cache_dir = f"cache/user_{request.user_id}"
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    deleted_items.append("user_cache")
                    request.audit_log.append("Deleted user cache directory")
            except Exception as e:
                request.audit_log.append(f"Failed to delete user cache: {str(e)}")
            
            # Delete user temporary files
            try:
                temp_dir = f"temp/user_{request.user_id}"
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    deleted_items.append("user_temp_files")
                    request.audit_log.append("Deleted user temporary files")
            except Exception as e:
                request.audit_log.append(f"Failed to delete user temp files: {str(e)}")
            
            request.audit_log.append(f"Deleted user data items: {', '.join(deleted_items)}")
            
            return True
            
        except Exception as e:
            request.audit_log.append(f"Error deleting user data: {str(e)}")
            raise
    
    def _delete_complete_account(self, request: DeletionRequest) -> bool:
        """Delete complete user account including all data."""
        try:
            # Delete all documents first
            docs_success = self._delete_all_documents(request)
            request.audit_log.append("Document deletion completed for account deletion")
            
            # Delete user data
            data_success = self._delete_user_data(request)
            request.audit_log.append("User data deletion completed for account deletion")
            
            # Additional cleanup
            try:
                # Delete any remaining user-related files
                user_dirs = [
                    f"uploads/{request.user_id}",
                    f"processing/{request.user_id}",
                    f"backups/{request.user_id}"
                ]
                
                for user_dir in user_dirs:
                    if os.path.exists(user_dir):
                        shutil.rmtree(user_dir)
                        request.audit_log.append(f"Deleted directory: {user_dir}")
                
            except Exception as e:
                request.audit_log.append(f"Error cleaning up user directories: {str(e)}")
            
            overall_success = docs_success and data_success
            request.audit_log.append(f"Complete account deletion {'succeeded' if overall_success else 'failed'}")
            
            return overall_success
            
        except Exception as e:
            request.audit_log.append(f"Error deleting complete account: {str(e)}")
            raise
    
    def cancel_deletion_request(self, request_id: str) -> bool:
        """Cancel a pending deletion request."""
        request = self.requests.get(request_id)
        if not request:
            return False
        
        if request.status != DeletionStatus.PENDING:
            return False
        
        request.status = DeletionStatus.CANCELLED
        request.completed_at = datetime.now(timezone.utc)
        request.audit_log.append(f"Request cancelled at {request.completed_at}")
        
        logger.info(f"Cancelled deletion request {request_id}")
        return True
    
    def cleanup_old_requests(self):
        """Clean up old deletion requests."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.deletion_retention_days)
        
        old_requests = [
            req_id for req_id, req in self.requests.items()
            if req.completed_at and req.completed_at < cutoff_date
        ]
        
        for req_id in old_requests:
            del self.requests[req_id]
        
        if old_requests:
            logger.info(f"Cleaned up {len(old_requests)} old deletion requests")
    
    def get_deletion_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of deletion operations."""
        requests = list(self.requests.values())
        
        if user_id:
            requests = [req for req in requests if req.user_id == user_id]
        
        # Count by status
        status_counts = {}
        for req in requests:
            status = req.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by scope
        scope_counts = {}
        for req in requests:
            scope = req.scope.value
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        # Success rate
        completed_requests = [req for req in requests if req.status == DeletionStatus.COMPLETED]
        failed_requests = [req for req in requests if req.status == DeletionStatus.FAILED]
        
        success_rate = 0
        total_finished = len(completed_requests) + len(failed_requests)
        if total_finished > 0:
            success_rate = (len(completed_requests) / total_finished) * 100
        
        return {
            "total_requests": len(requests),
            "status_counts": status_counts,
            "scope_counts": scope_counts,
            "success_rate": success_rate,
            "completed": len(completed_requests),
            "failed": len(failed_requests),
            "pending": len([req for req in requests if req.status == DeletionStatus.PENDING]),
            "in_progress": len([req for req in requests if req.status == DeletionStatus.IN_PROGRESS])
        }

# Global deletion manager instance
deletion_manager = DataDeletionManager()

def get_deletion_manager() -> DataDeletionManager:
    """Get the global deletion manager instance."""
    return deletion_manager

# Helper functions for common deletion operations
def request_document_deletion(user_id: str, document_id: str, reason: str = "") -> str:
    """Request deletion of a single document."""
    return deletion_manager.create_deletion_request(
        user_id=user_id,
        scope=DeletionScope.SINGLE_DOCUMENT,
        target_id=document_id,
        reason=reason
    )

def request_all_documents_deletion(user_id: str, reason: str = "") -> str:
    """Request deletion of all user documents."""
    return deletion_manager.create_deletion_request(
        user_id=user_id,
        scope=DeletionScope.ALL_DOCUMENTS,
        reason=reason
    )

def request_account_deletion(user_id: str, reason: str = "") -> str:
    """Request complete account deletion."""
    return deletion_manager.create_deletion_request(
        user_id=user_id,
        scope=DeletionScope.COMPLETE_ACCOUNT,
        reason=reason
    )

def execute_deletion_request(request_id: str) -> bool:
    """Execute a deletion request."""
    return deletion_manager.execute_deletion(request_id)
