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
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging

from app.core.security import require_role, ACTIVE_SESSIONS, get_metrics, update_session_impersonation, get_session
from app.core.user_context import UserRole, UserContext, StorageProvider
from app.core.utc import utc_now
from app.core.navigation import navigation
from app.core.semptify_internal_sdk import (
    get_module_status, 
    module_registry, 
    ProductTier,
    ModuleCapability,
)
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Stealth admin guard - returns 404 (not 403) to hide admin API existence
async def _stealth_admin(request: Request) -> UserContext:
    """
    Security: Returns 404 Not Found instead of 403 Forbidden.
    This prevents attackers from discovering admin endpoints exist.

    Accepts either:
    1. Normal user session with UserRole.ADMIN (via OAuth)
    2. Admin token via X-Admin-Token header or admin_token query param
    """
    from app.core.security import get_current_user, get_admin_token_from_request, get_admin_token_store
    from app.core.rate_limit import limiter
    from app.core.utc import utc_now
    from datetime import timedelta

    # Try admin token first (for testing/dev)
    admin_token = get_admin_token_from_request(request)
    if admin_token:
        # Rate limit admin token attempts to prevent brute force
        # Use IP-based rate limiting (5 attempts per minute per IP)
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_key = f"admin_token:{client_ip}"

        # Simple in-memory rate limit check
        if not hasattr(_stealth_admin, "_rate_limit_cache"):
            _stealth_admin._rate_limit_cache = {}

        now = utc_now()
        cache = _stealth_admin._rate_limit_cache

        # Clean old entries
        cache[rate_limit_key] = [t for t in cache.get(rate_limit_key, []) if now - t < timedelta(minutes=1)]

        # Check rate limit
        if len(cache.get(rate_limit_key, [])) >= 5:
            logger.warning(f"Admin token rate limit exceeded for IP {client_ip}")
            raise HTTPException(status_code=404, detail="Not Found")

        # Record this attempt
        cache.setdefault(rate_limit_key, []).append(now)

        admin_store = get_admin_token_store()
        admin = admin_store.validate_admin_token(admin_token)
        if admin:
            # Create a synthetic admin user context
            return UserContext(
                user_id=admin.get("id", "admin"),
                role=UserRole.ADMIN,
                storage_provider=StorageProvider.LOCAL,
                email="admin@semptify.org",
                display_name="Admin",
            )

    # Try normal user session
    try:
        user = await get_current_user(request)
    except Exception as e:
        logger.warning(f"Admin API auth failed: {e}")
        raise HTTPException(status_code=404, detail="Not Found")

    # No user = 404 (looks like endpoint doesn't exist)
    if not user:
        logger.warning("Admin API access: No user found")
        raise HTTPException(status_code=404, detail="Not Found")

    # Not admin = 404 (looks like endpoint doesn't exist)
    if user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin {user.user_id[:6]}... attempted admin API access to {request.url.path}")
        raise HTTPException(status_code=404, detail="Not Found")

    return user

# Admin role guard (legacy - returns 403)
require_admin = require_role(UserRole.ADMIN)

router = APIRouter(tags=["Admin Console"])

# =============================================================================
# Phase 3: Runtime Configuration Store
# =============================================================================

# In-memory runtime configuration (would be DB-backed in production)
_RUNTIME_CONFIG = {
    "enabled_tiers": ["core", "extended", "advocate", "admin", "research", "dev"],  # ALL tiers active
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Start impersonation session for a user (admin only).

    Checks that a valid relationship exists (ADMIN_OVERRIDE) then sets
    acting_as on the admin's own session so every subsequent request from
    that admin sees the target user's context.
    """
    from app.core.security import can_access

    # Verify relationship in DB (admin_override row must exist, or role is admin)
    allowed = await can_access(
        from_user_id=admin_user.user_id,
        to_user_id=user_id,
        db=db,
        relationship_type="admin",
    )
    # Admins always get ADMIN_OVERRIDE access — if no row exists yet, still allow
    # but log it so we can backfill the relationship row
    if not allowed and getattr(admin_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active relationship found permitting access to this user.",
        )

    # Find the target user's active session to read their role/provider
    target_session = None
    for session_id, session in ACTIVE_SESSIONS.items():
        if session.user_id == user_id and (not session.expires_at or session.expires_at > utc_now()):
            target_session = session
            break

    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found for this user. They must be logged in.",
        )

    # Set acting_as on the admin's own session
    if not admin_user.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin session ID not found — cannot set impersonation state.",
        )

    update_session_impersonation(
        session_id=admin_user.session_id,
        acting_as=user_id,
        acting_as_role=target_session.role,
    )

    logger.warning(
        "IMPERSONATION START: admin=%s acting_as=%s role=%s",
        admin_user.user_id[:8], user_id[:8], target_session.role,
    )

    await _log_admin_action(
        admin_user=admin_user,
        action="impersonate_start",
        target_user=user_id,
        details={"target_role": target_session.role},
    )

    return {
        "status": "impersonating",
        "acting_as": user_id,
        "acting_as_role": target_session.role,
        "warning": "You are now acting on behalf of this user. All actions are logged.",
    }


@router.post("/api/users/{user_id}/stop-impersonation")
async def stop_impersonation(
    user_id: str,
    admin_user: UserContext = Depends(_stealth_admin),
) -> dict:
    """Stop impersonating and return to the admin's own context."""
    if not admin_user.session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID not found.")

    update_session_impersonation(
        session_id=admin_user.session_id,
        acting_as=None,
        acting_as_role=None,
    )

    logger.warning(
        "IMPERSONATION STOP: admin=%s was acting_as=%s",
        admin_user.user_id[:8], user_id[:8],
    )

    await _log_admin_action(
        admin_user=admin_user,
        action="impersonate_stop",
        target_user=user_id,
        details={},
    )

    return {"status": "impersonation_ended"}


@router.get("/api/system/status")
async def system_status(user: UserContext = Depends(_stealth_admin)) -> dict:
    """
    Get comprehensive system status for admin dashboard.
    Includes active sessions, metrics, modules, tiers, and navigation info.
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
    
    # Get module counts by tier
    tier_module_counts = {
        t.value: len(module_registry.list_by_tier(t))
        for t in ProductTier.all()
    }
    
    # Calculate total active modules (from enabled tiers, not disabled)
    total_modules = sum(
        count for tier, count in tier_module_counts.items()
        if tier in _RUNTIME_CONFIG["enabled_tiers"]
    )
    
    return {
        "status": "operational",
        "mode": "full_live",
        "timestamp": utc_now().isoformat(),
        "sessions": {
            "active": active_count,
            "total_in_memory": len(ACTIVE_SESSIONS),
            "unique_users": len(unique_users),
        },
        "tiers": {
            "enabled": _RUNTIME_CONFIG["enabled_tiers"],
            "all_tiers_active": len(_RUNTIME_CONFIG["enabled_tiers"]) == len(ProductTier.all()),
            "module_counts_by_tier": tier_module_counts,
        },
        "modules": {
            "total_active": total_modules,
            "runtime_disabled": len(_RUNTIME_CONFIG["disabled_modules"]),
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
    gates: List[str],
    admin_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset onboarding gates for a user.
    Use with caution - forces user to re-complete onboarding steps.
    """
    logger.warning(
        f"GATE_RESET: Admin {admin_user.user_id} resetting gates {gates} for user {user_id}"
    )
    
    # Import gate functions
    from app.modules.onboarding.gates import get_user_gates, mark_gate
    
    # Get current gates before reset
    current_gates = await get_user_gates(db, user_id)
    
    # Reset requested gates by removing them from completed_groups
    # Note: Gates are stored as comma-separated values in User.completed_groups
    from app.models.models import User
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Remove the specified gates from completed_groups
    existing_gates = set(g.strip() for g in (user.completed_groups or "").split(",") if g.strip())
    removed_gates = existing_gates.intersection(set(gates))
    remaining_gates = existing_gates - set(gates)
    
    user.completed_groups = ",".join(sorted(remaining_gates)) if remaining_gates else None
    await db.commit()
    
    # Log the action
    await _log_admin_action(
        admin_user=admin_user,
        action="reset_gates",
        target_user=user_id,
        details={
            "gates_reset": list(removed_gates),
            "gates_before": list(current_gates),
            "gates_after": list(remaining_gates),
        },
        db=db,
    )
    
    return {
        "status": "gates_reset",
        "user_id": user_id,
        "gates_removed": list(removed_gates),
        "gates_remaining": list(remaining_gates),
        "live_data": True,
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
    await _log_admin_action(
        admin_user=admin_user,
        action="view_vault_summary",
        target_user=user_id,
        details={"provider": target_session.provider},
    )
    
    # Get live vault data from vault service
    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()
        docs = await vault_service.get_user_documents(user_id)
        
        # Calculate storage stats
        total_size_bytes = sum(doc.file_size for doc in docs if doc.file_size)
        storage_used_mb = round(total_size_bytes / (1024 * 1024), 2)
        
        # Get unique folder paths from document storage paths
        folders = list(set(
            doc.storage_path.split('/')[0] if '/' in doc.storage_path else 'root'
            for doc in docs if hasattr(doc, 'storage_path') and doc.storage_path
        )) if docs else []
        
        # Recent documents (last 5)
        recent_docs = sorted(
            docs,
            key=lambda d: d.uploaded_at if hasattr(d, 'uploaded_at') and d.uploaded_at else datetime.min,
            reverse=True
        )[:5] if docs else []
        
        recent_documents = [
            {
                "vault_id": doc.vault_id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "file_size": doc.file_size,
                "uploaded_at": doc.uploaded_at.isoformat() if hasattr(doc.uploaded_at, 'isoformat') else str(doc.uploaded_at),
            }
            for doc in recent_docs
        ]
        
        return {
            "user_id": user_id,
            "provider": target_session.provider,
            "document_count": len(docs),
            "storage_used_mb": storage_used_mb,
            "folders": folders,
            "recent_documents": recent_documents,
            "document_types": {
                doc_type: sum(1 for d in docs if d.document_type == doc_type)
                for doc_type in set(d.document_type for d in docs if d.document_type)
            } if docs else {},
            "live_data": True,
            "timestamp": utc_now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch vault summary for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vault data: {str(e)}"
        )


# =============================================================================
# Phase 2: Audit Log Endpoints
# =============================================================================

async def _log_admin_action(
    admin_user: UserContext, 
    action: str, 
    target_user: str, 
    details: dict,
    db: AsyncSession = None,
    request: Request = None,
) -> None:
    """
    Log an admin action to the database audit log.
    
    Args:
        admin_user: The admin performing the action
        action: Action type (e.g., "reset_gates", "view_vault_summary")
        target_user: Target user_id or resource identifier
        details: JSON-serializable details dict
        db: Optional DB session (if None, creates new session)
        request: Optional FastAPI request for IP/UA logging
    """
    from app.models.models import AdminAuditLog
    from app.core.database import get_db_session
    
    # Extract client info if request provided
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent") if request.headers else None
    
    entry = AdminAuditLog(
        admin_user_id=admin_user.user_id,
        admin_role=admin_user.role.value,
        action=action,
        target_user=target_user if target_user else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=utc_now(),
    )
    
    # Write to DB
    if db:
        db.add(entry)
        await db.commit()
    else:
        async with get_db_session() as session:
            session.add(entry)
            await session.commit()
    
    logger.info(f"AUDIT: {action} by {admin_user.user_id} on {target_user}")


@router.get("/api/audit")
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    admin_user: Optional[str] = None,
    target_user: Optional[str] = None,
    action: Optional[str] = None,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get admin audit log from database.
    
    Query params:
        limit: Max results (default 100)
        offset: Pagination offset
        admin_user: Filter by admin user_id
        target_user: Filter by target user_id
        action: Filter by action type
    """
    from app.models.models import AdminAuditLog
    from sqlalchemy import select, func, desc
    
    limit = min(limit, 500)
    
    # Build query with filters
    query = select(AdminAuditLog)
    
    if admin_user:
        query = query.where(AdminAuditLog.admin_user_id.ilike(f"%{admin_user}%"))
    
    if target_user:
        query = query.where(AdminAuditLog.target_user.ilike(f"%{target_user}%"))
    
    if action:
        query = query.where(AdminAuditLog.action == action)
    
    # Count total matching records
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results sorted by timestamp desc
    query = query.order_by(desc(AdminAuditLog.timestamp)).offset(offset).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Format entries
    formatted_entries = [
        {
            "log_id": e.log_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "admin_user_id": e.admin_user_id,
            "admin_role": e.admin_role,
            "action": e.action,
            "target_user": e.target_user,
            "details": e.details,
            "ip_address": e.ip_address,
        }
        for e in entries
    ]
    
    # Get distinct action types for filtering
    actions_query = select(AdminAuditLog.action).distinct()
    actions_result = await db.execute(actions_query)
    available_actions = [a for a in actions_result.scalars().all() if a]
    
    return {
        "entries": formatted_entries,
        "total": total,
        "limit": limit,
        "offset": offset,
        "available_actions": available_actions,
        "live_data": True,
    }


@router.get("/api/audit/actions")
async def get_audit_actions(
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get list of all audit action types from database."""
    from app.models.models import AdminAuditLog
    from sqlalchemy import select
    
    query = select(AdminAuditLog.action).distinct()
    result = await db.execute(query)
    actions = [a for a in result.scalars().all() if a]
    
    return {"actions": actions, "live_data": True}


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
    db: AsyncSession = Depends(get_db),
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
    await _log_admin_action(
        admin_user=user,
        action="toggle_module",
        target_user=module_name,
        details={"new_status": new_status, "tier": module.manifest.tier.value},
        db=db,
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
    db: AsyncSession = Depends(get_db),
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
    await _log_admin_action(
        admin_user=user,
        action="toggle_tier",
        target_user=tier_name,
        details={"new_status": new_status},
        db=db,
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
    from app.core.features import features as _features
    return {
        "feature_flags": await _features.get_all_flags(),
        "status": await _features.get_status(),
        "timestamp": utc_now().isoformat(),
    }


@router.post("/api/system/feature-flags/{flag_name}")
async def set_feature_flag(
    flag_name: str,
    value: bool,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set a feature flag value — persists to PostgreSQL."""
    from app.core.features import features as _features
    all_flags = await _features.get_all_flags()
    old_value = all_flags.get(flag_name, {}).get("enabled")
    await _features.set_enabled(flag_name, value, updated_by=user.user_id)
    await _log_admin_action(
        admin_user=user,
        action="set_feature_flag",
        target_user=flag_name,
        details={"old_value": old_value, "new_value": value},
        db=db,
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
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set a system setting."""
    old_value = _RUNTIME_CONFIG["system_settings"].get(setting_name)
    _RUNTIME_CONFIG["system_settings"][setting_name] = value
    
    # Log the action
    await _log_admin_action(
        admin_user=user,
        action="set_system_setting",
        target_user=setting_name,
        details={"old_value": old_value, "new_value": value},
        db=db,
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
    await _log_admin_action(
        admin_user=user,
        action=action,
        target_user=article_id,
        details={"title": title, "category": category},
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
    
    await _log_admin_action(
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
    await _log_admin_action(
        admin_user=user,
        action=action,
        target_user=entry_id,
        details={"title": title, "jurisdiction": jurisdiction},
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
    await _log_admin_action(
        admin_user=user,
        action=action,
        target_user=template_id,
        details={"name": name, "category": category},
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


# =============================================================================
# API Key / Environment Variable Management
# =============================================================================

_MANAGED_KEYS = [
    ("Storage OAuth",   ["GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET",
                         "DROPBOX_APP_KEY", "DROPBOX_APP_SECRET",
                         "ONEDRIVE_CLIENT_ID", "ONEDRIVE_CLIENT_SECRET"]),
    ("AI Providers",    ["ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY",
                         "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"]),
    ("Azure AI",        ["AZURE_AI_ENDPOINT", "AZURE_AI_KEY1", "AZURE_AI_KEY2",
                         "AZURE_AI_REGION", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]),
    ("Cloudflare R2",   ["STORAGE_ENDPOINT", "STORAGE_ACCESS_KEY", "STORAGE_SECRET_KEY"]),
    ("Email",           ["RESEND_API_KEY", "FROM_EMAIL", "SUPPORT_EMAIL"]),
    ("Research APIs",   ["NEWS_API_KEY", "ASSESSOR_API_KEY", "RECORDER_API_KEY",
                         "UCC_API_KEY", "BANKRUPTCY_API_KEY", "SOS_API_KEY",
                         "DISPATCH_API_KEY", "INSURANCE_API_KEY"]),
    ("Core System",     ["SECRET_KEY", "DATABASE_URL", "PUBLIC_BASE_URL",
                         "SECURITY_MODE", "GITHUB_TOKEN", "INVITE_CODES", "TSA_URL"]),
]
_ALL_MANAGED_KEYS = [k for _, keys in _MANAGED_KEYS for k in keys]


@router.get("/api/env-status")
async def env_status(user: UserContext = Depends(_stealth_admin)) -> dict:
    """
    Return status of all managed env vars — names and set/unset state only.
    Values are NEVER returned; only whether each key is currently set.
    """
    import os
    groups = []
    for group_name, keys in _MANAGED_KEYS:
        groups.append({
            "group": group_name,
            "keys": [
                {"key": k, "set": bool(os.environ.get(k, "").strip())}
                for k in keys
            ],
        })
    total = sum(len(keys) for _, keys in _MANAGED_KEYS)
    filled = sum(1 for k in _ALL_MANAGED_KEYS if os.environ.get(k, "").strip())
    return {"groups": groups, "total": total, "filled": filled}


@router.get("/api/system/env")
async def system_env(user: UserContext = Depends(_stealth_admin)) -> dict:
    """
    Alias for /api/env-status for compatibility with dashboard test functions.
    Returns env variable status (set/unset) only, not actual values for security.
    """
    import os
    env = {}
    for group_name, keys in _MANAGED_KEYS:
        for k in keys:
            env[k] = bool(os.environ.get(k, "").strip())
    return {"env": env}


@router.post("/api/env-update")
async def env_update(
    payload: Dict[str, Any],
    user: UserContext = Depends(_stealth_admin),
) -> dict:
    """
    Update one or more managed environment variables at runtime.
    Also writes the changes to the project .env file for persistence.

    Body: { "updates": { "KEY": "value", ... } }
    Only keys in _ALL_MANAGED_KEYS are accepted — all others are rejected.
    """
    import os
    from pathlib import Path

    updates: Dict[str, str] = payload.get("updates", {})
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    rejected = [k for k in updates if k not in _ALL_MANAGED_KEYS]
    if rejected:
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognised or disallowed keys: {', '.join(rejected)}"
        )

    # Apply to running process
    applied = []
    for key, value in updates.items():
        if not isinstance(value, str):
            continue
        os.environ[key] = value
        applied.append(key)
        logger.info("Admin %s updated env var: %s", user.user_id[:6], key)

    # Persist to .env file (project root)
    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    try:
        existing_lines: list[str] = []
        if env_path.exists():
            existing_lines = env_path.read_text(encoding="utf-8").splitlines()

        # Build a dict of existing entries
        env_dict: dict[str, str] = {}
        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, v = stripped.partition("=")
                env_dict[k.strip()] = v

        # Overwrite with new values
        for k, v in updates.items():
            env_dict[k] = v

        # Write back
        new_lines = [f"{k}={v}" for k, v in env_dict.items()]
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        persisted = True
    except Exception as exc:
        logger.warning("Could not write .env file: %s", exc)
        persisted = False

    return {
        "applied": applied,
        "persisted_to_env": persisted,
        "env_path": str(env_path) if persisted else None,
        "note": "Changes are live immediately. Restart is NOT required for runtime changes.",
    }


# =============================================================================
# Module Registry / Overlay System Endpoints
# =============================================================================

@router.get("/api/system/modules")
async def list_modules(user: UserContext = Depends(require_admin)) -> dict:
    """List all modules in the registry with their status."""
    from app.core.module_overlay import module_overlay
    modules = await module_overlay.list_modules()
    return {
        "modules": modules,
        "count": len(modules),
        "timestamp": utc_now().isoformat(),
    }


@router.get("/api/system/modules/{module_name}")
async def get_module_status(
    module_name: str,
    user: UserContext = Depends(require_admin),
) -> dict:
    """Get detailed status of a single module."""
    from app.core.module_overlay import module_overlay
    info = await module_overlay.get_module_status(module_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module {module_name} not found")
    return info


@router.post("/api/system/modules/{module_name}/toggle")
async def toggle_module(
    module_name: str,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle a module on/off. Creates registry entry if missing."""
    from app.core.module_overlay import module_overlay
    info = await module_overlay.get_module_status(module_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module {module_name} not found in registry")
    new_state = not info["is_enabled"]
    success = await module_overlay.set_module_enabled(module_name, new_state, updated_by=user.user_id)
    await _log_admin_action(
        admin_user=user,
        action="toggle_module",
        target_user=module_name,
        details={"enabled": new_state},
        db=db,
    )
    logger.warning(f"MODULE_TOGGLE: Admin {user.user_id} set {module_name} enabled={new_state}")
    return {"module": module_name, "enabled": new_state, "previous": info["is_enabled"]}


@router.post("/api/system/modules/{module_name}/dev-mode")
async def set_module_dev_mode(
    module_name: str,
    enabled: bool,
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enable/disable dev mode strict logging for a module."""
    from app.core.module_overlay import module_overlay
    info = await module_overlay.get_module_status(module_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module {module_name} not found")
    success = await module_overlay.set_dev_mode(module_name, enabled, updated_by=user.user_id)
    await _log_admin_action(
        admin_user=user,
        action="set_dev_mode",
        target_user=module_name,
        details={"dev_mode": enabled},
        db=db,
    )
    logger.warning(f"DEV_MODE: Admin {user.user_id} set {module_name} dev_mode={enabled}")
    return {"module": module_name, "dev_mode": enabled}


@router.post("/api/system/modules/{module_name}/status")
async def set_module_status(
    module_name: str,
    status: str,  # unknown | active | beta | deprecated | broken
    user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set module lifecycle status."""
    from app.core.module_overlay import module_overlay
    valid = {"unknown", "active", "beta", "deprecated", "broken"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    info = await module_overlay.get_module_status(module_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module {module_name} not found")
    await module_overlay.set_status(module_name, status, updated_by=user.user_id)
    await _log_admin_action(
        admin_user=user,
        action="set_module_status",
        target_user=module_name,
        details={"status": status},
        db=db,
    )
    logger.warning(f"MODULE_STATUS: Admin {user.user_id} set {module_name} status={status}")
    return {"module": module_name, "status": status}
