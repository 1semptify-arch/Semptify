"""Admin authentication router.

Public-facing admin login endpoints. Step 1 validates credentials and returns
whether TOTP step 2 is required. Step 2 validates TOTP and issues the
short-lived admin elevation cookie.
"""

from __future__ import annotations

import logging
import os

import pyotp
from fastapi import APIRouter, HTTPException, Request, Response

from app.core.admin_elevation import set_elevation_cookie
from app.core.cookie_auth import extract_user_id
from app.core.navigation import navigation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Auth"])

# Admin credentials from environment (set in Render dashboard)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # Must be set in production
ADMIN_TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET")  # Base32 secret for 2FA


@router.post("/admin/api/login-step1")
async def admin_login_step1(request: Request):
    """
    Step 1: Validate username/password.
    Returns step2_required=true if 2FA is enabled.
    """
    logger.info("=== ADMIN LOGIN STEP 1 CALLED ===")
    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
    except Exception as e:
        logger.error("JSON parse error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON")  # noqa: B904

    # Debug: Log credential status (without logging actual passwords)
    logger.info(
        "Admin login attempt - Username: %s, ADMIN_USERNAME set: %s, ADMIN_PASSWORD set: %s, ADMIN_TOTP_SECRET set: %s",
        username,
        bool(ADMIN_USERNAME),
        bool(ADMIN_PASSWORD),
        bool(ADMIN_TOTP_SECRET),
    )

    # Validate credentials
    if not ADMIN_PASSWORD:
        logger.error("ADMIN_PASSWORD not set - admin login disabled")
        raise HTTPException(status_code=503, detail="Admin login not configured")

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        logger.warning("Failed admin login step 1: %s (expected: %s)", username, ADMIN_USERNAME)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if 2FA is enabled
    if ADMIN_TOTP_SECRET:
        return {"success": True, "step2_required": True, "message": "Two-step verification required"}
    else:
        # No 2FA configured - skip to step 2 directly
        return {"success": True, "step2_required": True, "message": "Two-step verification required"}


@router.post("/admin/api/login-step2")
async def admin_login_step2(request: Request, response: Response):
    """
    Step 2: Validate 2FA code and issue elevation cookie.
    Requires existing OAuth session. Issues a 4-hour elevation cookie.
    """
    admin_dashboard_stage = navigation.get_stage("admin_dashboard")
    admin_dashboard_path = admin_dashboard_stage.path if admin_dashboard_stage else "/admin/dashboard"
    storage_select_stage = navigation.get_stage("storage_select")
    storage_select_path = storage_select_stage.path if storage_select_stage else "/onboarding/providers"

    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        totp_code = data.get("totp_code", "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")  # noqa: B904

    # Re-validate credentials
    if not ADMIN_PASSWORD or username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Validate TOTP code if 2FA is configured
    if ADMIN_TOTP_SECRET:
        totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
        if not totp.verify(totp_code, valid_window=2):  # Allow 60sec drift
            logger.warning("Failed 2FA attempt for admin: %s", username)
            raise HTTPException(status_code=401, detail="Invalid two-step code")
    elif totp_code != "000000":
        pass  # TOTP not configured but code provided - ignore

    # Get OAuth user_id for the elevation token (may be None if no OAuth session yet)
    oauth_uid = extract_user_id(request) or f"admin_{username}"

    # Issue 4-hour elevation cookie
    set_elevation_cookie(response, oauth_uid)
    logger.info("Admin elevation granted for %s...", oauth_uid[:6])

    # If no OAuth session yet, redirect to onboarding to connect storage
    has_oauth = extract_user_id(request) is not None
    if not has_oauth:
        return {
            "success": True,
            "redirect": f"{storage_select_path}?role=admin",
            "message": "Please connect your storage to continue",
        }

    return {"success": True, "redirect": admin_dashboard_path}
