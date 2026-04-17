"""
Advanced Security System - 2FA and Session Management
==================================================

Provides two-factor authentication and enhanced session management.
"""

import logging
import secrets
import pyotp
import qrcode
import io
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)

class TwoFactorMethod(Enum):
    """Two-factor authentication methods."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"

class SessionStatus(Enum):
    """Session status types."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"

@dataclass
class TwoFactorSetup:
    """Two-factor authentication setup data."""
    user_id: str
    secret: str
    backup_codes: List[str]
    qr_code: Optional[str] = None
    method: TwoFactorMethod = TwoFactorMethod.TOTP
    created_at: datetime
    verified_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "method": self.method.value,
            "qr_code": self.qr_code,
            "backup_codes_count": len(self.backup_codes),
            "created_at": self.created_at.isoformat(),
            "verified_at": self.verified_at.isoformat() if self.verified_at else None
        }

@dataclass
class UserSession:
    """User session information."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    status: SessionStatus = SessionStatus.ACTIVE
    two_factor_verified: bool = False
    device_info: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status.value,
            "two_factor_verified": self.two_factor_verified,
            "device_info": self.device_info
        }

@dataclass
class SecurityEvent:
    """Security event log."""
    event_id: str
    user_id: str
    event_type: str
    description: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    severity: str = "medium"
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "description": self.description,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "metadata": self.metadata
        }

class TwoFactorAuthManager:
    """Manages two-factor authentication."""
    
    def __init__(self):
        self.totp_secrets: Dict[str, str] = {}
        self.backup_codes: Dict[str, List[str]] = {}
        self.verified_users: Dict[str, datetime] = {}
        
        # Security settings
        self.totp_validity_window = 1  # 30 seconds
        self.backup_code_length = 8
        self.max_backup_codes = 10
        self.backup_code_validity_minutes = 10
    
    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def generate_backup_codes(self, count: int = None) -> List[str]:
        """Generate backup codes."""
        if count is None:
            count = self.max_backup_codes
        
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice('0123456789') for _ in range(self.backup_code_length))
            codes.append(code)
        
        return codes
    
    def generate_qr_code(self, secret: str, user_email: str, issuer: str = "Semptify") -> str:
        """Generate QR code for TOTP setup."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        
        # Convert to base64 image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def setup_two_factor(self, user_id: str, user_email: str, 
                           method: TwoFactorMethod = TwoFactorMethod.TOTP) -> TwoFactorSetup:
        """Setup two-factor authentication for user."""
        secret = self.generate_totp_secret()
        backup_codes = self.generate_backup_codes()
        
        # Generate QR code for TOTP
        qr_code = None
        if method == TwoFactorMethod.TOTP:
            qr_code = self.generate_qr_code(secret, user_email)
        
        setup = TwoFactorSetup(
            user_id=user_id,
            secret=secret,
            backup_codes=backup_codes,
            qr_code=qr_code,
            method=method,
            created_at=datetime.now(timezone.utc)
        )
        
        # Store setup data
        self.totp_secrets[user_id] = secret
        self.backup_codes[user_id] = backup_codes
        
        logger.info(f"Setup 2FA for user {user_id} with method {method.value}")
        return setup
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify TOTP code."""
        if user_id not in self.totp_secrets:
            return False
        
        secret = self.totp_secrets[user_id]
        totp = pyotp.TOTP(secret)
        
        return totp.verify(code, valid_window=self.totp_validity_window)
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code."""
        if user_id not in self.backup_codes:
            return False
        
        backup_codes = self.backup_codes[user_id]
        
        if code in backup_codes:
            # Remove used backup code
            backup_codes.remove(code)
            self.backup_codes[user_id] = backup_codes
            return True
        
        return False
    
    def verify_two_factor(self, user_id: str, code: str, 
                         method: TwoFactorMethod = TwoFactorMethod.TOTP) -> bool:
        """Verify two-factor authentication code."""
        if method == TwoFactorMethod.TOTP:
            return self.verify_totp(user_id, code)
        elif method == TwoFactorMethod.BACKUP_CODES:
            return self.verify_backup_code(user_id, code)
        else:
            return False
    
    def enable_two_factor(self, user_id: str) -> bool:
        """Enable two-factor authentication for user."""
        if user_id not in self.totp_secrets:
            return False
        
        self.verified_users[user_id] = datetime.now(timezone.utc)
        logger.info(f"Enabled 2FA for user {user_id}")
        return True
    
    def disable_two_factor(self, user_id: str) -> bool:
        """Disable two-factor authentication for user."""
        # Remove user from all 2FA systems
        self.totp_secrets.pop(user_id, None)
        self.backup_codes.pop(user_id, None)
        self.verified_users.pop(user_id, None)
        
        logger.info(f"Disabled 2FA for user {user_id}")
        return True
    
    def is_two_factor_enabled(self, user_id: str) -> bool:
        """Check if two-factor authentication is enabled for user."""
        return user_id in self.verified_users
    
    def get_two_factor_status(self, user_id: str) -> Dict[str, Any]:
        """Get two-factor authentication status for user."""
        enabled = self.is_two_factor_enabled(user_id)
        has_setup = user_id in self.totp_secrets
        
        return {
            "user_id": user_id,
            "enabled": enabled,
            "has_setup": has_setup,
            "method": TwoFactorMethod.TOTP.value if has_setup else None,
            "enabled_at": self.verified_users.get(user_id).isoformat() if enabled else None
        }
    
    def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """Regenerate backup codes for user."""
        if user_id not in self.totp_secrets:
            return []
        
        backup_codes = self.generate_backup_codes()
        self.backup_codes[user_id] = backup_codes
        
        logger.info(f"Regenerated backup codes for user {user_id}")
        return backup_codes

class SessionManager:
    """Manages user sessions with enhanced security."""
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)
        
        # Session settings
        self.default_session_duration = timedelta(hours=24)
        self.max_sessions_per_user = 5
        self.session_cleanup_interval = timedelta(hours=1)
        self.inactive_timeout = timedelta(minutes=30)
        
        # Security events
        self.security_events: List[SecurityEvent] = []
    
    def create_session(self, user_id: str, ip_address: str, 
                    user_agent: str, device_info: Dict[str, Any] = None,
                    duration: timedelta = None) -> str:
        """Create a new user session."""
        # Check session limits
        if len(self.user_sessions[user_id]) >= self.max_sessions_per_user:
            # Remove oldest session
            oldest_session_id = min(self.user_sessions[user_id], 
                                key=lambda sid: self.sessions[sid].created_at)
            self.revoke_session(oldest_session_id)
        
        # Generate session ID
        session_id = secrets.token_urlsafe(32)
        
        # Set session duration
        if duration is None:
            duration = self.default_session_duration
        
        # Create session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + duration,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info or {}
        )
        
        # Store session
        self.sessions[session_id] = session
        self.user_sessions[user_id].append(session_id)
        
        # Log security event
        self.log_security_event(
            user_id=user_id,
            event_type="session_created",
            description="New session created",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"session_id": session_id}
        )
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def validate_session(self, session_id: str, ip_address: str = None) -> Optional[UserSession]:
        """Validate and update session."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if datetime.now(timezone.utc) > session.expires_at:
            session.status = SessionStatus.EXPIRED
            self.revoke_session(session_id)
            return None
        
        # Check if session is revoked
        if session.status != SessionStatus.ACTIVE:
            return None
        
        # Check IP address change (optional security check)
        if ip_address and session.ip_address != ip_address:
            self.log_security_event(
                user_id=session.user_id,
                event_type="ip_address_change",
                description="Session IP address changed",
                ip_address=ip_address,
                user_agent="",
                metadata={
                    "session_id": session_id,
                    "original_ip": session.ip_address,
                    "new_ip": ip_address
                }
            )
        
        # Update last activity
        session.last_activity = datetime.now(timezone.utc)
        
        return session
    
    def revoke_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """Revoke a user session."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        user_id = session.user_id
        
        # Remove session
        del self.sessions[session_id]
        self.user_sessions[user_id].remove(session_id)
        
        # Clean up empty user session list
        if not self.user_sessions[user_id]:
            del self.user_sessions[user_id]
        
        # Update session status
        session.status = SessionStatus.REVOKED
        
        # Log security event
        self.log_security_event(
            user_id=user_id,
            event_type="session_revoked",
            description=f"Session revoked: {reason}",
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            metadata={"session_id": session_id, "reason": reason}
        )
        
        logger.info(f"Revoked session {session_id} for user {user_id}")
        return True
    
    def revoke_all_user_sessions(self, user_id: str, except_session_id: str = None, 
                              reason: str = "security_action") -> int:
        """Revoke all sessions for a user."""
        if user_id not in self.user_sessions:
            return 0
        
        session_ids = self.user_sessions[user_id].copy()
        revoked_count = 0
        
        for session_id in session_ids:
            if session_id != except_session_id:
                if self.revoke_session(session_id, reason):
                    revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
        return revoked_count
    
    def extend_session(self, session_id: str, duration: timedelta = None) -> bool:
        """Extend session expiration."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        if duration is None:
            duration = self.default_session_duration
        
        session.expires_at = datetime.now(timezone.utc) + duration
        
        # Log security event
        self.log_security_event(
            user_id=session.user_id,
            event_type="session_extended",
            description="Session extended",
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            metadata={
                "session_id": session_id,
                "new_expires_at": session.expires_at.isoformat()
            }
        )
        
        logger.info(f"Extended session {session_id} for user {session.user_id}")
        return True
    
    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user."""
        if user_id not in self.user_sessions:
            return []
        
        sessions = []
        for session_id in self.user_sessions[user_id]:
            if session_id in self.sessions:
                sessions.append(self.sessions[session_id])
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time > session.expires_at:
                expired_sessions.append(session_id)
                session.status = SessionStatus.EXPIRED
        
        # Remove expired sessions
        for session_id in expired_sessions:
            session = self.sessions[session_id]
            user_id = session.user_id
            
            del self.sessions[session_id]
            if user_id in self.user_sessions:
                self.user_sessions[user_id].remove(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            # Log security event
            self.log_security_event(
                user_id=user_id,
                event_type="session_expired",
                description="Session expired",
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                metadata={"session_id": session_id}
            )
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def log_security_event(self, user_id: str, event_type: str, description: str,
                         ip_address: str, user_agent: str, 
                         severity: str = "medium", metadata: Dict[str, Any] = None):
        """Log a security event."""
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            user_id=user_id,
            event_type=event_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            severity=severity,
            metadata=metadata or {}
        )
        
        self.security_events.append(event)
        
        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    def get_user_security_events(self, user_id: str, limit: int = 50) -> List[SecurityEvent]:
        """Get security events for a user."""
        user_events = []
        
        for event in reversed(self.security_events):  # Most recent first
            if event.user_id == user_id:
                user_events.append(event)
                if len(user_events) >= limit:
                    break
        
        return user_events
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        current_time = datetime.now(timezone.utc)
        
        active_sessions = len([
            s for s in self.sessions.values()
            if s.status == SessionStatus.ACTIVE and s.expires_at > current_time
        ])
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "unique_users": len(self.user_sessions),
            "security_events_logged": len(self.security_events),
            "average_sessions_per_user": (
                len(self.sessions) / len(self.user_sessions)
                if self.user_sessions else 0
            )
        }

class AdvancedSecurityManager:
    """Manages advanced security features."""
    
    def __init__(self):
        self.two_factor = TwoFactorAuthManager()
        self.session_manager = SessionManager()
    
    def setup_two_factor_auth(self, user_id: str, user_email: str) -> TwoFactorSetup:
        """Setup two-factor authentication."""
        return self.two_factor.setup_two_factor(user_id, user_email)
    
    def verify_two_factor(self, user_id: str, code: str, 
                         method: TwoFactorMethod = TwoFactorMethod.TOTP) -> bool:
        """Verify two-factor authentication."""
        return self.two_factor.verify_two_factor(user_id, code, method)
    
    def enable_two_factor(self, user_id: str) -> bool:
        """Enable two-factor authentication."""
        return self.two_factor.enable_two_factor(user_id)
    
    def disable_two_factor(self, user_id: str) -> bool:
        """Disable two-factor authentication."""
        return self.two_factor.disable_two_factor(user_id)
    
    def create_secure_session(self, user_id: str, ip_address: str, 
                          user_agent: str, device_info: Dict[str, Any] = None,
                          require_2fa: bool = False) -> Dict[str, Any]:
        """Create a secure session with optional 2FA requirement."""
        # Create session
        session_id = self.session_manager.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info
        )
        
        # Check if 2FA is required and enabled
        two_factor_required = require_2fa and self.two_factor.is_two_factor_enabled(user_id)
        
        # Get session
        session = self.session_manager.sessions[session_id]
        session.two_factor_verified = not two_factor_required
        
        return {
            "session_id": session_id,
            "two_factor_required": two_factor_required,
            "session": session.to_dict()
        }
    
    def validate_secure_session(self, session_id: str, ip_address: str = None) -> Optional[UserSession]:
        """Validate a secure session."""
        return self.session_manager.validate_session(session_id, ip_address)
    
    def revoke_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """Revoke a secure session."""
        return self.session_manager.revoke_session(session_id, reason)
    
    def get_security_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive security status for user."""
        two_factor_status = self.two_factor.get_two_factor_status(user_id)
        user_sessions = self.session_manager.get_user_sessions(user_id)
        security_events = self.session_manager.get_user_security_events(user_id, limit=10)
        
        return {
            "user_id": user_id,
            "two_factor": two_factor_status,
            "active_sessions": len(user_sessions),
            "sessions": [s.to_dict() for s in user_sessions],
            "recent_security_events": [e.to_dict() for e in security_events],
            "security_score": self._calculate_security_score(user_id)
        }
    
    def _calculate_security_score(self, user_id: str) -> int:
        """Calculate security score for user."""
        score = 50  # Base score
        
        # 2FA enabled
        if self.two_factor.is_two_factor_enabled(user_id):
            score += 30
        
        # Session management
        user_sessions = self.session_manager.get_user_sessions(user_id)
        if len(user_sessions) <= 2:
            score += 10
        elif len(user_sessions) <= 5:
            score += 5
        
        # Recent security events
        recent_events = self.session_manager.get_user_security_events(user_id, limit=20)
        failed_attempts = len([
            e for e in recent_events
            if e.event_type in ["login_failed", "session_revoked"]
        ])
        
        if failed_attempts == 0:
            score += 10
        elif failed_attempts <= 2:
            score += 5
        elif failed_attempts <= 5:
            score += 0
        else:
            score -= 10
        
        return max(0, min(100, score))

# Global advanced security manager instance
_advanced_security_manager: Optional[AdvancedSecurityManager] = None

def get_advanced_security_manager() -> AdvancedSecurityManager:
    """Get the global advanced security manager instance."""
    global _advanced_security_manager
    
    if _advanced_security_manager is None:
        _advanced_security_manager = AdvancedSecurityManager()
    
    return _advanced_security_manager

# Helper functions
def setup_two_factor_auth(user_id: str, user_email: str) -> TwoFactorSetup:
    """Setup two-factor authentication."""
    manager = get_advanced_security_manager()
    return manager.setup_two_factor_auth(user_id, user_email)

def verify_two_factor(user_id: str, code: str, method: str = "totp") -> bool:
    """Verify two-factor authentication."""
    manager = get_advanced_security_manager()
    method_enum = TwoFactorMethod(method)
    return manager.verify_two_factor(user_id, code, method_enum)

def enable_two_factor(user_id: str) -> bool:
    """Enable two-factor authentication."""
    manager = get_advanced_security_manager()
    return manager.enable_two_factor(user_id)

def disable_two_factor(user_id: str) -> bool:
    """Disable two-factor authentication."""
    manager = get_advanced_security_manager()
    return manager.disable_two_factor(user_id)

def create_secure_session(user_id: str, ip_address: str, user_agent: str,
                        device_info: Dict[str, Any] = None,
                        require_2fa: bool = False) -> Dict[str, Any]:
    """Create a secure session."""
    manager = get_advanced_security_manager()
    return manager.create_secure_session(user_id, ip_address, user_agent, device_info, require_2fa)

def validate_secure_session(session_id: str, ip_address: str = None) -> Optional[UserSession]:
    """Validate a secure session."""
    manager = get_advanced_security_manager()
    return manager.validate_secure_session(session_id, ip_address)

def get_security_status(user_id: str) -> Dict[str, Any]:
    """Get comprehensive security status."""
    manager = get_advanced_security_manager()
    return manager.get_security_status(user_id)
