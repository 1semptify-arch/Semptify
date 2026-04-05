"""
Semptify 5.0 - Process Group Registry
Single source of truth for all 8 process groups.

Every page in the system maps to these groups via a PageContract.
Groups are mechanical — they define what a page DOES, not how it looks.

Coverage states used by PageContract:
  active   — page directly delivers this group's function
  linked   — page links out to this group's pages
  guarded  — group is locked until qualification met
  n-a      — group not relevant to this page
"""

from dataclasses import dataclass
from typing import FrozenSet
from app.core.user_context import UserRole


# =============================================================================
# Group Coverage Literals
# =============================================================================

COVERAGE_ACTIVE = "active"
COVERAGE_LINKED = "linked"
COVERAGE_GUARDED = "guarded"
COVERAGE_NA = "n-a"

VALID_COVERAGE_VALUES = {COVERAGE_ACTIVE, COVERAGE_LINKED, COVERAGE_GUARDED, COVERAGE_NA}


# =============================================================================
# ProcessGroup Definition
# =============================================================================

@dataclass(frozen=True)
class ProcessGroup:
    """
    Defines one of the 8 canonical process groups.
    All pages must declare their coverage of every group.
    """
    group_id: int
    name: str                              # machine key, e.g. "welcome"
    title: str                             # display title
    purpose: str                           # one-sentence function description
    roles_with_access: FrozenSet[UserRole] # roles that can reach this group's pages
    scope_includes: tuple[str, ...]        # what belongs here
    scope_excludes: tuple[str, ...]        # explicitly out of scope
    entry_criteria: tuple[str, ...]        # preconditions before a page in this group loads
    exit_criteria: tuple[str, ...]         # conditions that mark group work as complete
    success_metrics: tuple[str, ...]       # measurable outcomes


# =============================================================================
# The 8 Process Groups
# =============================================================================

ALL_ROLES: FrozenSet[UserRole] = frozenset(UserRole)
PROFESSIONAL_ROLES: FrozenSet[UserRole] = frozenset({
    UserRole.ADVOCATE, UserRole.MANAGER, UserRole.LEGAL, UserRole.ADMIN
})
ADMIN_ONLY: FrozenSet[UserRole] = frozenset({UserRole.ADMIN})


GROUP_WELCOME = ProcessGroup(
    group_id=1,
    name="welcome",
    title="Welcome",
    purpose="Establish who the user is, what they need, and where documents live before any case work begins.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "role selection",
        "storage provider connection",
        "onboarding wizard",
        "process routing (A → B1/B2/B4)",
        "first-time user guidance",
    ),
    scope_excludes=(
        "case analysis",
        "document upload",
        "authentication credential management",
    ),
    entry_criteria=(
        "user is unauthenticated OR has no active session",
        "no role cookie present OR user explicitly resets",
    ),
    exit_criteria=(
        "role selected",
        "storage provider status confirmed",
        "user routed to correct Process B variant",
    ),
    success_metrics=(
        "welcome_completed_rate",
        "role_selection_time_seconds",
        "storage_connect_success_rate",
        "process_route_accuracy",
    ),
)

GROUP_SECURITY = ProcessGroup(
    group_id=2,
    name="security_validation",
    title="Security & Validation",
    purpose="Verify user identity, authenticate storage providers, and validate document authenticity.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "OAuth storage authentication",
        "token refresh and expiry handling",
        "document authenticity checks",
        "session management",
        "permission gate enforcement",
        "conflict-of-interest checks (legal role)",
    ),
    scope_excludes=(
        "case content review",
        "AI analysis",
        "storage file browsing",
    ),
    entry_criteria=(
        "user has selected a role",
        "storage provider status is known",
    ),
    exit_criteria=(
        "storage OAuth token valid OR review-only mode confirmed",
        "session active with correct role permissions",
    ),
    success_metrics=(
        "auth_success_rate",
        "token_refresh_success_rate",
        "permission_gate_block_rate",
        "session_duration_minutes",
    ),
)

GROUP_DOCUMENTATION = ProcessGroup(
    group_id=3,
    name="documentation",
    title="Documentation",
    purpose="Upload, organise, tag, and manage all case documents in the user's vault.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "document upload (PDF, image, text)",
        "vault organisation and tagging",
        "document metadata editing",
        "duplicate detection",
        "version history",
        "bulk document operations",
    ),
    scope_excludes=(
        "AI analysis of document content",
        "legal review",
        "document delivery/export",
    ),
    entry_criteria=(
        "storage provider authenticated OR review-only mode",
        "vault namespace initialised for user",
    ),
    exit_criteria=(
        "at least one document uploaded or confirmed present",
        "documents tagged with case type",
    ),
    success_metrics=(
        "vault_documents_count",
        "upload_success_rate",
        "tagging_completion_rate",
        "duplicate_detection_hits",
    ),
)

GROUP_RESEARCH = ProcessGroup(
    group_id=4,
    name="research_knowledge",
    title="Research & Knowledge",
    purpose="Surface relevant law, precedent, HUD guidance, and AI-assisted case analysis.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "law library search",
        "AI case analysis and recommendations",
        "HUD funding and jurisdiction lookup",
        "precedent and citation search",
        "evidence strength scoring",
        "timeline auto-generation",
    ),
    scope_excludes=(
        "document creation",
        "court filing",
        "live legal advice (privileged communication)",
    ),
    entry_criteria=(
        "at least one document or case detail present",
        "jurisdiction identified",
    ),
    exit_criteria=(
        "relevant statutes identified",
        "evidence strength score generated",
        "timeline populated",
    ),
    success_metrics=(
        "research_queries_per_session",
        "law_matches_returned",
        "evidence_score_accuracy",
        "ai_recommendation_acceptance_rate",
    ),
)

GROUP_FUNCTIONS = ProcessGroup(
    group_id=5,
    name="functions_actions",
    title="Functions & Actions",
    purpose="Execute case actions: build letters, fill court forms, file complaints, and automate case tasks.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "letter builder",
        "court form auto-fill",
        "complaint filing",
        "eviction defense wizard",
        "case assignment (advocate/manager)",
        "bulk case operations",
    ),
    scope_excludes=(
        "document storage",
        "legal analysis output",
        "final delivery/export",
    ),
    entry_criteria=(
        "case documents present",
        "research phase completed OR skipped by experienced role",
    ),
    exit_criteria=(
        "target action completed (letter generated / form filled / complaint submitted)",
        "action logged to case timeline",
    ),
    success_metrics=(
        "actions_completed_per_session",
        "letter_builder_completion_rate",
        "court_form_fill_accuracy",
        "complaint_submission_rate",
    ),
)

GROUP_OUTPUT = ProcessGroup(
    group_id=6,
    name="output_delivery",
    title="Output & Delivery",
    purpose="Package, export, and deliver finalised case materials to the user, their advocate, or courts.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "case packet assembly",
        "PDF export",
        "secure share links",
        "advocate handoff",
        "court-ready filing bundles",
        "bulk export (advocate/manager/legal roles)",
    ),
    scope_excludes=(
        "document editing",
        "new action generation",
        "system configuration",
    ),
    entry_criteria=(
        "at least one completed action or document ready for export",
    ),
    exit_criteria=(
        "package delivered to target (user / advocate / court)",
        "delivery confirmed and logged",
    ),
    success_metrics=(
        "export_success_rate",
        "packet_assembly_time_seconds",
        "delivery_confirmation_rate",
        "filing_bundle_accuracy",
    ),
)

GROUP_HELP = ProcessGroup(
    group_id=7,
    name="help_contacts",
    title="Help & Contacts",
    purpose="Connect users to human support: advocates, legal aid, and platform help resources.",
    roles_with_access=ALL_ROLES,
    scope_includes=(
        "advocate request flow",
        "legal aid directory",
        "in-app help and tooltips",
        "contact form",
        "emergency housing resources",
        "jurisdiction-specific hotlines",
    ),
    scope_excludes=(
        "case work",
        "document processing",
        "system administration",
    ),
    entry_criteria=(
        "user is authenticated OR on welcome screen",
    ),
    exit_criteria=(
        "help request submitted OR contact delivered to user",
    ),
    success_metrics=(
        "help_requests_submitted",
        "advocate_match_rate",
        "help_resource_click_rate",
        "contact_resolution_rate",
    ),
)

GROUP_ADMIN = ProcessGroup(
    group_id=8,
    name="system_admin_monitoring",
    title="System Admin & Monitoring",
    purpose="Platform operations: configuration, analytics, KPI dashboards, security audits, and contract health.",
    roles_with_access=ADMIN_ONLY,
    scope_includes=(
        "system configuration",
        "user management",
        "KPI dashboard",
        "process contract health report",
        "security audit logs",
        "AI agent monitoring",
        "workflow engine state inspection",
        "storage provider health",
    ),
    scope_excludes=(
        "tenant case work",
        "legal advice",
        "document content review",
    ),
    entry_criteria=(
        "user has admin role",
        "session has system_config permission",
    ),
    exit_criteria=(
        "monitoring task completed",
        "configuration change saved and validated",
    ),
    success_metrics=(
        "system_uptime_percent",
        "contract_health_score",
        "security_audit_pass_rate",
        "kpi_dashboard_load_time_ms",
    ),
)


# =============================================================================
# Registry: ordered list + lookup dict
# =============================================================================

PROCESS_GROUPS: tuple[ProcessGroup, ...] = (
    GROUP_WELCOME,
    GROUP_SECURITY,
    GROUP_DOCUMENTATION,
    GROUP_RESEARCH,
    GROUP_FUNCTIONS,
    GROUP_OUTPUT,
    GROUP_HELP,
    GROUP_ADMIN,
)

PROCESS_GROUP_BY_NAME: dict[str, ProcessGroup] = {g.name: g for g in PROCESS_GROUPS}
PROCESS_GROUP_BY_ID: dict[int, ProcessGroup] = {g.group_id: g for g in PROCESS_GROUPS}

ALL_GROUP_NAMES: tuple[str, ...] = tuple(g.name for g in PROCESS_GROUPS)


def get_group(name: str) -> ProcessGroup:
    """Return a group by its machine name. Raises KeyError if unknown."""
    return PROCESS_GROUP_BY_NAME[name]


def get_groups_for_role(role: UserRole) -> list[ProcessGroup]:
    """Return all groups accessible to a given role."""
    return [g for g in PROCESS_GROUPS if role in g.roles_with_access]
