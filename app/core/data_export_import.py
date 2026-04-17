"""
Data Export/Import System - GDPR Compliant Data Management
=======================================================

Handles data export and import operations with GDPR compliance and validation.
"""

import logging
import json
import csv
import io
import zipfile
import asyncio
from typing import Dict, Any, List, Optional, Union, BinaryIO
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import tempfile
import os

logger = logging.getLogger(__name__)

class ExportFormat(Enum):
    """Data export formats."""
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"
    PDF = "pdf"

class ImportFormat(Enum):
    """Data import formats."""
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"

class ExportType(Enum):
    """Data export types."""
    ALL_DATA = "all_data"
    DOCUMENTS_ONLY = "documents_only"
    TIMELINE_ONLY = "timeline_only"
    CONTACTS_ONLY = "contacts_only"
    USER_PROFILE = "user_profile"
    AUDIT_LOG = "audit_log"

@dataclass
class ExportRequest:
    """Data export request."""
    export_id: str
    user_id: str
    export_type: ExportType
    format: ExportFormat
    filters: Dict[str, Any]
    created_at: datetime
    status: str = "pending"
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ImportRequest:
    """Data import request."""
    import_id: str
    user_id: str
    import_type: str
    format: ImportFormat
    created_at: datetime
    file_path: Optional[str] = None
    validation_required: bool = True
    status: str = "pending"
    processed_at: Optional[datetime] = None
    items_processed: int = 0
    items_failed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class DataExportImportManager:
    """Manages data export and import operations."""
    
    def __init__(self):
        self.active_exports: Dict[str, ExportRequest] = {}
        self.active_imports: Dict[str, ImportRequest] = {}
        
        # Statistics
        self.stats = {
            "total_exports": 0,
            "completed_exports": 0,
            "total_imports": 0,
            "completed_imports": 0,
            "exported_documents": 0,
            "imported_documents": 0
        }
        
        # Export retention (days)
        self.export_retention_days = 7
    
    def create_export_request(self, user_id: str, export_type: ExportType,
                           format: ExportFormat, filters: Dict[str, Any] = None) -> str:
        """Create a new export request."""
        export_id = f"export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(user_id.encode()).hexdigest()[:8]}"
        
        request = ExportRequest(
            export_id=export_id,
            user_id=user_id,
            export_type=export_type,
            format=format,
            filters=filters or {},
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_exports[export_id] = request
        self.stats["total_exports"] += 1
        
        logger.info(f"Created export request {export_id} for user {user_id}")
        return export_id
    
    def create_import_request(self, user_id: str, import_type: str,
                           format: ImportFormat, validation_required: bool = True) -> str:
        """Create a new import request."""
        import_id = f"import_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(user_id.encode()).hexdigest()[:8]}"
        
        request = ImportRequest(
            import_id=import_id,
            user_id=user_id,
            import_type=import_type,
            format=format,
            validation_required=validation_required,
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_imports[import_id] = request
        self.stats["total_imports"] += 1
        
        logger.info(f"Created import request {import_id} for user {user_id}")
        return import_id
    
    async def process_export_request(self, export_id: str) -> bool:
        """Process an export request."""
        if export_id not in self.active_exports:
            return False
        
        request = self.active_exports[export_id]
        request.status = "processing"
        
        try:
            # Get user data based on export type
            if request.export_type == ExportType.ALL_DATA:
                export_data = await self._export_all_user_data(request.user_id, request.filters)
            elif request.export_type == ExportType.DOCUMENTS_ONLY:
                export_data = await self._export_documents(request.user_id, request.filters)
            elif request.export_type == ExportType.TIMELINE_ONLY:
                export_data = await self._export_timeline(request.user_id, request.filters)
            elif request.export_type == ExportType.CONTACTS_ONLY:
                export_data = await self._export_contacts(request.user_id, request.filters)
            elif request.export_type == ExportType.USER_PROFILE:
                export_data = await self._export_user_profile(request.user_id)
            elif request.export_type == ExportType.AUDIT_LOG:
                export_data = await self._export_audit_log(request.user_id, request.filters)
            else:
                raise ValueError(f"Unsupported export type: {request.export_type}")
            
            # Generate export file
            file_path = await self._generate_export_file(export_data, request)
            request.file_path = file_path
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            request.expires_at = datetime.now(timezone.utc) + timedelta(days=self.export_retention_days)
            
            # Generate download URL
            request.download_url = f"/export/download/{export_id}"
            
            # Update statistics
            self.stats["completed_exports"] += 1
            if request.export_type in [ExportType.ALL_DATA, ExportType.DOCUMENTS_ONLY]:
                self.stats["exported_documents"] += len(export_data.get("documents", []))
            
            logger.info(f"Completed export {export_id}")
            return True
            
        except Exception as e:
            request.status = "failed"
            request.completed_at = datetime.now(timezone.utc)
            logger.error(f"Export {export_id} failed: {e}")
            return False
    
    async def _export_all_user_data(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Export all user data."""
        # Get all data types
        documents = await self._export_documents(user_id, filters)
        timeline = await self._export_timeline(user_id, filters)
        contacts = await self._export_contacts(user_id, filters)
        profile = await self._export_user_profile(user_id)
        audit_log = await self._export_audit_log(user_id, filters)
        
        return {
            "export_type": "all_data",
            "user_id": user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "documents": documents.get("documents", []),
            "timeline": timeline.get("events", []),
            "contacts": contacts.get("contacts", []),
            "user_profile": profile,
            "audit_log": audit_log.get("events", []),
            "filters": filters
        }
    
    async def _export_documents(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Export user documents."""
        try:
            from app.core.database import get_db_session
            from app.models.models import Document as DocumentModel
            from sqlalchemy import select
            
            async with get_db_session() as session:
                # Build query with filters
                query = select(DocumentModel).where(DocumentModel.user_id == user_id)
                
                # Apply filters
                if "date_from" in filters:
                    date_from = datetime.fromisoformat(filters["date_from"])
                    query = query.where(DocumentModel.created_at >= date_from)
                
                if "date_to" in filters:
                    date_to = datetime.fromisoformat(filters["date_to"])
                    query = query.where(DocumentModel.created_at <= date_to)
                
                if "document_types" in filters:
                    doc_types = filters["document_types"]
                    query = query.where(DocumentModel.document_type.in_(doc_types))
                
                if "tags" in filters:
                    # This would require proper tag filtering implementation
                    pass
                
                result = await session.execute(query)
                documents = result.scalars().all()
                
                # Convert to export format
                export_documents = []
                for doc in documents:
                    export_documents.append({
                        "id": doc.id,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                        "file_size": doc.file_size,
                        "sha256_hash": doc.sha256_hash,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                        "metadata": {
                            "storage_provider": doc.storage_provider,
                            "storage_path": doc.storage_path
                        }
                    })
                
                return {
                    "export_type": "documents",
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "documents": export_documents,
                    "total_count": len(export_documents),
                    "filters": filters
                }
                
        except Exception as e:
            logger.error(f"Document export failed: {e}")
            return {"documents": [], "error": str(e)}
    
    async def _export_timeline(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Export user timeline events."""
        try:
            from app.core.database import get_db_session
            from app.models.models import TimelineEvent as TimelineEventModel
            from sqlalchemy import select
            
            async with get_db_session() as session:
                # Build query with filters
                query = select(TimelineEventModel).where(TimelineEventModel.user_id == user_id)
                
                # Apply filters
                if "date_from" in filters:
                    date_from = datetime.fromisoformat(filters["date_from"])
                    query = query.where(TimelineEventModel.event_date >= date_from)
                
                if "date_to" in filters:
                    date_to = datetime.fromisoformat(filters["date_to"])
                    query = query.where(TimelineEventModel.event_date <= date_to)
                
                if "event_types" in filters:
                    event_types = filters["event_types"]
                    query = query.where(TimelineEventModel.event_type.in_(event_types))
                
                result = await session.execute(query)
                events = result.scalars().all()
                
                # Convert to export format
                export_events = []
                for event in events:
                    export_events.append({
                        "id": event.id,
                        "title": event.title,
                        "description": event.description,
                        "event_type": event.event_type,
                        "event_date": event.event_date.isoformat() if event.event_date else None,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                        "is_evidence": event.is_evidence,
                        "metadata": {
                            "location": event.location,
                            "people_present": event.people_present
                        }
                    })
                
                return {
                    "export_type": "timeline",
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "events": export_events,
                    "total_count": len(export_events),
                    "filters": filters
                }
                
        except Exception as e:
            logger.error(f"Timeline export failed: {e}")
            return {"events": [], "error": str(e)}
    
    async def _export_contacts(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Export user contacts."""
        try:
            from app.core.database import get_db_session
            from app.models.models import Contact as ContactModel
            from sqlalchemy import select
            
            async with get_db_session() as session:
                query = select(ContactModel).where(ContactModel.user_id == user_id)
                
                # Apply filters
                if "contact_types" in filters:
                    contact_types = filters["contact_types"]
                    query = query.where(ContactModel.role.in_(contact_types))
                
                result = await session.execute(query)
                contacts = result.scalars().all()
                
                # Convert to export format
                export_contacts = []
                for contact in contacts:
                    export_contacts.append({
                        "id": contact.id,
                        "name": contact.name,
                        "role": contact.role,
                        "organization": contact.organization,
                        "phone": contact.phone,
                        "email": contact.email,
                        "address": contact.address,
                        "notes": contact.notes,
                        "created_at": contact.created_at.isoformat() if contact.created_at else None,
                        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None
                    })
                
                return {
                    "export_type": "contacts",
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "contacts": export_contacts,
                    "total_count": len(export_contacts),
                    "filters": filters
                }
                
        except Exception as e:
            logger.error(f"Contacts export failed: {e}")
            return {"contacts": [], "error": str(e)}
    
    async def _export_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Export user profile information."""
        try:
            from app.core.database import get_db_session
            from app.models.models import User as UserModel
            from sqlalchemy import select
            
            async with get_db_session() as session:
                query = select(UserModel).where(UserModel.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                
                if not user:
                    return {"error": "User not found"}
                
                # Export user profile (excluding sensitive data)
                profile = {
                    "export_type": "user_profile",
                    "user_id": user_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "profile": {
                        "email": user.email,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "preferences": user.preferences or {},
                        "storage_provider": user.provider,
                        "subscription_tier": getattr(user, 'subscription_tier', 'basic')
                    }
                }
                
                return profile
                
        except Exception as e:
            logger.error(f"User profile export failed: {e}")
            return {"error": str(e)}
    
    async def _export_audit_log(self, user_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Export user audit log."""
        try:
            from app.core.audit_logger import get_audit_logger
            
            audit_logger = get_audit_logger()
            
            # Get audit events with filters
            date_from = datetime.fromisoformat(filters["date_from"]) if "date_from" in filters else None
            date_to = datetime.fromisoformat(filters["date_to"]) if "date_to" in filters else None
            event_types = filters.get("event_types", [])
            
            audit_events = audit_logger.get_user_events(user_id, event_types, date_from, date_to)
            
            return {
                "export_type": "audit_log",
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "events": [event.to_dict() for event in audit_events],
                "total_count": len(audit_events),
                "filters": filters
            }
            
        except Exception as e:
            logger.error(f"Audit log export failed: {e}")
            return {"events": [], "error": str(e)}
    
    async def _generate_export_file(self, data: Dict[str, Any], request: ExportRequest) -> str:
        """Generate export file based on format."""
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        filename = f"{request.export_id}.{request.format.value}"
        file_path = os.path.join(temp_dir, filename)
        
        try:
            if request.format == ExportFormat.JSON:
                await self._generate_json_export(data, file_path)
            elif request.format == ExportFormat.CSV:
                await self._generate_csv_export(data, file_path)
            elif request.format == ExportFormat.ZIP:
                await self._generate_zip_export(data, file_path)
            elif request.format == ExportFormat.PDF:
                await self._generate_pdf_export(data, file_path)
            else:
                raise ValueError(f"Unsupported export format: {request.format}")
            
            return file_path
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e
    
    async def _generate_json_export(self, data: Dict[str, Any], file_path: str):
        """Generate JSON export file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    async def _generate_csv_export(self, data: Dict[str, Any], file_path: str):
        """Generate CSV export file."""
        # CSV export is mainly for documents and contacts
        if "documents" in data:
            await self._generate_documents_csv(data["documents"], file_path)
        elif "contacts" in data:
            await self._generate_contacts_csv(data["contacts"], file_path)
        else:
            # Generic CSV export
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    writer.writerow([key, value])
    
    async def _generate_documents_csv(self, documents: List[Dict[str, Any]], file_path: str):
        """Generate documents CSV export."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "ID", "Filename", "Document Type", "File Size", 
                "SHA256 Hash", "Created At", "Storage Provider"
            ])
            
            # Data rows
            for doc in documents:
                writer.writerow([
                    doc.get("id", ""),
                    doc.get("filename", ""),
                    doc.get("document_type", ""),
                    doc.get("file_size", ""),
                    doc.get("sha256_hash", ""),
                    doc.get("created_at", ""),
                    doc.get("metadata", {}).get("storage_provider", "")
                ])
    
    async def _generate_contacts_csv(self, contacts: List[Dict[str, Any]], file_path: str):
        """Generate contacts CSV export."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "ID", "Name", "Role", "Organization", 
                "Phone", "Email", "Address", "Notes", "Created At"
            ])
            
            # Data rows
            for contact in contacts:
                writer.writerow([
                    contact.get("id", ""),
                    contact.get("name", ""),
                    contact.get("role", ""),
                    contact.get("organization", ""),
                    contact.get("phone", ""),
                    contact.get("email", ""),
                    contact.get("address", ""),
                    contact.get("notes", ""),
                    contact.get("created_at", "")
                ])
    
    async def _generate_zip_export(self, data: Dict[str, Any], file_path: str):
        """Generate ZIP export file."""
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add JSON data
            json_data = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            zip_file.writestr("data.json", json_data)
            
            # Add documents if available
            if "documents" in data:
                documents_dir = "documents/"
                for doc in data["documents"]:
                    # In a real implementation, this would download actual files
                    # For now, just add metadata
                    doc_metadata = json.dumps(doc, indent=2)
                    zip_file.writestr(f"{documents_dir}{doc.get('id', 'unknown')}.json", doc_metadata)
    
    async def _generate_pdf_export(self, data: Dict[str, Any], file_path: str):
        """Generate PDF export file."""
        # This would require a PDF library like ReportLab
        # For now, create a simple text-based PDF
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph(f"Data Export - {data.get('export_type', 'Unknown')}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Content
            if "documents" in data:
                story.append(Paragraph("Documents", styles['Heading2']))
                for doc in data["documents"][:10]:  # Limit to first 10
                    doc_text = f"{doc.get('filename', 'Unknown')} - {doc.get('document_type', 'Unknown')}"
                    story.append(Paragraph(doc_text, styles['Normal']))
                    story.append(Spacer(1, 6))
            
            doc.build(story)
            
        except ImportError:
            # Fallback to text file if reportlab not available
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Data Export - {data.get('export_type', 'Unknown')}\n\n")
                f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    
    def get_export_request(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Get export request details."""
        if export_id not in self.active_exports:
            return None
        
        return self.active_exports[export_id].to_dict()
    
    def get_user_exports(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all export requests for a user."""
        user_exports = []
        
        for export_request in self.active_exports.values():
            if export_request.user_id == user_id:
                user_exports.append(export_request.to_dict())
        
        # Sort by creation time (newest first)
        user_exports.sort(key=lambda x: x["created_at"], reverse=True)
        return user_exports
    
    def cleanup_expired_exports(self):
        """Clean up expired export files."""
        current_time = datetime.now(timezone.utc)
        expired_exports = []
        
        for export_id, request in self.active_exports.items():
            if (request.expires_at and current_time > request.expires_at and
                request.file_path and os.path.exists(request.file_path)):
                expired_exports.append(export_id)
                
                # Remove file
                try:
                    os.remove(request.file_path)
                    logger.info(f"Removed expired export file {export_id}")
                except Exception as e:
                    logger.error(f"Failed to remove expired export file {export_id}: {e}")
        
        # Remove expired requests from active list
        for export_id in expired_exports:
            del self.active_exports[export_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get export/import statistics."""
        return {
            "active_exports": len(self.active_exports),
            "active_imports": len(self.active_imports),
            "total_exports": self.stats["total_exports"],
            "completed_exports": self.stats["completed_exports"],
            "total_imports": self.stats["total_imports"],
            "completed_imports": self.stats["completed_imports"],
            "exported_documents": self.stats["exported_documents"],
            "imported_documents": self.stats["imported_documents"]
        }

# Global export/import manager instance
_export_import_manager: Optional[DataExportImportManager] = None

def get_export_import_manager() -> DataExportImportManager:
    """Get the global export/import manager instance."""
    global _export_import_manager
    
    if _export_import_manager is None:
        _export_import_manager = DataExportImportManager()
    
    return _export_import_manager

# Helper functions
def create_export_request(user_id: str, export_type: str, format: str, 
                        filters: Dict[str, Any] = None) -> str:
    """Create a new export request."""
    manager = get_export_import_manager()
    
    export_type_enum = ExportType(export_type)
    format_enum = ExportFormat(format)
    
    return manager.create_export_request(user_id, export_type_enum, format_enum, filters)

async def process_export_request(export_id: str) -> bool:
    """Process an export request."""
    manager = get_export_import_manager()
    return await manager.process_export_request(export_id)

def get_export_request(export_id: str) -> Optional[Dict[str, Any]]:
    """Get export request details."""
    manager = get_export_import_manager()
    return manager.get_export_request(export_id)

def get_user_exports(user_id: str) -> List[Dict[str, Any]]:
    """Get all export requests for a user."""
    manager = get_export_import_manager()
    return manager.get_user_exports(user_id)

def cleanup_expired_exports():
    """Clean up expired export files."""
    manager = get_export_import_manager()
    manager.cleanup_expired_exports()

def get_export_statistics() -> Dict[str, Any]:
    """Get export/import statistics."""
    manager = get_export_import_manager()
    return manager.get_statistics()

# Background cleanup task
async def start_export_cleanup_task():
    """Start background task for cleaning up expired exports."""
    while True:
        try:
            cleanup_expired_exports()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Export cleanup task error: {e}")
            await asyncio.sleep(300)  # Retry after 5 minutes
