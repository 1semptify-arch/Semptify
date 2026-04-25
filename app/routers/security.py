"""
Advanced Security API - 2FA and Session Management
==============================================

Provides advanced security features including two-factor authentication
and enhanced session management.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.advanced_security import (
    get_advanced_security_manager, TwoFactorMethod, TwoFactorSetup,
    setup_two_factor_auth, verify_two_factor, enable_two_factor, disable_two_factor,
    create_secure_session, validate_secure_session, revoke_session,
    get_security_status
)

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class TwoFactorSetupRequest(BaseModel):
    """Two-factor setup request."""
    method: str = Field("totp", description="2FA method: totp")
    user_email: str = Field(..., description="User email for TOTP")

class TwoFactorVerifyRequest(BaseModel):
    """Two-factor verification request."""
    code: str = Field(..., description="Verification code")
    method: str = Field("totp", description="2FA method")

class TwoFactorEnableRequest(BaseModel):
    """Enable two-factor authentication."""
    verification_code: str = Field(..., description="Verification code")
    method: str = Field("totp", description="2FA method")

class SessionCreateRequest(BaseModel):
    """Secure session creation request."""
    require_2fa: bool = Field(False, description="Require 2FA verification")
    device_info: Optional[Dict[str, Any]] = Field(None, description="Device information")

class SecurityStatusResponse(BaseModel):
    """Security status response."""
    user_id: str
    two_factor_enabled: bool
    two_factor_method: Optional[str]
    active_sessions: int
    security_score: int
    last_security_events: List[Dict[str, Any]]

# =============================================================================
# Two-Factor Authentication Endpoints
# =============================================================================

@router.post("/2fa/setup")
async def setup_two_factor_endpoint(
    request: TwoFactorSetupRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Setup two-factor authentication.
    
    Methods:
    - totp: Time-based One-Time Password (recommended)
    - sms: SMS verification (future)
    - email: Email verification (future)
    - backup_codes: Backup recovery codes
    """
    try:
        # Validate method
        try:
            method = TwoFactorMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported 2FA method: {request.method}"
            )
        
        # Setup two-factor authentication
        setup = setup_two_factor_auth(user.user_id, request.user_email, method)
        
        return {
            "success": True,
            "setup_id": setup.user_id,
            "method": request.method,
            "qr_code": setup.qr_code,
            "backup_codes_count": len(setup.backup_codes),
            "message": "Two-factor authentication setup completed",
            "next_step": "verify_and_enable"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA setup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to setup two-factor authentication")

@router.post("/2fa/verify")
async def verify_two_factor_endpoint(
    request: TwoFactorVerifyRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Verify two-factor authentication code.
    
    This endpoint verifies the code generated during setup
    and enables two-factor authentication for the user.
    """
    try:
        # Validate method
        try:
            method = TwoFactorMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported 2FA method: {request.method}"
            )
        
        # Verify two-factor code
        verified = verify_two_factor(user.user_id, request.code, method)
        
        if not verified:
            raise HTTPException(
                status_code=400,
                detail="Invalid verification code"
            )
        
        # Enable two-factor authentication
        enabled = enable_two_factor(user.user_id)
        
        return {
            "success": True,
            "verified": True,
            "enabled": enabled,
            "method": request.method,
            "message": "Two-factor authentication enabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verification failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify two-factor authentication")

@router.post("/2fa/enable")
async def enable_two_factor_endpoint(
    request: TwoFactorEnableRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Enable two-factor authentication with verification code.
    
    Alternative to /verify endpoint that combines verification and enabling.
    """
    try:
        # Validate method
        try:
            method = TwoFactorMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported 2FA method: {request.method}"
            )
        
        # Verify and enable
        verified = verify_two_factor(user.user_id, request.verification_code, method)
        
        if not verified:
            raise HTTPException(
                status_code=400,
                detail="Invalid verification code"
            )
        
        enabled = enable_two_factor(user.user_id)
        
        return {
            "success": True,
            "verified": True,
            "enabled": enabled,
            "method": request.method,
            "message": "Two-factor authentication enabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA enable failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable two-factor authentication")

@router.post("/2fa/disable")
async def disable_two_factor_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Disable two-factor authentication for the current user.
    
    This action requires re-authentication and should be used with caution.
    """
    try:
        disabled = disable_two_factor(user.user_id)
        
        if not disabled:
            raise HTTPException(
                status_code=400,
                detail="Failed to disable two-factor authentication"
            )
        
        return {
            "success": True,
            "disabled": True,
            "message": "Two-factor authentication disabled successfully",
            "warning": "Account security has been reduced"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA disable failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable two-factor authentication")

@router.get("/2fa/status")
async def get_two_factor_status_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get two-factor authentication status.
    """
    try:
        from app.core.advanced_security import get_advanced_security_manager
        manager = get_advanced_security_manager()
        
        status = manager.two_factor.get_two_factor_status(user.user_id)
        
        return {
            "user_id": user.user_id,
            "enabled": status["enabled"],
            "has_setup": status["has_setup"],
            "method": status["method"],
            "enabled_at": status["enabled_at"]
        }
        
    except Exception as e:
        logger.error(f"Get 2FA status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get two-factor status")

@router.post("/2fa/regenerate-codes")
async def regenerate_backup_codes_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Regenerate backup codes for two-factor authentication.
    
    Backup codes are used when the primary 2FA method is unavailable.
    """
    try:
        from app.core.advanced_security import get_advanced_security_manager
        manager = get_advanced_security_manager()
        
        backup_codes = manager.two_factor.regenerate_backup_codes(user.user_id)
        
        return {
            "success": True,
            "backup_codes_count": len(backup_codes),
            "message": "Backup codes regenerated successfully",
            "warning": "Save these codes in a secure location"
        }
        
    except Exception as e:
        logger.error(f"Regenerate backup codes failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate backup codes")

# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.post("/session/create")
async def create_secure_session_endpoint(
    request: SessionCreateRequest,
    http_request: Request,
    user: StorageUser = Depends(require_user)
):
    """
    Create a new secure session.
    
    Enhanced session creation with optional 2FA requirement.
    """
    try:
        # Get client information
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")
        
        # Create secure session
        session_data = create_secure_session(
            user_id=user.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=request.device_info,
            require_2fa=request.require_2fa
        )
        
        # Set session cookie
        response = JSONResponse(content={
            "success": True,
            "session_id": session_data["session_id"],
            "two_factor_required": session_data["two_factor_required"],
            "expires_at": session_data["session"]["expires_at"]
        })
        
        # Set secure cookie - secure=False for localhost HTTP, True for HTTPS production
        import os
        is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
        response.set_cookie(
            key="semptify_session",
            value=session_data["session_id"],
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False if is_localhost else True,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Secure session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create secure session")

@router.post("/session/validate")
async def validate_session_endpoint(
    http_request: Request,
    user: StorageUser = Depends(require_user)
):
    """
    Validate current session and return session information.
    """
    try:
        # Get session ID from cookie
        session_id = http_request.cookies.get("semptify_session")
        
        if not session_id:
            raise HTTPException(
                status_code=401,
                detail="No session found"
            )
        
        # Get client information
        ip_address = http_request.client.host if http_request.client else "unknown"
        
        # Validate session
        session = validate_secure_session(session_id, ip_address)
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            )
        
        return {
            "success": True,
            "session": session.to_dict(),
            "valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate session")

@router.post("/session/revoke/{session_id}")
async def revoke_session_endpoint(
    session_id: str,
    reason: str = Query("user_logout", description="Reason for revocation"),
    user: StorageUser = Depends(require_user)
):
    """
    Revoke a specific session.
    
    Can be used to logout from specific devices or sessions.
    """
    try:
        revoked = revoke_session(session_id, reason)
        
        if not revoked:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        return {
            "success": True,
            "revoked": True,
            "session_id": session_id,
            "reason": reason,
            "message": "Session revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session revocation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke session")

@router.post("/session/revoke-all")
async def revoke_all_sessions_endpoint(
    except_session_id: Optional[str] = Query(None, description="Session ID to keep active"),
    reason: str = Query("security_action", description="Reason for revocation"),
    user: StorageUser = Depends(require_user)
):
    """
    Revoke all sessions for the user except optionally one.
    
    Useful for security incidents or when user wants to logout from all devices.
    """
    try:
        from app.core.advanced_security import get_advanced_security_manager
        manager = get_advanced_security_manager()
        
        revoked_count = manager.session_manager.revoke_all_user_sessions(
            user.user_id, except_session_id, reason
        )
        
        return {
            "success": True,
            "revoked_count": revoked_count,
            "except_session_id": except_session_id,
            "reason": reason,
            "message": f"Revoked {revoked_count} sessions successfully"
        }
        
    except Exception as e:
        logger.error(f"Revoke all sessions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke sessions")

@router.get("/sessions")
async def get_user_sessions_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get all active sessions for the current user.
    
    Returns session information including device details and activity.
    """
    try:
        from app.core.advanced_security import get_advanced_security_manager
        manager = get_advanced_security_manager()
        
        sessions = manager.session_manager.get_user_sessions(user.user_id)
        
        return {
            "user_id": user.user_id,
            "sessions": [session.to_dict() for session in sessions],
            "total_sessions": len(sessions),
            "security_recommendation": "Revoke any unrecognized sessions"
        }
        
    except Exception as e:
        logger.error(f"Get user sessions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user sessions")

# =============================================================================
# Security Status Endpoints
# =============================================================================

@router.get("/status")
async def get_security_status_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get comprehensive security status for the current user.
    
    Includes 2FA status, active sessions, recent security events,
    and overall security score.
    """
    try:
        status = get_security_status(user.user_id)
        
        return SecurityStatusResponse(
            user_id=status["user_id"],
            two_factor_enabled=status["two_factor"]["enabled"],
            two_factor_method=status["two_factor"]["method"],
            active_sessions=status["active_sessions"],
            security_score=status["security_score"],
            last_security_events=status["recent_security_events"]
        ).dict()
        
    except Exception as e:
        logger.error(f"Get security status failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security status")

@router.get("/events")
async def get_security_events_endpoint(
    limit: int = Query(20, ge=1, le=100, description="Max events to return"),
    severity: str = Query(None, description="Filter by severity: low, medium, high, critical"),
    event_type: str = Query(None, description="Filter by event type"),
    user: StorageUser = Depends(require_user)
):
    """
    Get recent security events for the current user.
    
    Security events include:
    - Login attempts (success/failure)
    - Session creation/revocation
    - Two-factor authentication events
    - IP address changes
    - Suspicious activities
    """
    try:
        from app.core.advanced_security import get_advanced_security_manager
        manager = get_advanced_security_manager()
        
        events = manager.session_manager.get_user_security_events(user.user_id, limit)
        
        # Apply filters
        filtered_events = []
        for event in events:
            # Filter by severity
            if severity and event["severity"] != severity:
                continue
            
            # Filter by event type
            if event_type and event["event_type"] != event_type:
                continue
            
            filtered_events.append(event)
        
        return {
            "user_id": user.user_id,
            "events": filtered_events,
            "total_events": len(filtered_events),
            "filters": {
                "severity": severity,
                "event_type": event_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Get security events failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security events")

@router.get("/recommendations")
async def get_security_recommendations_endpoint(
    user: StorageUser = Depends(require_user)
):
    """
    Get security recommendations based on current security status.
    
    Provides actionable recommendations to improve account security.
    """
    try:
        status = get_security_status(user.user_id)
        recommendations = []
        
        # 2FA recommendations
        if not status["two_factor"]["enabled"]:
            recommendations.append({
                "priority": "high",
                "category": "two_factor",
                "title": "Enable Two-Factor Authentication",
                "description": "Add an extra layer of security to your account",
                "action": "Setup 2FA using TOTP app",
                "action_url": "/security/2fa/setup"
            })
        
        # Session recommendations
        if status["active_sessions"] > 3:
            recommendations.append({
                "priority": "medium",
                "category": "sessions",
                "title": "Review Active Sessions",
                "description": "You have multiple active sessions",
                "action": "Review and revoke unrecognized sessions",
                "action_url": "/security/sessions"
            })
        
        # Security score recommendations
        if status["security_score"] < 70:
            recommendations.append({
                "priority": "medium",
                "category": "overall_security",
                "title": "Improve Account Security",
                "description": "Your security score could be improved",
                "action": "Enable 2FA and review active sessions",
                "action_url": "/security/status"
            })
        
        return {
            "user_id": user.user_id,
            "security_score": status["security_score"],
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "next_steps": [
                "Enable two-factor authentication",
                "Review active sessions regularly",
                "Monitor security events"
            ]
        }
        
    except Exception as e:
        logger.error(f"Get security recommendations failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security recommendations")

# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/2fa/methods")
async def get_supported_2fa_methods():
    """
    Get list of supported two-factor authentication methods.
    """
    return {
        "methods": [
            {
                "method": "totp",
                "name": "Time-based One-Time Password (TOTP)",
                "description": "Use authenticator app like Google Authenticator",
                "recommended": True,
                "setup_required": True,
                "apps": ["Google Authenticator", "Authy", "Microsoft Authenticator", "1Password"]
            },
            {
                "method": "sms",
                "name": "SMS Verification",
                "description": "Receive codes via SMS message",
                "recommended": False,
                "setup_required": True,
                "availability": "Future feature"
            },
            {
                "method": "email",
                "name": "Email Verification",
                "description": "Receive codes via email",
                "recommended": False,
                "setup_required": True,
                "availability": "Future feature"
            },
            {
                "method": "backup_codes",
                "name": "Backup Codes",
                "description": "Pre-generated recovery codes",
                "recommended": False,
                "setup_required": False,
                "generated_automatically": True
            }
        ],
        "default_method": "totp",
        "backup_codes_count": 10,
        "backup_codes_validity_days": 30
    }
