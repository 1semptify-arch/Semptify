"""
Semptify 5.0 - Role-Based UI Router
Routes users to appropriate interface based on their role and device.

Role → UI Mapping:
- USER (Tenant):    Mobile-first, simplified wizard-driven interface
- ADVOCATE:         Responsive, multi-case management view
- MANAGER (Case Manager): Multi-client professional workspace
- LEGAL:            Desktop, full features + privilege separation
- ADMIN:            Desktop, system configuration + analytics
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
import logging

from app.core.user_context import (
    UserRole, 
    UserContext, 
    get_role_metadata,
    get_role_definition,
    ROLE_METADATA
)
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["Role UI"])


# =============================================================================
# Device Detection Helper
# =============================================================================

def detect_device_type(request: Request) -> str:
    """
    Detect if user is on mobile, tablet, or desktop.
    Returns: 'mobile', 'tablet', or 'desktop'
    """
    user_agent = request.headers.get("user-agent", "").lower()
    
    mobile_keywords = ["iphone", "android", "mobile", "phone", "ipod"]
    tablet_keywords = ["ipad", "tablet", "kindle"]
    
    if any(kw in user_agent for kw in tablet_keywords):
        return "tablet"
    elif any(kw in user_agent for kw in mobile_keywords):
        return "mobile"
    return "desktop"


# =============================================================================
# Role-Based Landing Pages
# =============================================================================

# Canonical landing page for each role (derived from user_context single source)
ROLE_LANDING_PAGES = {
    role: meta["landing_page"]
    for role, meta in ROLE_METADATA.items()
}

# Static fallback pages if canonical role route is unavailable
ROLE_FALLBACK_PAGES = {
    UserRole.USER: "/static/tenant/index.html",
    UserRole.ADVOCATE: "/static/advocate/index.html",
    UserRole.LEGAL: "/static/legal/index.html",
    UserRole.MANAGER: "/static/admin/mission_control.html",
    UserRole.ADMIN: "/static/admin/mission_control.html",
}


@router.get("/")
async def ui_router(
    request: Request,
    user: Optional[UserContext] = Depends(get_current_user)
):
    """
    Main UI router - redirects to appropriate interface based on role.
    If not authenticated, redirects to welcome/login page.
    """
    if not user:
        return RedirectResponse(url="/static/public/welcome.html", status_code=302)
    
    device = detect_device_type(request)
    logger.info("UI routing: user=%s, role=%s, device=%s", user.user_id, user.role.value, device)
    
    # Use canonical role landing page first, static fallback handled by route layer
    landing_page = ROLE_LANDING_PAGES.get(user.role) or ROLE_FALLBACK_PAGES.get(user.role, "/static/public/welcome.html")
    
    # Log for debugging
    logger.info("Redirecting to: %s", landing_page)
    
    return RedirectResponse(url=landing_page, status_code=302)


@router.get("/route")
async def ui_route(request: Request):
    """
    Post-auth/post-onboarding redirect. Reads the user cookie, checks the vault,
    and sends the user directly to their role home page. No extra hops.
    Returning users and newly onboarded users both land here cleanly.
    """
    from app.core.workflow_engine import route_user as _route_user
    from app.core.cookie_auth import extract_user_id
    user_id = extract_user_id(request)
    if not user_id:
        return RedirectResponse(url="/static/public/welcome.html", status_code=302)
    landing = _route_user(user_id)
    logger.info("ui/route: user=%s → %s", user_id, landing)
    return RedirectResponse(url=landing, status_code=302)


@router.get("/role-info")
async def get_role_info(
    user: Optional[UserContext] = Depends(get_current_user)
) -> dict:
    """
    Get current user's role information for UI customization.
    Returns role metadata, permissions, and UI configuration.
    """
    if not user:
        return {
            "authenticated": False,
            "role": None,
            "ui_mode": "public",
            "landing_page": "/static/public/welcome.html"
        }
    
    role_meta = get_role_metadata(user.role)
    
    return {
        "authenticated": True,
        "user_id": user.user_id,
        "role": user.role.value,
        "role_display": role_meta["display_name"],
        "role_icon": role_meta["icon"],
        "ui_mode": role_meta["ui_mode"],
        "landing_page": role_meta["landing_page"],
        "permissions": list(user.permissions),
        "can_view_privileged": user.has_permission("privileged_read"),
        "can_create_privileged": user.has_permission("privileged_create"),
        "can_help_multiple_users": user.has_permission("multi_user"),
    }


@router.get("/available-roles")
async def get_available_roles() -> dict:
    """
    Get all available roles with their metadata.
    Public endpoint for role selection UI.
    """
    roles = []
    for role in UserRole:
        meta = ROLE_METADATA.get(role, {})
        role_def = get_role_definition(role)
        roles.append({
            "role": role.value,
            "display_name": meta.get("display_name", role.value),
            "description": meta.get("description", ""),
            "purpose": role_def.get("purpose", meta.get("description", "")),
            "default_landing_process": role_def.get("default_landing_process", ""),
            "landing_page": meta.get("landing_page", "/static/public/welcome.html"),
            "icon": meta.get("icon", "👤"),
            "ui_mode": meta.get("ui_mode", "desktop"),
        })
    
    return {
        "roles": roles,
        "default_role": UserRole.USER.value
    }


# =============================================================================
# Role-Specific Feature Flags
# =============================================================================

@router.get("/features")
async def get_role_features(
    user: Optional[UserContext] = Depends(get_current_user)
) -> dict:
    """
    Get feature flags based on user's role.
    Frontend uses this to show/hide UI elements.
    """
    if not user:
        return {
            "features": {
                "show_login": True,
                "show_demo": True,
            }
        }
    
    # Base features for all authenticated users
    features = {
        "show_login": False,
        "show_demo": False,
        "show_vault": user.has_permission("vault_read"),
        "show_timeline": user.has_permission("timeline_read"),
        "show_calendar": user.has_permission("calendar_read"),
        "show_copilot": user.has_permission("copilot_use"),
        "show_complaints": user.has_permission("complaints_create"),
        "show_ledger": user.has_permission("ledger_read"),
    }
    
    # Role-specific features
    if user.role == UserRole.USER:
        features.update({
            "ui_mode": "simplified",
            "show_wizard": True,           # Guided wizards for tenants
            "show_quick_actions": True,    # Big action buttons
            "show_help_request": True,     # Request advocate help
        })
    
    elif user.role == UserRole.ADVOCATE:
        features.update({
            "ui_mode": "standard",
            "show_client_list": True,      # List of assigned clients
            "show_case_queue": True,       # Incoming cases
            "show_intake_form": True,      # New client intake
            "show_case_notes": True,       # Non-privileged notes
        })
    
    elif user.role == UserRole.LEGAL:
        features.update({
            "ui_mode": "advanced",
            "show_client_list": True,
            "show_case_queue": True,
            "show_intake_form": True,
            "show_case_notes": True,
            # Attorney-specific
            "show_privileged_notes": True,   # Attorney-client privilege
            "show_work_product": True,       # Work product section
            "show_legal_research": True,     # Advanced legal tools
            "show_court_filing": True,       # Generate court docs
            "show_discovery_tools": True,    # Discovery prep
            "show_conflict_check": True,     # Conflict checking
            "privilege_indicator": True,     # Show privilege badges
        })
    
    elif user.role == UserRole.ADMIN:
        features.update({
            "ui_mode": "full",
            "show_system_config": True,
            "show_analytics": True,
            "show_user_management": True,
            "show_all_features": True,
        })
    
    return {"features": features, "role": user.role.value}


# =============================================================================
# Navigation Menu by Role
# =============================================================================

@router.get("/navigation")
async def get_navigation_menu(
    user: Optional[UserContext] = Depends(get_current_user)
) -> dict:
    """
    Get navigation menu items based on user's role.
    Returns ordered list of menu items for the UI.
    """
    if not user:
        return {
            "menu": [
                {"label": "Home", "path": "/", "icon": "🏠"},
                {"label": "Sign In", "path": "/storage/providers", "icon": "🔑"},
            ]
        }
    
    # Base menu for all users
    menu = []
    
    # Tenant (USER) - simplified menu
    if user.role == UserRole.USER:
        menu = [
            {"label": "My Case", "path": "/tenant", "icon": "📁"},
            {"label": "Documents", "path": "/documents", "icon": "📄"},
            {"label": "Timeline", "path": "/timeline", "icon": "📅"},
            {"label": "Get Help", "path": "/tenant/help", "icon": "🆘"},
            {"label": "AI Assistant", "path": "/tenant/copilot", "icon": "🤖"},
        ]
    
    # Advocate - case management focus
    elif user.role == UserRole.ADVOCATE:
        menu = [
            {"label": "Dashboard", "path": "/advocate", "icon": "📊"},
            {"label": "Documents", "path": "/documents", "icon": "📄"},
            {"label": "Timeline", "path": "/timeline", "icon": "📅"},
            {"label": "My Clients", "path": "/advocate/clients", "icon": "👥"},
            {"label": "Case Queue", "path": "/advocate/queue", "icon": "📋"},
            {"label": "New Intake", "path": "/advocate/intake", "icon": "➕"},
        ]
    
    # Legal (Attorney) - full legal tools
    elif user.role == UserRole.LEGAL:
        menu = [
            {"label": "Dashboard", "path": "/legal", "icon": "⚖️"},
            {"label": "Documents", "path": "/documents", "icon": "📄"},
            {"label": "Timeline", "path": "/timeline", "icon": "📅"},
            {"label": "Case Files", "path": "/legal/cases", "icon": "📁"},
            {"label": "Court Filings", "path": "/legal/filings", "icon": "🏛️"},
            {"divider": True},
            {"label": "Privileged Notes", "path": "/legal/privileged", "icon": "🔒", "badge": "PRIV"},
            {"label": "Conflict Check", "path": "/legal/conflicts", "icon": "🧭"},
            {"divider": True},
            {"label": "Legal Research", "path": "/law-library", "icon": "🔍"},
            {"label": "Law Library", "path": "/law-library", "icon": "📚"},
        ]
    
    # Admin - system management
    elif user.role == UserRole.ADMIN:
        menu = [
            {"label": "Dashboard", "path": "/admin", "icon": "📊"},
            {"label": "Documents", "path": "/documents", "icon": "📄"},
            {"label": "Timeline", "path": "/timeline", "icon": "📅"},
            {"label": "Mission Control", "path": "/admin/mission-control", "icon": "🎯"},
            {"label": "GUI Hub", "path": "/admin/gui", "icon": "🗺️"},
            {"label": "Mode Selector", "path": "/admin/mode-selector", "icon": "⚙️"},
            {"label": "Easy Settings", "path": "/admin/easy-mode", "icon": "👶"},
            {"divider": True},
            {"label": "Docs Hub", "path": "/admin/docs", "icon": "📚"},
            {"label": "All Features", "path": "/dashboard", "icon": "🔧"},
        ]
    
    return {
        "menu": menu,
        "role": user.role.value,
        "role_display": get_role_metadata(user.role)["display_name"],
    }
