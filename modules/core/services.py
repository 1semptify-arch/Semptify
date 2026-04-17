"""
Core Module Services

Provides core business logic and utilities used across the application.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import secrets

from .models import SystemLog, SystemConfig, UserSession
from . import logger

class SystemService:
    """System-level services"""

    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_string(value: str) -> str:
        """Create SHA-256 hash of a string"""
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return ".1f"
            bytes_size /= 1024.0
        return ".1f"

    @staticmethod
    def get_mime_type(filename: str) -> str:
        """Get MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'

class LoggingService:
    """Centralized logging service"""

    @staticmethod
    def log(level: str, module: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log a message with structured data"""
        logger.log(getattr(logging, level.upper(), logging.INFO), f"[{module}] {message}")

        # TODO: Store in database
        # log_entry = create_system_log(level, module, message, data)
        # db.add(log_entry)
        # db.commit()

    @staticmethod
    def info(module: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log info message"""
        LoggingService.log('info', module, message, data)

    @staticmethod
    def error(module: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log error message"""
        LoggingService.log('error', module, message, data)

    @staticmethod
    def warning(module: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        LoggingService.log('warning', module, message, data)

    @staticmethod
    def debug(module: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        LoggingService.log('debug', module, message, data)

class ConfigService:
    """Configuration management service"""

    _config_cache: Dict[str, Any] = {}
    _cache_timestamp: Optional[datetime] = None
    _cache_ttl = timedelta(minutes=5)

    @classmethod
    def get_config(cls, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        # TODO: Implement database-backed configuration
        # For now, return hardcoded defaults
        defaults = {
            'app.name': 'Semptify',
            'app.version': '5.0.0',
            'storage.max_file_size': 100 * 1024 * 1024,  # 100MB
            'storage.allowed_types': ['pdf', 'doc', 'docx', 'txt', 'jpg', 'png'],
            'ui.theme': 'auto',
            'ui.language': 'en',
            'security.session_timeout': 3600,  # 1 hour
        }
        return defaults.get(key, default)

    @classmethod
    def set_config(cls, key: str, value: Any, description: Optional[str] = None):
        """Set configuration value"""
        # TODO: Implement database storage
        cls._config_cache[key] = value
        cls._cache_timestamp = datetime.now()

class SessionService:
    """Session management service"""

    @staticmethod
    def create_session(user_id: str, ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> str:
        """Create a new user session"""
        session_id = SystemService.generate_session_id()
        expires_at = datetime.now() + timedelta(hours=1)  # 1 hour session

        # TODO: Store in database
        # session = UserSession(
        #     user_id=user_id,
        #     session_id=session_id,
        #     ip_address=ip_address,
        #     user_agent=user_agent,
        #     expires_at=expires_at
        # )
        # db.add(session)
        # db.commit()

        LoggingService.info('session', f'Created session for user {user_id}')
        return session_id

    @staticmethod
    def validate_session(session_id: str) -> Optional[str]:
        """Validate session and return user_id if valid"""
        # TODO: Check database
        # session = db.query(UserSession).filter(
        #     UserSession.session_id == session_id,
        #     UserSession.is_active == True,
        #     UserSession.expires_at > datetime.now()
        # ).first()

        # return session.user_id if session else None
        return None  # Placeholder

    @staticmethod
    def destroy_session(session_id: str):
        """Destroy a user session"""
        # TODO: Update database
        LoggingService.info('session', f'Destroyed session {session_id}')

class FileService:
    """File handling utilities"""

    @staticmethod
    def ensure_directory(path: Path):
        """Ensure directory exists"""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """Generate a safe filename"""
        import re
        # Remove dangerous characters
        safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
        # Ensure it doesn't start with dot
        if safe_name.startswith('.'):
            safe_name = 'file' + safe_name
        return safe_name

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """Generate a unique filename"""
        import uuid
        name, ext = Path(original_filename).stem, Path(original_filename).suffix
        return f"{name}_{uuid.uuid4().hex[:8]}{ext}"

# Global service instances
system_service = SystemService()
logging_service = LoggingService()
config_service = ConfigService()
session_service = SessionService()
file_service = FileService()