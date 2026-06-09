"""
Admin Console Router
Phase 4: Analytics, Automation & Advanced Admin

Protected by ADMIN role. All routes require user to have UserRole.ADMIN.

Phase 4 Features:
- Analytics dashboard (signup funnel, retention, feature usage)
- System configuration (tiers, modules, feature flags)
- Content management (help articles, law library)
- Audit logging and compliance
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

from app.core.security import require_role, ACTIVE_SESSIONS, get_metrics
from app.core.user_context import UserRole, UserContext, StorageProvider
from app.core.utc import utc_now
from app.core.navigation import navigation
from app.core.semptify_internal_sdk import (
    get_module_status, 
    module_registry, 
    ProductTier,
    ModuleCapability,
)

logger = logging.getLogger(__name__)

# Stealth admin guard - returns 404 (not 403) to hide admin API existence
async def _stealth_admin(request: Request) -> UserContext:
    """
    Security: Returns 404 Not Found instead of 403 Forbidden.
    This prevents attackers from discovering admin endpoints exist.
    """
    from app.core.security import get_current_user
    
    user = await get_current_user(request)
    
    # No user = 404 (looks like endpoint doesn't exist)
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Not admin = 404 (looks like endpoint doesn't exist)
    if user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin {user.user_id[:6]}... attempted admin API access to {request.url.path}")
        raise HTTPException(status_code=404, detail="Not Found")
    
    return user

# Admin role guard (legacy - returns 403)
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(prefix="/admin-console", tags=["Admin Console"])

# =============================================================================
# Phase 3: Runtime Configuration Store
# =============================================================================

# In-memory runtime configuration (would be DB-backed in production)
_RUNTIME_CONFIG = {
    "enabled_tiers": ["core", "extended", "admin"],  # Default enabled tiers
    "disabled_modules": [],  # List of module names disabled at runtime
    "feature_flags": {
        "new_onboarding": False,
        "beta_analytics": False,
        "experimental_ai": False,
    },
    "system_settings": {
        "max_upload_size_mb": 50,
        "session_timeout_hours": 24,
        "rate_limit_requests_per_min": 60,
    },
}


@router.get("/panel", response_class=HTMLResponse)
async def admin_panel(user: UserContext = Depends(_stealth_admin)):
    """Redirect stub panel to real dashboard."""
    return RedirectResponse(url="/admin/dashboard.html")


@router.get("/health")
async def health_check(user: UserContext = Depends(_stealth_admin)):
    """Admin-only health check with system status."""
    return {
        "status": "admin console online",
        "user_id": user.user_id if user else None,
        "role": user.role.value if user else None,
    }


# =============================================================================
# Admin API Endpoints (Phase 1)
# =============================================================================

@router.get("/api/users")
async def list_users(
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    active_only: bool = True,
    user: UserContext = Depends(_stealth_admin),
) -> dict:
    """
    List users from session store (active sessions).
    
    Query params:
        limit: Max results (default 100, max 500)
        offset: Pagination offset
        search: Optional search string for user_id or role
        active_only: Only show users with active sessions (default true)
    
    Returns:
        List of user records with session info
    """
    limit = min(limit, 500)
    logger.info(f"Admin {user.user_id[:6]}... listing users (limit={limit}, offset={offset}, search={search})")
    
    # Get all active sessions from memory store
    # Note: In production with Redis, this would scan Redis keys
    all_sessions = []
    for session_id, session in ACTIVE_SESSIONS.items():
        # Skip expired sessions
        if session.expires_at and session.expires_at < utc_now():
            continue
            
        user_data = {
            "user_id": session.user_id,
            "session_id": session.session_id[:8] + "...",  # Truncated for security
            "provider": session.provider,
            "role": session.role,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "is_active": True,
        }
        all_sessions.append(user_data)
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        all_sessions = [
            s for s in all_sessions 
            if search_lower in s["user_id"].lower() 
            or search_lower in s["role"].lower()
            or search_lower in s["provider"].lower()
        ]
    
    # Get unique users (a user may have multiple sessions)
    seen_users = set()
    unique_users = []
    for session in all_sessions:
        if session["user_id"] not in seen_users:
            seen_users.add(session["user_id"])
            # Count sessions for this user
            session_count = sum(1 for s in all_sessions if s["user_id"] == session["user_id"])
            session["session_count"] = session_count
            unique_users.append(session)
    
    total = len(unique_users)
    
    # Apply pagination
    paginated_users = unique_users[offset:offset + limit]
    
    return {
        "users": paginated_users,
        "total": total,
        "limit": limit,
        "offset": offset,
        "search": search,
        "source": "session_store",
        "note": "Showing active sessions. For full user database, query user_accounts table directly.",
    }


@router.get("/api/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin_user: UserContext = Depends(_stealth_admin),
) -> dict:
    """
    Get detailed information about a specific user from session store.
    Includes all active sessions and basic metadata.
    """
    logger.info(f"Admin {admin_user.user_id[:6]}... requesting details for user {user_id[:6]}...")
    
    # Find all sessions for this user
    user_sessions = []
    for session_id, session in ACTIVE_SESSIONS.items():
        if session.user_id == user_id:
            user_sessions.append({
                "session_id": session_id[:8] + "...",
                "provider": session.provider,
                "role": session.role,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "is_expired": session.expires_at and session.expires_at < utc_now(),
            })
    
    if not user_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found in active sessions"
        )
    
    # Get primary session info
    primary = user_sessions[0]
    
    return {
        "user_id": user_id,
        "provider": primary["provider"],
        "current_role": primary["role"],
        "active_sessions": len([s for s in user_sessions if not s["is_expired"]]),
        "total_sessions": len(user_sessions),
        "sessions": user_sessions,
        "first_seen": min(s["created_at"] for s in user_sessions if s["created_at"]),
        "admin_actions_available": ["impersonate", "reset_gates", "view_vault"],
    }


@router.post("/api/users/{user_id}/impersonate")
async def impersonate_user(
    user_id: str,
    admin_user: UserContext = Depends(_stealth_admin),
) -> dict:
    """
    Start impersonation session for user support.
    
    Creates a temporary session that allows admin to act as the user
    for debugging and support purposes. All actions are logged.
    """
    logger.warning(
        f"IMPERSONATION: Admin {admin_user.user_id} starting impersonation of {user_id}"
    )
    
    # Find user's active session
    target_session = None
    for session_id, session in ACTIVE_SESSIONS.items():
        if session.user_id == user_id and (not session.expires_at or session.expires_at > utc_now()):
            target_session = session
            break
    
    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for user {user_id}"
        )
    
    # Generate impersonation token (admin's session + target user context)
    impersonation_token = f"imp_{admin_user.user_id[:8]}_{user_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    # Log the impersonation attempt
    _log_admin_action(
        admin_user=admin_user,
        action="impersonate",
        target_user=user_id,
        details={"provider": target_session.provider, "role": target_session.role}
    )
    
    return {
        "status": "impersonation_ready",
        "target_user": user_id,
        "target_role": target_session.role,
        "target_provider": target_session.provider,
        "impersonation_token": impersonation_token,
        "landing_page": "/vault",  # Where to redirect after impersonation
        "warning": "You are now acting on behalf of this user. All actions will be logged.",
    }


@router.get("/api/system/status")
async def system_status(user: UserContext = Depends(_stealth_admin)) -> dict:
    """
    Get comprehensive system status for admin dashboard.
    Includes active sessions, metrics, and navigation info.
    """
    metrics = get_metrics()
    
    # Count active sessions
    active_count = sum(
        1 for s in ACTIVE_SESSIONS.values()
        if not s.expires_at or s.expires_at > utc_now()
    )
    
    # Count unique users
    unique_users = set(s.user_id for s in ACTIVE_SESSIONS.values())
    
    # Get navigation stages count
    nav_stages = len(navigation._stages) if hasattr(navigation, '_stages') else 0
    
    return {
        "status": "operational",
        "timestamp": utc_now().isoformat(),
        "sessions": {
            "active": active_count,
            "total_in_memory": len(ACTIVE_SESSIONS),
            "unique_users": len(unique_users),
        },
        "metrics": metrics,
        "navigation": {
            "stages_registered": nav_stages,
        },
    }


# =============================================================================
# Phase 2: User Management Endpoints
# =============================================================================

@router.post("/api/users/{user_id}/reset-gates")
async def reset_user_gates(
    user_id: str,
    gates: List[str],  # e.g., ["storage_connected", "vault_initialized"]
    admin_user: UserContext = Depends(require_admin),
) -> dict:
    """
    Reset onboarding gates for a user.
    Use with caution - forces user to re-complete onboarding steps.
    """
    logger.warning(
        f"GATE_RESET: Admin {admin_user.user_id} resetting gates {gates} for user {user_id}"
    )
    
    # Log the action
    _log_admin_action(
        admin_user=admin_user,
        action="reset_gates",
        target_user=user_id,
        details={"gates_reset": gates}
    )
    
    # TODO: Implement actual gate reset via gate service
    # This would clear the gates from wherever they're stored (DB/cache)
    
    return {
        "status": "gates_reset_requested",
        "user_id": user_id,
        "gates": gates,
        "note": "Gate reset not fully implemented - requires gate service integration",
    }


@router.get("/api/users/{user_id}/vault-summary")
async def get_user_vault_summary(
    user_id: str,
    admin_user: UserContext = Depends(require_admin),
) -> dict:
    """
    Get summary of user's vault contents for support purposes.
    Shows document count, types, and storage usage (metadata only).
    """
    logger.info(f"Admin {admin_user.user_id[:6]}... requesting vault summary for {user_id[:6]}...")
    
    # Find user's session to get provider info
    target_session = None
    for session in ACTIVE_SESSIONS.values():
        if session.user_id == user_id:
            target_session = session
            break
    
    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found in active sessions"
        )
    
    # Log the access (privacy-sensitive)
    _log_admin_action(
        admin_user=admin_user,
        action="view_vault_summary",
        target_user=user_id,
        details={"provider": target_session.provider}
    )
    
    # TODO: Implement vault service call to get actual document count
    # For now, return placeholder showing the structure
    return {
        "user_id": user_id,
        "provider": target_session.provider,
        "document_count": 0,  # Would be actual count from vault
        "storage_used_mb": 0,  # Would be actual usage
        "folders": [],  # Would be folder list
        "recent_documents": [],  # Would be recent docs metadata
        "note": "Vault summary not fully implemented - requires vault service integration",
    }


# =============================================================================
# Phase 2: Audit Log Endpoints
# =============================================================================

# In-memory audit log (production would use DB table)
_AUDIT_LOG: List[dict] = []


def _log_admin_action(admin_user: UserContext, action: str, target_user: str, details: dict):
    """Log an admin action to the audit log."""
    entry = {
        "timestamp": utc_now().isoformat(),
        "admin_user_id": admin_user.user_id,
        "admin_role": admin_user.role.value,
        "action": action,
        "target_user": target_user,
        "details": details,
    }
    _AUDIT_LOG.append(entry)
    logger.info(f"AUDIT: {action} by {admin_user.user_id} on {target_user}")
    
    # Keep log size manageable (keep last 10000 entries)
    if len(_AUDIT_LOG) > 10000:
        _AUDIT_LOG.pop(0)


@router.get("/api/audit")
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    admin_user: Optional[str] = None,
    target_user: Optional[str] = None,
    action: Optional[str] = None,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Get admin audit log.
    
    Query params:
        limit: Max results (default 100)
        offset: Pagination offset
        admin_user: Filter by admin user_id
        target_user: Filter by target user_id
        action: Filter by action type
    """
    limit = min(limit, 500)
    
    # Filter the audit log
    filtered = _AUDIT_LOG
    
    if admin_user:
        filtered = [e for e in filtered if admin_user in e["admin_user_id"]]
    
    if target_user:
        filtered = [e for e in filtered if target_user in e["target_user"]]
    
    if action:
        filtered = [e for e in filtered if e["action"] == action]
    
    # Sort by timestamp (newest first)
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)
    
    total = len(filtered)
    paginated = filtered[offset:offset + limit]
    
    return {
        "entries": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "available_actions": list(set(e["action"] for e in _AUDIT_LOG)),
    }


@router.get("/api/audit/actions")
async def get_audit_actions(user: UserContext = Depends(require_admin)) -> dict:
    """Get list of all audit action types that have been logged."""
    actions = list(set(e["action"] for e in _AUDIT_LOG))
    return {"actions": actions}


# =============================================================================
# Phase 3: System Configuration Endpoints
# =============================================================================

@router.get("/api/system/config")
async def get_system_config(user: UserContext = Depends(require_admin)) -> dict:
    """
    Get current system configuration.
    Includes enabled tiers, feature flags, and system settings.
    """
    return {
        "runtime_config": _RUNTIME_CONFIG,
        "timestamp": utc_now().isoformat(),
    }


@router.get("/api/system/modules")
async def get_modules_status(user: UserContext = Depends(require_admin)) -> dict:
    """
    Get complete module registry status.
    Shows all installed modules, their tiers, capabilities, and runtime status.
    """
    status = get_module_status()
    
    # Add runtime enabled/disabled status
    for module in status.get("installed_modules", []):
        module_name = module.get("manifest", {}).get("name", "")
        module["runtime_enabled"] = module_name not in _RUNTIME_CONFIG["disabled_modules"]
        module["tier_enabled"] = module.get("manifest", {}).get("tier", "") in _RUNTIME_CONFIG["enabled_tiers"]
    
    return {
        **status,
        "runtime_disabled": _RUNTIME_CONFIG["disabled_modules"],
        "enabled_tiers": _RUNTIME_CONFIG["enabled_tiers"],
    }


@router.post("/api/system/modules/{module_name}/toggle")
async def toggle_module(
    module_name: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Enable or disable a module at runtime.
    
    Note: This affects runtime routing only. Restart required for full effect.
    """
    # Check if module exists
    module = module_registry.get(module_name)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module {module_name} not found"
        )
    
    # Toggle the module
    currently_disabled = module_name in _RUNTIME_CONFIG["disabled_modules"]
    
    if currently_disabled:
        _RUNTIME_CONFIG["disabled_modules"].remove(module_name)
        new_status = "enabled"
    else:
        _RUNTIME_CONFIG["disabled_modules"].append(module_name)
        new_status = "disabled"
    
    # Log the action
    _log_admin_action(
        admin_user=user,
        action="toggle_module",
        target_user=module_name,
        details={"new_status": new_status, "tier": module.manifest.tier.value}
    )
    
    logger.warning(f"MODULE_TOGGLE: Admin {user.user_id} {new_status} module {module_name}")
    
    return {
        "module": module_name,
        "status": new_status,
        "manifest": module.manifest.to_dict(),
        "note": "Runtime toggle only. Restart for full effect.",
    }


@router.get("/api/system/tiers")
async def get_tiers(user: UserContext = Depends(require_admin)) -> dict:
    """Get all product tiers and their status."""
    return {
        "tiers": [
            {
                "name": t.value,
                "enabled": t.value in _RUNTIME_CONFIG["enabled_tiers"],
                "module_count": len(module_registry.list_by_tier(t)),
            }
            for t in ProductTier.all()
        ],
        "enabled_tiers": _RUNTIME_CONFIG["enabled_tiers"],
    }


@router.post("/api/system/tiers/{tier_name}/toggle")
async def toggle_tier(
    tier_name: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Enable or disable a product tier.
    
    Disabling a tier prevents new users from accessing those features.
    """
    # Validate tier name
    try:
        tier = ProductTier(tier_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier_name}. Valid: {[t.value for t in ProductTier.all()]}"
        )
    
    # CORE tier cannot be disabled
    if tier == ProductTier.CORE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CORE tier cannot be disabled"
        )
    
    # Toggle the tier
    currently_enabled = tier_name in _RUNTIME_CONFIG["enabled_tiers"]
    
    if currently_enabled:
        _RUNTIME_CONFIG["enabled_tiers"].remove(tier_name)
        new_status = "disabled"
    else:
        _RUNTIME_CONFIG["enabled_tiers"].append(tier_name)
        new_status = "enabled"
    
    # Log the action
    _log_admin_action(
        admin_user=user,
        action="toggle_tier",
        target_user=tier_name,
        details={"new_status": new_status}
    )
    
    logger.warning(f"TIER_TOGGLE: Admin {user.user_id} {new_status} tier {tier_name}")
    
    # Get affected modules
    affected_modules = [m.manifest.name for m in module_registry.list_by_tier(tier)]
    
    return {
        "tier": tier_name,
        "status": new_status,
        "affected_modules": affected_modules,
        "affected_count": len(affected_modules),
    }


@router.get("/api/system/feature-flags")
async def get_feature_flags(user: UserContext = Depends(require_admin)) -> dict:
    """Get all feature flags and their current values."""
    return {
        "feature_flags": _RUNTIME_CONFIG["feature_flags"],
        "timestamp": utc_now().isoformat(),
    }


@router.post("/api/system/feature-flags/{flag_name}")
async def set_feature_flag(
    flag_name: str,
    value: bool,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Set a feature flag value."""
    # Create flag if it doesn't exist
    if flag_name not in _RUNTIME_CONFIG["feature_flags"]:
        logger.info(f"Creating new feature flag: {flag_name}")
    
    old_value = _RUNTIME_CONFIG["feature_flags"].get(flag_name)
    _RUNTIME_CONFIG["feature_flags"][flag_name] = value
    
    # Log the action
    _log_admin_action(
        admin_user=user,
        action="set_feature_flag",
        target_user=flag_name,
        details={"old_value": old_value, "new_value": value}
    )
    
    logger.warning(f"FEATURE_FLAG: Admin {user.user_id} set {flag_name}={value}")
    
    return {
        "flag": flag_name,
        "value": value,
        "old_value": old_value,
    }


@router.get("/api/system/settings")
async def get_system_settings(user: UserContext = Depends(require_admin)) -> dict:
    """Get system settings."""
    return {
        "settings": _RUNTIME_CONFIG["system_settings"],
    }


@router.post("/api/system/settings/{setting_name}")
async def set_system_setting(
    setting_name: str,
    value: Any,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Set a system setting."""
    old_value = _RUNTIME_CONFIG["system_settings"].get(setting_name)
    _RUNTIME_CONFIG["system_settings"][setting_name] = value
    
    # Log the action
    _log_admin_action(
        admin_user=user,
        action="set_system_setting",
        target_user=setting_name,
        details={"old_value": old_value, "new_value": value}
    )
    
    logger.warning(f"SYSTEM_SETTING: Admin {user.user_id} set {setting_name}={value}")
    
    return {
        "setting": setting_name,
        "value": value,
        "old_value": old_value,
    }


# =============================================================================
# Phase 3: Content Management Endpoints
# =============================================================================

# In-memory content store (would be DB-backed in production)
_CONTENT_STORE = {
    "help_articles": {},
    "law_library": {},
    "letter_templates": {},
}


@router.get("/api/content/help-articles")
async def list_help_articles(
    category: Optional[str] = None,
    user: UserContext = Depends(require_admin),
) -> dict:
    """List all help articles."""
    articles = _CONTENT_STORE["help_articles"]
    
    if category:
        articles = {k: v for k, v in articles.items() if v.get("category") == category}
    
    return {
        "articles": [
            {
                "id": k,
                "title": v.get("title"),
                "category": v.get("category"),
                "updated_at": v.get("updated_at"),
                "author": v.get("author"),
            }
            for k, v in articles.items()
        ],
        "total": len(articles),
    }


@router.get("/api/content/help-articles/{article_id}")
async def get_help_article(
    article_id: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Get a specific help article."""
    article = _CONTENT_STORE["help_articles"].get(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found"
        )
    return {"id": article_id, **article}


@router.post("/api/content/help-articles")
async def create_help_article(
    article_id: str,
    title: str,
    content: str,
    category: str = "general",
    user: UserContext = Depends(require_admin),
) -> dict:
    """Create or update a help article."""
    is_new = article_id not in _CONTENT_STORE["help_articles"]
    
    _CONTENT_STORE["help_articles"][article_id] = {
        "title": title,
        "content": content,
        "category": category,
        "author": user.user_id,
        "created_at": utc_now().isoformat() if is_new else _CONTENT_STORE["help_articles"][article_id].get("created_at"),
        "updated_at": utc_now().isoformat(),
    }
    
    action = "create_help_article" if is_new else "update_help_article"
    _log_admin_action(
        admin_user=user,
        action=action,
        target_user=article_id,
        details={"title": title, "category": category}
    )
    
    return {
        "id": article_id,
        "action": "created" if is_new else "updated",
        "article": _CONTENT_STORE["help_articles"][article_id],
    }


@router.delete("/api/content/help-articles/{article_id}")
async def delete_help_article(
    article_id: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Delete a help article."""
    if article_id not in _CONTENT_STORE["help_articles"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found"
        )
    
    article = _CONTENT_STORE["help_articles"].pop(article_id)
    
    _log_admin_action(
        admin_user=user,
        action="delete_help_article",
        target_user=article_id,
        details={"title": article.get("title")}
    )
    
    return {"id": article_id, "action": "deleted", "deleted_article": article}


@router.get("/api/content/law-library")
async def list_law_library_entries(
    jurisdiction: Optional[str] = None,
    user: UserContext = Depends(require_admin),
) -> dict:
    """List law library entries."""
    entries = _CONTENT_STORE["law_library"]
    
    if jurisdiction:
        entries = {k: v for k, v in entries.items() if v.get("jurisdiction") == jurisdiction}
    
    return {
        "entries": [
            {
                "id": k,
                "title": v.get("title"),
                "jurisdiction": v.get("jurisdiction"),
                "topic": v.get("topic"),
                "updated_at": v.get("updated_at"),
            }
            for k, v in entries.items()
        ],
        "total": len(entries),
    }


@router.post("/api/content/law-library")
async def create_law_library_entry(
    entry_id: str,
    title: str,
    content: str,
    jurisdiction: str,
    topic: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Create or update a law library entry."""
    is_new = entry_id not in _CONTENT_STORE["law_library"]
    
    _CONTENT_STORE["law_library"][entry_id] = {
        "title": title,
        "content": content,
        "jurisdiction": jurisdiction,
        "topic": topic,
        "author": user.user_id,
        "created_at": utc_now().isoformat() if is_new else _CONTENT_STORE["law_library"][entry_id].get("created_at"),
        "updated_at": utc_now().isoformat(),
    }
    
    action = "create_law_entry" if is_new else "update_law_entry"
    _log_admin_action(
        admin_user=user,
        action=action,
        target_user=entry_id,
        details={"title": title, "jurisdiction": jurisdiction}
    )
    
    return {
        "id": entry_id,
        "action": "created" if is_new else "updated",
        "entry": _CONTENT_STORE["law_library"][entry_id],
    }


@router.get("/api/content/letter-templates")
async def list_letter_templates(
    category: Optional[str] = None,
    user: UserContext = Depends(require_admin),
) -> dict:
    """List letter templates."""
    templates = _CONTENT_STORE["letter_templates"]
    
    if category:
        templates = {k: v for k, v in templates.items() if v.get("category") == category}
    
    return {
        "templates": [
            {
                "id": k,
                "name": v.get("name"),
                "category": v.get("category"),
                "description": v.get("description"),
            }
            for k, v in templates.items()
        ],
        "total": len(templates),
    }


@router.post("/api/content/letter-templates")
async def create_letter_template(
    template_id: str,
    name: str,
    content: str,
    category: str = "general",
    description: str = "",
    variables: Optional[List[str]] = None,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Create or update a letter template."""
    is_new = template_id not in _CONTENT_STORE["letter_templates"]
    
    _CONTENT_STORE["letter_templates"][template_id] = {
        "name": name,
        "content": content,
        "category": category,
        "description": description,
        "variables": variables or [],
        "author": user.user_id,
        "created_at": utc_now().isoformat() if is_new else _CONTENT_STORE["letter_templates"][template_id].get("created_at"),
        "updated_at": utc_now().isoformat(),
    }
    
    action = "create_template" if is_new else "update_template"
    _log_admin_action(
        admin_user=user,
        action=action,
        target_user=template_id,
        details={"name": name, "category": category}
    )
    
    return {
        "id": template_id,
        "action": "created" if is_new else "updated",
        "template": _CONTENT_STORE["letter_templates"][template_id],
    }


# =============================================================================
# Phase 4: Analytics Dashboard
# =============================================================================

# In-memory analytics store (production: time-series DB like InfluxDB/TimescaleDB)
_ANALYTICS_EVENTS: List[dict] = []
_DAILY_METRICS: Dict[str, dict] = {}


def _track_event(event_type: str, user_id: Optional[str] = None, metadata: Optional[dict] = None):
    """Track an analytics event."""
    event = {
        "timestamp": utc_now().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "metadata": metadata or {},
    }
    _ANALYTICS_EVENTS.append(event)
    
    # Keep memory bounded (last 50k events)
    if len(_ANALYTICS_EVENTS) > 50000:
        _ANALYTICS_EVENTS.pop(0)


@router.get("/api/analytics/overview")
async def get_analytics_overview(
    days: int = 30,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Get high-level analytics overview.
    
    Returns signup funnel, active users, document stats.
    """
    cutoff = utc_now() - datetime.timedelta(days=days)
    
    # Count events in period
    recent_events = [e for e in _ANALYTICS_EVENTS if datetime.fromisoformat(e["timestamp"]) > cutoff]
    
    # User signup funnel (from session data)
    active_sessions = [
        s for s in ACTIVE_SESSIONS.values()
        if s.created_at and s.created_at > cutoff
    ]
    
    unique_users = set(s.user_id for s in active_sessions)
    by_role = {}
    for s in active_sessions:
        role = s.role
        by_role[role] = by_role.get(role, 0) + 1
    
    return {
        "period_days": days,
        "generated_at": utc_now().isoformat(),
        "users": {
            "total_active_sessions": len(active_sessions),
            "unique_users": len(unique_users),
            "by_role": by_role,
        },
        "events": {
            "total_tracked": len(recent_events),
            "by_type": _count_by_key(recent_events, "event_type"),
        },
        "funnel": {
            "step_1_storage_connected": len([s for s in active_sessions if s.provider]),
            "step_2_vault_initialized": len([s for s in active_sessions if s.user_id]),
            "note": "Full funnel requires gate tracking integration",
        },
    }


@router.get("/api/analytics/signup-funnel")
async def get_signup_funnel(
    days: int = 30,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Detailed signup funnel analysis.
    """
    cutoff = utc_now() - datetime.timedelta(days=days)
    
    # Analyze session creation over time
    daily_signups = {}
    for s in ACTIVE_SESSIONS.values():
        if s.created_at and s.created_at > cutoff:
            day = s.created_at.strftime("%Y-%m-%d")
            daily_signups[day] = daily_signups.get(day, 0) + 1
    
    return {
        "period_days": days,
        "total_new_sessions": sum(daily_signups.values()),
        "daily_breakdown": daily_signups,
        "by_provider": _count_by_key(
            [s for s in ACTIVE_SESSIONS.values() if s.created_at and s.created_at > cutoff],
            "provider"
        ),
        "by_role": _count_by_key(
            [s for s in ACTIVE_SESSIONS.values() if s.created_at and s.created_at > cutoff],
            "role"
        ),
    }


@router.get("/api/analytics/feature-usage")
async def get_feature_usage(
    days: int = 30,
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    Feature usage metrics from tracked events.
    """
    cutoff = utc_now() - datetime.timedelta(days=days)
    recent_events = [
        e for e in _ANALYTICS_EVENTS
        if datetime.fromisoformat(e["timestamp"]) > cutoff
    ]
    
    # Count by event type (which maps to features)
    feature_counts = _count_by_key(recent_events, "event_type")
    
    return {
        "period_days": days,
        "total_events": len(recent_events),
        "feature_usage": feature_counts,
        "top_features": sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:10],
    }


@router.get("/api/analytics/retention")
async def get_retention_metrics(
    user: UserContext = Depends(require_admin),
) -> dict:
    """
    User retention metrics.
    """
    now = utc_now()
    
    # Group sessions by user and find last activity
    user_last_seen = {}
    for s in ACTIVE_SESSIONS.values():
        last_seen = s.created_at  # Using creation as proxy
        if s.user_id in user_last_seen:
            if last_seen and last_seen > user_last_seen[s.user_id]:
                user_last_seen[s.user_id] = last_seen
        else:
            user_last_seen[s.user_id] = last_seen
    
    # Calculate retention buckets
    day_1 = now - datetime.timedelta(days=1)
    day_7 = now - datetime.timedelta(days=7)
    day_30 = now - datetime.timedelta(days=30)
    
    active_1d = sum(1 for ts in user_last_seen.values() if ts and ts > day_1)
    active_7d = sum(1 for ts in user_last_seen.values() if ts and ts > day_7)
    active_30d = sum(1 for ts in user_last_seen.values() if ts and ts > day_30)
    
    total_users = len(user_last_seen)
    
    return {
        "total_users": total_users,
        "active_last_1d": active_1d,
        "active_last_7d": active_7d,
        "active_last_30d": active_30d,
        "retention_rate_7d": round(active_7d / total_users * 100, 1) if total_users else 0,
        "retention_rate_30d": round(active_30d / total_users * 100, 1) if total_users else 0,
    }


def _count_by_key(items: List[dict], key: str) -> dict:
    """Helper: count items by a key value."""
    counts = {}
    for item in items:
        value = item.get(key, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts
