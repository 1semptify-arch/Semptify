"""
Semptify 5.0 - Stateless OAuth Token Management

PRIVACY ARCHITECTURE:
- OAuth tokens stored in USER'S cloud storage (not server database)
- Server never sees user's identity from provider
- Tokens validated directly with provider API (stateless)
- Single HMAC-signed cookie for identity (semptify_uid)

STATELESS DESIGN:
- No session table
- No database token storage
- Token validation on-demand (lazy)
- Provider API calls for validity checks

MULTI-ROLE SUPPORT:
- Role encoded in user_id (GU7x9kM2pQ = Google + User)
- Role selected before OAuth
- OAuth flow includes role parameter
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from app.core.utc import utc_now
from app.core.user_id import parse_user_id, generate_user_id
from app.core.cookie_auth import sign_user_id, verify_user_id
from app.core.vault_paths import AUTH_FOLDER, SEMPTIFY_ROOT

logger = logging.getLogger(__name__)


class StatelessOAuthManager:
    """
    Manages OAuth tokens in a stateless, privacy-preserving manner.
    
    Tokens are stored in the user's cloud storage, not the server database.
    This ensures server never has access to user's provider identity.
    """
    
    def __init__(self, vault_service):
        """
        Initialize with vault service for cloud storage access.
        
        Args:
            vault_service: Service to access user's cloud storage
        """
        self.vault = vault_service
        # Per-user+provider locks to prevent concurrent token refresh races.
        # Without this, two concurrent requests could both try to refresh with
        # the same refresh_token, and one would fail because providers
        # invalidate the old refresh_token after issuing a new one.
        self._refresh_locks: Dict[Tuple[str, str], asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _get_refresh_lock(self, user_id: str, provider: str) -> asyncio.Lock:
        """Get or create a per-user+provider lock for serialized token refresh."""
        key = (user_id, provider)
        async with self._locks_guard:
            lock = self._refresh_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._refresh_locks[key] = lock
            return lock
    
    async def store_oauth_tokens(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> bool:
        """
        Store OAuth tokens in user's cloud storage.
        
        Tokens are encrypted and stored in .semptify/auth/ directory
        in the user's own cloud storage (Google Drive, Dropbox, OneDrive).
        
        Args:
            user_id: User's Semptify ID
            provider: Storage provider (google_drive, dropbox, onedrive)
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_at: Token expiration timestamp (optional)
        
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Strip HMAC signature for vault operations
            raw_user_id = user_id.split('.')[0] if '.' in user_id else user_id
            
            # Prepare token data
            token_data = {
                "provider": provider,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "stored_at": utc_now().isoformat(),
            }
            
            # Store in user's cloud storage
            token_path = f"{AUTH_FOLDER}/{provider}_tokens.json"
            token_json = json.dumps(token_data)
            
            await self.vault.write_file(
                path=token_path,
                content=token_json.encode('utf-8'),
                metadata={"purpose": "oauth_tokens", "encrypted": True}
            )
            
            logger.info(f"OAuth tokens stored in cloud storage for user={raw_user_id[:4]}... provider={provider}")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to store OAuth tokens in cloud storage: {e}")
            return False
    
    async def get_oauth_tokens(
        self,
        user_id: str,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth tokens from user's cloud storage.
        
        Args:
            user_id: User's Semptify ID
            provider: Storage provider
        
        Returns:
            Token data dict or None if not found
        """
        try:
            # Strip HMAC signature for vault operations
            raw_user_id = user_id.split('.')[0] if '.' in user_id else user_id
            
            # Read from user's cloud storage
            token_path = f"{AUTH_FOLDER}/{provider}_tokens.json"
            token_content = await self.vault.read_file(token_path)
            
            if not token_content:
                logger.warning(f"No OAuth tokens found in cloud storage for user={raw_user_id[:4]}... provider={provider}")
                return None
            
            token_data = json.loads(token_content.decode('utf-8'))
            logger.info(f"OAuth tokens retrieved from cloud storage for user={raw_user_id[:4]}... provider={provider}")
            return token_data
            
        except Exception as e:
            logger.exception(f"Failed to retrieve OAuth tokens from cloud storage: {e}")
            return None
    
    async def validate_token_with_provider(
        self,
        provider: str,
        access_token: str,
    ) -> bool:
        """
        Validate OAuth token directly with provider API.
        
        This is the stateless validation method - no database required.
        
        Args:
            provider: Storage provider
            access_token: OAuth access token to validate
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            if provider == "google_drive":
                return await self._validate_google_token(access_token)
            elif provider == "dropbox":
                return await self._validate_dropbox_token(access_token)
            elif provider == "onedrive":
                return await self._validate_onedrive_token(access_token)
            else:
                logger.warning(f"Unknown provider for token validation: {provider}")
                return False
                
        except Exception as e:
            logger.exception(f"Token validation failed for provider={provider}: {e}")
            return False
    
    async def _validate_google_token(self, access_token: str) -> bool:
        """Validate Google Drive OAuth token."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/tokeninfo",
                params={"access_token": access_token}
            )
            return response.status_code == 200
    
    async def _validate_dropbox_token(self, access_token: str) -> bool:
        """Validate Dropbox OAuth token."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dropboxapi.com/2/check/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.status_code == 200
    
    async def _validate_onedrive_token(self, access_token: str) -> bool:
        """Validate OneDrive OAuth token."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.status_code == 200
    
    async def refresh_token_if_needed(
        self,
        user_id: str,
        provider: str,
    ) -> Optional[str]:
        """
        Refresh OAuth token if expired.
        
        Args:
            user_id: User's Semptify ID
            provider: Storage provider
        
        Returns:
            New access token if refreshed, None otherwise
        """
        token_data = await self.get_oauth_tokens(user_id, provider)
        if not token_data:
            return None
        
        # Check if token is expired
        expires_at = token_data.get("expires_at")
        if expires_at:
            expires_datetime = datetime.fromtimestamp(expires_at, timezone.utc)
            if utc_now() < expires_datetime:
                # Token still valid
                return token_data.get("access_token")
        
        # Token expired or no expiration - attempt refresh
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            logger.warning(f"No refresh token available for user={user_id[:4]}... provider={provider}")
            return None

        # Serialize refresh per (user_id, provider) to prevent concurrent
        # refresh races where two requests both try the same refresh_token
        # and one fails because providers invalidate it after first use.
        refresh_lock = await self._get_refresh_lock(user_id, provider)
        async with refresh_lock:
            # Re-read token under lock — another request may have refreshed it
            token_data = await self.get_oauth_tokens(user_id, provider)
            if token_data:
                expires_at = token_data.get("expires_at")
                if expires_at:
                    expires_datetime = datetime.fromtimestamp(expires_at, timezone.utc)
                    if utc_now() < expires_datetime:
                        return token_data.get("access_token")
                refresh_token = token_data.get("refresh_token") or refresh_token

            new_tokens = await self._refresh_with_provider(provider, refresh_token)
            if not new_tokens:
                logger.warning(f"Token refresh failed for user={user_id[:4]}... provider={provider}")
                return None

            new_access = new_tokens.get("access_token")
            new_refresh = new_tokens.get("refresh_token", refresh_token)
            expires_in = new_tokens.get("expires_in", 3600)
            new_expires_at = int(utc_now().timestamp()) + int(expires_in)

            # Persist refreshed tokens back to user's cloud storage.
            # If storage fails, still return the new access token so the
            # current request succeeds — the next request will re-refresh.
            stored = await self.store_oauth_tokens(
                user_id=user_id,
                provider=provider,
                access_token=new_access,
                refresh_token=new_refresh,
                expires_at=new_expires_at,
            )
            if not stored:
                logger.warning(
                    f"Token refreshed but cloud storage failed for user={user_id[:4]}... "
                    f"provider={provider} — next request may need to re-authenticate"
                )
            else:
                logger.info(f"Token refreshed and stored for user={user_id[:4]}... provider={provider}")
            return new_access

    async def _refresh_with_provider(
        self,
        provider: str,
        refresh_token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Provider-specific OAuth token refresh.

        Posts refresh_token to the provider's token endpoint with client
        credentials from settings. Returns the new token JSON on success,
        None on failure.
        """
        try:
            from app.core.config import get_settings
            import httpx

            settings = get_settings()

            if provider == "google_drive":
                if not settings.google_drive_client_id:
                    return None
                token_url = "https://oauth2.googleapis.com/token"
                data = {
                    "client_id": settings.google_drive_client_id,
                    "client_secret": settings.google_drive_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            elif provider == "dropbox":
                if not settings.dropbox_app_key:
                    return None
                token_url = "https://api.dropboxapi.com/oauth2/token"
                data = {
                    "client_id": settings.dropbox_app_key,
                    "client_secret": settings.dropbox_app_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            elif provider == "onedrive":
                if not settings.onedrive_client_id:
                    return None
                token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
                data = {
                    "client_id": settings.onedrive_client_id,
                    "client_secret": settings.onedrive_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "Files.ReadWrite.AppFolder User.Read offline_access",
                }
            else:
                logger.warning(f"Unknown provider for token refresh: {provider}")
                return None

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, data=data)
                if response.status_code != 200:
                    logger.error(
                        f"Token refresh failed for provider={provider}: "
                        f"HTTP {response.status_code} - {response.text}"
                    )
                    return None
                return response.json()

        except Exception as e:
            logger.exception(f"Token refresh error for provider={provider}: {e}")
            return None
    
    async def store_session(
        self,
        user_id: str,
        session_data: Dict[str, Any],
    ) -> bool:
        """
        Store session data in user's cloud storage.
        
        STEP 2: Migrate sessions from database to cloud storage.
        Sessions are stored as encrypted JSON in .semptify/sessions/
        
        Args:
            user_id: User's Semptify ID
            session_data: Session data to store
        
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Strip HMAC signature for vault operations
            raw_user_id = user_id.split('.')[0] if '.' in user_id else user_id
            
            # Prepare session data
            session_json = json.dumps(session_data)
            
            # Store in user's cloud storage
            session_path = f"{SEMPTIFY_ROOT}/sessions/{raw_user_id}_session.json"
            
            await self.vault.write_file(
                path=session_path,
                content=session_json.encode('utf-8'),
                metadata={"purpose": "session", "encrypted": True}
            )
            
            logger.info(f"Session stored in cloud storage for user={raw_user_id[:4]}...")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to store session in cloud storage: {e}")
            return False
    
    async def get_session(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from user's cloud storage.
        
        Args:
            user_id: User's Semptify ID
        
        Returns:
            Session data dict or None if not found
        """
        try:
            # Strip HMAC signature for vault operations
            raw_user_id = user_id.split('.')[0] if '.' in user_id else user_id
            
            # Read from user's cloud storage
            session_path = f"{SEMPTIFY_ROOT}/sessions/{raw_user_id}_session.json"
            session_content = await self.vault.read_file(session_path)
            
            if not session_content:
                logger.warning(f"No session found in cloud storage for user={raw_user_id[:4]}...")
                return None
            
            session_data = json.loads(session_content.decode('utf-8'))
            logger.info(f"Session retrieved from cloud storage for user={raw_user_id[:4]}...")
            return session_data
            
        except Exception as e:
            logger.exception(f"Failed to retrieve session from cloud storage: {e}")
            return None
    
    async def delete_session(
        self,
        user_id: str,
    ) -> bool:
        """
        Delete session from user's cloud storage.
        
        Args:
            user_id: User's Semptify ID
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Strip HMAC signature for vault operations
            raw_user_id = user_id.split('.')[0] if '.' in user_id else user_id
            
            # Delete from user's cloud storage
            session_path = f"{SEMPTIFY_ROOT}/sessions/{raw_user_id}_session.json"
            
            await self.vault.delete_file(session_path)
            
            logger.info(f"Session deleted from cloud storage for user={raw_user_id[:4]}...")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to delete session from cloud storage: {e}")
            return False


def create_stateless_auth_cookie(user_id: str) -> str:
    """
    Create HMAC-signed auth cookie for stateless authentication.
    
    This is the ONLY cookie needed for authentication.
    Contains: provider + role + random (encoded in user_id)
    Signed with: HMAC-SHA256 using SECRET_KEY
    
    Args:
        user_id: Raw user ID (will be signed)
    
    Returns:
        Signed cookie value
    """
    return sign_user_id(user_id)


def verify_stateless_auth_cookie(cookie_value: str) -> Optional[str]:
    """
    Verify HMAC-signed auth cookie.
    
    Args:
        cookie_value: Cookie value from request
    
    Returns:
        Raw user ID if valid, None otherwise
    """
    return verify_user_id(cookie_value)
