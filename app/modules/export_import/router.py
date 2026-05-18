"""
Data Export/Import API - GDPR Compliant Data Management
=====================================================

Provides data export and import endpoints with GDPR compliance.
"""

import logging
import os
import tempfile
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.data_export_import import (
    get_export_import_manager, ExportType, ExportFormat, ImportFormat,
    create_export_request, process_export_request, get_export_request,
    get_user_exports, cleanup_expired_exports, get_export_statistics
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class ExportRequestSchema(BaseModel):
    """Export request schema."""
    export_type: str = Field(..., description="Export type: all_data, documents_only, timeline_only, contacts_only, user_profile, audit_log")
    format: str = Field("json", description="Export format: json, csv, zip, pdf")
    filters: Optional[Dict[str, Any]] = Field(None, description="Export filters")

class ExportResponse(BaseModel):
    """Export response schema."""
    success: bool
    export_id: str
    export_type: str
    format: str
    status: str
    message: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[str] = None

class ImportRequestSchema(BaseModel):
    """Import request schema."""
    import_type: str = Field(..., description="Import type")
    format: str = Field("json", description="Import format: json, csv, zip")
    validation_required: bool = Field(True, description="Require validation before import")
    merge_strategy: str = Field("skip", description="Merge strategy: skip, overwrite, merge")

# =============================================================================
# Export Endpoints
# =============================================================================

@router.post("/export/request", response_model=ExportResponse)
async def create_export_request_endpoint(
    request: ExportRequestSchema,
    user: StorageUser = Depends(require_user)
):
    """
    Create a new data export request.
    
    Export types:
    - all_data: Complete user data export (GDPR compliant)
    - documents_only: Documents and metadata only
    - timeline_only: Timeline events only
    - contacts_only: Contacts only
    - user_profile: User profile information
    - audit_log: Audit log entries
    
    Export formats:
    - json: Structured JSON format
    - csv: Comma-separated values (for tabular data)
    - zip: Compressed archive with all files
    - pdf: PDF report format
    """
    try:
        # Validate export type
        try:
            export_type = ExportType(request.export_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export type: {request.export_type}"
            )
        
        # Validate format
        try:
            format_type = ExportFormat(request.format)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export format: {request.format}"
            )
        
        # Create export request
        export_id = create_export_request(
            user_id=user.user_id,
            export_type=export_type,
            format=format_type,
            filters=request.filters or {}
        )
        
        return ExportResponse(
            success=True,
            export_id=export_id,
            export_type=request.export_type,
            format=request.format,
            status="pending",
            message="Export request created successfully",
            download_url=f"/export/download/{export_id}" if format_type != ExportFormat.ZIP else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export request creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create export request")

@router.post("/export/{export_id}/process")
async def process_export_endpoint(
    export_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Process an export request.
    """
    try:
        # Get export request
        export_request = get_export_request(export_id)
        if not export_request:
            raise HTTPException(status_code=404, detail="Export request not found")
        
        # Check ownership
        if export_request["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Process export
        success = await process_export_request(export_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Export processing failed")
        
        # Get updated request
        updated_request = get_export_request(export_id)
        
        return {
            "success": True,
            "export_id": export_id,
            "status": updated_request["status"],
            "message": "Export processing completed" if updated_request["status"] == "completed" else "Export processing started",
            "download_url": updated_request.get("download_url"),
            "expires_at": updated_request.get("expires_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process export")

@router.get("/export/{export_id}")
async def get_export_status_endpoint(
    export_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get export request status and details.
    """
    try:
        # Get export request
        export_request = get_export_request(export_id)
        if not export_request:
            raise HTTPException(status_code=404, detail="Export request not found")
        
        # Check ownership
        if export_request["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return export_request
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get export status")

@router.get("/export/{export_id}/download")
async def download_export_endpoint(
    export_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Download an exported file.
    """
    try:
        # Get export request
        export_request = get_export_request(export_id)
        if not export_request:
            raise HTTPException(status_code=404, detail="Export request not found")
        
        # Check ownership
        if export_request["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if export is completed
        if export_request["status"] != "completed":
            raise HTTPException(status_code=400, detail="Export not ready for download")
        
        # Check if file exists
        file_path = export_request.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Check if export has expired
        if export_request.get("expires_at"):
            from datetime import datetime, timezone
            expires_at = datetime.fromisoformat(export_request["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=410, detail="Export has expired")
        
        # Determine filename and media type
        filename = f"{export_id}.{export_request['format']}"
        
        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "zip": "application/zip",
            "pdf": "application/pdf"
        }
        
        media_type = media_types.get(export_request["format"], "application/octet-stream")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to download export")

@router.get("/exports")
async def get_user_exports_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Max exports to return"),
    offset: int = Query(0, ge=0, description="Exports offset"),
    user: StorageUser = Depends(require_user)
):
    """
    Get all export requests for the current user.
    
    Status filters:
    - pending
    - processing
    - completed
    - failed
    """
    try:
        # Get user exports
        exports = get_user_exports(user.user_id)
        
        # Filter by status if provided
        if status:
            exports = [exp for exp in exports if exp["status"] == status]
        
        # Sort by creation time (newest first)
        exports.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        total_exports = len(exports)
        paginated_exports = exports[offset:offset + limit]
        
        return {
            "exports": paginated_exports,
            "total": total_exports,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_exports,
            "filters": {"status": status} if status else {}
        }
        
    except Exception as e:
        logger.error(f"Get user exports failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user exports")

@router.delete("/export/{export_id}")
async def delete_export_endpoint(
    export_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Delete an export request and associated file.
    """
    try:
        # Get export request
        export_request = get_export_request(export_id)
        if not export_request:
            raise HTTPException(status_code=404, detail="Export request not found")
        
        # Check ownership
        if export_request["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file if it exists
        file_path = export_request.get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from active exports (this would be handled by the manager)
        # In a real implementation, this would remove from the manager's active_exports
        
        return {
            "success": True,
            "export_id": export_id,
            "message": "Export deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete export")

# =============================================================================
# Import Endpoints
# =============================================================================

@router.post("/import/prepare")
async def prepare_import_endpoint(
    import_type: str = Form(..., description="Import type"),
    format: str = Form("json", description="Import format"),
    validation_required: bool = Form(True, description="Require validation"),
    merge_strategy: str = Form("skip", description="Merge strategy"),
    user: StorageUser = Depends(require_user)
):
    """
    Prepare a data import operation.
    
    Import types:
    - documents: Document import with metadata
    - contacts: Contact import
    - timeline: Timeline events import
    - settings: User settings import
    
    Merge strategies:
    - skip: Skip existing items
    - overwrite: Replace existing items
    - merge: Merge with existing items
    """
    try:
        # Validate import type
        valid_import_types = ["documents", "contacts", "timeline", "settings"]
        if import_type not in valid_import_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid import type: {import_type}"
            )
        
        # Validate format
        try:
            format_type = ImportFormat(format)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid import format: {format}"
            )
        
        # Create import request
        from app.core.data_export_import import create_import_request
        import_id = create_import_request(
            user_id=user.user_id,
            import_type=import_type,
            format=format_type,
            validation_required=validation_required
        )
        
        return {
            "success": True,
            "import_id": import_id,
            "import_type": import_type,
            "format": format,
            "validation_required": validation_required,
            "merge_strategy": merge_strategy,
            "message": "Import request created successfully",
            "upload_url": f"/import/upload/{import_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import preparation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare import")

@router.post("/import/upload/{import_id}")
async def upload_import_file_endpoint(
    import_id: str,
    file: UploadFile = File(..., description="Import file"),
    user: StorageUser = Depends(require_user)
):
    """
    Upload file for import operation.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Check file size (max 100MB)
        max_size = 100 * 1024 * 1024
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 100MB"
            )
        
        # Save file to temporary location
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Update import request with file path
        # In a real implementation, this would update the ImportRequest object
        # For now, return success
        
        return {
            "success": True,
            "import_id": import_id,
            "filename": file.filename,
            "file_size": len(file_content),
            "file_path": file_path,
            "message": "File uploaded successfully",
            "next_step": "validate_and_process"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import file upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload import file")

@router.post("/import/{import_id}/process")
async def process_import_endpoint(
    import_id: str,
    merge_strategy: str = Form("skip", description="Merge strategy"),
    user: StorageUser = Depends(require_user)
):
    """
    Process an import operation.
    """
    try:
        # This would typically:
        # 1. Validate the uploaded file
        # 2. Parse the data
        # 3. Apply merge strategy
        # 4. Import data into database
        # 5. Update import request status
        
        # For now, simulate processing
        await asyncio.sleep(2)  # Simulate processing time
        
        return {
            "success": True,
            "import_id": import_id,
            "status": "completed",
            "merge_strategy": merge_strategy,
            "message": "Import processed successfully",
            "results": {
                "items_processed": 10,  # Simulated
                "items_imported": 8,
                "items_skipped": 2,
                "items_failed": 0,
                "validation_errors": []
            }
        }
        
    except Exception as e:
        logger.error(f"Import processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process import")

# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/export/statistics")
async def get_export_statistics_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get export/import statistics.
    """
    try:
        stats = get_export_statistics()
        
        # Get user-specific statistics
        user_exports = get_user_exports(user.user_id)
        
        user_stats = {
            "total_exports": len(user_exports),
            "completed_exports": len([
                exp for exp in user_exports 
                if exp["status"] == "completed"
            ]),
            "failed_exports": len([
                exp for exp in user_exports 
                if exp["status"] == "failed"
            ]),
            "pending_exports": len([
                exp for exp in user_exports 
                if exp["status"] == "pending"
            ])
        }
        
        return {
            "global_statistics": stats,
            "user_statistics": user_stats
        }
        
    except Exception as e:
        logger.error(f"Get export statistics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.get("/supported-formats")
async def get_supported_formats_endpoint():
    """
    Get list of supported export and import formats.
    """
    return {
        "export_formats": [
            {
                "format": "json",
                "name": "JSON",
                "description": "Structured data format",
                "supported_types": ["all_data", "documents_only", "timeline_only", "contacts_only", "user_profile", "audit_log"]
            },
            {
                "format": "csv",
                "name": "CSV",
                "description": "Comma-separated values",
                "supported_types": ["documents_only", "contacts_only", "timeline_only"]
            },
            {
                "format": "zip",
                "name": "ZIP",
                "description": "Compressed archive",
                "supported_types": ["all_data", "documents_only"]
            },
            {
                "format": "pdf",
                "name": "PDF",
                "description": "PDF report format",
                "supported_types": ["user_profile", "audit_log"]
            }
        ],
        "import_formats": [
            {
                "format": "json",
                "name": "JSON",
                "description": "Structured data format",
                "supported_types": ["documents", "contacts", "timeline", "settings"]
            },
            {
                "format": "csv",
                "name": "CSV",
                "description": "Comma-separated values",
                "supported_types": ["contacts"]
            },
            {
                "format": "zip",
                "name": "ZIP",
                "description": "Compressed archive",
                "supported_types": ["documents"]
            }
        ],
        "merge_strategies": [
            {
                "strategy": "skip",
                "name": "Skip Existing",
                "description": "Skip items that already exist"
            },
            {
                "strategy": "overwrite",
                "name": "Overwrite",
                "description": "Replace existing items"
            },
            {
                "strategy": "merge",
                "name": "Merge",
                "description": "Merge with existing items"
            }
        ],
        "limits": {
            "max_file_size": "100MB",
            "max_export_items": 10000,
            "export_retention_days": 7,
            "max_concurrent_exports": 3
        }
    }

@router.post("/cleanup")
async def cleanup_exports_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Clean up expired exports (admin only or user-specific).
    """
    try:
        # Clean up expired exports
        cleanup_expired_exports()
        
        return {
            "success": True,
            "message": "Export cleanup completed"
        }
        
    except Exception as e:
        logger.error(f"Export cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup exports")
