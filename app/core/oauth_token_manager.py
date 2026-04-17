"""
OAuth Token Manager - Secure Token Refresh and Management
=====================================================

Handles OAuth token refresh, expiration, and secure storage.
"""

import logging
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class OAuthToken:
    """OAuth token with metadata."""
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[datetime]
    token_type: str = "Bearer"
    scope: Optional[str] = None
    provider: Optional[str] = None
    
    def is_expired(self, buffer_minutes: int = 5) -> bool:
        """Check if token is expired or will expire soon."""
        if not self.expires_at:
            return False  # No expiration info, assume valid
        expiry_buffer = timedelta(minutes=buffer_minutes)
        return datetime.now(timezone.utc) >= (self.expires_at - expiry_buffer)
    
    def expires_in_seconds(self) -> int:
        """Get seconds until token expires."""
        if not self.expires_at:
            return 3600  # Default to 1 hour if no expiration
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))

class OAuthTokenManager:
    """Manages OAuth tokens with automatic refresh."""
    
    def __init__(self):
        self.tokens: Dict[str, OAuthToken] = {}
        self.refresh_callbacks: Dict[str, callable] = {}
        self.max_refresh_attempts = 3
        self.refresh_cooldown = 60  # seconds between refresh attempts
        
    def register_refresh_callback(self, provider: str, callback: callable):
        """Register a callback function for token refresh."""
        self.refresh_callbacks[provider] = callback
        
    def store_token(self, user_id: str, token: OAuthToken):
        """Store a token for a user."""
        self.tokens[user_id] = token
        logger.info(f"Stored token for user {user_id}, provider {token.provider}")
        
    def get_token(self, user_id: str) -> Optional[OAuthToken]:
        """Get stored token for user."""
        return self.tokens.get(user_id)
    
    def remove_token(self, user_id: str):
        """Remove token for user."""
        if user_id in self.tokens:
            del self.tokens[user_id]
            logger.info(f"Removed token for user {user_id}")
    
    def refresh_token_if_needed(self, user_id: str) -> Optional[OAuthToken]:
        """Refresh token if it's expired or will expire soon."""
        token = self.get_token(user_id)
        if not token:
            return None
            
        if not token.is_expired():
            return token
            
        return self._refresh_token(user_id, token)
    
    def _refresh_token(self, user_id: str, token: OAuthToken) -> Optional[OAuthToken]:
        """Refresh an expired token."""
        if not token.refresh_token:
            logger.warning(f"No refresh token available for user {user_id}")
            return None
            
        provider = token.provider
        if not provider or provider not in self.refresh_callbacks:
            logger.error(f"No refresh callback for provider {provider}")
            return None
            
        try:
            # Call provider-specific refresh callback
            refresh_callback = self.refresh_callbacks[provider]
            new_token_data = refresh_callback(token.refresh_token)
            
            if new_token_data:
                # Create new token object
                new_token = OAuthToken(
                    access_token=new_token_data.get('access_token', ''),
                    refresh_token=new_token_data.get('refresh_token', token.refresh_token),
                    expires_at=self._parse_expires_at(new_token_data.get('expires_in')),
                    token_type=new_token_data.get('token_type', 'Bearer'),
                    scope=new_token_data.get('scope', token.scope),
                    provider=provider
                )
                
                # Store new token
                self.store_token(user_id, new_token)
                
                logger.info(f"Successfully refreshed token for user {user_id}")
                return new_token
            else:
                logger.error(f"Token refresh failed for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing token for user {user_id}: {e}")
            return None
    
    def _parse_expires_at(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Parse expires_in to datetime."""
        if expires_in:
            return datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return None
    
    def get_valid_token(self, user_id: str) -> Optional[OAuthToken]:
        """Get a valid token, refreshing if necessary."""
        return self.refresh_token_if_needed(user_id)
    
    def validate_token(self, user_id: str) -> bool:
        """Validate that user has a valid token."""
        token = self.get_valid_token(user_id)
        return token is not None and not token.is_expired()
    
    def get_token_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get token information for debugging."""
        token = self.get_token(user_id)
        if not token:
            return None
            
        return {
            'provider': token.provider,
            'token_type': token.token_type,
            'expires_at': token.expires_at.isoformat() if token.expires_at else None,
            'expires_in_seconds': token.expires_in_seconds(),
            'is_expired': token.is_expired(),
            'has_refresh_token': bool(token.refresh_token),
            'scope': token.scope
        }
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens that can't be refreshed."""
        expired_users = []
        
        for user_id, token in self.tokens.items():
            if token.is_expired() and not token.refresh_token:
                expired_users.append(user_id)
                
        for user_id in expired_users:
            self.remove_token(user_id)
            logger.info(f"Cleaned up expired token for user {user_id}")
    
    def export_tokens(self) -> Dict[str, Dict[str, Any]]:
        """Export tokens for backup (without sensitive data)."""
        export_data = {}
        
        for user_id, token in self.tokens.items():
            export_data[user_id] = {
                'provider': token.provider,
                'token_type': token.token_type,
                'expires_at': token.expires_at.isoformat() if token.expires_at else None,
                'scope': token.scope,
                'has_refresh_token': bool(token.refresh_token)
            }
            
        return export_data

# Global token manager instance
token_manager = OAuthTokenManager()

def get_token_manager() -> OAuthTokenManager:
    """Get the global token manager instance."""
    return token_manager

# Provider-specific refresh implementations
def register_google_refresh_callback():
    """Register Google Drive token refresh callback."""
    def refresh_google_token(refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            import httpx
            
            settings = get_settings()
            if not settings.google_drive_client_id:
                return None
                
            data = {
                'client_id': settings.google_drive_client_id,
                'client_secret': settings.google_drive_client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    'https://oauth2.googleapis.com/token',
                    data=data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Google token refresh failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Google token refresh error: {e}")
            return None
    
    token_manager.register_refresh_callback('google_drive', refresh_google_token)

def register_dropbox_refresh_callback():
    """Register Dropbox token refresh callback."""
    def refresh_dropbox_token(refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            import httpx
            
            settings = get_settings()
            if not settings.dropbox_app_key:
                return None
                
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': settings.dropbox_app_key,
                'client_secret': settings.dropbox_app_secret
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    'https://api.dropboxapi.com/oauth2/token',
                    data=data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Dropbox token refresh failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Dropbox token refresh error: {e}")
            return None
    
    token_manager.register_refresh_callback('dropbox', refresh_dropbox_token)

def register_onedrive_refresh_callback():
    """Register OneDrive token refresh callback."""
    def refresh_onedrive_token(refresh_token: str) -> Optional[Dict[str, Any]]:
        try:
            import httpx
            
            settings = get_settings()
            if not settings.onedrive_client_id:
                return None
                
            data = {
                'client_id': settings.onedrive_client_id,
                'client_secret': settings.onedrive_client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                    data=data
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"OneDrive token refresh failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"OneDrive token refresh error: {e}")
            return None
    
    token_manager.register_refresh_callback('onedrive', refresh_onedrive_token)

# Initialize refresh callbacks
def init_oauth_token_manager():
    """Initialize OAuth token manager with provider callbacks."""
    register_google_refresh_callback()
    register_dropbox_refresh_callback()
    register_onedrive_refresh_callback()
    logger.info("OAuth token manager initialized")

# Helper functions
def get_valid_token_for_user(user_id: str) -> Optional[str]:
    """Get valid access token for user."""
    token = token_manager.get_valid_token(user_id)
    return token.access_token if token else None

def is_token_valid(user_id: str) -> bool:
    """Check if user has valid token."""
    return token_manager.validate_token(user_id)

def refresh_user_token(user_id: str) -> bool:
    """Force refresh user token."""
    token = token_manager.refresh_token_if_needed(user_id)
    return token is not None
