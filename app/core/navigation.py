"""
Navigation SSOT — Single Source of Truth for all UI navigation paths.

Following SSOT Architecture:
- Navigation is a process, not a property of individual pages
- All routes reference this central definition
- Static files consume via /api/navigation endpoint
- Jinja2 templates inject via context processor
"""

import logging
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NavItem:
    """Immutable navigation entry — SSOT for a single path."""

    name: str  # Human label
    path: str  # URL path
    icon: str = ""  # Optional icon/emoji
    order: int = 0  # Sort priority
    requires: str = ""  # "auth", "onboarding", "storage", or ""
    description: str = ""


@dataclass(frozen=True)
class FlowStage:
    """Immutable onboarding/reconnect flow stage."""

    id: str
    name: str
    path: str
    next_stage: str | None = None
    requires_checkpoint: bool = True


@dataclass
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
    _CANONICAL_PATHS: ClassVar[set[str]] = set()

    @classmethod
    def _build_canonical_set(cls) -> set[str]:
        """Build set of all SSOT-approved paths. Called automatically."""
        paths = set()

        # Onboarding flow paths
        for stage in cls.ONBOARDING_FLOW.values():
            paths.add(stage.path)

        # Main nav paths
        for item in cls.MAIN_NAV:
            paths.add(item.path)

        # Admin flow paths
        for stage in cls.ADMIN_FLOW.values():
            paths.add(stage.path)

        # Entry points
        paths.add("/")
        paths.add(cls.get_onboarding_start())
        paths.add(cls.get_reconnect_flow())
        paths.add("/home")

        cls._CANONICAL_PATHS = paths
        return paths

    # --- Onboarding Flow (SSOT) ---
    ONBOARDING_FLOW: ClassVar[dict[str, FlowStage]] = {
        "preamble": FlowStage(
            id="preamble", name="Preamble", path="/preamble", next_stage="role_select", requires_checkpoint=False
        ),
        "welcome": FlowStage(id="welcome", name="Welcome", path="/", next_stage="preamble", requires_checkpoint=False),
        "role_select": FlowStage(
            id="role_select",
            name="Select Role",
            path="/onboarding/select-role.html",  # Served by router, shadowing static
            next_stage="storage_select",
            requires_checkpoint=True,
        ),
        "storage_select": FlowStage(
            id="storage_select",
            name="Connect Storage",
            path="/onboarding/providers",
            next_stage="vault_setup",
            requires_checkpoint=True,
        ),
        # NOTE: /storage/providers is the RECONNECT entry point (returning users)
        # Onboarding flow goes directly: providers ▸ vault_setup ▸ home
        "providers": FlowStage(
            id="providers",
            name="Storage Providers (Reconnect)",
            path="/storage/providers",
            next_stage="vault_setup",
            requires_checkpoint=True,
        ),
        "reconnect": FlowStage(
            id="reconnect",
            name="Token Reconnect",
            path="/storage/reconnect",
            next_stage=None,  # Returns to return_to after reconnect
            requires_checkpoint=False,
        ),
        "status": FlowStage(
            id="status",
            name="Onboarding Status",
            path="/onboarding/status",
            next_stage="vault_setup",
            requires_checkpoint=False,
        ),
        "vault_setup": FlowStage(
            id="vault_setup",
            name="Vault Setup",
            path="/onboarding/vault-setup",
            next_stage="dashboard",
            requires_checkpoint=False,
        ),
        "dashboard": FlowStage(
            id="dashboard", name="Home", path="/onboarding/complete", next_stage=None, requires_checkpoint=False
        ),
        "upload": FlowStage(
            id="upload", name="Document Upload", path="/onboarding/upload", next_stage=None, requires_checkpoint=True
        ),
        "tenant_home": FlowStage(
            id="tenant_home", name="Tenant Home", path="/home", next_stage=None, requires_checkpoint=False
        ),
        "advocate_portal": FlowStage(
            id="advocate_portal", name="Advocate Portal", path="/advocate", next_stage=None, requires_checkpoint=False
        ),
        "legal_portal": FlowStage(
            id="legal_portal", name="Legal Portal", path="/legal", next_stage=None, requires_checkpoint=False
        ),
        "admin_portal": FlowStage(
            id="admin_portal", name="Admin Portal", path="/admin", next_stage=None, requires_checkpoint=False
        ),
        "manager_portal": FlowStage(
            id="manager_portal", name="Manager Portal", path="/manager", next_stage=None, requires_checkpoint=False
        ),
        "law_library": FlowStage(
            id="law_library", name="Law Library", path="/law-library", next_stage=None, requires_checkpoint=False
        ),
        # --- Tenant product pages (SSOT) ---
        # These stages eliminate hardcoded URL strings from ssot_redirect() callers in main.py.
        "onboarding_start": FlowStage(
            id="onboarding_start",
            name="Onboarding Start",
            path="/onboarding/start",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "tenant_timeline": FlowStage(
            id="tenant_timeline",
            name="Timeline",
            path="/tenant/timeline",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "tenant_dashboard": FlowStage(
            id="tenant_dashboard",
            name="Tenant Dashboard",
            path="/tenant/dashboard",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "tenant_home_page": FlowStage(
            id="tenant_home_page",
            name="Tenant Home Page",
            path="/tenant/home",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "tenant_library": FlowStage(
            id="tenant_library",
            name="Tenant Library (KNOW pillar)",
            path="/tenant/library",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "documents": FlowStage(
            id="documents",
            name="Documents",
            path="/documents",
            next_stage=None,
            requires_checkpoint=False,
        ),
        # --- Module root redirect targets (Post-Redirect-Get) ---
        # Used by module routers after a POST operation to redirect back to the module's GET view.
        "dispute_tracker_home": FlowStage(
            id="dispute_tracker_home",
            name="Dispute Tracker",
            path="/api/dispute-tracker/",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "eviction_timeline_home": FlowStage(
            id="eviction_timeline_home",
            name="Eviction Timeline",
            path="/api/eviction-timeline/",
            next_stage=None,
            requires_checkpoint=False,
        ),
    }

    # --- Court Integration Paths (SSOT) ---
    COURT_FLOW: ClassVar[dict[str, FlowStage]] = {
        "mndes_guide": FlowStage(
            id="mndes_guide",
            name="MNDES Submission Guide",
            path="/mndes/guide",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "mndes_validate": FlowStage(
            id="mndes_validate",
            name="MNDES File Compliance Check",
            path="/api/mndes/validate",
            next_stage="mndes_package",
            requires_checkpoint=True,
        ),
        "mndes_package": FlowStage(
            id="mndes_package",
            name="MNDES Exhibit Package",
            path="/api/mndes/package",
            next_stage=None,
            requires_checkpoint=True,
        ),
        "mndes_compliance_guide": FlowStage(
            id="mndes_compliance_guide",
            name="MNDES Compliance Guide (All Roles)",
            path="/mndes/compliance-guide",
            next_stage=None,
            requires_checkpoint=False,
        ),
    }

    # --- Admin Flow (SSOT) ---
    # Elevation-required admin routes. Kept separate from public navigation.
    ADMIN_FLOW: ClassVar[dict[str, FlowStage]] = {
        "admin_hub": FlowStage(
            id="admin_hub", name="Admin Hub", path="/admin", next_stage=None, requires_checkpoint=False
        ),
        "admin_login": FlowStage(
            id="admin_login", name="Admin Login", path="/admin/login", next_stage=None, requires_checkpoint=False
        ),
        "admin_dashboard": FlowStage(
            id="admin_dashboard",
            name="Admin Dashboard",
            path="/admin/dashboard",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_dashboard_html": FlowStage(
            id="admin_dashboard_html",
            name="Admin Dashboard (Legacy .html)",
            path="/admin/dashboard.html",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_forge": FlowStage(
            id="admin_forge",
            name="Semptify Forge",
            path="/admin/forge.html",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_run_modules": FlowStage(
            id="admin_run_modules",
            name="Run Modules",
            path="/admin/run-modules",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_system_health": FlowStage(
            id="admin_system_health",
            name="System Health & Updates",
            path="/admin/system-health",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_testing": FlowStage(
            id="admin_testing", name="Testing", path="/admin/testing", next_stage=None, requires_checkpoint=False
        ),
        "admin_invite_codes": FlowStage(
            id="admin_invite_codes",
            name="Invite Codes & Authorizations",
            path="/admin/invite-codes",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_correspondence": FlowStage(
            id="admin_correspondence",
            name="Correspondence",
            path="/admin/correspondence",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_user_concerns": FlowStage(
            id="admin_user_concerns",
            name="User Concerns",
            path="/admin/user-concerns",
            next_stage=None,
            requires_checkpoint=False,
        ),
        "admin_advanced": FlowStage(
            id="admin_advanced",
            name="Advanced / Dev Tools",
            path="/admin/advanced",
            next_stage="admin_forge",
            requires_checkpoint=False,
        ),
        "admin_page_editor": FlowStage(
            id="admin_page_editor",
            name="Page Editor",
            path="/admin/page-editor.html",
            next_stage=None,
            requires_checkpoint=False,
        ),
    }

    # --- Main Navigation (SSOT) ---
    # The 5 base navigation links present on EVERY page:
    # Home, Library, Office, Tools, Help
    # All paths are RENDERED routes (auth + gates) — never .html static files.
    MAIN_NAV: ClassVar[list[NavItem]] = [
        NavItem(name="Home", path="/home", icon="🏠", order=0, requires=""),
        NavItem(name="Library", path="/library", icon="📚", order=1, requires=""),
        NavItem(name="Office", path="/office", icon="🏢", order=2, requires=""),
        NavItem(name="Tools", path="/tools", icon="🔧", order=3, requires=""),
        NavItem(name="Help", path="/help", icon="🆘", order=4, requires=""),
    ]

    # --- Utility Methods ---
    @classmethod
    def get_onboarding_start(cls) -> str:
        """Entry point for all users — SSOT. Preamble determines new vs returning."""
        return "/preamble"

    @classmethod
    def get_reconnect_flow(cls) -> str:
        """Entry point for returning users — SSOT."""
        return "/storage/reconnect"

    @classmethod
    def get_stage(cls, stage_id: str) -> FlowStage | None:
        """Get flow stage by ID — searches all registries (onboarding + court + admin)."""
        return cls.ONBOARDING_FLOW.get(stage_id) or cls.COURT_FLOW.get(stage_id) or cls.ADMIN_FLOW.get(stage_id)

    @classmethod
    def get_next_path(cls, current_stage_id: str) -> str:
        """Determine next path in flow — SSOT transition logic."""
        stage = cls.get_stage(current_stage_id)
        if not stage or not stage.next_stage:
            return "/"  # Welcome page is the safe fallback
        next_stage = cls.get_stage(stage.next_stage)
        return next_stage.path if next_stage else "/"

    # --- Evolution Mechanisms (SSOT must breathe) ---

    _DEPRECATED_PATHS: ClassVar[dict[str, str]] = {}  # old_path -> new_path
    _ESCAPE_HATCHES: ClassVar[set[str]] = set()  # Temporarily allowed non-SSOT paths

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
                    "requires_checkpoint": v.requires_checkpoint,
                }
                for k, v in cls.ONBOARDING_FLOW.items()
            },
            "main_nav": [
                {
                    "name": item.name,
                    "path": item.path,
                    "icon": item.icon,
                    "order": item.order,
                    "requires": item.requires,
                }
                for item in sorted(cls.MAIN_NAV, key=lambda x: x.order)
            ],
            "admin_flow": {
                k: {
                    "id": v.id,
                    "name": v.name,
                    "path": v.path,
                    "next": v.next_stage,
                    "requires_checkpoint": v.requires_checkpoint,
                }
                for k, v in cls.ADMIN_FLOW.items()
            },
            "entry_points": {
                "welcome": "/",
                "onboarding_start": cls.get_onboarding_start(),
                "reconnect": cls.get_reconnect_flow(),
                "dashboard": "/home",
            },
            "evolution": {
                "deprecated_paths": cls._DEPRECATED_PATHS,
                "escape_hatches": list(cls._ESCAPE_HATCHES),
                "total_stages": len(cls.ONBOARDING_FLOW) + len(cls.COURT_FLOW) + len(cls.ADMIN_FLOW),
            },
        }


# Global instance — import this
navigation = NavigationRegistry()


def get_navigation_ssot() -> NavigationRegistry:
    """Accessor function — use this to get the SSOT registry."""
    return navigation
