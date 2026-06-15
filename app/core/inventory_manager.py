"""
Semptify Inventory Manager
Version: 1.0.0
Purpose: Manage file inventory with rotation, dating, and color-coded security
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class InventoryType(str, Enum):
    """Types of inventory items."""
    BACKUP = "backup"
    ARCHIVE = "archive"
    SNAPSHOT = "snapshot"
    MIGRATION = "migration"
    EXPORT = "export"
    SYSTEM_STATE = "system_state"


class RotationPolicy(str, Enum):
    """Rotation policies for inventory items."""
    KEEP_2 = "keep_2"  # Keep only 2 most recent
    KEEP_5 = "keep_5"  # Keep 5 most recent
    KEEP_10 = "keep_10"  # Keep 10 most recent
    KEEP_WEEKLY = "keep_weekly"  # Keep one per week
    KEEP_MONTHLY = "keep_monthly"  # Keep one per month
    KEEP_ALL = "keep_all"  # Don't delete any


@dataclass
class InventoryItem:
    """Single inventory item."""
    item_id: str
    inventory_type: InventoryType
    file_path: str
    created_at: datetime
    file_size: int
    checksum: str
    metadata: Dict[str, Any]
    color_code: Optional[str] = None
    rotation_policy: RotationPolicy = RotationPolicy.KEEP_2
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class InventoryManager:
    """Manages file inventory with rotation and security features."""
    
    def __init__(self, inventory_dir: str = "inventory"):
        self.inventory_dir = Path(inventory_dir)
        self.inventory_dir.mkdir(exist_ok=True)
        self.items: Dict[str, InventoryItem] = {}
        self._load_inventory()
    
    def _load_inventory(self):
        """Load inventory from disk."""
        inventory_file = self.inventory_dir / "inventory.json"
        if inventory_file.exists():
            try:
                with open(inventory_file, 'r') as f:
                    data = json.load(f)
                
                for item_data in data.get('items', []):
                    item = InventoryItem(
                        item_id=item_data['item_id'],
                        inventory_type=InventoryType(item_data['inventory_type']),
                        file_path=item_data['file_path'],
                        created_at=datetime.fromisoformat(item_data['created_at']),
                        file_size=item_data['file_size'],
                        checksum=item_data['checksum'],
                        metadata=item_data['metadata'],
                        color_code=item_data.get('color_code'),
                        rotation_policy=RotationPolicy(item_data.get('rotation_policy', 'keep_2')),
                        tags=item_data.get('tags', [])
                    )
                    self.items[item.item_id] = item
                
                logger.info(f"Loaded {len(self.items)} inventory items")
            except Exception as e:
                logger.error(f"Failed to load inventory: {str(e)}")
    
    def _save_inventory(self):
        """Save inventory to disk."""
        inventory_file = self.inventory_dir / "inventory.json"
        
        data = {
            'items': [],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        for item in self.items.values():
            item_data = {
                'item_id': item.item_id,
                'inventory_type': item.inventory_type.value,
                'file_path': item.file_path,
                'created_at': item.created_at.isoformat(),
                'file_size': item.file_size,
                'checksum': item.checksum,
                'metadata': item.metadata,
                'color_code': item.color_code,
                'rotation_policy': item.rotation_policy.value,
                'tags': item.tags
            }
            data['items'].append(item_data)
        
        with open(inventory_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(self.items)} inventory items")
    
    def _generate_color_code(self, file_path: str, checksum: str) -> str:
        """Generate color code based on file characteristics."""
        # Create a hash from file path and checksum
        hash_input = f"{file_path}:{checksum}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        
        # Convert to RGB values (using first 3 bytes)
        r = hash_bytes[0]
        g = hash_bytes[1]
        b = hash_bytes[2]
        
        # Convert to hex color code
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _format_filename_with_date(self, base_name: str, extension: str = "") -> str:
        """Format filename with readable date."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        
        if extension:
            return f"{base_name}_{date_str}.{extension}"
        return f"{base_name}_{date_str}"
    
    def add_inventory_item(self, 
                          inventory_type: InventoryType,
                          source_file: str,
                          metadata: Optional[Dict[str, Any]] = None,
                          rotation_policy: RotationPolicy = RotationPolicy.KEEP_2,
                          tags: Optional[List[str]] = None) -> str:
        """Add a new item to inventory."""
        try:
            source_path = Path(source_file)
            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
            
            # Calculate checksum
            with open(source_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Generate inventory filename with date
            base_name = source_path.stem
            extension = source_path.suffix.lstrip('.')
            inventory_filename = self._format_filename_with_date(base_name, extension)
            inventory_path = self.inventory_dir / inventory_type.value / inventory_filename
            
            # Create subdirectory if needed
            inventory_path.parent.mkdir(exist_ok=True)
            
            # Copy file to inventory
            import shutil
            shutil.copy2(source_file, inventory_path)
            
            # Generate color code
            color_code = self._generate_color_code(str(inventory_path), checksum)
            
            # Create inventory item
            item = InventoryItem(
                item_id=f"{inventory_type.value}_{int(datetime.now().timestamp())}",
                inventory_type=inventory_type,
                file_path=str(inventory_path),
                created_at=datetime.now(timezone.utc),
                file_size=source_path.stat().st_size,
                checksum=checksum,
                metadata=metadata or {},
                color_code=color_code,
                rotation_policy=rotation_policy,
                tags=tags or []
            )
            
            self.items[item.item_id] = item
            self._save_inventory()
            
            # Apply rotation policy
            self._apply_rotation_policy(inventory_type)
            
            logger.info(f"Added inventory item: {item.item_id}")
            return item.item_id
            
        except Exception as e:
            logger.error(f"Failed to add inventory item: {str(e)}")
            raise
    
    def _apply_rotation_policy(self, inventory_type: InventoryType):
        """Apply rotation policy to keep only specified number of items."""
        # Get items of this type, sorted by creation date (newest first)
        items_of_type = [
            item for item in self.items.values() 
            if item.inventory_type == inventory_type
        ]
        items_of_type.sort(key=lambda x: x.created_at, reverse=True)
        
        policy = items_of_type[0].rotation_policy if items_of_type else RotationPolicy.KEEP_2
        
        if policy == RotationPolicy.KEEP_2:
            keep_count = 2
        elif policy == RotationPolicy.KEEP_5:
            keep_count = 5
        elif policy == RotationPolicy.KEEP_10:
            keep_count = 10
        elif policy == RotationPolicy.KEEP_WEEKLY:
            # Keep one per week
            keep_count = self._calculate_weekly_keep_count(items_of_type)
        elif policy == RotationPolicy.KEEP_MONTHLY:
            # Keep one per month
            keep_count = self._calculate_monthly_keep_count(items_of_type)
        else:
            keep_count = len(items_of_type)  # Keep all
        
        # Delete excess items (oldest first)
        if len(items_of_type) > keep_count:
            items_to_delete = items_of_type[keep_count:]
            for item in items_to_delete:
                self._delete_item(item.item_id)
    
    def _calculate_weekly_keep_count(self, items: List[InventoryItem]) -> int:
        """Calculate how many items to keep for weekly policy."""
        if not items:
            return 0
        
        # Group by week
        weeks = {}
        for item in items:
            week_key = item.created_at.strftime("%Y-%W")
            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(item)
        
        # Keep one per week
        return len(weeks)
    
    def _calculate_monthly_keep_count(self, items: List[InventoryItem]) -> int:
        """Calculate how many items to keep for monthly policy."""
        if not items:
            return 0
        
        # Group by month
        months = {}
        for item in items:
            month_key = item.created_at.strftime("%Y-%m")
            if month_key not in months:
                months[month_key] = []
            months[month_key].append(item)
        
        # Keep one per month
        return len(months)
    
    def _delete_item(self, item_id: str):
        """Delete an inventory item."""
        item = self.items.get(item_id)
        if not item:
            return
        
        try:
            # Delete the file
            file_path = Path(item.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Remove from inventory
            del self.items[item_id]
            self._save_inventory()
            
            logger.info(f"Deleted inventory item: {item_id}")
        except Exception as e:
            logger.error(f"Failed to delete inventory item {item_id}: {str(e)}")
    
    def get_inventory_items(self, 
                           inventory_type: Optional[InventoryType] = None,
                           tags: Optional[List[str]] = None) -> List[InventoryItem]:
        """Get inventory items with optional filters."""
        items = list(self.items.values())
        
        if inventory_type:
            items = [item for item in items if item.inventory_type == inventory_type]
        
        if tags:
            items = [item for item in items if any(tag in item.tags for tag in tags)]
        
        # Sort by creation date (newest first)
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items
    
    def get_item_by_id(self, item_id: str) -> Optional[InventoryItem]:
        """Get inventory item by ID."""
        return self.items.get(item_id)
    
    def rotate_inventory(self, inventory_type: Optional[InventoryType] = None):
        """Manually trigger rotation for inventory type."""
        if inventory_type:
            self._apply_rotation_policy(inventory_type)
        else:
            # Apply to all types
            for inv_type in InventoryType:
                self._apply_rotation_policy(inv_type)
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get summary of inventory status."""
        summary = {
            'total_items': len(self.items),
            'by_type': {},
            'by_policy': {},
            'total_size': 0,
            'oldest_item': None,
            'newest_item': None
        }
        
        for item in self.items.values():
            # Count by type
            type_name = item.inventory_type.value
            if type_name not in summary['by_type']:
                summary['by_type'][type_name] = 0
            summary['by_type'][type_name] += 1
            
            # Count by policy
            policy_name = item.rotation_policy.value
            if policy_name not in summary['by_policy']:
                summary['by_policy'][policy_name] = 0
            summary['by_policy'][policy_name] += 1
            
            # Total size
            summary['total_size'] += item.file_size
            
            # Oldest/newest
            if not summary['oldest_item'] or item.created_at < summary['oldest_item'].created_at:
                summary['oldest_item'] = item
            if not summary['newest_item'] or item.created_at > summary['newest_item'].created_at:
                summary['newest_item'] = item
        
        return summary
    
    def create_backup(self, source_path: str, tags: Optional[List[str]] = None) -> str:
        """Create a backup with rotation (keep only 2 most recent)."""
        return self.add_inventory_item(
            inventory_type=InventoryType.BACKUP,
            source_file=source_path,
            metadata={"backup_type": "manual", "source": source_path},
            rotation_policy=RotationPolicy.KEEP_2,
            tags=tags or ["backup"]
        )
    
    def create_snapshot(self, source_path: str, tags: Optional[List[str]] = None) -> str:
        """Create a snapshot with rotation (keep 5 most recent)."""
        return self.add_inventory_item(
            inventory_type=InventoryType.SNAPSHOT,
            source_file=source_path,
            metadata={"snapshot_type": "manual", "source": source_path},
            rotation_policy=RotationPolicy.KEEP_5,
            tags=tags or ["snapshot"]
        )


# Global instance
inventory_manager = InventoryManager()
