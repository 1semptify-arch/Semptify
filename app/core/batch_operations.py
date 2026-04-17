"""
Batch Operations Manager - Bulk Document Processing
==============================================

Handles batch operations for document management with progress tracking.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import json
import tempfile
import zipfile
import io
from pathlib import Path

logger = logging.getLogger(__name__)

class BatchOperationType(Enum):
    """Batch operation types."""
    UPLOAD = "upload"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    MOVE = "move"
    COPY = "copy"
    TAG = "tag"
    ANALYZE = "analyze"
    PREVIEW = "preview"

class BatchOperationStatus(Enum):
    """Batch operation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class BatchItem:
    """Single item in batch operation."""
    item_id: str
    item_type: str
    data: Dict[str, Any]
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

@dataclass
class BatchOperation:
    """Batch operation with multiple items."""
    operation_id: str
    operation_type: BatchOperationType
    user_id: str
    items: List[BatchItem]
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.total_items == 0:
            self.total_items = len(self.items)
        if self.settings is None:
            self.settings = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "success_rate": (self.completed_items / self.total_items) if self.total_items > 0 else 0,
            "settings": self.settings,
            "items": [item.to_dict() for item in self.items]
        }

class BatchProcessor:
    """Batch operations processor with progress tracking."""
    
    def __init__(self, max_concurrent_operations: int = 5):
        self.max_concurrent_operations = max_concurrent_operations
        self.operations: Dict[str, BatchOperation] = {}
        self.active_operations: Dict[str, asyncio.Task] = {}
        
        # Operation handlers
        self.handlers: Dict[BatchOperationType, Callable] = {}
        
        # Statistics
        self.stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
            "total_items_processed": 0,
            "average_processing_time": 0.0
        }
        
        # Shutdown flag
        self.shutdown_event = asyncio.Event()
    
    def register_handler(self, operation_type: BatchOperationType, handler: Callable):
        """Register a handler for batch operation type."""
        self.handlers[operation_type] = handler
        logger.info(f"Registered handler for {operation_type.value}")
    
    def create_batch_operation(self, operation_type: BatchOperationType, user_id: str,
                           items: List[Dict[str, Any]], settings: Dict[str, Any] = None) -> str:
        """Create a new batch operation."""
        operation_id = str(uuid.uuid4())
        
        # Create batch items
        batch_items = []
        for i, item_data in enumerate(items):
            batch_item = BatchItem(
                item_id=str(uuid.uuid4()),
                item_type=item_data.get("type", "unknown"),
                data=item_data
            )
            batch_items.append(batch_item)
        
        # Create batch operation
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            user_id=user_id,
            items=batch_items,
            settings=settings or {}
        )
        
        self.operations[operation_id] = operation
        self.stats["total_operations"] += 1
        
        logger.info(f"Created batch operation {operation_id} with {len(items)} items")
        return operation_id
    
    async def start_batch_operation(self, operation_id: str) -> bool:
        """Start processing a batch operation."""
        if operation_id not in self.operations:
            return False
        
        if len(self.active_operations) >= self.max_concurrent_operations:
            logger.warning(f"Max concurrent operations reached, queuing {operation_id}")
            return False
        
        operation = self.operations[operation_id]
        operation.status = BatchOperationStatus.RUNNING
        operation.started_at = datetime.now(timezone.utc)
        
        # Start processing task
        task = asyncio.create_task(self._process_batch_operation(operation))
        self.active_operations[operation_id] = task
        
        logger.info(f"Started batch operation {operation_id}")
        return True
    
    async def _process_batch_operation(self, operation: BatchOperation):
        """Process a batch operation."""
        try:
            # Get handler for operation type
            handler = self.handlers.get(operation.operation_type)
            if not handler:
                raise ValueError(f"No handler for operation type: {operation.operation_type}")
            
            # Process items in batches
            batch_size = operation.settings.get("batch_size", 10)
            delay_between_batches = operation.settings.get("delay_between_batches", 1.0)
            
            total_items = len(operation.items)
            processed_items = 0
            
            for i in range(0, total_items, batch_size):
                if self.shutdown_event.is_set():
                    operation.status = BatchOperationStatus.CANCELLED
                    break
                
                # Get batch of items
                batch_items = operation.items[i:i + batch_size]
                
                # Process batch
                batch_results = await handler(batch_items, operation.settings)
                
                # Update item statuses
                for j, item in enumerate(batch_items):
                    item_index = i + j
                    
                    if item_index < len(batch_results):
                        result = batch_results[j]
                        if result.get("success", False):
                            operation.items[item_index].status = "completed"
                            operation.items[item_index].result = result.get("data")
                            operation.completed_items += 1
                        else:
                            operation.items[item_index].status = "failed"
                            operation.items[item_index].error = result.get("error", "Unknown error")
                            operation.failed_items += 1
                    else:
                        operation.items[item_index].status = "failed"
                        operation.items[item_index].error = "No result returned"
                        operation.failed_items += 1
                    
                    operation.items[item_index].started_at = datetime.now(timezone.utc)
                    operation.items[item_index].completed_at = datetime.now(timezone.utc)
                
                processed_items += len(batch_items)
                
                # Update progress
                operation.progress = (processed_items / total_items) * 100
                
                # Send progress update via WebSocket
                await self._send_progress_update(operation)
                
                # Delay between batches
                if i + batch_size < total_items and delay_between_batches > 0:
                    await asyncio.sleep(delay_between_batches)
            
            # Mark operation as completed
            if operation.status != BatchOperationStatus.CANCELLED:
                operation.status = BatchOperationStatus.COMPLETED
                operation.completed_at = datetime.now(timezone.utc)
                operation.progress = 100.0
                
                self.stats["completed_operations"] += 1
                self.stats["total_items_processed"] += processed_items
                
                # Calculate processing time
                if operation.started_at and operation.completed_at:
                    processing_time = (operation.completed_at - operation.started_at).total_seconds()
                    total_ops = self.stats["completed_operations"]
                    avg_time = self.stats["average_processing_time"]
                    self.stats["average_processing_time"] = (
                        (avg_time * (total_ops - 1) + processing_time) / total_ops
                    )
            
            logger.info(f"Completed batch operation {operation_id}")
            
        except Exception as e:
            operation.status = BatchOperationStatus.FAILED
            operation.completed_at = datetime.now(timezone.utc)
            
            self.stats["failed_operations"] += 1
            
            logger.error(f"Batch operation {operation.operation_id} failed: {e}")
        
        finally:
            # Remove from active operations
            if operation.operation_id in self.active_operations:
                del self.active_operations[operation.operation_id]
            
            # Send final update
            await self._send_progress_update(operation)
    
    async def _send_progress_update(self, operation: BatchOperation):
        """Send progress update via WebSocket."""
        try:
            from app.core.websocket_manager import get_websocket_manager
            
            ws_manager = get_websocket_manager()
            
            update_data = {
                "operation_id": operation.operation_id,
                "status": operation.status.value,
                "progress": operation.progress,
                "completed_items": operation.completed_items,
                "failed_items": operation.failed_items,
                "total_items": operation.total_items,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await ws_manager.send_to_user(
                operation.user_id,
                WebSocketMessage(
                    type="batch_operation_update",
                    data=update_data,
                    timestamp=datetime.now(timezone.utc),
                    user_id=operation.user_id
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")
    
    def cancel_batch_operation(self, operation_id: str) -> bool:
        """Cancel a batch operation."""
        if operation_id not in self.operations:
            return False
        
        operation = self.operations[operation_id]
        
        if operation.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED]:
            return False
        
        operation.status = BatchOperationStatus.CANCELLED
        
        # Cancel active task if running
        if operation_id in self.active_operations:
            task = self.active_operations[operation_id]
            task.cancel()
            del self.active_operations[operation_id]
        
        logger.info(f"Cancelled batch operation {operation_id}")
        return True
    
    def get_batch_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get batch operation details."""
        if operation_id not in self.operations:
            return None
        
        return self.operations[operation_id].to_dict()
    
    def get_user_operations(self, user_id: str, status: Optional[BatchOperationStatus] = None) -> List[Dict[str, Any]]:
        """Get all operations for a user."""
        user_operations = []
        
        for operation in self.operations.values():
            if operation.user_id == user_id:
                if status is None or operation.status == status:
                    user_operations.append(operation.to_dict())
        
        # Sort by creation time (newest first)
        user_operations.sort(key=lambda x: x["created_at"], reverse=True)
        return user_operations
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get batch operations statistics."""
        return {
            "total_operations": self.stats["total_operations"],
            "completed_operations": self.stats["completed_operations"],
            "failed_operations": self.stats["failed_operations"],
            "total_items_processed": self.stats["total_items_processed"],
            "average_processing_time": self.stats["average_processing_time"],
            "active_operations": len(self.active_operations),
            "queued_operations": len([
                op for op in self.operations.values()
                if op.status == BatchOperationStatus.PENDING
            ])
        }
    
    async def cleanup_old_operations(self, days_old: int = 30):
        """Clean up old completed operations."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        operations_to_remove = []
        for operation_id, operation in self.operations.items():
            if (operation.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED] and
                operation.completed_at and operation.completed_at < cutoff_time):
                operations_to_remove.append(operation_id)
        
        for operation_id in operations_to_remove:
            del self.operations[operation_id]
        
        logger.info(f"Cleaned up {len(operations_to_remove)} old operations")

# Default batch operation handlers
async def batch_upload_handler(items: List[BatchItem], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle batch upload operation."""
    results = []
    
    for item in items:
        try:
            # Simulate upload processing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            results.append({
                "success": True,
                "item_id": item.item_id,
                "data": {
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "file_path": f"/uploads/{item.data.get('filename', 'unknown')}"
                }
            })
        except Exception as e:
            results.append({
                "success": False,
                "item_id": item.item_id,
                "error": str(e)
            })
    
    return results

async def batch_delete_handler(items: List[BatchItem], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle batch delete operation."""
    results = []
    
    for item in items:
        try:
            # Simulate delete processing
            await asyncio.sleep(0.05)  # Simulate processing time
            
            results.append({
                "success": True,
                "item_id": item.item_id,
                "data": {
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                    "document_id": item.data.get("document_id")
                }
            })
        except Exception as e:
            results.append({
                "success": False,
                "item_id": item.item_id,
                "error": str(e)
            })
    
    return results

async def batch_export_handler(items: List[BatchItem], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle batch export operation."""
    results = []
    
    try:
        # Create export package
        export_format = settings.get("format", "zip")
        
        if export_format == "zip":
            # Create ZIP file
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for item in items:
                    # Add item to ZIP
                    file_data = item.data.get("content", "")
                    filename = item.data.get("filename", f"document_{item.item_id}")
                    
                    zip_file.writestr(filename, file_data)
            
            zip_buffer.seek(0)
            zip_data = zip_buffer.getvalue()
            
            # Store export data (in real system, would save to storage)
            export_id = str(uuid.uuid4())
            
            for item in items:
                results.append({
                    "success": True,
                    "item_id": item.item_id,
                    "data": {
                        "export_id": export_id,
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                        "format": "zip"
                    }
                })
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    except Exception as e:
        for item in items:
            results.append({
                "success": False,
                "item_id": item.item_id,
                "error": str(e)
            })
    
    return results

# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None

def get_batch_processor() -> BatchProcessor:
    """Get the global batch processor instance."""
    global _batch_processor
    
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
        
        # Register default handlers
        _batch_processor.register_handler(BatchOperationType.UPLOAD, batch_upload_handler)
        _batch_processor.register_handler(BatchOperationType.DELETE, batch_delete_handler)
        _batch_processor.register_handler(BatchOperationType.EXPORT, batch_export_handler)
    
    return _batch_processor

# Helper functions
def create_batch_operation(operation_type: str, user_id: str, items: List[Dict[str, Any]], 
                        settings: Dict[str, Any] = None) -> str:
    """Create a new batch operation."""
    processor = get_batch_processor()
    
    op_type = BatchOperationType(operation_type)
    return processor.create_batch_operation(op_type, user_id, items, settings)

async def start_batch_operation(operation_id: str) -> bool:
    """Start a batch operation."""
    processor = get_batch_processor()
    return await processor.start_batch_operation(operation_id)

def cancel_batch_operation(operation_id: str) -> bool:
    """Cancel a batch operation."""
    processor = get_batch_processor()
    return processor.cancel_batch_operation(operation_id)

def get_batch_operation(operation_id: str) -> Optional[Dict[str, Any]]:
    """Get batch operation details."""
    processor = get_batch_processor()
    return processor.get_batch_operation(operation_id)

def get_user_batch_operations(user_id: str, status: str = None) -> List[Dict[str, Any]]:
    """Get all operations for a user."""
    processor = get_batch_processor()
    
    status_filter = BatchOperationStatus(status) if status else None
    return processor.get_user_operations(user_id, status_filter)

def get_batch_statistics() -> Dict[str, Any]:
    """Get batch operations statistics."""
    processor = get_batch_processor()
    return processor.get_statistics()
