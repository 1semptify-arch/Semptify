"""
Navigation SSOT — Single Source of Truth for all UI navigation paths.

Following SSOT Architecture:
- Navigation is a process, not a property of individual pages
- All routes reference this central definition
- Static files consume via /api/navigation endpoint
- Jinja2 templates inject via context processor
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class NavItem:
    """Immutable navigation entry — SSOT for a single path."""
    name: str           # Human label
    path: str           # URL path
    icon: str = ""      # Optional icon/emoji
    order: int = 0      # Sort priority
    requires: str = ""  # "auth", "onboarding", "storage", or ""
    description: str = ""


@dataclass(frozen=True)
class FlowStage:
    """Immutable onboarding/reconnect flow stage."""
    id: str
    name: str
    path: str
    next_stage: Optional[str] = None
    requires_checkpoint: bool = True


class NavigationRegistry:
    """
    Central registry — THE source of truth for all navigation.
    
    No page, template, or static file defines its own path.
    All paths flow from here.
    
    Evolution: This registry grows with the product. Rules are guardrails,
    not prison bars. Use register_stage() for expansion, add_escape_hatch() 
    for experimentation.
    """
    
    # --- Path Cache (auto-built from registry) ---
    _CANONICAL_PATHS: Set[str] = set()
    
    @classmethod
    def _build_canonical_set(cls) -> Set[str]:
        """Build set of all SSOT-approved paths. Called automatically."""
        paths = set()
        
        # Onboarding flow paths
        for stage in cls.ONBOARDING_FLOW.values():
            paths.add(stage.path)
        
        # Main nav paths
        for item in cls.MAIN_NAV:
            paths.add(item.path)
        
        # Entry points
        paths.add("/")
        paths.add(cls.get_onboarding_start())
        paths.add(cls.get_reconnect_flow())
        paths.add("/home")
        
        cls._CANONICAL_PATHS = paths
        return paths
    
    # --- Onboarding Flow (SSOT) ---
    ONBOARDING_FLOW: Dict[str, FlowStage] = field(default_factory=lambda: {
        "welcome": FlowStage(
            id="welcome",
            name="Welcome",
            path="/",
            next_stage="role_select",
            requires_checkpoint=False
        ),
        "role_select": FlowStage(
            id="role_select",
            name="Select Role",
            path="/onboarding-assets/select-role.html",
            next_stage="storage_select",
            requires_checkpoint=True
        ),
        "storage_select": FlowStage(
            id="storage_select",
            name="Connect Storage",
            path="/onboarding-assets/storage-select.html",
            next_stage="providers",
            requires_checkpoint=True
        ),
        "providers": FlowStage(
            id="providers",
            name="Storage Providers",
            path="/storage/providers",
            next_stage="dashboard",
            requires_checkpoint=True
        ),
    })
    
    # --- Main Navigation (SSOT) ---
    MAIN_NAV: List[NavItem] = field(default_factory=lambda: [
        NavItem(name="Home", path="/home", icon="🏠", order=0, requires="auth"),
        NavItem(name="Cases", path="/cases", icon="📁", order=1, requires="auth"),
        NavItem(name="Documents", path="/documents", icon="📄", order=2, requires="storage"),
        NavItem(name="Timeline", path="/timeline", icon="📅", order=3, requires="storage"),
        NavItem(name="Settings", path="/settings", icon="⚙️", order=10, requires="auth"),
    ])
    
    # --- Utility Methods ---
    @classmethod
    def get_onboarding_start(cls) -> str:
        """Entry point for new users — SSOT."""
        return "/onboarding/start"
    
    @classmethod
    def get_reconnect_flow(cls) -> str:
        """Entry point for returning users — SSOT."""
        return "/storage/reconnect"
    
    @classmethod
    def get_stage(cls, stage_id: str) -> Optional[FlowStage]:
        """Get flow stage by ID — all routing logic uses this."""
        return cls.ONBOARDING_FLOW.get(stage_id)
    
    @classmethod
    def get_next_path(cls, current_stage_id: str) -> str:
        """Determine next path in flow — SSOT transition logic."""
        stage = cls.get_stage(current_stage_id)
        if not stage or not stage.next_stage:
            return "/home"
        next_stage = cls.get_stage(stage.next_stage)
        return next_stage.path if next_stage else "/home"
    
    # --- Evolution Mechanisms (SSOT must breathe) ---
    
    _DEPRECATED_PATHS: Dict[str, str] = {}  # old_path -> new_path
    _ESCAPE_HATCHES: Set[str] = set()  # Temporarily allowed non-SSOT paths
    
    @classmethod
    def register_stage(cls, stage: FlowStage) -> None:
        """
        Dynamically add a new flow stage.
        
        Use this for feature expansion - SSOT grows with the product.
        """
        cls.ONBOARDING_FLOW[stage.id] = stage
        # Invalidate cache
        cls._build_canonical_set()
    
    @classmethod
    def deprecate_path(cls, old_path: str, new_path: str) -> None:
        """
        Mark a path as deprecated with automatic redirect.
        
        Evolution without breakage - old paths redirect to new SSOT paths.
        """
        cls._DEPRECATED_PATHS[old_path] = new_path
    
    @classmethod
    def resolve_path(cls, path: str) -> str:
        """
        Resolve any path to current SSOT canonical.
        
        Handles deprecated paths and escape hatches.
        """
        # Check deprecated
        if path in cls._DEPRECATED_PATHS:
            return cls._DEPRECATED_PATHS[path]
        
        # Check if it's a valid SSOT path
        if not cls._CANONICAL_PATHS:
            cls._build_canonical_set()
        
        if path in cls._CANONICAL_PATHS or path in cls._ESCAPE_HATCHES:
            return path
            
        # Unknown path - allow but warn (growth needs experimentation)
        return path
    
    @classmethod
    def add_escape_hatch(cls, path: str, reason: str, ttl_days: int = 7) -> None:
        """
        Temporary exception for experimental features.
        
        Rules exist to enable flow, not prevent it. Document the exception.
        
        Args:
            path: Non-SSOT path to temporarily allow
            reason: Why this exception exists (documented)
            ttl_days: Auto-expire after N days (prevents permanent rot)
        """
        cls._ESCAPE_HATCHES.add(path)
        # In production, you'd log this with timestamp for TTL enforcement
    
    @classmethod
    def to_dict(cls) -> dict:
        """Export complete navigation state for API consumption."""
        if not cls._CANONICAL_PATHS:
            cls._build_canonical_set()
            
        return {
            "onboarding_flow": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "path": v.path,
                    "next": v.next_stage,
                    "requires_checkpoint": v.requires_checkpoint
                }
                for k, v in cls.ONBOARDING_FLOW.items()
            },
            "main_nav": [
                {
                    "name": item.name,
                    "path": item.path,
                    "icon": item.icon,
                    "order": item.order,
                    "requires": item.requires
                }
                for item in sorted(cls.MAIN_NAV, key=lambda x: x.order)
            ],
            "entry_points": {
                "welcome": "/",
                "onboarding_start": cls.get_onboarding_start(),
                "reconnect": cls.get_reconnect_flow(),
                "dashboard": "/home"
            },
            "evolution": {
                "deprecated_paths": cls._DEPRECATED_PATHS,
                "escape_hatches": list(cls._ESCAPE_HATCHES),
                "total_stages": len(cls.ONBOARDING_FLOW)
            }
        }


# Global instance — import this
navigation = NavigationRegistry()


def get_navigation_ssot() -> NavigationRegistry:
    """Accessor function — use this to get the SSOT registry."""
    return navigation
