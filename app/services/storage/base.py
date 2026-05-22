"""
Semptify 5.0 Storage Service - Base Interface
Abstract base class for all storage providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime
from app.core.vault_paths import SEMPTIFY_ROOT, AUTH_FOLDER, VAULT_DOCUMENTS, TOKEN_FILE as _VAULT_TOKEN_FILE


@dataclass
class StorageFile:
    """Represents a file in storage."""
    id: str
    name: str
    path: str
    size: int
    mime_type: str
    modified_at: datetime
    is_folder: bool = False
    
    
@dataclass  
class StorageToken:
    """User's encrypted auth token stored in their cloud."""
    token_hash: str
    user_id: str
    role: str  # tenant, advocate, legal, manager, admin
    created_at: datetime
    provider: str  # google_drive, dropbox, onedrive
    encrypted_token: str  # AES-256-GCM encrypted


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    All providers (Google Drive, Dropbox, OneDrive, R2) implement this.
    """
    
    SEMPTIFY_FOLDER = SEMPTIFY_ROOT
    TOKEN_FILE = "token.enc"  # Matches vault_paths.TOKEN_FILE filename (Semptify5.0/auth/token.enc)
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name: google_drive, dropbox, onedrive, r2"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if storage is connected and accessible."""
        pass
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        destination_path: str,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> StorageFile:
        """Upload a file to storage."""
        pass
    
    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """Download a file from storage."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        folder_path: str = "/",
        recursive: bool = False,
    ) -> list[StorageFile]:
        """List files in a folder."""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    async def create_folder(self, folder_path: str) -> bool:
        """Create a folder (and parent folders if needed)."""
        pass
    
    # =========================================================================
    # Semptify Token Operations
    # =========================================================================
    
    async def ensure_semptify_folder(self) -> bool:
        """Ensure Semptify5.0 folder exists in storage root."""
        try:
            if not await self.file_exists(self.SEMPTIFY_FOLDER):
                await self.create_folder(self.SEMPTIFY_FOLDER)
            return True
        except Exception:
            return False
    
    async def write_auth_token(self, encrypted_token_data: str) -> bool:
        """
        Write encrypted auth token to user's storage.
        Writes to AUTH_FOLDER/token.enc — same path as VaultInstaller and vault_manager.
        NOTE: Active write path is vault_manager.update_oauth_credentials(), not this method.
        """
        try:
            await self.ensure_semptify_folder()
            await self.upload_file(
                file_content=encrypted_token_data.encode("utf-8"),
                destination_path=AUTH_FOLDER,
                filename=self.TOKEN_FILE,
                mime_type="application/octet-stream",
            )
            return True
        except Exception:
            return False
    
    async def read_auth_token(self) -> Optional[str]:
        """
        Read encrypted auth token from user's storage.
        Reads from AUTH_FOLDER/token.enc — same path as vault_manager.get_token().
        NOTE: Active read path is vault_manager.get_token(), not this method.
        """
        try:
            token_path = _VAULT_TOKEN_FILE
            if not await self.file_exists(token_path):
                return None
            content = await self.download_file(token_path)
            return content.decode("utf-8")
        except Exception:
            return None
    
    async def token_exists(self) -> bool:
        """Check if auth token exists in storage."""
        return await self.file_exists(_VAULT_TOKEN_FILE)
    
    # =========================================================================
    # Vault Operations (User Documents)
    # =========================================================================
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> StorageFile:
        """
        Upload a document to user's vault in their storage.
        Documents go to Semptify5.0/Vault/documents/
        """
        vault_folder = VAULT_DOCUMENTS
        if document_type:
            vault_folder = f"{vault_folder}/{document_type}"
        
        await self.create_folder(vault_folder)
        return await self.upload_file(
            file_content=file_content,
            destination_path=vault_folder,
            filename=filename,
            mime_type=mime_type,
        )
    
    async def list_documents(
        self,
        document_type: Optional[str] = None,
    ) -> list[StorageFile]:
        """List documents in user's vault."""
        vault_folder = VAULT_DOCUMENTS
        if document_type:
            vault_folder = f"{vault_folder}/{document_type}"
        
        try:
            return await self.list_files(vault_folder, recursive=True)
        except Exception:
            return []
