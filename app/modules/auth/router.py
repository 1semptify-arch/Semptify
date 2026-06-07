"""
Authentication Status Router

Provides authentication status endpoints for checking current user state.
"""

from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.user_id import parse_user_id
from app.core.storage_middleware import is_valid_storage_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class AuthStatusResponse(BaseModel):
    """Response model for auth status check."""
    authenticated: bool
    user_id: Optional[str] = None
    provider: Optional[str] = None
    role: Optional[str] = None


@router.get("/me", response_model=AuthStatusResponse)
async def get_auth_status(
    semptify_uid: Optional[str] = Cookie(default=None),
):
    """
    Get current authentication status.
    
    Returns user info if authenticated, or unauthenticated status if not.
    This endpoint is used by the frontend to check if the user is logged in.
    """
    if not semptify_uid:
        return AuthStatusResponse(authenticated=False)
    
    try:
        # Parse the user ID to extract provider and role
        user_id_data = parse_user_id(semptify_uid)
        
        # Verify the user is valid
        if is_valid_storage_user(semptify_uid):
            return AuthStatusResponse(
                authenticated=True,
                user_id=semptify_uid[:12] + "***",  # Partial ID for security
                provider=user_id_data.get("provider"),
                role=user_id_data.get("role"),
            )
        else:
            return AuthStatusResponse(authenticated=False)
            
    except (ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Auth status check failed: {e}")
        return AuthStatusResponse(authenticated=False)


@router.get("/register")
async def auth_register_info():
    """
    Auth registration endpoint info.
    
    Returns information about registration. Actual registration
    is handled by the onboarding module.
    """
    return {
        "message": "Registration is handled through the onboarding flow",
        "onboarding_url": "/onboarding/start",
    }
