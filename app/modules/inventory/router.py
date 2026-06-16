"""
Inventory Management Router
Version: 1.0.0
Purpose: API endpoints for file inventory with rotation and dating
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from app.core.utc import utc_now
from app.core.inventory_manager import (
    inventory_manager,
    InventoryType,
    RotationPolicy
)
from app.core.accountability_planner import accountability_planner, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/backup")
async def create_backup(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Create a backup with automatic rotation (keeps only 2 most recent)."""
    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Parse tags
        tag_list = tags.split(",") if tags else ["backup"]
        if description:
            tag_list.append(f"desc:{description}")
        
        # Create backup
        item_id = inventory_manager.create_backup(
            source_path=tmp_path,
            tags=tag_list
        )
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        # Log the backup
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource=f"inventory:backup:{item_id}",
            details={
                "filename": file.filename,
                "size": len(content),
                "tags": tag_list
            },
            success=True
        )
        
        return {
            "message": "Backup created successfully",
            "item_id": item_id,
            "filename": file.filename,
            "size": len(content),
            "rotation_policy": "keep_2",
            "timestamp": utc_now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create backup")


@router.post("/snapshot")
async def create_snapshot(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Create a snapshot with rotation (keeps 5 most recent)."""
    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Parse tags
        tag_list = tags.split(",") if tags else ["snapshot"]
        if description:
            tag_list.append(f"desc:{description}")
        
        # Create snapshot
        item_id = inventory_manager.create_snapshot(
            source_path=tmp_path,
            tags=tag_list
        )
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        # Log the snapshot
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource=f"inventory:snapshot:{item_id}",
            details={
                "filename": file.filename,
                "size": len(content),
                "tags": tag_list
            },
            success=True
        )
        
        return {
            "message": "Snapshot created successfully",
            "item_id": item_id,
            "filename": file.filename,
            "size": len(content),
            "rotation_policy": "keep_5",
            "timestamp": utc_now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create snapshot")


@router.get("/items")
async def get_inventory_items(
    inventory_type: Optional[str] = None,
    tags: Optional[str] = None
):
    """Get inventory items with optional filters."""
    try:
        inv_type = InventoryType(inventory_type) if inventory_type else None
        tag_list = tags.split(",") if tags else None
        
        items = inventory_manager.get_inventory_items(
            inventory_type=inv_type,
            tags=tag_list
        )
        
        return {
            "items": [
                {
                    "item_id": item.item_id,
                    "inventory_type": item.inventory_type.value,
                    "file_path": item.file_path,
                    "created_at": item.created_at.isoformat(),
                    "file_size": item.file_size,
                    "checksum": item.checksum,
                    "color_code": item.color_code,
                    "rotation_policy": item.rotation_policy.value,
                    "tags": item.tags,
                    "metadata": item.metadata
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"Error getting inventory items: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get inventory items")


@router.get("/items/{item_id}")
async def get_inventory_item(item_id: str):
    """Get specific inventory item."""
    try:
        item = inventory_manager.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {
            "item_id": item.item_id,
            "inventory_type": item.inventory_type.value,
            "file_path": item.file_path,
            "created_at": item.created_at.isoformat(),
            "file_size": item.file_size,
            "checksum": item.checksum,
            "color_code": item.color_code,
            "rotation_policy": item.rotation_policy.value,
            "tags": item.tags,
            "metadata": item.metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inventory item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get inventory item")


@router.get("/summary")
async def get_inventory_summary():
    """Get inventory summary."""
    try:
        summary = inventory_manager.get_inventory_summary()
        
        # Format dates for JSON
        if summary['oldest_item']:
            summary['oldest_item'] = {
                'item_id': summary['oldest_item'].item_id,
                'created_at': summary['oldest_item'].created_at.isoformat(),
                'file_size': summary['oldest_item'].file_size
            }
        
        if summary['newest_item']:
            summary['newest_item'] = {
                'item_id': summary['newest_item'].item_id,
                'created_at': summary['newest_item'].created_at.isoformat(),
                'file_size': summary['newest_item'].file_size
            }
        
        return summary
    except Exception as e:
        logger.error(f"Error getting inventory summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get inventory summary")


@router.post("/rotate")
async def rotate_inventory(inventory_type: Optional[str] = None):
    """Manually trigger inventory rotation."""
    try:
        inv_type = InventoryType(inventory_type) if inventory_type else None
        
        inventory_manager.rotate_inventory(inv_type)
        
        # Log the rotation
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource=f"inventory:rotate:{inventory_type or 'all'}",
            details={"manual_rotation": True},
            success=True
        )
        
        return {
            "message": f"Rotation triggered for {inventory_type or 'all types'}",
            "timestamp": utc_now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error rotating inventory: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to rotate inventory")


@router.delete("/items/{item_id}")
async def delete_inventory_item(item_id: str):
    """Delete an inventory item."""
    try:
        item = inventory_manager.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        inventory_manager._delete_item(item_id)
        
        # Log the deletion
        accountability_planner.log_audit_event(
            user_id=None,
            action=AuditAction.SYSTEM_CHANGE,
            resource=f"inventory:delete:{item_id}",
            details={"file_path": item.file_path},
            success=True
        )
        
        return {"message": f"Item {item_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting inventory item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete inventory item")


@router.get("/health")
async def inventory_health():
    """Health check for inventory system."""
    try:
        summary = inventory_manager.get_inventory_summary()
        
        # Determine health status
        total_items = summary['total_items']
        
        if total_items == 0:
            health_status = "healthy"  # No items is OK
        elif total_items > 1000:
            health_status = "warning"  # Too many items
        else:
            health_status = "healthy"
        
        return {
            "status": health_status,
            "timestamp": utc_now().isoformat(),
            "metrics": {
                "total_items": total_items,
                "total_size_mb": round(summary['total_size'] / (1024 * 1024), 2),
                "types": len(summary['by_type']),
                "oldest_item_days": (
                    (utc_now() - summary['oldest_item'].created_at).days
                    if summary['oldest_item'] else 0
                )
            }
        }
    except Exception as e:
        logger.error(f"Error in inventory health check: {str(e)}")
        return {
            "status": "error",
            "timestamp": utc_now().isoformat(),
            "error": str(e)
        }
