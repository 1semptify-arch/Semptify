"""
ModuleGateMiddleware — Role + Jurisdiction Module Activation
=============================================================

Controls which modules are active based on:
1. User role (tenant, advocate, legal, admin, etc.)
2. Jurisdiction (state, county, court system)

This enables geographic feature rollouts and role-based module gating.

Usage:
    from app.core.module_gate import ModuleGateMiddleware, get_module_access
    
    # Add to FastAPI app
    app.add_middleware(ModuleGateMiddleware)
    
    # Check access in routes
    @router.get("/some-feature")
    async def feature(request: Request):
        access = get_module_access(request)
        if not access.can_use("eviction_defense"):
            raise HTTPException(403, "Not available in your jurisdiction")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Set, Dict, List, Any
from enum import Enum

from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.user_context import UserRole
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class JurisdictionLevel(str, Enum):
    """Levels of jurisdiction granularity."""
    COUNTRY = "country"        # e.g., "US"
    STATE = "state"            # e.g., "ND", "MN"
    COUNTY = "county"          # e.g., "Cass County"
    COURT = "court"            # e.g., "East Central Judicial District"
    MUNICIPALITY = "municipality"  # e.g., "Fargo"


@dataclass(frozen=True)
class Jurisdiction:
    """Immutable jurisdiction identifier."""
    country: str = "US"
    state: Optional[str] = None
    county: Optional[str] = None
    court: Optional[str] = None
    municipality: Optional[str] = None
    
    def to_key(self) -> str:
        """Generate cache key for this jurisdiction."""
        parts = [self.country]
        if self.state:
            parts.append(self.state)
        if self.county:
            parts.append(self.county)
        if self.court:
            parts.append(self.court)
        return ":".join(parts)


@dataclass
class ModuleActivationRule:
    """Rule for when a module should be active."""
    module_id: str
    # Role requirements
    min_role: Optional[UserRole] = None
    allowed_roles: Set[UserRole] = field(default_factory=set)
    # Jurisdiction requirements
    allowed_states: Set[str] = field(default_factory=set)  # Empty = all states
    blocked_states: Set[str] = field(default_factory=set)  # Overrides allowed
    # Feature flag override
    requires_flag: Optional[str] = None
    # Rollout percentage (0-100)
    rollout_percent: int = 100


@dataclass
class ModuleAccess:
    """Per-request module access container."""
    user_role: UserRole
    jurisdiction: Jurisdiction
    active_modules: Set[str] = field(default_factory=set)
    restricted_modules: Dict[str, str] = field(default_factory=dict)  # module -> reason
    
    def can_use(self, module_id: str) -> bool:
        """Check if user can use a specific module."""
        if module_id in self.active_modules:
            return True
        # Check if restricted with reason
        return module_id not in self.restricted_modules
    
    def get_restriction_reason(self, module_id: str) -> Optional[str]:
        """Get why a module is restricted."""
        return self.restricted_modules.get(module_id)


# =============================================================================
# Module Registry — Declaration of which modules need gating
# =============================================================================

MODULE_RULES: Dict[str, ModuleActivationRule] = {}


def register_module_gate(
    module_id: str,
    min_role: Optional[UserRole] = None,
    allowed_roles: Optional[Set[UserRole]] = None,
    allowed_states: Optional[Set[str]] = None,
    blocked_states: Optional[Set[str]] = None,
    requires_flag: Optional[str] = None,
    rollout_percent: int = 100,
) -> None:
    """
    Register a module with gating rules.
    
    Example:
        register_module_gate(
            "eviction_defense",
            allowed_roles={UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL},
            allowed_states={"ND", "MN"},  # Only available in Dakotas/Minnesota
            rollout_percent=50,  # 50% rollout
        )
    """
    MODULE_RULES[module_id] = ModuleActivationRule(
        module_id=module_id,
        min_role=min_role,
        allowed_roles=allowed_roles or set(),
        allowed_states=allowed_states or set(),
        blocked_states=blocked_states or set(),
        requires_flag=requires_flag,
        rollout_percent=rollout_percent,
    )
    logger.info(f"Registered module gate: {module_id}")


# =============================================================================
# Default Module Registrations
# =============================================================================

def _register_default_gates():
    """Register default module gating rules."""
    # Eviction defense - available to tenants, advocates, legal
    # Restricted by state (example: only ND initially)
    register_module_gate(
        "eviction_defense",
        allowed_roles={UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL},
        allowed_states={"ND"},  # Start with North Dakota
        rollout_percent=100,
    )
    
    # Counterclaim - legal and advocate only
    register_module_gate(
        "counterclaim",
        min_role=UserRole.ADVOCATE,
        allowed_roles={UserRole.ADVOCATE, UserRole.LEGAL},
        allowed_states={"ND", "MN"},
    )
    
    # Complaints - available to all roles
    register_module_gate(
        "complaints",
        allowed_roles={UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER},
    )
    
    # Case builder - advocate and up
    register_module_gate(
        "case_builder",
        min_role=UserRole.ADVOCATE,
        allowed_roles={UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER},
    )
    
    # Law library - available to all
    register_module_gate(
        "law_library",
        allowed_roles=set(UserRole),  # All roles
    )
    
    # Hearing prep - legal only
    register_module_gate(
        "hearing_prep",
        min_role=UserRole.LEGAL,
        allowed_roles={UserRole.LEGAL, UserRole.JUDGE},
    )


# Initialize default gates on import
_register_default_gates()


# =============================================================================
# Middleware
# =============================================================================

class ModuleGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that determines module access based on role + jurisdiction.
    
    Adds `module_access` to request.state for downstream use.
    """
    
    def __init__(self, app: ASGIApp, default_state: Optional[str] = None) -> None:
        super().__init__(app)
        self.default_state = default_state or "ND"  # Default for testing
    
    async def dispatch(self, request: Request, call_next):
        # Extract user role from request (set by auth middleware)
        user_role = self._extract_role(request)
        
        # Extract jurisdiction from request
        jurisdiction = self._extract_jurisdiction(request)
        
        # Calculate module access
        access = self._calculate_access(user_role, jurisdiction, request)
        
        # Store in request state
        request.state.module_access = access
        request.state.jurisdiction = jurisdiction
        
        # Log for debugging
        logger.debug(f"Module access for {user_role.value}: {access.active_modules}")
        
        return await call_next(request)
    
    def _extract_role(self, request: Request) -> UserRole:
        """Extract user role from request state (set by auth)."""
        # Try to get from user context in state
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user.role
        
        # Try to get from cookie/header
        role_header = request.headers.get("x-user-role")
        if role_header:
            try:
                return UserRole(role_header.lower())
            except ValueError:
                pass
        
        # Default to tenant
        return UserRole.USER
    
    def _extract_jurisdiction(self, request: Request) -> Jurisdiction:
        """Extract jurisdiction from request (headers, params, or IP geolocation)."""
        # Try explicit jurisdiction header
        state = request.headers.get("x-jurisdiction-state") or request.query_params.get("state")
        county = request.headers.get("x-jurisdiction-county") or request.query_params.get("county")
        
        # Fallback to default
        if not state:
            state = self.default_state
        
        return Jurisdiction(
            country="US",
            state=state.upper() if state else None,
            county=county,
        )
    
    def _calculate_access(
        self, 
        role: UserRole, 
        jurisdiction: Jurisdiction,
        request: Request
    ) -> ModuleAccess:
        """Calculate which modules are accessible."""
        active: Set[str] = set()
        restricted: Dict[str, str] = {}
        
        for module_id, rule in MODULE_RULES.items():
            # Check role
            if rule.min_role and role.value < rule.min_role.value:
                restricted[module_id] = f"Requires {rule.min_role.value} role or higher"
                continue
            
            if rule.allowed_roles and role not in rule.allowed_roles:
                restricted[module_id] = f"Not available for {role.value} role"
                continue
            
            # Check jurisdiction (state-level)
            if jurisdiction.state:
                if rule.blocked_states and jurisdiction.state in rule.blocked_states:
                    restricted[module_id] = f"Not available in {jurisdiction.state}"
                    continue
                
                if rule.allowed_states and jurisdiction.state not in rule.allowed_states:
                    restricted[module_id] = f"Not yet available in {jurisdiction.state}"
                    continue
            
            # Check feature flag (would integrate with feature flag system)
            if rule.requires_flag:
                # For now, assume enabled if flag not implemented
                pass
            
            # Check rollout (deterministic by user ID)
            if rule.rollout_percent < 100:
                user_hash = self._hash_user(request)
                if (user_hash % 100) >= rule.rollout_percent:
                    restricted[module_id] = "Not in rollout group"
                    continue
            
            # All checks passed
            active.add(module_id)
        
        return ModuleAccess(
            user_role=role,
            jurisdiction=jurisdiction,
            active_modules=active,
            restricted_modules=restricted,
        )
    
    def _hash_user(self, request: Request) -> int:
        """Generate deterministic hash for user (for rollout grouping)."""
        user_id = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.user_id
        
        # Simple hash for demonstration
        return hash(user_id) % 10000


def get_module_access(request: Request) -> ModuleAccess:
    """
    Get module access from request state.
    
    Usage in routes:
        access = get_module_access(request)
        if not access.can_use("eviction_defense"):
            raise HTTPException(403, "Feature not available")
    """
    if hasattr(request.state, "module_access"):
        return request.state.module_access
    
    # Return empty access if middleware not configured
    return ModuleAccess(
        user_role=UserRole.USER,
        jurisdiction=Jurisdiction(),
    )


def get_jurisdiction(request: Request) -> Jurisdiction:
    """Get jurisdiction from request state."""
    if hasattr(request.state, "jurisdiction"):
        return request.state.jurisdiction
    return Jurisdiction()
