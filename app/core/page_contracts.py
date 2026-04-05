"""
Semptify 5.0 - Page Contract System
Every page in the system must have a PageContract registered here.

A PageContract is a machine-readable declaration of:
  - which roles can access the page
  - how the page relates to each of the 8 process groups
  - what must be true before the page loads (entry criteria)
  - what must be true when the user leaves (exit criteria)
  - what telemetry events the page emits

Coverage values (see process_registry.py):
  active   — page directly delivers this group's function
  linked   — page links out to this group's pages
  guarded  — group visible but locked until qualification met
  n-a      — group not relevant to this page

Usage:
    from app.core.page_contracts import get_contract, PAGE_CONTRACTS
    contract = get_contract("welcome")
    print(contract.group_coverage["documentation"])  # "guarded"
"""

from dataclasses import dataclass
from app.core.user_context import UserRole
from app.core.process_registry import (
    ALL_GROUP_NAMES,
    VALID_COVERAGE_VALUES,
    COVERAGE_ACTIVE,
    COVERAGE_LINKED,
    COVERAGE_GUARDED,
    COVERAGE_NA,
)


# =============================================================================
# PageContract Schema
# =============================================================================

@dataclass
class PageContract:
    """
    Declares a page's relationship to the 8 process groups and routing rules.
    All 8 group names must be present in group_coverage.
    """
    page_id: str                              # e.g. "welcome", "tenant_vault"
    title: str                                # human-readable page name
    route: str                                # URL path, e.g. "/"
    roles_supported: list[UserRole]           # roles that may access this page
    primary_groups: list[str]                 # group names this page leads with
    secondary_groups: list[str]               # group names touched but not primary
    group_coverage: dict[str, str]            # all 8 group names → coverage state
    qualification: str                        # plain-English access requirement
    expectations: str                         # what the user accomplishes here
    scope_of_use: str                         # intended use boundaries
    entry_criteria: list[str]                 # what must be true before page loads
    exit_criteria: list[str]                  # what must be true for a "clean exit"
    telemetry_events: list[str]               # event names emitted by this page

    def validate(self) -> list[str]:
        """
        Returns a list of violation strings. Empty list = valid contract.
        Call this from CI or at startup.
        """
        errors: list[str] = []

        # All 8 groups must be covered
        for group_name in ALL_GROUP_NAMES:
            if group_name not in self.group_coverage:
                errors.append(f"[{self.page_id}] Missing group coverage: '{group_name}'")
            elif self.group_coverage[group_name] not in VALID_COVERAGE_VALUES:
                errors.append(
                    f"[{self.page_id}] Invalid coverage value '{self.group_coverage[group_name]}' "
                    f"for group '{group_name}'. Must be one of {sorted(VALID_COVERAGE_VALUES)}"
                )

        # primary_groups must reference real groups
        for g in self.primary_groups:
            if g not in ALL_GROUP_NAMES:
                errors.append(f"[{self.page_id}] Unknown primary group: '{g}'")

        # secondary_groups must reference real groups
        for g in self.secondary_groups:
            if g not in ALL_GROUP_NAMES:
                errors.append(f"[{self.page_id}] Unknown secondary group: '{g}'")

        # Must have at least one role
        if not self.roles_supported:
            errors.append(f"[{self.page_id}] roles_supported is empty")

        # Must have at least one telemetry event
        if not self.telemetry_events:
            errors.append(f"[{self.page_id}] telemetry_events is empty")

        return errors


def _full_coverage(**overrides: str) -> dict[str, str]:
    """
    Build a complete 8-group coverage dict starting from all n-a,
    then applying the given overrides.
    """
    base = {name: COVERAGE_NA for name in ALL_GROUP_NAMES}
    base.update(overrides)
    return base


# =============================================================================
# Page Contract Registry
# =============================================================================

# --- Process A: Welcome ---
CONTRACT_WELCOME = PageContract(
    page_id="welcome",
    title="Welcome — Process A",
    route="/",
    roles_supported=list(UserRole),
    primary_groups=["welcome"],
    secondary_groups=["security_validation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_ACTIVE,
        security_validation=COVERAGE_GUARDED,    # storage connect is surfaced but optional
        documentation=COVERAGE_GUARDED,          # shown as "coming next" but not active
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,           # link to help is always visible
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="No authentication required. Public entry point.",
    expectations="User selects their role and storage status, then is routed to the correct Process B variant.",
    scope_of_use="First screen for all new sessions. Also shown when session is reset or role is changed.",
    entry_criteria=[
        "No active authenticated session required",
        "App server is running",
    ],
    exit_criteria=[
        "Role selected (cookie or query param set)",
        "Storage status confirmed (need_connect / already_connected / review_only)",
        "User clicks 'Start Process' and is routed to Process B",
    ],
    telemetry_events=[
        "welcome_page_load",
        "role_selected",
        "storage_status_set",
        "process_start_clicked",
        "storage_connect_clicked",
    ],
)

# --- Process B2: Tenant Quick Triage (Tenant / mobile-first) ---
CONTRACT_TENANT = PageContract(
    page_id="tenant",
    title="Tenant Dashboard — Process B2",
    route="/tenant",
    roles_supported=[UserRole.USER],
    primary_groups=["documentation", "functions_actions"],
    secondary_groups=["research_knowledge", "output_delivery", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,     # token check happens here
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="User role required. Storage provider connected or review-only mode.",
    expectations="Tenant can upload documents, view guided actions, and access quick-help tools.",
    scope_of_use="Primary workspace for tenants. Mobile-first layout.",
    entry_criteria=[
        "Role = user (tenant)",
        "Storage status confirmed",
        "Session initialised",
    ],
    exit_criteria=[
        "At least one document uploaded or case action taken",
        "Or user routed to help/contacts",
    ],
    telemetry_events=[
        "tenant_dashboard_load",
        "document_upload_started",
        "quick_action_clicked",
        "help_requested",
        "case_action_completed",
    ],
)

# --- Process B2: Tenant Help & Contacts ---
CONTRACT_TENANT_HELP = PageContract(
    page_id="tenant_help",
    title="Tenant Help & Contacts",
    route="/tenant/help",
    roles_supported=[UserRole.USER],
    primary_groups=["help_contacts"],
    secondary_groups=["functions_actions", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_LINKED,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="User role required. Accessible from the tenant workspace when support is needed.",
    expectations="Tenant can access emergency guidance, hotlines, legal aid, and support escalation paths.",
    scope_of_use="Support surface for tenants seeking human help, urgent contacts, or crisis-oriented next steps.",
    entry_criteria=[
        "Role = user (tenant)",
        "Session is valid or routed through the tenant workspace",
    ],
    exit_criteria=[
        "User selects a support channel, hotline, or next-step resource",
        "Or user returns to the tenant dashboard with a clearer action path",
    ],
    telemetry_events=[
        "tenant_help_load",
        "emergency_help_clicked",
        "hotline_clicked",
        "legal_aid_resource_opened",
        "tenant_help_returned",
    ],
)

# --- Process B4: Professional Review Workspace (Advocate / Manager / Legal / Admin) ---
CONTRACT_PROFESSIONAL = PageContract(
    page_id="professional_workspace",
    title="Professional Workspace — Process B4",
    route="/advocate",
    roles_supported=[UserRole.ADVOCATE, UserRole.MANAGER, UserRole.LEGAL, UserRole.ADMIN],
    primary_groups=["documentation", "research_knowledge", "functions_actions"],
    secondary_groups=["output_delivery", "help_contacts", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_GUARDED,   # admin link visible but guarded for non-admins
    ),
    qualification="Advocate, Case Manager, Legal, or Admin role required.",
    expectations="Professional multi-tab workspace for case management, research, and action generation.",
    scope_of_use="Primary workspace for non-tenant professional roles. Desktop-first layout.",
    entry_criteria=[
        "Role in (advocate, manager, legal, admin)",
        "Storage provider authenticated or review-only",
        "Session active with correct permissions",
    ],
    exit_criteria=[
        "Case action completed or handed off",
        "Output exported or delivered",
    ],
    telemetry_events=[
        "professional_workspace_load",
        "case_opened",
        "research_query_submitted",
        "action_generated",
        "export_initiated",
    ],
)

# --- Admin / System Control ---
CONTRACT_ADMIN = PageContract(
    page_id="admin_control",
    title="System Admin & Control",
    route="/admin",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER],
    primary_groups=["system_admin_monitoring"],
    secondary_groups=["security_validation", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Admin or Manager role required. Admin-only sections additionally guarded.",
    expectations="Monitor system health, review KPIs, manage users, and inspect contract health.",
    scope_of_use="Operations dashboard. Managers see client-level metrics; admins see platform-level metrics.",
    entry_criteria=[
        "Role in (admin, manager)",
        "Session active",
    ],
    exit_criteria=[
        "Monitoring task completed or configuration saved",
    ],
    telemetry_events=[
        "admin_dashboard_load",
        "kpi_dashboard_viewed",
        "contract_health_checked",
        "config_change_saved",
        "user_management_action",
    ],
)

# --- Legal Professional ---
CONTRACT_LEGAL = PageContract(
    page_id="legal_workspace",
    title="Legal Workspace",
    route="/legal",
    roles_supported=[UserRole.LEGAL],
    primary_groups=["research_knowledge", "functions_actions", "output_delivery"],
    secondary_groups=["documentation", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Legal role required. Privileged sections additionally gated by permission check.",
    expectations="Full legal toolkit: research, privileged notes, court filing bundles, conflict checks.",
    scope_of_use="Attorneys, judges, court clerks, and paralegals. Desktop-only.",
    entry_criteria=[
        "Role = legal",
        "Storage provider authenticated",
        "Conflict check passed (if client case)",
    ],
    exit_criteria=[
        "Legal output generated (filing, notes, analysis)",
        "Or conflict flagged and case rejected",
    ],
    telemetry_events=[
        "legal_workspace_load",
        "privileged_note_created",
        "court_filing_generated",
        "conflict_check_run",
        "legal_research_query",
    ],
)


# =============================================================================
# Registry & Lookup
# =============================================================================

PAGE_CONTRACTS: dict[str, PageContract] = {
    c.page_id: c
    for c in [
        CONTRACT_WELCOME,
        CONTRACT_TENANT,
        CONTRACT_TENANT_HELP,
        CONTRACT_PROFESSIONAL,
        CONTRACT_ADMIN,
        CONTRACT_LEGAL,
    ]
}


def get_contract(page_id: str) -> PageContract:
    """Return a page contract by page_id. Raises KeyError if not registered."""
    return PAGE_CONTRACTS[page_id]


def validate_all_contracts() -> dict[str, list[str]]:
    """
    Validate every registered contract.
    Returns dict of page_id → list of violation strings.
    Only pages with violations appear in the output.
    """
    results: dict[str, list[str]] = {}
    for page_id, contract in PAGE_CONTRACTS.items():
        violations = contract.validate()
        if violations:
            results[page_id] = violations
    return results
