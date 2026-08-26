"""
Semptify 5.0 - User Context System
Handles role, storage provider, and permissions for each user session.

Architecture Principles (ONE SOURCE OF TRUTH):
- ROLE = stable identity (USER, JUDGE, ADVOCATE, LEGAL, MANAGER, ADMIN)
- GATE = state flag (storage_connected, vault_initialized)
- Do NOT conflate role with gate
- USER role displays as "Tenant" in UI for housing context

Clean Separation:
  role == UserRole.USER:           Who they are
  "vault_initialized" in gates:    What they've done (state)

Design Principles:
- User ID is stable (derived from first storage provider used)
- Role determines what UI/features to show
- Provider tells us where to look for documents/tokens
- Permissions are derived from role
- Gates track user progression without changing identity
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

logger = logging.getLogger(__name__)


# =============================================================================
# User Roles
# =============================================================================


class UserRole(StrEnum):
    """
    User roles determine what features/UI to show.
    A user can have ONE active role per session, but can switch.

    NOTE: Role is stable identity, not tied to gates or activation state.
    TENANT is the canonical role for housing context (previously "user").
    """

    ADMIN = "admin"  # System admin: full access
    MANAGER = "manager"  # Case manager: multi-client coordination
    TENANT = "tenant"  # Tenant: standard housing case user
    USER = "user"  # Legacy alias for tenant (deprecated, use TENANT)
    ADVOCATE = "advocate"  # Tenant advocate: help multiple users
    LEGAL = "legal"  # Legal role: attorneys, judges, clerks, paralegals (sub-roles via legal_sub_role)
    JUDGE = "judge"  # DEPRECATED — merged into LEGAL as sub_role='judge'. Kept for backward compat only.


# =============================================================================
# Storage Providers
# =============================================================================


class StorageProvider(StrEnum):
    """Supported cloud storage providers."""

    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    LOCAL = "local"  # For admin/system users without cloud storage
    # R2 is system-only, not for user auth


# =============================================================================
# Permissions (derived from role)
# =============================================================================

ROLE_PERMISSIONS = {
    # ==========================================================================
    # TENANT - Mobile-first, simplified access (canonical housing role)
    # Focus: Own case management, self-help tools, guided workflows
    # ==========================================================================
    UserRole.TENANT: {
        # Vault - own documents only
        "vault_read",
        "vault_write",
        # Timeline - own case history
        "timeline_read",
        "timeline_write",
        # Calendar - own deadlines
        "calendar_read",
        "calendar_write",
        # AI assistance
        "copilot_use",
        # File complaints on own behalf
        "complaints_create",
        # Rent ledger
        "ledger_read",
        "ledger_write",
        # Self-help tools
        "eviction_defense",
        "court_forms",
        "letter_builder",
    },
    # Legacy alias - same permissions as TENANT
    UserRole.USER: {
        "vault_read",
        "vault_write",
        "timeline_read",
        "timeline_write",
        "calendar_read",
        "calendar_write",
        "copilot_use",
        "complaints_create",
        "ledger_read",
        "ledger_write",
        "eviction_defense",
        "court_forms",
        "letter_builder",
    },
    # ==========================================================================
    # MANAGER - Multi-client housing support coordination
    # ==========================================================================
    UserRole.MANAGER: {
        "vault_read",
        "vault_write",
        "timeline_read",
        "calendar_read",
        "calendar_write",
        "property_manage",
        "user_view",  # View user info (not edit)
    },
    # ==========================================================================
    # ADVOCATE - Legal aid workers, paralegals, housing counselors
    # Focus: Help multiple tenants, case management across clients
    # ==========================================================================
    UserRole.ADVOCATE: {
        # All tenant permissions
        "vault_read",
        "vault_write",
        "timeline_read",
        "timeline_write",
        "calendar_read",
        "calendar_write",
        "copilot_use",
        "complaints_create",
        "ledger_read",
        "ledger_write",
        "eviction_defense",
        "court_forms",
        "letter_builder",
        # Advocate-specific
        "complaints_review",  # Review/help with complaints
        "multi_user",  # Access multiple tenant cases
        "case_assignment",  # Assign cases to self
        "case_notes",  # Add advocate notes (non-privileged)
        "client_intake",  # Intake new clients
        "bulk_export",  # Export case summaries
    },
    # ==========================================================================
    # LEGAL - Legal and court professionals (unified role with sub-roles)
    # Sub-roles: attorney, judge, clerk, paralegal
    # All sub-roles require bar_license_number on User model.
    # Focus: Full read access to invited tenant cases, legal overlays, forms sharing.
    # CANNOT modify or delete tenant vault documents (read-only on tenant vault).
    # Can create legal overlays (notes, redaction) on tenant documents.
    # Can share from their own forms list with tenants.
    # ==========================================================================
    UserRole.LEGAL: {
        # Read access to tenant data (requires invite/relationship)
        "vault_read",  # View tenant documents (with invite)
        # NO vault_write — legal cannot modify or delete tenant documents
        "timeline_read",
        "calendar_read",
        "calendar_write",  # Can write to own calendar
        "copilot_use",
        "complaints_create",
        "complaints_review",
        "ledger_read",
        # Legal tools
        "document_analysis",
        "eviction_defense",
        "court_forms",
        "letter_builder",
        # Multi-tenant access
        "multi_user",  # Access multiple tenant cases (with invite)
        "case_assignment",
        "case_notes",  # Add legal case notes (as overlays, not on tenant docs)
        "client_intake",
        "bulk_export",
        # Legal-specific (PRIVILEGED)
        "legal_tools",  # Advanced legal analysis tools
        "privileged_create",  # Create attorney-client privileged notes
        "privileged_read",  # Read privileged work product
        "work_product",  # Attorney work product protection
        "legal_research",  # Advanced legal research tools
        "court_filing",  # Generate court-ready filings
        "discovery_prep",  # Prepare discovery responses
        "case_strategy",  # Strategic case planning
        "conflict_check",  # Check for conflicts of interest
        # Merged from Judge role (for judge sub-role, but available to all legal)
        "case_review",  # Review all case materials
        "case_oversight",  # Case oversight capabilities
        "judicial_order",  # Record judicial orders/decisions (judge sub-role)
        # New: Legal overlay + forms sharing
        "overlay_create_legal",  # Create legal overlays (notes, redaction) on tenant docs
        "forms_share",  # Share from own forms list with tenants
    },
    # ==========================================================================
    # JUDGE - Judicial officers with oversight capabilities
    # Focus: Case review, read-only access to evidence and timelines
    # ==========================================================================
    UserRole.JUDGE: {
        # Read access
        "vault_read",
        "timeline_read",
        "calendar_read",
        "ledger_read",
        # Case oversight
        "case_review",  # Review all case materials
        "case_oversight",  # Judicial oversight of cases
        "complaints_review",  # Review complaints and evidence
        "multi_user",  # View multiple case files
        # Legal tools (read-only)
        "legal_research",  # Access legal research
        # Judicial functions
        "judicial_order",  # Record judicial orders/decisions
        "case_notes",  # Add judicial notes
    },
    # ==========================================================================
    # ADMIN - System administrators (you)
    # Focus: System config, analytics, full access
    # ==========================================================================
    UserRole.ADMIN: {
        "*",  # All permissions
    },
}


# =============================================================================
# Canonical Role Dictionary (single source of truth)
# =============================================================================

ROLE_DEFINITIONS = {
    UserRole.USER: {
        "display_name": "Tenant",
        "purpose": "Individual renter or resident organizing their own housing and case documents with guided help.",
        "default_landing_process": "B2 - Quick Case Triage",
        "ui_mode": "mobile",  # Mobile-first, simplified
        "landing_page": "/tenant/home",
        "icon": "○",
    },
    UserRole.ADVOCATE: {
        "display_name": "Advocate",
        "purpose": "Frontline support worker helping tenants prepare evidence, organize timelines, and complete non-privileged actions.",
        "default_landing_process": "B4 - Professional Review Workspace",
        "ui_mode": "responsive",  # Tablet-friendly
        "landing_page": "/advocate/home",
        "icon": "▸",
    },
    UserRole.MANAGER: {
        "display_name": "Case Manager",
        "purpose": "Multi-client housing support professional coordinating client cases across nonprofit, charity, and agency programs.",
        "default_landing_process": "B4 - Professional Review Workspace",
        "ui_mode": "desktop",
        "landing_page": "/manager/home",
        "icon": "●",
    },
    UserRole.LEGAL: {
        "display_name": "Legal",
        "purpose": "Legal and court professionals (attorneys, judges, clerks, paralegals). Bar license required. Read-only access to invited tenant cases with legal overlay and forms sharing.",
        "default_landing_process": "B4 - Professional Review Workspace",
        "ui_mode": "desktop",  # Full complexity
        "landing_page": "/legal/home",
        "icon": "▸",
        "sub_roles": ("attorney", "judge", "clerk", "paralegal"),
        "requires_bar_license": True,
    },
    UserRole.JUDGE: {
        "display_name": "Judge",
        "purpose": "Judicial officer with case oversight, evidence review, and decision recording capabilities.",
        "default_landing_process": "B4 - Professional Review Workspace",
        "ui_mode": "desktop",  # Full complexity
        "landing_page": "/judge/home",
        "icon": "●",
    },
    UserRole.ADMIN: {
        "display_name": "Administrator",
        "purpose": "Platform operations role with system-wide configuration, governance, and support access.",
        "default_landing_process": "B4 - Professional Review Workspace",
        "ui_mode": "desktop",  # Full complexity
        "landing_page": "/admin/home",
        "icon": "▸",
    },
}


# =============================================================================
# Role Metadata (for UI routing and display)
# =============================================================================

ROLE_METADATA = {
    role: {
        "display_name": role_def["display_name"],
        "description": role_def["purpose"],
        "purpose": role_def["purpose"],
        "default_landing_process": role_def["default_landing_process"],
        "ui_mode": role_def["ui_mode"],
        "landing_page": role_def["landing_page"],
        "icon": role_def["icon"],
    }
    for role, role_def in ROLE_DEFINITIONS.items()
}


# =============================================================================
# Legal Sub-Roles (unified Legal role with sub-role differentiation)
# =============================================================================

LEGAL_SUB_ROLES = ("attorney", "judge", "clerk", "paralegal")
"""Canonical sub-roles within the Legal role.

All sub-roles require a bar_license_number on the User model:
- attorney: Full legal tools, privileged work product, court filing
- judge:    Case review, oversight, judicial orders (merged from JUDGE role)
- clerk:    Court clerk — filings processing, calendar, document review
- paralegal: Legal support — research, drafting, document organization

The legacy UserRole.JUDGE enum is DEPRECATED. Judge is now a sub-role
of Legal. Existing JUDGE references in services should treat judge
as a legal_sub_role='judge' when refining behavior.
"""


def get_legal_sub_role(user_id: str) -> str | None:
    """Get the legal sub-role for a user, if they are a legal role.

    Returns one of LEGAL_SUB_ROLES or None if the user is not legal
    or has no sub-role set.
    """
    from app.core.database import get_db_session
    from app.models.models import User

    try:
        with get_db_session() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user or user.default_role != "legal":
                return None
            return user.legal_sub_role
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def is_legal_sub_role(user_id: str, sub_role: str) -> bool:
    """Check if a user is a specific legal sub-role.

    Args:
        user_id: The user's ID
        sub_role: One of LEGAL_SUB_ROLES ('attorney', 'judge', 'clerk', 'paralegal')

    Returns:
        True if the user is a legal role with the specified sub-role.
    """
    if sub_role not in LEGAL_SUB_ROLES:
        return False
    return get_legal_sub_role(user_id) == sub_role


def get_role_metadata(role: UserRole) -> dict:
    """Get metadata for a role (display name, UI mode, etc.)."""
    return ROLE_METADATA.get(role, ROLE_METADATA[UserRole.USER])


def get_role_definition(role: UserRole) -> dict:
    """Get canonical role definition (display, purpose, and default process)."""
    return ROLE_DEFINITIONS.get(role, ROLE_DEFINITIONS[UserRole.USER])


def get_permissions(role: UserRole) -> set[str]:
    """Get permissions for a role."""
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        # Admin has all permissions
        all_perms = set()
        for role_perms in ROLE_PERMISSIONS.values():
            if "*" not in role_perms:
                all_perms.update(role_perms)
        return all_perms
    return perms


# =============================================================================
# User Context (carries all session context)
# =============================================================================


@dataclass
class UserContext:
    """
    Complete context for an authenticated user session.
    This is what gets passed to route handlers.
    """

    # Identity (stable)
    user_id: str  # Internal ID (hash of provider:storage_id)

    # Storage info
    provider: StorageProvider  # Which storage provider authenticated
    storage_user_id: str  # ID in the storage provider
    access_token: str  # Current access token for API calls

    # Role & permissions
    role: UserRole = UserRole.USER  # Active role for this session
    permissions: set[str] = field(default_factory=set)

    # Role impersonation (acting_as)
    # When set, this user is impersonating another user's context
    acting_as: str | None = None  # user_id of user being impersonated
    acting_as_role: UserRole | None = None  # Role being assumed

    # SSOT PRIVACY RULE: For the tenant role, no personal user information
    # may be stored on Semptify servers. Only provider metadata and access state
    # are retained. Tenant PII remains in the user's cloud vault or provider data.
    # This is the strict tenant privacy rule; it may extend to other roles later.

    # Session tracking
    session_id: str | None = None
    authenticated_at: datetime | None = None

    # Reconnect reason (e.g. token_corrupt) for access-level responses
    reconnect_reason: str | None = None

    def __post_init__(self):
        """Set permissions based on role if not provided."""
        if not self.permissions:
            self.permissions = get_permissions(self.role)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or "*" in self.permissions

    def can(self, *permissions: str) -> bool:
        """Check if user has ALL specified permissions."""
        return all(self.has_permission(p) for p in permissions)

    def can_any(self, *permissions: str) -> bool:
        """Check if user has ANY of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)

    @property
    def is_user(self) -> bool:
        return self.role == UserRole.USER

    @property
    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER

    @property
    def is_advocate(self) -> bool:
        return self.role == UserRole.ADVOCATE

    @property
    def is_legal(self) -> bool:
        return self.role == UserRole.LEGAL

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_impersonating(self) -> bool:
        """Check if user is currently impersonating another user."""
        return self.acting_as is not None

    def start_impersonation(self, target_user_id: str, target_role: UserRole) -> None:
        """
        Start impersonating another user.

        Only admins should be able to do this. Permission check should happen
        before calling this method.
        """
        self.acting_as = target_user_id
        self.acting_as_role = target_role
        logger.info(f"User {self.user_id[:6]}... started impersonating {target_user_id[:6]}... as {target_role}")

    def stop_impersonation(self) -> None:
        """Stop impersonating and return to original role."""
        if self.acting_as:
            logger.info(f"User {self.user_id[:6]}... stopped impersonating {self.acting_as[:6]}...")
            self.acting_as = None
            self.acting_as_role = None

    def get_effective_user_id(self) -> str:
        """
        Get the effective user ID for this session.
        Returns acting_as user_id if impersonating, otherwise own user_id.
        """
        return self.acting_as if self.acting_as else self.user_id

    def get_effective_role(self) -> UserRole:
        """
        Get the effective role for this session.
        Returns acting_as_role if impersonating, otherwise own role.
        """
        return self.acting_as_role if self.acting_as_role else self.role


# =============================================================================
# Session Storage Structure
# =============================================================================


@dataclass
class StoredSession:
    """
    What we store in the session store (memory/Redis/DB).
    Contains everything needed to reconstruct UserContext.
    """

    session_id: str

    # Identity
    user_id: str
    provider: str  # StorageProvider value
    storage_user_id: str

    # Auth
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None

    # Role (can be switched)
    role: str = "user"  # UserRole value

    # Impersonation state (admin only)
    acting_as: str | None = None  # user_id being impersonated
    acting_as_role: str | None = None  # role being assumed

    # SSOT PRIVACY: No email or display_name stored.

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    def to_context(self) -> UserContext:
        """Convert stored session to UserContext for route handlers."""
        ctx = UserContext(
            user_id=self.user_id,
            provider=StorageProvider(self.provider),
            storage_user_id=self.storage_user_id,
            access_token=self.access_token,
            role=UserRole(self.role),
            session_id=self.session_id,
            authenticated_at=self.created_at,
        )
        if self.acting_as:
            ctx.acting_as = self.acting_as
            ctx.acting_as_role = UserRole(self.acting_as_role) if self.acting_as_role else None
        return ctx

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "storage_user_id": self.storage_user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "role": self.role,
            "acting_as": self.acting_as,
            "acting_as_role": self.acting_as_role,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoredSession":
        """Deserialize from storage."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            provider=data["provider"],
            storage_user_id=data["storage_user_id"],
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expires_at=datetime.fromisoformat(data["token_expires_at"]) if data.get("token_expires_at") else None,
            role=data.get("role", "user"),
            acting_as=data.get("acting_as"),
            acting_as_role=data.get("acting_as_role"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


# =============================================================================
# UI Configuration by Role
# =============================================================================

ROLE_UI_CONFIG = {
    UserRole.TENANT: {
        "theme": "tenant",
        "nav_items": ["vault", "timeline", "calendar", "copilot", "complaints", "ledger"],
        "dashboard": "tenant_dashboard",
        "landing": "/vault",
    },
    UserRole.USER: {  # Legacy alias - same as TENANT
        "theme": "tenant",
        "nav_items": ["vault", "timeline", "calendar", "copilot", "complaints", "ledger"],
        "dashboard": "tenant_dashboard",
        "landing": "/vault",
    },
    UserRole.MANAGER: {
        "theme": "manager",
        "nav_items": ["properties", "users", "calendar", "documents"],
        "dashboard": "manager_dashboard",
        "landing": "/properties",
    },
    UserRole.ADVOCATE: {
        "theme": "advocate",
        "nav_items": ["clients", "vault", "timeline", "complaints", "resources"],
        "dashboard": "advocate_dashboard",
        "landing": "/clients",
    },
    UserRole.LEGAL: {
        "theme": "legal",
        "nav_items": ["cases", "vault", "timeline", "documents", "resources"],
        "dashboard": "legal_dashboard",
        "landing": "/cases",
    },
    UserRole.ADMIN: {
        "theme": "admin",
        "nav_items": ["users", "system", "logs", "metrics"],
        "dashboard": "admin_dashboard",
        "landing": "/admin",
    },
}


def get_ui_config(role: UserRole) -> dict:
    """Get UI configuration for a role."""
    return ROLE_UI_CONFIG.get(role, ROLE_UI_CONFIG[UserRole.TENANT])


def get_role_from_user_id(user_id: str) -> UserRole:
    """Get role for a user ID from their stored context."""
    if not user_id:
        return UserRole.USER

    # In a real implementation, this would look up the user's role from storage
    # For now, default to USER role since role assignment happens during onboarding
    return UserRole.USER


async def get_user_context(
    storage_provider: str | None = None,
    semptify_uid: str | None = None,
) -> dict:
    """
    Get user context for API responses.
    This is a simplified version that returns basic user info.
    """
    return {
        "user_id": semptify_uid or "anonymous",
        "role": UserRole.USER.value,
        "storage_provider": storage_provider,
        "gates": [],
        "permissions": list(get_permissions(UserRole.USER)),
    }
