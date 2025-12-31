"""
🔄 User Cloud Sync - Persistent Storage in User's Cloud
========================================================

This service uses the user's connected cloud storage (Google Drive, Dropbox, OneDrive)
as their persistent database. Semptify stores NOTHING - all data lives in user's cloud.

Storage Structure in User's Cloud:
    .semptify/
    ├── profile.json          # User settings, preferences
    ├── case.json             # Current case data
    ├── timeline.json         # Timeline events
    ├── calendar.json         # Calendar/deadlines
    ├── documents/            # Uploaded documents
    │   ├── index.json        # Document metadata
    │   └── [doc files]
    ├── forms/                # Generated forms
    │   └── [pdf files]
    └── sync_state.json       # Sync metadata

Benefits:
- User owns 100% of their data
- Works across browsers/devices automatically
- No Semptify database needed for user data
- GDPR/Privacy compliant by design
- User can backup/export anytime
"""

import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class SyncStatus(str, Enum):
    """Sync status states."""
    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    ERROR = "error"
    CONFLICT = "conflict"


@dataclass
class UserProfile:
    """User profile stored in cloud."""
    user_id: str
    display_name: str = ""
    email: str = ""
    role: str = "tenant"  # tenant, advocate, legal, admin
    created_at: str = ""
    last_sync: str = ""
    
    # Preferences
    theme: str = "dark"
    language: str = "en"
    notifications: bool = True
    auto_sync: bool = True
    sync_interval_minutes: int = 5
    
    # Case context
    current_case_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CaseData:
    """Case data stored in cloud."""
    case_id: str
    case_number: str = ""
    court: str = "Dakota County District Court"
    case_type: str = "eviction"
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    
    # Parties
    tenant_name: str = ""
    tenant_address: str = ""
    landlord_name: str = ""
    landlord_address: str = ""
    property_address: str = ""
    
    # Key dates
    notice_date: Optional[str] = None
    summons_date: Optional[str] = None
    hearing_date: Optional[str] = None
    answer_deadline: Optional[str] = None
    
    # Case details
    rent_amount: float = 0.0
    amount_owed: float = 0.0
    eviction_reason: str = ""
    
    # Defenses identified
    defenses: List[str] = field(default_factory=list)
    
    # Notes
    notes: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CaseData":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass 
class SyncState:
    """Sync state metadata."""
    last_sync: str = ""
    sync_count: int = 0
    version: str = "1.0"
    checksum: str = ""
    device_id: str = ""
    conflicts: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Cloud Sync Service
# =============================================================================

class UserCloudSync:
    """
    Manages user data sync with their cloud storage.
    
    Usage:
        sync = UserCloudSync(storage_client, user_id)
        
        # Load user data from cloud
        profile = await sync.load_profile()
        case = await sync.load_case()
        timeline = await sync.load_timeline()
        
        # Save changes to cloud
        await sync.save_profile(profile)
        await sync.save_case(case)
        
        # Full sync
        await sync.sync_all()
    """
    
    SEMPTIFY_FOLDER = ".semptify"
    
    def __init__(self, storage_client, user_id: str):
        """
        Initialize sync service.
        
        Args:
            storage_client: Storage provider client (GoogleDrive, Dropbox, OneDrive)
            user_id: User's unique ID
        """
        self.storage = storage_client
        self.user_id = user_id
        self.status = SyncStatus.IDLE
        self._cache: Dict[str, Any] = {}
        self._dirty: set = set()  # Files that need syncing
        
    # =========================================================================
    # Folder Management
    # =========================================================================
    
    async def ensure_folder_structure(self) -> bool:
        """Create .semptify folder structure if it doesn't exist."""
        try:
            folders = [
                self.SEMPTIFY_FOLDER,
                f"{self.SEMPTIFY_FOLDER}/documents",
                f"{self.SEMPTIFY_FOLDER}/forms",
                f"{self.SEMPTIFY_FOLDER}/exports",
            ]
            
            for folder in folders:
                await self.storage.create_folder_if_not_exists(folder)
            
            logger.info(f"📁 Folder structure ensured for user {self.user_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create folder structure: {e}")
            return False
    
    # =========================================================================
    # Profile Management
    # =========================================================================
    
    async def load_profile(self) -> Optional[UserProfile]:
        """Load user profile from cloud."""
        try:
            data = await self._read_json("profile.json")
            if data:
                self._cache["profile"] = data
                return UserProfile.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to load profile: {e}")
            return None
    
    async def save_profile(self, profile: UserProfile) -> bool:
        """Save user profile to cloud."""
        try:
            profile.last_sync = datetime.now(timezone.utc).isoformat()
            data = profile.to_dict()
            await self._write_json("profile.json", data)
            self._cache["profile"] = data
            logger.info(f"💾 Profile saved for user {self.user_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            return False
    
    async def get_or_create_profile(self) -> UserProfile:
        """Get existing profile or create new one."""
        profile = await self.load_profile()
        if not profile:
            profile = UserProfile(
                user_id=self.user_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await self.save_profile(profile)
        return profile
    
    # =========================================================================
    # Case Management
    # =========================================================================
    
    async def load_case(self) -> Optional[CaseData]:
        """Load current case from cloud."""
        try:
            data = await self._read_json("case.json")
            if data:
                self._cache["case"] = data
                return CaseData.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Failed to load case: {e}")
            return None
    
    async def save_case(self, case: CaseData) -> bool:
        """Save case to cloud."""
        try:
            case.updated_at = datetime.now(timezone.utc).isoformat()
            data = case.to_dict()
            await self._write_json("case.json", data)
            self._cache["case"] = data
            logger.info(f"💾 Case saved: {case.case_number or case.case_id[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to save case: {e}")
            return False
    
    async def get_or_create_case(self) -> CaseData:
        """Get existing case or create new one."""
        case = await self.load_case()
        if not case:
            import uuid
            case = CaseData(
                case_id=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            await self.save_case(case)
        return case
    
    # =========================================================================
    # Timeline Management
    # =========================================================================
    
    async def load_timeline(self) -> List[dict]:
        """Load timeline events from cloud."""
        try:
            data = await self._read_json("timeline.json")
            events = data.get("events", []) if data else []
            self._cache["timeline"] = events
            return events
        except Exception as e:
            logger.error(f"Failed to load timeline: {e}")
            return []
    
    async def save_timeline(self, events: List[dict]) -> bool:
        """Save timeline events to cloud."""
        try:
            data = {
                "events": events,
                "count": len(events),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._write_json("timeline.json", data)
            self._cache["timeline"] = events
            logger.info(f"💾 Timeline saved: {len(events)} events")
            return True
        except Exception as e:
            logger.error(f"Failed to save timeline: {e}")
            return False
    
    async def add_timeline_event(self, event: dict) -> bool:
        """Add a single event to timeline."""
        events = await self.load_timeline()
        events.append(event)
        return await self.save_timeline(events)
    
    # =========================================================================
    # Calendar Management
    # =========================================================================
    
    async def load_calendar(self) -> List[dict]:
        """Load calendar events from cloud."""
        try:
            data = await self._read_json("calendar.json")
            events = data.get("events", []) if data else []
            self._cache["calendar"] = events
            return events
        except Exception as e:
            logger.error(f"Failed to load calendar: {e}")
            return []
    
    async def save_calendar(self, events: List[dict]) -> bool:
        """Save calendar events to cloud."""
        try:
            data = {
                "events": events,
                "count": len(events),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._write_json("calendar.json", data)
            self._cache["calendar"] = events
            logger.info(f"💾 Calendar saved: {len(events)} events")
            return True
        except Exception as e:
            logger.error(f"Failed to save calendar: {e}")
            return False
    
    # =========================================================================
    # Document Index Management
    # =========================================================================
    
    async def load_document_index(self) -> List[dict]:
        """Load document metadata index from cloud."""
        try:
            data = await self._read_json("documents/index.json")
            docs = data.get("documents", []) if data else []
            self._cache["documents"] = docs
            return docs
        except Exception as e:
            logger.error(f"Failed to load document index: {e}")
            return []
    
    async def save_document_index(self, documents: List[dict]) -> bool:
        """Save document metadata index to cloud."""
        try:
            data = {
                "documents": documents,
                "count": len(documents),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._write_json("documents/index.json", data)
            self._cache["documents"] = documents
            logger.info(f"💾 Document index saved: {len(documents)} docs")
            return True
        except Exception as e:
            logger.error(f"Failed to save document index: {e}")
            return False
    
    async def upload_document(self, filename: str, content: bytes, metadata: dict) -> Optional[str]:
        """Upload document to user's cloud storage."""
        try:
            # Upload file
            path = f"{self.SEMPTIFY_FOLDER}/documents/{filename}"
            file_id = await self.storage.upload_file(path, content)
            
            # Update index
            docs = await self.load_document_index()
            doc_entry = {
                "id": file_id,
                "filename": filename,
                "path": path,
                "size": len(content),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                **metadata,
            }
            docs.append(doc_entry)
            await self.save_document_index(docs)
            
            logger.info(f"📤 Document uploaded: {filename}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return None
    
    async def download_document(self, file_id_or_path: str) -> Optional[bytes]:
        """Download document from user's cloud storage."""
        try:
            # Try as path first
            if file_id_or_path.startswith(self.SEMPTIFY_FOLDER):
                path = file_id_or_path
            else:
                # Look up in index by id
                docs = await self.load_document_index()
                doc = next((d for d in docs if d.get("id") == file_id_or_path or d.get("cloud_id") == file_id_or_path), None)
                if doc and doc.get("path"):
                    path = doc["path"]
                else:
                    # Assume it's a filename
                    path = f"{self.SEMPTIFY_FOLDER}/documents/{file_id_or_path}"
            
            content = await self.storage.download_file(path)
            logger.info(f"📥 Document downloaded: {path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download document: {e}")
            return None
    
    async def delete_document(self, file_id_or_path: str) -> bool:
        """Delete document from user's cloud storage."""
        try:
            # Try as path first
            if file_id_or_path.startswith(self.SEMPTIFY_FOLDER):
                path = file_id_or_path
            else:
                # Look up in index by id
                docs = await self.load_document_index()
                doc = next((d for d in docs if d.get("id") == file_id_or_path or d.get("cloud_id") == file_id_or_path), None)
                if doc and doc.get("path"):
                    path = doc["path"]
                else:
                    path = f"{self.SEMPTIFY_FOLDER}/documents/{file_id_or_path}"
            
            await self.storage.delete_file(path)
            logger.info(f"🗑️ Document deleted: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    # =========================================================================
    # Full Sync
    # =========================================================================
    
    async def sync_all(self) -> dict:
        """
        Perform full sync - load all data from cloud.
        Returns summary of loaded data.
        """
        self.status = SyncStatus.SYNCING
        
        try:
            # Ensure folder structure exists
            await self.ensure_folder_structure()
            
            # Load all data
            profile = await self.get_or_create_profile()
            case = await self.get_or_create_case()
            timeline = await self.load_timeline()
            calendar = await self.load_calendar()
            documents = await self.load_document_index()
            
            # Update sync state
            await self._update_sync_state()
            
            self.status = SyncStatus.SYNCED
            
            summary = {
                "status": "synced",
                "user_id": self.user_id,
                "profile": profile.to_dict() if profile else None,
                "case": case.to_dict() if case else None,
                "timeline_count": len(timeline),
                "calendar_count": len(calendar),
                "document_count": len(documents),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
            
            logger.info(f"🔄 Full sync complete for user {self.user_id[:8]}...")
            return summary
            
        except Exception as e:
            self.status = SyncStatus.ERROR
            logger.error(f"Sync failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def export_all(self) -> dict:
        """Export all user data as a single JSON blob."""
        return {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "profile": self._cache.get("profile"),
            "case": self._cache.get("case"),
            "timeline": self._cache.get("timeline", []),
            "calendar": self._cache.get("calendar", []),
            "documents": self._cache.get("documents", []),
        }
    
    async def import_all(self, data: dict) -> bool:
        """Import data from export blob."""
        try:
            if "profile" in data and data["profile"]:
                await self._write_json("profile.json", data["profile"])
            if "case" in data and data["case"]:
                await self._write_json("case.json", data["case"])
            if "timeline" in data:
                await self.save_timeline(data["timeline"])
            if "calendar" in data:
                await self.save_calendar(data["calendar"])
            if "documents" in data:
                await self.save_document_index(data["documents"])
            
            logger.info(f"📥 Data imported for user {self.user_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    async def _read_json(self, filename: str) -> Optional[dict]:
        """Read JSON file from cloud storage."""
        path = f"{self.SEMPTIFY_FOLDER}/{filename}"
        try:
            content = await self.storage.read_file(path)
            if content:
                return json.loads(content.decode('utf-8'))
            return None
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Read failed for {path}: {e}")
            return None
    
    async def _write_json(self, filename: str, data: dict) -> None:
        """Write JSON file to cloud storage."""
        path = f"{self.SEMPTIFY_FOLDER}/{filename}"
        content = json.dumps(data, indent=2, default=str).encode('utf-8')
        await self.storage.write_file(path, content)
    
    async def _update_sync_state(self) -> None:
        """Update sync state metadata."""
        state = SyncState(
            last_sync=datetime.now(timezone.utc).isoformat(),
            sync_count=self._cache.get("sync_count", 0) + 1,
            checksum=self._calculate_checksum(),
        )
        await self._write_json("sync_state.json", state.to_dict())
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of cached data for conflict detection."""
        data = json.dumps(self._cache, sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()[:16]


# =============================================================================
# Factory Function
# =============================================================================

async def get_cloud_sync(storage_client, user_id: str) -> UserCloudSync:
    """
    Get a UserCloudSync instance for a user.
    
    Usage:
        from app.services.storage.google_drive import GoogleDriveClient
        
        client = GoogleDriveClient(access_token)
        sync = await get_cloud_sync(client, user_id)
        
        # Now use sync to load/save user data
        profile = await sync.load_profile()
    """
    sync = UserCloudSync(storage_client, user_id)
    return sync


# =============================================================================
# Quick Sync Endpoints Helper
# =============================================================================

class QuickSyncData:
    """
    Lightweight sync data structure for API responses.
    Contains just the essential data for quick loading.
    """
    
    @staticmethod
    def from_sync(sync: UserCloudSync) -> dict:
        """Create quick sync response from sync service."""
        return {
            "user_id": sync.user_id,
            "status": sync.status.value,
            "profile": sync._cache.get("profile"),
            "case_summary": {
                "case_number": sync._cache.get("case", {}).get("case_number"),
                "status": sync._cache.get("case", {}).get("status"),
                "hearing_date": sync._cache.get("case", {}).get("hearing_date"),
            } if sync._cache.get("case") else None,
            "counts": {
                "timeline": len(sync._cache.get("timeline", [])),
                "calendar": len(sync._cache.get("calendar", [])),
                "documents": len(sync._cache.get("documents", [])),
            },
        }
