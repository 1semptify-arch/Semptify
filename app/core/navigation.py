"""
Navigation SSOT — Single Source of Truth for all UI navigation paths.

Following SSOT Architecture:
- Navigation is a process, not a property of individual pages
- All routes reference this central definition
- Static files consume via /api/navigation endpoint
- Jinja2 templates inject via context processor
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
    """
    
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
    
    @classmethod
    def to_dict(cls) -> dict:
        """Export complete navigation state for API consumption."""
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
            }
        }


# Global instance — import this
navigation = NavigationRegistry()


def get_navigation_ssot() -> NavigationRegistry:
    """Accessor function — use this to get the SSOT registry."""
    return navigation
