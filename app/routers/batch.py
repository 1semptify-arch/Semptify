"""
Batch Operations API - Bulk Document Management
============================================

Provides batch operations for document management with progress tracking.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.batch_operations import (
    get_batch_processor, BatchOperationType, BatchOperationStatus,
    create_batch_operation, start_batch_operation, cancel_batch_operation,
    get_batch_operation, get_user_batch_operations, get_batch_statistics
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class BatchRequest(BaseModel):
    """Batch operation request."""
    operation_type: str = Field(..., description="Operation type: upload, delete, export, import, move, copy, tag, analyze, preview")
    items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    settings: Optional[Dict[str, Any]] = Field(None, description="Operation settings")

class BatchResponse(BaseModel):
    """Batch operation response."""
    success: bool
    operation_id: str
    operation_type: str
    status: str
    total_items: int
    message: Optional[str] = None

class BatchItemRequest(BaseModel):
    """Single batch item."""
    type: str = Field(..., description="Item type")
    data: Dict[str, Any] = Field(..., description="Item data")

# =============================================================================
# Batch Operations Endpoints
# =============================================================================

@router.post("/create", response_model=BatchResponse)
async def create_batch_operation_endpoint(
    request: BatchRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Create a new batch operation.
    
    Supported operations:
    - upload: Bulk document upload
    - delete: Bulk document deletion
    - export: Bulk document export
    - import: Bulk document import
    - move: Bulk document move
    - copy: Bulk document copy
    - tag: Bulk document tagging
    - analyze: Bulk document analysis
    - preview: Bulk preview generation
    """
    try:
        # Validate operation type
        try:
            operation_type = BatchOperationType(request.operation_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation type: {request.operation_type}"
            )
        
        # Validate items
        if not request.items:
            raise HTTPException(status_code=400, detail="At least one item is required")
        
        if len(request.items) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 1000 items per batch operation"
            )
        
        # Create batch operation
        operation_id = create_batch_operation(
            operation_type=request.operation_type,
            user_id=user.user_id,
            items=request.items,
            settings=request.settings or {}
        )
        
        return BatchResponse(
            success=True,
            operation_id=operation_id,
            operation_type=request.operation_type,
            status="pending",
            total_items=len(request.items),
            message="Batch operation created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch operation creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create batch operation")

@router.post("/{operation_id}/start")
async def start_batch_operation_endpoint(
    operation_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Start processing a batch operation.
    """
    try:
        # Check if operation exists and belongs to user
        operation = get_batch_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Batch operation not found")
        
        if operation["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Start operation
        success = await start_batch_operation(operation_id)
        
        if not success:
            raise HTTPException(status_code=409, detail="Operation cannot be started (max concurrent operations reached)")
        
        return {
            "success": True,
            "operation_id": operation_id,
            "message": "Batch operation started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch operation start failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start batch operation")

@router.post("/{operation_id}/cancel")
async def cancel_batch_operation_endpoint(
    operation_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Cancel a batch operation.
    """
    try:
        # Check if operation exists and belongs to user
        operation = get_batch_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Batch operation not found")
        
        if operation["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cancel operation
        success = cancel_batch_operation(operation_id)
        
        if not success:
            raise HTTPException(status_code=409, detail="Operation cannot be cancelled")
        
        return {
            "success": True,
            "operation_id": operation_id,
            "message": "Batch operation cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch operation cancel failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel batch operation")

@router.get("/{operation_id}")
async def get_batch_operation_endpoint(
    operation_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get details of a batch operation.
    """
    try:
        # Get operation
        operation = get_batch_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Batch operation not found")
        
        # Check ownership
        if operation["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return operation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get batch operation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get batch operation")

@router.get("/")
async def get_user_batch_operations_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max operations to return"),
    offset: int = Query(0, ge=0, description="Operations offset"),
    user: StorageUser = Depends(require_user)
):
    """
    Get all batch operations for the current user.
    
    Status filters:
    - pending
    - running
    - completed
    - failed
    - cancelled
    - paused
    """
    try:
        # Validate status if provided
        status_filter = None
        if status:
            try:
                status_filter = BatchOperationStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )
        
        # Get user operations
        operations = get_user_batch_operations(user.user_id, status_filter)
        
        # Apply pagination
        total_operations = len(operations)
        paginated_operations = operations[offset:offset + limit]
        
        return {
            "operations": paginated_operations,
            "total": total_operations,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_operations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user batch operations failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get batch operations")

@router.get("/statistics")
async def get_batch_statistics_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get batch operations statistics.
    """
    try:
        # Get global statistics
        stats = get_batch_statistics()
        
        # Get user-specific statistics
        user_operations = get_user_batch_operations(user.user_id)
        
        user_stats = {
            "total_operations": len(user_operations),
            "completed_operations": len([
                op for op in user_operations 
                if op["status"] == "completed"
            ]),
            "failed_operations": len([
                op for op in user_operations 
                if op["status"] == "failed"
            ]),
            "running_operations": len([
                op for op in user_operations 
                if op["status"] == "running"
            ]),
            "pending_operations": len([
                op for op in user_operations 
                if op["status"] == "pending"
            ])
        }
        
        return {
            "global_statistics": stats,
            "user_statistics": user_stats
        }
        
    except Exception as e:
        logger.error(f"Get batch statistics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get batch statistics")

# =============================================================================
# Batch Upload Endpoints
# =============================================================================

@router.post("/upload/prepare")
async def prepare_batch_upload(
    files_info: List[BatchItemRequest],
    user: StorageUser = Depends(require_user)
):
    """
    Prepare a batch upload operation.
    
    This endpoint validates files and returns upload URLs/parameters
    for the actual upload process.
    """
    try:
        if len(files_info) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 files per batch upload"
            )
        
        # Validate each file
        validated_files = []
        for file_info in files_info:
            if not file_info.data.get("filename"):
                raise HTTPException(
                    status_code=400,
                    detail="Filename is required for each file"
                )
            
            # Add validation logic here
            validated_files.append({
                "type": file_info.type,
                "data": file_info.data,
                "validated": True
            })
        
        # Create batch upload operation
        operation_id = create_batch_operation(
            operation_type="upload",
            user_id=user.user_id,
            items=validated_files,
            settings={
                "batch_size": 10,
                "delay_between_batches": 0.5,
                "max_file_size": 50 * 1024 * 1024  # 50MB
            }
        )
        
        return {
            "success": True,
            "operation_id": operation_id,
            "files_count": len(validated_files),
            "upload_settings": {
                "max_file_size": "50MB",
                "allowed_types": ["pdf", "doc", "docx", "jpg", "png", "txt"],
                "chunk_size": "8MB"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prepare batch upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare batch upload")

@router.post("/upload/execute/{operation_id}")
async def execute_batch_upload(
    operation_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Execute a prepared batch upload operation.
    """
    try:
        # Check if operation exists and belongs to user
        operation = get_batch_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Batch operation not found")
        
        if operation["user_id"] != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if operation["operation_type"] != "upload":
            raise HTTPException(status_code=400, detail="Operation is not a batch upload")
        
        # Start the batch upload
        success = await start_batch_operation(operation_id)
        
        if not success:
            raise HTTPException(status_code=409, detail="Upload cannot be started")
        
        return {
            "success": True,
            "operation_id": operation_id,
            "message": "Batch upload started",
            "websocket_channel": f"batch_operation_{operation_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute batch upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute batch upload")

# =============================================================================
# Batch Delete Endpoints
# =============================================================================

@router.post("/delete/prepare")
async def prepare_batch_delete(
    document_ids: List[str],
    user: StorageUser = Depends(require_user)
):
    """
    Prepare a batch delete operation.
    """
    try:
        if len(document_ids) > 500:
            raise HTTPException(
                status_code=400,
                detail="Maximum 500 documents per batch delete"
            )
        
        # Create delete items
        delete_items = []
        for doc_id in document_ids:
            delete_items.append({
                "type": "document",
                "data": {
                    "document_id": doc_id,
                    "delete_from_storage": True,
                    "delete_from_database": True
                }
            })
        
        # Create batch delete operation
        operation_id = create_batch_operation(
            operation_type="delete",
            user_id=user.user_id,
            items=delete_items,
            settings={
                "batch_size": 20,
                "delay_between_batches": 0.1,
                "require_confirmation": True
            }
        )
        
        return {
            "success": True,
            "operation_id": operation_id,
            "documents_count": len(document_ids),
            "confirmation_required": True,
            "warning": f"This will permanently delete {len(document_ids)} documents"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prepare batch delete failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare batch delete")

# =============================================================================
# Batch Export Endpoints
# =============================================================================

@router.post("/export/prepare")
async def prepare_batch_export(
    document_ids: List[str],
    export_format: str = Query("zip", description="Export format: zip, pdf, csv"),
    user: StorageUser = Depends(require_user)
):
    """
    Prepare a batch export operation.
    """
    try:
        if len(document_ids) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 1000 documents per batch export"
            )
        
        # Create export items
        export_items = []
        for doc_id in document_ids:
            export_items.append({
                "type": "document",
                "data": {
                    "document_id": doc_id,
                    "include_metadata": True,
                    "include_content": True,
                    "include_previews": export_format == "zip"
                }
            })
        
        # Create batch export operation
        operation_id = create_batch_operation(
            operation_type="export",
            user_id=user.user_id,
            items=export_items,
            settings={
                "format": export_format,
                "batch_size": 50,
                "delay_between_batches": 1.0,
                "compression_level": 6
            }
        )
        
        return {
            "success": True,
            "operation_id": operation_id,
            "documents_count": len(document_ids),
            "export_format": export_format,
            "estimated_size": f"{len(document_ids) * 2}MB"  # Rough estimate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prepare batch export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare batch export")

# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/supported-operations")
async def get_supported_operations():
    """
    Get list of supported batch operations.
    """
    return {
        "operations": [
            {
                "type": "upload",
                "name": "Bulk Upload",
                "description": "Upload multiple documents at once",
                "max_items": 100,
                "settings": ["batch_size", "delay_between_batches", "max_file_size"]
            },
            {
                "type": "delete",
                "name": "Bulk Delete",
                "description": "Delete multiple documents at once",
                "max_items": 500,
                "settings": ["batch_size", "require_confirmation"]
            },
            {
                "type": "export",
                "name": "Bulk Export",
                "description": "Export multiple documents",
                "max_items": 1000,
                "settings": ["format", "compression_level", "include_previews"]
            },
            {
                "type": "move",
                "name": "Bulk Move",
                "description": "Move multiple documents",
                "max_items": 500,
                "settings": ["destination_folder", "preserve_structure"]
            },
            {
                "type": "copy",
                "name": "Bulk Copy",
                "description": "Copy multiple documents",
                "max_items": 500,
                "settings": ["destination_folder", "preserve_metadata"]
            },
            {
                "type": "tag",
                "name": "Bulk Tag",
                "description": "Tag multiple documents",
                "max_items": 1000,
                "settings": ["tags", "replace_existing"]
            },
            {
                "type": "analyze",
                "name": "Bulk Analysis",
                "description": "Analyze multiple documents",
                "max_items": 100,
                "settings": ["analysis_type", "depth"]
            },
            {
                "type": "preview",
                "name": "Bulk Preview Generation",
                "description": "Generate previews for multiple documents",
                "max_items": 200,
                "settings": ["preview_type", "quality", "size"]
            }
        ]
    }
