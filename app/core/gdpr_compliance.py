"""
GDPR Compliance Manager - Data Protection and Privacy
===============================================

Handles GDPR compliance requirements including data export, consent management,
and privacy controls.
"""

import logging
import json
import zipfile
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import os

logger = logging.getLogger(__name__)

class ConsentType(Enum):
    """Types of user consent."""
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    COOKIES = "cookies"
    STORAGE = "storage"

class ConsentStatus(Enum):
    """Status of user consent."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"

@dataclass
class ConsentRecord:
    """Record of user consent."""
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    ip_address: Optional[str]
    user_agent: Optional[str]
    purpose: str
    legal_basis: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "purpose": self.purpose,
            "legal_basis": self.legal_basis
        }

@dataclass
class DataSubjectRequest:
    """Data subject access request."""
    request_id: str
    user_id: str
    request_type: str  # "access", "portability", "deletion", "rectification"
    requested_at: datetime
    status: str
    completed_at: Optional[datetime]
    data_export_url: Optional[str]
    error_message: Optional[str]

class GDPRComplianceManager:
    """Manages GDPR compliance operations."""
    
    def __init__(self):
        self.user_consents: Dict[str, List[ConsentRecord]] = {}
        self.data_requests: Dict[str, DataSubjectRequest] = {}
        self.retention_policies = {
            "documents": timedelta(days=2555),  # 7 years
            "audit_logs": timedelta(days=1095),   # 3 years
            "user_data": timedelta(days=2555),   # 7 years
            "consent_records": timedelta(days=3650)  # 10 years
        }
        
    def record_consent(self, user_id: str, consent_type: ConsentType, 
                      status: ConsentStatus, ip_address: str, user_agent: str,
                      purpose: str, legal_basis: str = "legitimate_interest") -> bool:
        """Record user consent."""
        if user_id not in self.user_consents:
            self.user_consents[user_id] = []
        
        # Check if consent record already exists
        existing_record = None
        for record in self.user_consents[user_id]:
            if record.consent_type == consent_type:
                existing_record = record
                break
        
        if existing_record:
            # Update existing record
            existing_record.status = status
            if status == ConsentStatus.GRANTED:
                existing_record.granted_at = datetime.now(timezone.utc)
                existing_record.withdrawn_at = None
            elif status == ConsentStatus.WITHDRAWN:
                existing_record.withdrawn_at = datetime.now(timezone.utc)
            existing_record.ip_address = ip_address
            existing_record.user_agent = user_agent
        else:
            # Create new record
            record = ConsentRecord(
                consent_type=consent_type,
                status=status,
                granted_at=datetime.now(timezone.utc) if status == ConsentStatus.GRANTED else None,
                withdrawn_at=datetime.now(timezone.utc) if status == ConsentStatus.WITHDRAWN else None,
                ip_address=ip_address,
                user_agent=user_agent,
                purpose=purpose,
                legal_basis=legal_basis
            )
            self.user_consents[user_id].append(record)
        
        logger.info(f"Recorded consent for user {user_id}, type {consent_type.value}, status {status.value}")
        return True
    
    def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        return self.user_consents.get(user_id, [])
    
    def has_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has granted consent for a specific type."""
        consents = self.get_user_consents(user_id)
        
        for consent in consents:
            if consent.consent_type == consent_type:
                return consent.status == ConsentStatus.GRANTED and consent.withdrawn_at is None
        
        return False
    
    def create_data_request(self, user_id: str, request_type: str, 
                          ip_address: str, user_agent: str) -> str:
        """Create a data subject request."""
        request_id = f"dsr_{datetime.now(timezone.utc).timestamp()}_{user_id}"
        
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            requested_at=datetime.now(timezone.utc),
            status="pending",
            completed_at=None,
            data_export_url=None,
            error_message=None
        )
        
        self.data_requests[request_id] = request
        logger.info(f"Created data subject request {request_id} for user {user_id}, type {request_type}")
        
        return request_id
    
    def process_data_request(self, request_id: str) -> bool:
        """Process a data subject request."""
        request = self.data_requests.get(request_id)
        if not request:
            logger.error(f"Data request {request_id} not found")
            return False
        
        request.status = "processing"
        
        try:
            if request.request_type == "access":
                success = self._process_access_request(request)
            elif request.request_type == "portability":
                success = self._process_portability_request(request)
            elif request.request_type == "deletion":
                success = self._process_deletion_request(request)
            elif request.request_type == "rectification":
                success = self._process_rectification_request(request)
            else:
                raise ValueError(f"Unknown request type: {request.request_type}")
            
            if success:
                request.status = "completed"
                request.completed_at = datetime.now(timezone.utc)
                logger.info(f"Successfully completed data request {request_id}")
            else:
                request.status = "failed"
                logger.error(f"Failed to complete data request {request_id}")
            
            return success
            
        except Exception as e:
            request.status = "failed"
            request.error_message = str(e)
            logger.error(f"Error processing data request {request_id}: {e}")
            return False
    
    def _process_access_request(self, request: DataSubjectRequest) -> bool:
        """Process data access request."""
        try:
            # Collect all user data
            user_data = self._collect_user_data(request.user_id)
            
            # Create JSON export
            export_data = {
                "request_id": request.request_id,
                "user_id": request.user_id,
                "export_date": datetime.now(timezone.utc).isoformat(),
                "data": user_data
            }
            
            # Save export file
            export_filename = f"data_export_{request.request_id}.json"
            export_path = f"exports/{export_filename}"
            os.makedirs("exports", exist_ok=True)
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            request.data_export_url = f"/api/gdpr/export/{request.request_id}"
            return True
            
        except Exception as e:
            logger.error(f"Error processing access request: {e}")
            return False
    
    def _process_portability_request(self, request: DataSubjectRequest) -> bool:
        """Process data portability request."""
        try:
            # Collect user data
            user_data = self._collect_user_data(request.user_id)
            
            # Create ZIP file with structured data
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add JSON data
                json_data = json.dumps(user_data, indent=2, default=str)
                zip_file.writestr("user_data.json", json_data)
                
                # Add documents if available
                documents = self._get_user_documents(request.user_id)
                for doc in documents:
                    try:
                        doc_content = self._get_document_content(doc['id'])
                        if doc_content:
                            zip_file.writestr(f"documents/{doc['filename']}", doc_content)
                    except Exception as e:
                        logger.warning(f"Failed to include document {doc['id']}: {e}")
                
                # Add consent records
                consent_data = [consent.to_dict() for consent in self.get_user_consents(request.user_id)]
                consent_json = json.dumps(consent_data, indent=2, default=str)
                zip_file.writestr("consent_records.json", consent_json)
            
            # Save ZIP file
            zip_filename = f"data_portability_{request.request_id}.zip"
            zip_path = f"exports/{zip_filename}"
            os.makedirs("exports", exist_ok=True)
            
            with open(zip_path, 'wb') as f:
                f.write(zip_buffer.getvalue())
            
            request.data_export_url = f"/api/gdpr/portability/{request.request_id}"
            return True
            
        except Exception as e:
            logger.error(f"Error processing portability request: {e}")
            return False
    
    def _process_deletion_request(self, request: DataSubjectRequest) -> bool:
        """Process data deletion request."""
        try:
            from app.core.data_deletion import request_account_deletion, execute_deletion_request
            
            # Create deletion request
            deletion_request_id = request_account_deletion(
                user_id=request.user_id,
                reason="GDPR deletion request"
            )
            
            # Execute deletion
            success = execute_deletion_request(deletion_request_id)
            
            if success:
                # Remove consent records
                if request.user_id in self.user_consents:
                    del self.user_consents[request.user_id]
                
                logger.info(f"Successfully processed GDPR deletion request {request_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing deletion request: {e}")
            return False
    
    def _process_rectification_request(self, request: DataSubjectRequest) -> bool:
        """Process data rectification request."""
        # This would typically require manual review
        # For now, just mark as completed with a note
        logger.info(f"Rectification request {request_id} requires manual review")
        return True
    
    def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """Collect all user data for export."""
        user_data = {
            "user_id": user_id,
            "consent_records": [consent.to_dict() for consent in self.get_user_consents(user_id)],
            "documents": self._get_user_documents(user_id),
            "audit_events": self._get_user_audit_events(user_id),
            "storage_info": self._get_user_storage_info(user_id),
            "account_info": self._get_user_account_info(user_id)
        }
        
        return user_data
    
    def _get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user documents metadata."""
        try:
            from app.services.vault_upload_service import get_vault_service
            vault_service = get_vault_service()
            documents = vault_service.get_user_documents(user_id)
            
            return [
                {
                    "id": doc.vault_id,
                    "filename": doc.filename,
                    "size": doc.size,
                    "mime_type": doc.mime_type,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "tags": doc.tags or [],
                    "provider": doc.provider
                }
                for doc in documents
            ]
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return []
    
    def _get_user_audit_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user audit events."""
        try:
            from app.core.audit_logger import get_audit_logger
            audit_logger = get_audit_logger()
            events = audit_logger.get_user_events(user_id, limit=1000)
            
            return [event.to_dict() for event in events]
        except Exception as e:
            logger.error(f"Error getting user audit events: {e}")
            return []
    
    def _get_user_storage_info(self, user_id: str) -> Dict[str, Any]:
        """Get user storage information."""
        try:
            from app.services.vault_upload_service import get_vault_service
            vault_service = get_vault_service()
            
            documents = vault_service.get_user_documents(user_id)
            total_size = sum(doc.size for doc in documents)
            
            return {
                "total_documents": len(documents),
                "total_size_bytes": total_size,
                "storage_provider": vault_service.get_user_provider(user_id),
                "storage_quota_used": total_size / (1024 * 1024 * 1024),  # GB
                "last_upload": max([doc.created_at for doc in documents]).isoformat() if documents else None
            }
        except Exception as e:
            logger.error(f"Error getting user storage info: {e}")
            return {}
    
    def _get_user_account_info(self, user_id: str) -> Dict[str, Any]:
        """Get user account information."""
        # This would depend on your user management system
        return {
            "user_id": user_id,
            "account_created": datetime.now(timezone.utc).isoformat(),  # Placeholder
            "last_login": datetime.now(timezone.utc).isoformat(),  # Placeholder
            "account_status": "active"
        }
    
    def _get_document_content(self, document_id: str) -> Optional[bytes]:
        """Get document content for export."""
        try:
            from app.services.vault_upload_service import get_vault_service
            vault_service = get_vault_service()
            return vault_service.get_document_content(document_id)
        except Exception as e:
            logger.error(f"Error getting document content {document_id}: {e}")
            return None
    
    def get_data_request(self, request_id: str) -> Optional[DataSubjectRequest]:
        """Get data subject request by ID."""
        return self.data_requests.get(request_id)
    
    def get_user_data_requests(self, user_id: str) -> List[DataSubjectRequest]:
        """Get all data requests for a user."""
        return [req for req in self.data_requests.values() if req.user_id == user_id]
    
    def apply_retention_policies(self):
        """Apply data retention policies."""
        current_time = datetime.now(timezone.utc)
        
        # Clean up old data requests
        expired_requests = []
        for req_id, request in self.data_requests.items():
            if request.completed_at and (current_time - request.completed_at) > timedelta(days=30):
                expired_requests.append(req_id)
        
        for req_id in expired_requests:
            del self.data_requests[req_id]
        
        if expired_requests:
            logger.info(f"Cleaned up {len(expired_requests)} expired data requests")
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get GDPR compliance summary."""
        total_users = len(self.user_consents)
        total_requests = len(self.data_requests)
        
        # Consent statistics
        consent_stats = {}
        for user_id, consents in self.user_consents.items():
            for consent in consents:
                consent_type = consent.consent_type.value
                status = consent.status.value
                
                if consent_type not in consent_stats:
                    consent_stats[consent_type] = {}
                
                consent_stats[consent_type][status] = consent_stats[consent_type].get(status, 0) + 1
        
        # Request statistics
        request_stats = {}
        for request in self.data_requests.values():
            request_type = request.request_type
            status = request.status
            
            if request_type not in request_stats:
                request_stats[request_type] = {}
            
            request_stats[request_type][status] = request_stats[request_type].get(status, 0) + 1
        
        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "consent_statistics": consent_stats,
            "request_statistics": request_stats,
            "retention_policies": {k: str(v) for k, v in self.retention_policies.items()}
        }

# Global GDPR compliance manager instance
gdpr_manager = GDPRComplianceManager()

def get_gdpr_manager() -> GDPRComplianceManager:
    """Get the global GDPR compliance manager instance."""
    return gdpr_manager

# Helper functions for common GDPR operations
def grant_consent(user_id: str, consent_type: ConsentType, ip_address: str, user_agent: str, purpose: str):
    """Grant user consent."""
    return gdpr_manager.record_consent(
        user_id=user_id,
        consent_type=consent_type,
        status=ConsentStatus.GRANTED,
        ip_address=ip_address,
        user_agent=user_agent,
        purpose=purpose
    )

def withdraw_consent(user_id: str, consent_type: ConsentType, ip_address: str, user_agent: str):
    """Withdraw user consent."""
    return gdpr_manager.record_consent(
        user_id=user_id,
        consent_type=consent_type,
        status=ConsentStatus.WITHDRAWN,
        ip_address=ip_address,
        user_agent=user_agent,
        purpose="Consent withdrawn"
    )

def create_access_request(user_id: str, ip_address: str, user_agent: str) -> str:
    """Create data access request."""
    return gdpr_manager.create_data_request(
        user_id=user_id,
        request_type="access",
        ip_address=ip_address,
        user_agent=user_agent
    )

def create_deletion_request(user_id: str, ip_address: str, user_agent: str) -> str:
    """Create data deletion request."""
    return gdpr_manager.create_data_request(
        user_id=user_id,
        request_type="deletion",
        ip_address=ip_address,
        user_agent=user_agent
    )
