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

try:
    from app.core.user_context import UserRole
    from app.core.process_registry import (
        ALL_GROUP_NAMES,
        VALID_COVERAGE_VALUES,
        COVERAGE_ACTIVE,
        COVERAGE_LINKED,
        COVERAGE_GUARDED,
        COVERAGE_NA,
    )
except ImportError:
    import sys
    sys.path.insert(0, r"c:\Semptify\Semptify-FastAPI")
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

# Status values for page contracts
STATUS_ACTIVE = "active"
STATUS_COMING_SOON = "coming_soon"
STATUS_BETA = "beta"
STATUS_DEPRECATED = "deprecated"
VALID_STATUSES = {STATUS_ACTIVE, STATUS_COMING_SOON, STATUS_BETA, STATUS_DEPRECATED}


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
    status: str = STATUS_ACTIVE               # "active", "coming_soon", "beta", "deprecated"

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

        # Status must be valid
        if self.status not in VALID_STATUSES:
            errors.append(
                f"[{self.page_id}] Invalid status '{self.status}'. "
                f"Must be one of {sorted(VALID_STATUSES)}"
            )

        return errors

    def is_coming_soon(self) -> bool:
        """Check if this contract is marked as coming soon."""
        return self.status == STATUS_COMING_SOON

    def is_active(self) -> bool:
        """Check if this contract is active and usable."""
        return self.status == STATUS_ACTIVE

    def is_beta(self) -> bool:
        """Check if this contract is in beta."""
        return self.status == STATUS_BETA


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
    qualification="User role required. Storage provider must be connected.",
    expectations="Tenant can upload documents (via vault), view guided actions, and access quick-help tools.",
    scope_of_use=(
        "Primary workspace for tenants. "
        "Supports a specific mobile layout variant — applied only if the mobile layout is chosen, not assumed. "
        "Document upload is a trigger to vault — this page does not own upload logic."
    ),
    entry_criteria=[
        "Role = user (tenant)",
        "Storage provider connected",
        "Session initialised",
    ],
    exit_criteria=[
        "At least one document uploaded (via vault) or case action taken",
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
    qualification="User role required. Always accessible from the tenant workspace — no case stage restriction.",
    expectations=(
        "Tenant can access emergency guidance, hotlines, legal aid, and support escalation paths. "
        "Emergency and crisis content lives here — including immediate-threat guidance for tenants "
        "facing physical removal, lockouts, or urgent court deadlines. "
        "This page is reachable at any point regardless of where the user is in their case."
    ),
    scope_of_use=(
        "Support surface for tenants seeking human help, urgent contacts, or crisis-oriented next steps. "
        "Always visible and always accessible — never gated by case stage or progress. "
        "Crisis intake (crisis_intake page) is a separate deeper flow — this page is the entry point that can route there."
    ),
    entry_criteria=[
        "Role = user (tenant)",
        "Always accessible — no case stage or progress gate",
    ],
    exit_criteria=[
        "User selects a support channel, hotline, or legal aid resource",
        "Or user is routed to crisis_intake for deeper emergency intake",
        "Or user returns to tenant dashboard",
    ],
    telemetry_events=[
        "tenant_help_load",
        "emergency_help_clicked",
        "crisis_content_viewed",
        "hotline_clicked",
        "legal_aid_resource_opened",
        "crisis_intake_triggered",
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
    qualification="Advocate, Case Manager, Legal, or Admin role required. Storage must be connected.",
    expectations=(
        "Professional workspace for reviewing tenant cases, conducting research, and generating actions. "
        "Role capabilities differ within this page: "
        "ADVOCATE — broadest access, can take the most actions, annotate, escalate, and generate outputs. "
        "LEGAL — review and research focused, action scope limited to legal analysis and filings. "
        "MANAGER — oversight and case assignment, limited direct case actions. "
        "ADMIN — system-level access only, guarded from case-level actions. "
        "EXCEPTION: Advocate and Manager may upload documents requiring tenant signature — "
        "clearly marked with uploader identity + full security chain. These are PENDING SIGNATURE items, not tenant documents. "
        "Advocate and Legal may leave notes for the tenant via the messaging/chat system. "
        "CRITICAL: Attorney (legal role) may only view tenant case documents if the tenant has sent an explicit invitation. "
        "No legal professional gets unsolicited access to tenant documents under any circumstances."
    ),
    scope_of_use=(
        "Primary workspace for non-tenant professional roles. Desktop-first layout. "
        "Read access to tenant case documents is permitted. Write access is role-gated. "
        "Upload on behalf of tenant is explicitly prohibited on this page and in this system."
    ),
    entry_criteria=[
        "Role in (advocate, manager, legal, admin)",
        "Storage provider connected",
        "Session active with correct role permissions",
    ],
    exit_criteria=[
        "Case action completed or handed off",
        "Output exported or delivered",
        "Or research saved to case record",
    ],
    telemetry_events=[
        "professional_workspace_load",
        "case_opened",
        "research_query_submitted",
        "action_generated",
        "annotation_added",
        "case_escalated",
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
    expectations=(
        "Monitor system health, review KPIs, manage users, and inspect contract health. "
        "Admin and Manager may upload documents that require tenant signature — "
        "e.g. agreements, notices, or formal requests. "
        "All such uploads are clearly marked with uploader identity, role, timestamp, and full security chain. "
        "These documents appear in the tenant's vault as PENDING SIGNATURE items, not as tenant-owned documents."
    ),
    scope_of_use=(
        "Operations dashboard. Managers see client-level metrics; admins see platform-level metrics. "
        "Document uploads here are signature-request only — not case document injection. "
        "Tenant must explicitly sign or reject any document uploaded to them by admin or manager."
    ),
    entry_criteria=[
        "Role in (admin, manager)",
        "Session active",
    ],
    exit_criteria=[
        "Monitoring task completed or configuration saved",
        "Or signature-request document uploaded to tenant vault",
    ],
    telemetry_events=[
        "admin_dashboard_load",
        "kpi_dashboard_viewed",
        "contract_health_checked",
        "config_change_saved",
        "user_management_action",
        "signature_request_uploaded",
        "signature_request_sent",
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
    qualification=(
        "Legal role required. "
        "CRITICAL: Attorney may only access tenant case documents if the tenant has sent an explicit invitation. "
        "No unsolicited access to tenant documents permitted under any circumstance."
    ),
    expectations=(
        "Full legal toolkit: research, privileged notes, court filing bundles, conflict checks. "
        "Legal professionals may leave notes for the tenant via the messaging/chat system. "
        "Legal may upload documents requiring tenant signature — clearly marked with uploader identity, "
        "role, timestamp, and full security chain. These appear as PENDING SIGNATURE items in the tenant vault. "
        "Document access is invitation-gated: tenant must invite the attorney before any case documents are visible."
    ),
    scope_of_use=(
        "Attorneys, judges, court clerks, and paralegals. Desktop-only. "
        "Invitation-only access to tenant documents. "
        "Messaging system used for tenant-attorney communication."
    ),
    entry_criteria=[
        "Role = legal",
        "Storage provider authenticated",
        "Tenant invitation confirmed for any case document access",
        "Conflict check passed",
    ],
    exit_criteria=[
        "Legal output generated (filing, notes, analysis)",
        "Or message/note left for tenant",
        "Or conflict flagged and case rejected",
    ],
    telemetry_events=[
        "legal_workspace_load",
        "tenant_invitation_verified",
        "privileged_note_created",
        "tenant_message_sent",
        "court_filing_generated",
        "conflict_check_run",
        "legal_research_query",
        "signature_request_uploaded",
    ],
)



# =============================================================================
# HIGH-PRIORITY PAGE CONTRACTS (From Page Manifest)
# =============================================================================

CONTRACT_DASHBOARD = PageContract(
    page_id="dashboard",
    title="User Dashboard",
    route="/dashboard",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.MANAGER, UserRole.LEGAL, UserRole.ADMIN],
    primary_groups=["documentation", "functions_actions", "output_delivery"],
    secondary_groups=["research_knowledge", "help_contacts", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated tenant role. Optional — only used if this layout is chosen.",
    expectations=(
        "Optional home page variant for tenants. "
        "Shows case summary, documents, deadlines, and quick actions in a richer layout than /home. "
        "Used only if the dashboard layout is selected as the tenant home design. "
        "Not a required page — /home is always the fallback and safety net. "
        "NOTE: Each role has its own dedicated route (/tenant, /advocate, /legal, /admin etc). "
        "This dashboard is not a shared multi-role page — it is a tenant-specific optional layout."
    ),
    scope_of_use=(
        "Optional tenant home layout variant. "
        "If not chosen as the design, this page is unused. "
        "Role-specific dashboards are being developed separately for each role."
    ),
    entry_criteria=[
        "Authenticated session",
        "Role = user (tenant)",
        "Dashboard layout selected as home variant",
    ],
    exit_criteria=[
        "User navigates to specific module",
        "Or initiates workflow action",
    ],
    telemetry_events=[
        "dashboard_load",
        "quick_action_clicked",
        "deadline_viewed",
        "case_summary_expanded",
    ],
)

CONTRACT_DOCUMENTS = PageContract(
    page_id="documents",
    title="Documents Manager",
    route="/documents",
    roles_supported=list(UserRole),
    primary_groups=["documentation"],
    secondary_groups=["functions_actions", "security_validation", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="TABLED — document system is being reworked. Purpose not yet determined.",
    expectations=(
        "TABLED. The entire document system is under rework. "
        "This contract must not be treated as final or built against until the rework is complete "
        "and the purpose of this page is confirmed by the user."
    ),
    scope_of_use="TABLED — pending document system rework decision.",
    entry_criteria=["TABLED"],
    exit_criteria=["TABLED"],
    telemetry_events=[
        "documents_page_load",
    ],
)

CONTRACT_VAULT = PageContract(
    page_id="vault",
    title="Secure Document Vault",
    route="/vault",
    roles_supported=list(UserRole),
    primary_groups=["documentation", "security_validation"],
    secondary_groups=["functions_actions", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Any authenticated role. Storage provider must be connected.",
    expectations=(
        "Secure document storage interface. "
        "ALL documents entering Semptify go through vault first — no exceptions. "
        "Vault is the single source of truth (SSOT) for document upload. "
        "Documents are stored in the user's own cloud storage (Google Drive, OneDrive, Dropbox). "
        "Certificates are stored alongside documents in .semptify/vault/. "
        "Modules access documents FROM the vault — they never implement their own upload. "
        "Any page with an upload button is a trigger-only surface that calls the vault router. "
        "Vault is a permanent fixture visible on every page from /home onward."
    ),
    scope_of_use=(
        "SSOT for all document ingestion. One upload handler, one validation pipeline, one storage writer. "
        "No other page, router, or module may implement independent document upload logic. "
        "Vault also handles: certificate generation, document preview, timeline extraction trigger, "
        "and mesh workflow dispatch on upload completion."
    ),
    entry_criteria=[
        "Authenticated session",
        "Storage provider OAuth connected",
        "Vault service available (vault_upload_service)",
    ],
    exit_criteria=[
        "Document uploaded to user's cloud storage → mesh workflow triggered",
        "Document downloaded or previewed",
        "Certificate generated and stored",
    ],
    telemetry_events=[
        "vault_load",
        "vault_upload_started",
        "vault_upload_complete",
        "vault_upload_failed",
        "vault_download",
        "vault_preview_opened",
        "certificate_generated",
        "mesh_workflow_triggered",
    ],
)

CONTRACT_COURT_PACKET = PageContract(
    page_id="court_packet",
    title="Court Packet Builder",
    route="/court-packet",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["output_delivery", "functions_actions"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification=(
        "Tenant, Advocate, or Legal role. "
        "Tenant can build their own packet — this is not professional-only. "
        "Requires active case with minimum one document in vault."
    ),
    expectations=(
        "Assembles a court-ready packet dictated by the courtroom procedures and case type. "
        "Contents are determined by jurisdiction and case — not freely configured by the user. "
        "Typical contents: evidence, documentation, security certificates, affidavits, motions, "
        "court-required forms, and watermarked copies for opposing side, judge, and clerk. "
        "CRITICAL: No duplicate files are created. The packet is an overlay/query system — "
        "documents remain in vault and the packet is assembled as a watermarked view layer on demand. "
        "Copies are clearly watermarked as COPY. Nothing is physically duplicated in storage."
    ),
    scope_of_use=(
        "Court preparation surface. Overlay-based — no new files written to storage. "
        "Packet assembly is a query against vault documents + case metadata + court procedure rules. "
        "Output is a watermarked rendered view, not a stored file copy. "
        "If saved back to vault, it is saved as a single packet record with references, not copied documents."
    ),
    entry_criteria=[
        "Authenticated session",
        "Active case with known jurisdiction and court procedure",
        "Minimum one document in vault",
    ],
    exit_criteria=[
        "Packet assembled and rendered as overlay",
        "Packet downloaded or printed (watermarked as COPY)",
        "Or packet record saved to vault as reference",
    ],
    telemetry_events=[
        "court_packet_load",
        "packet_assembled",
        "packet_contents_determined",
        "evidence_indexed",
        "affidavit_included",
        "motion_included",
        "packet_downloaded",
        "packet_saved_to_vault",
    ],
)

CONTRACT_EVICTION_ANSWER = PageContract(
    page_id="eviction_answer",
    title="Eviction Answer Form",
    route="/eviction-answer",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["output_delivery", "functions_actions"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Tenant with active eviction case, or advocate/legal assisting.",
    expectations=(
        "Presents the jurisdiction-specific eviction answer form as an overlay on the user's own system. "
        "Form is pre-referenced from case context via user_id only — no personal data stored on Semptify servers. "
        "User fills and signs the form on their own system. "
        "Semptify is stateless — it references, not stores. "
        "The system knows the correct form template based on jurisdiction derived from case context. "
        "Output stays on the user's system and vault — nothing is retained server-side. "
        "Defenses, counterclaims, and supporting facts are guided by the overlay, not pre-filled by Semptify."
    ),
    scope_of_use=(
        "Eviction defense workflow step. Overlay and form-fill only — stateless. "
        "Jurisdiction-specific form template is referenced, not stored. "
        "System references user_id only — no personal identifiers held by Semptify. "
        "Completed form is saved to user's vault, not to any Semptify server."
    ),
    entry_criteria=[
        "Authenticated session",
        "Eviction notice present in vault",
        "Jurisdiction determinable from case context",
    ],
    exit_criteria=[
        "Answer form completed and signed on user's system",
        "Completed form saved to user's vault",
        "Or draft saved to vault for later completion",
    ],
    telemetry_events=[
        "eviction_answer_load",
        "jurisdiction_form_loaded",
        "defense_selected",
        "counterclaim_added",
        "answer_form_completed",
        "answer_signed",
        "answer_saved_to_vault",
    ],
)

CONTRACT_HEARING_PREP = PageContract(
    page_id="hearing_prep",
    title="Hearing Preparation",
    route="/hearing-prep",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Upcoming hearing date in case. Tenant, Advocate, or Legal role.",
    expectations=(
        "Guided court preparation — the system walks the tenant through hearing procedures step by step. "
        "Court procedure is consistent and predictable by design (rule of law) — the prep follows the same engine every time. "
        "Talking points are derived directly from the complaint and the answer: "
        "what was claimed, what was disputed, what needs to be questioned in court. "
        "Evidence checklist is generated from vault documents relevant to the case. "
        "Zoom mock hearing tool is real — runs a simulated hearing so a tenant who has never been "
        "in a courtroom learns the procedures, the sequence, and what to expect before facing a judge. "
        "Goal: tenant walks in knowing the process as well as anyone in the room."
    ),
    scope_of_use=(
        "Pre-hearing guided workflow. Stateless — references case context via user_id only. "
        "Talking points and evidence checklist assembled as overlay from vault + case data. "
        "Zoom mock hearing is an interactive simulation, not a live court connection. "
        "Prep guide saved to user's vault — nothing retained server-side."
    ),
    entry_criteria=[
        "Authenticated session",
        "Hearing date scheduled in case",
        "Complaint and answer present in case record",
    ],
    exit_criteria=[
        "Guided prep steps completed",
        "Talking points reviewed and saved to vault",
        "Evidence checklist confirmed",
        "Mock hearing completed (optional but recommended)",
        "Or partial prep saved to vault for later completion",
    ],
    telemetry_events=[
        "hearing_prep_load",
        "prep_step_completed",
        "talking_points_generated",
        "evidence_checklist_completed",
        "mock_hearing_started",
        "mock_hearing_completed",
        "prep_guide_saved_to_vault",
    ],
)

CONTRACT_STORAGE_SETUP = PageContract(
    page_id="storage_setup",
    title="Storage Provider Setup",
    route="/storage-setup",
    roles_supported=list(UserRole),
    primary_groups=["security_validation", "functions_actions"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_GUARDED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Any role. Required before document upload.",
    expectations="Connect Google Drive, OneDrive, or Dropbox for secure document storage.",
    scope_of_use="Onboarding step or settings reconfiguration. OAuth flow handler.",
    entry_criteria=[
        "Authenticated session",
        "No storage connected OR changing provider",
    ],
    exit_criteria=[
        "Storage provider connected",
        "OAuth callback successful",
        "Tokens stored securely",
    ],
    telemetry_events=[
        "storage_setup_load",
        "provider_selected",
        "oauth_started",
        "oauth_completed",
        "storage_connected",
    ],
)

CONTRACT_CRISIS_INTAKE = PageContract(
    page_id="crisis_intake",
    title="Crisis Intake",
    route="/crisis-intake",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE],
    primary_groups=["help_contacts", "functions_actions"],
    secondary_groups=["documentation", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Urgent housing crisis. Fast-tracked intake. No case created, no tracking initiated.",
    expectations=(
        "Rapid 5-step guided assessment of crisis situation: 1) What's happening, 2) How urgent, "
        "3) Court date (if applicable), 4) Documents available, 5) Personalized plan. "
        "Immediate resources displayed (211 hotline, legal aid). No case file opened. "
        "No tracking initiated. Pure triage and direction to appropriate tool."
    ),
    scope_of_use=(
        "Emergency triage only. Stateless — intake data saved to localStorage only, not server. "
        "Routes user to appropriate next step based on situation. No retention of crisis details."
    ),
    entry_criteria=[
        "User clicks crisis/emergency help button",
        "Or advocate directs user to crisis intake",
        "Or system detects high-urgency context",
    ],
    exit_criteria=[
        "User has immediate resources (hotlines, next steps)",
        "User directed to appropriate tool based on responses",
        "No case created, no server-side data retained",
    ],
    telemetry_events=[
        "crisis_intake_load",
        "situation_type_selected",
        "urgency_level_selected",
        "has_docs_selected",
        "emergency_alert_shown",
        "crisis_intake_completed",
        "outflow_to_documents",
        "outflow_to_journey",
        "outflow_to_library",
        "outflow_to_help",
    ],
)


# =============================================================================
# ADDITIONAL PAGE CONTRACTS (Medium Priority)
# =============================================================================

CONTRACT_TIMELINE = PageContract(
    page_id="timeline",
    title="Case Timeline",
    route="/timeline",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["documentation", "research_knowledge"],
    secondary_groups=["functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Any authenticated role with case access. Documents present in vault.",
    expectations=(
        "Read-only view of case chronology. Timeline is a query layer on media objects — "
        "documents, events, and extracted dates from vault. No separate timeline data store. "
        "Three sort views available: by event date (when it happened), by document date "
        "(when created), by ingestion date (when Semptify received it). "
        "Visual presentation only — all data lives in vault documents and overlay events.json."
    ),
    scope_of_use=(
        "Case chronology visualization. Stateless query view on vault data. "
        "Renders overlay of document metadata + extracted timeline events. "
        "Tenant: view only. Advocate/Legal: view only — all data comes from document processing."
    ),
    entry_criteria=[
        "Authenticated session",
        "Documents present in vault",
    ],
    exit_criteria=[
        "User navigates to document detail",
        "Or changes sort/filter view",
        "Or exports timeline view (PDF)",
    ],
    telemetry_events=[
        "timeline_load",
        "sort_by_event_date",
        "sort_by_document_date",
        "sort_by_ingestion_date",
        "event_expanded",
        "timeline_filtered",
        "timeline_exported",
    ],
)

CONTRACT_CALENDAR = PageContract(
    page_id="calendar",
    title="Deadline Calendar",
    route="/calendar",
    roles_supported=list(UserRole),
    primary_groups=["documentation", "functions_actions"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Any authenticated role.",
    expectations="Calendar view of deadlines, hearings, and case milestones.",
    scope_of_use="Deadline tracking. Integrates with timeline and court data.",
    entry_criteria=[
        "Authenticated session",
    ],
    exit_criteria=[
        "Date selected",
        "Or event added",
    ],
    telemetry_events=[
        "calendar_load",
        "date_selected",
        "deadline_viewed",
        "event_added",
    ],
)

CONTRACT_DOCUMENT_VIEWER = PageContract(
    page_id="document_viewer",
    title="Document Viewer",
    route="/document-viewer",
    roles_supported=list(UserRole),
    primary_groups=["documentation"],
    secondary_groups=["security_validation", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_NA,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Any authenticated role with document access.",
    expectations="View documents with overlays, annotations, and metadata.",
    scope_of_use="Document inspection surface. Certificate validation display.",
    entry_criteria=[
        "Authenticated session",
        "Document ID provided",
    ],
    exit_criteria=[
        "Document closed",
        "Or annotation added",
    ],
    telemetry_events=[
        "document_viewer_load",
        "overlay_toggled",
        "annotation_added",
        "document_printed",
    ],
)

CONTRACT_ZOOM_COURT = PageContract(
    page_id="zoom_court",
    title="Zoom Court Integration",
    route="/zoom-court",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["functions_actions"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Upcoming virtual hearing scheduled.",
    expectations="Connect to Zoom court hearings, test audio/video, view case docs.",
    scope_of_use="Virtual court appearance surface. Test mode + live mode.",
    entry_criteria=[
        "Authenticated session",
        "Hearing scheduled with Zoom link",
    ],
    exit_criteria=[
        "Hearing completed",
        "Or test mode exited",
    ],
    telemetry_events=[
        "zoom_court_load",
        "test_mode_started",
        "hearing_joined",
        "audio_test_completed",
        "document_shared_in_hearing",
    ],
)

CONTRACT_MOTIONS = PageContract(
    page_id="motions",
    title="Motions Builder",
    route="/motions",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["output_delivery", "functions_actions"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Case-active roles only.",
    expectations="Draft and file motions with court. Template selection.",
    scope_of_use="Motion preparation workflow. Generates court-ready documents.",
    entry_criteria=[
        "Authenticated session",
        "Active case context",
    ],
    exit_criteria=[
        "Motion drafted",
        "Or filed electronically",
    ],
    telemetry_events=[
        "motions_load",
        "motion_template_selected",
        "motion_drafted",
        "motion_filed",
    ],
)

CONTRACT_LEGAL_ANALYSIS = PageContract(
    page_id="legal_analysis",
    title="Legal Analysis",
    route="/legal-analysis",
    roles_supported=[UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["research_knowledge", "functions_actions"],
    secondary_groups=["documentation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Advocate, Legal, or Manager roles.",
    expectations="Analyze legal issues, research statutes, check precedents.",
    scope_of_use="Legal research surface. Integrates with MN Revisor, case law.",
    entry_criteria=[
        "Authenticated session",
        "Role in (advocate, legal, manager)",
    ],
    exit_criteria=[
        "Analysis completed",
        "Or memo generated",
    ],
    telemetry_events=[
        "legal_analysis_load",
        "statute_searched",
        "precedent_checked",
        "analysis_memo_generated",
    ],
)


# =============================================================================
# Group C: Guided Role Journeys
# =============================================================================

CONTRACT_TENANCY = PageContract(
    page_id="tenancy",
    title="My Tenancy",
    route="/tenancy",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["documentation", "functions_actions"],
    secondary_groups=["research_knowledge", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user with active case context.",
    expectations="User reviews tenancy details, lease info, and case context.",
    scope_of_use="Tenant-facing case overview and tenancy facts.",
    entry_criteria=["User authenticated", "Active tenancy data available"],
    exit_criteria=["Tenancy reviewed", "Next step selected"],
    telemetry_events=["tenancy_load", "lease_viewed", "tenancy_fact_added", "tenancy_next_step"],
)

CONTRACT_ADVOCATE_PORTAL = PageContract(
    page_id="advocate",
    title="Advocate Portal",
    route="/advocate",
    roles_supported=[UserRole.ADVOCATE],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Tenant-invited support person (friend, family, volunteer). Not a professional credential.",
    expectations=(
        "Personal advocate supports a specific tenant who invited them. "
        "Cannot self-register — access granted only by tenant invitation. "
        "Sees only the inviting tenant's case, no multi-tenant access. "
        "Can view documents, leave notes, coordinate on tenant's behalf."
    ),
    scope_of_use=(
        "Trust-based support role. Tenant controls access — can revoke at any time. "
        "No case assignment from orgs or agencies. Purely tenant-directed support."
    ),
    entry_criteria=[
        "Valid tenant invitation accepted",
        "Advocate role assigned via invitation flow",
        "Storage connected",
    ],
    exit_criteria=[
        "Support action completed",
        "Tenant revokes access",
        "Session ended",
    ],
    telemetry_events=[
        "advocate_portal_load",
        "invitation_accepted",
        "tenant_case_viewed",
        "support_note_added",
        "advocacy_action_taken",
        "access_revoked_by_tenant",
    ],
)

CONTRACT_ADMIN_PORTAL = PageContract(
    page_id="admin",
    title="Admin Portal",
    route="/admin",
    roles_supported=[UserRole.ADMIN],
    primary_groups=["system_admin_monitoring"],
    secondary_groups=["security_validation", "functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Platform administrator. Full system access.",
    expectations=(
        "System-level operations: user management, platform configuration, health monitoring. "
        "Can invite MANAGER and LEGAL roles. Can manage ADVOCATE invitations."
    ),
    scope_of_use="Platform administration only. No direct case access.",
    entry_criteria=[
        "Admin role authenticated",
        "Internal/platform operations access",
    ],
    exit_criteria=[
        "Admin action completed",
        "Configuration saved",
    ],
    telemetry_events=[
        "admin_portal_load",
        "user_managed",
        "system_config_changed",
        "audit_log_viewed",
        "manager_invited",
        "legal_invited",
    ],
)

CONTRACT_MANAGER_PORTAL = PageContract(
    page_id="manager",
    title="Manager Portal",
    route="/manager",
    roles_supported=[UserRole.MANAGER],
    primary_groups=["documentation", "functions_actions", "help_contacts"],
    secondary_groups=["output_delivery", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_LINKED,
    ),
    qualification="Professional case manager, counselor, or housing worker. Multi-tenant access.",
    expectations=(
        "Manages multiple tenant cases. Caseload dashboard, coordination tools. "
        "Can send documents to tenants (review/signature required). "
        "Cannot access case without tenant assignment or org relationship."
    ),
    scope_of_use=(
        "Housing professionals: case workers, counselors, tenant advocates. "
        "Org-verified or admin-invited. Multi-tenant caseload view."
    ),
    entry_criteria=[
        "Manager role authenticated",
        "Org verification or admin invitation complete",
        "At least one assigned tenant or caseload",
    ],
    exit_criteria=[
        "Caseload reviewed",
        "Tenant coordination completed",
        "Document delivered to tenant",
    ],
    telemetry_events=[
        "manager_portal_load",
        "caseload_viewed",
        "tenant_coordinated",
        "document_sent_to_tenant",
        "case_note_added",
    ],
)

CONTRACT_LEGAL_PORTAL = PageContract(
    page_id="legal",
    title="Legal Portal",
    route="/legal",
    roles_supported=[UserRole.LEGAL],
    primary_groups=["research_knowledge", "output_delivery"],
    secondary_groups=["documentation", "functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Legal professional (attorney, clerk). Invitation-only case access.",
    expectations=(
        "Full legal toolkit: research, privileged notes, court filings. "
        "Can only access tenant documents via explicit tenant invitation. "
        "Can send documents to tenants for signature."
    ),
    scope_of_use=(
        "Legal professionals. Bar verification or org affiliation. "
        "Invitation-gated: tenant must invite attorney before case access."
    ),
    entry_criteria=[
        "Legal role authenticated",
        "Bar verification or org invitation complete",
        "Tenant invitation accepted (per-case)",
    ],
    exit_criteria=[
        "Legal review completed",
        "Strategy or memo generated",
        "Document sent to tenant",
    ],
    telemetry_events=[
        "legal_portal_load",
        "case_reviewed",
        "strategy_drafted",
        "legal_memo_exported",
        "tenant_invitation_verified",
        "privileged_note_created",
    ],
)


# =============================================================================
# Legal / Research Pages
# =============================================================================

CONTRACT_LAW_LIBRARY = PageContract(
    page_id="law_library",
    title="Law Library",
    route="/law-library",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["research_knowledge"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User searches statutes, reads legal guides, bookmarks resources.",
    scope_of_use="Read-only legal reference library.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Resource found or bookmarked"],
    telemetry_events=["law_library_load", "statute_searched", "guide_opened", "resource_bookmarked"],
)

CONTRACT_RESEARCH = PageContract(
    page_id="research",
    title="Legal Research",
    route="/research",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["research_knowledge"],
    secondary_groups=["documentation", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User performs deep research on tenant law topics.",
    scope_of_use="Tenant law research with jurisdiction awareness.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Research completed or saved"],
    telemetry_events=["research_load", "topic_searched", "case_law_found", "research_saved"],
)

CONTRACT_LEGAL_TRAILS = PageContract(
    page_id="legal_trails",
    title="Legal Trails",
    route="/legal-trails",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["research_knowledge", "documentation"],
    secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User explores procedural paths through the legal system.",
    scope_of_use="Guided procedural decision trees for legal navigation.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Trail completed or path selected"],
    telemetry_events=["legal_trails_load", "trail_started", "trail_step_completed", "trail_path_selected"],
)


# =============================================================================
# Document Management
# =============================================================================

CONTRACT_DOCUMENT_INTAKE = PageContract(
    page_id="document_intake",
    title="Document Intake",
    route="/document-intake",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.ADMIN, UserRole.MANAGER],
    primary_groups=["documentation"],
    secondary_groups=["functions_actions", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user with vault access.",
    expectations="User uploads and classifies documents for their case.",
    scope_of_use="Intake, classification, and initial processing of case documents.",
    entry_criteria=["User authenticated", "Vault connected"],
    exit_criteria=["Document uploaded and classified"],
    telemetry_events=["intake_load", "document_uploaded", "document_classified", "intake_complete"],
)


# =============================================================================
# Court / Legal Actions
# =============================================================================

CONTRACT_COUNTERCLAIM = PageContract(
    page_id="counterclaim",
    title="Counterclaim Builder",
    route="/counterclaim",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user with active eviction case.",
    expectations="User builds counterclaim against landlord based on tenant rights violations.",
    scope_of_use="Counterclaim drafting for eviction defense proceedings.",
    entry_criteria=["User authenticated", "Eviction case active"],
    exit_criteria=["Counterclaim drafted or added to packet"],
    telemetry_events=["counterclaim_load", "counterclaim_type_selected", "counterclaim_drafted", "counterclaim_added_to_packet"],
)

CONTRACT_CASE_BUILDER = PageContract(
    page_id="case_builder",
    title="Case Builder",
    route="/case-builder",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["documentation", "functions_actions"],
    secondary_groups=["research_knowledge", "output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User builds a structured case from facts, evidence, and timeline.",
    scope_of_use="Structured case assembly combining evidence, facts, and legal strategy.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Case structure created or updated"],
    telemetry_events=["case_builder_load", "case_fact_added", "evidence_linked", "case_structure_saved"],
)

CONTRACT_BRIEFCASE = PageContract(
    page_id="briefcase",
    title="Briefcase",
    route="/briefcase",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "output_delivery"],
    secondary_groups=["functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User organizes and reviews case documents before court.",
    scope_of_use="Pre-hearing document organization and review workspace.",
    entry_criteria=["User authenticated", "Documents in vault"],
    exit_criteria=["Documents organized for hearing"],
    telemetry_events=["briefcase_load", "document_organized", "folder_created", "briefcase_exported"],
)

CONTRACT_DAKOTA_DEFENSE = PageContract(
    page_id="dakota_defense",
    title="Dakota County Defense",
    route="/dakota-defense",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user with Dakota County eviction case.",
    expectations="User prepares jurisdiction-specific defense for Dakota County court.",
    scope_of_use="Dakota County MN-specific eviction defense workflows.",
    entry_criteria=["User authenticated", "Dakota County jurisdiction confirmed"],
    exit_criteria=["Defense prepared for Dakota County filing"],
    telemetry_events=["dakota_load", "dakota_defense_started", "dakota_form_generated", "dakota_packet_ready"],
)


# =============================================================================
# Utility / Tools
# =============================================================================

CONTRACT_PDF_TOOLS = PageContract(
    page_id="pdf_tools",
    title="PDF Tools",
    route="/pdf-tools",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User manipulates PDFs: merge, split, annotate, compress.",
    scope_of_use="PDF manipulation tools for court documents.",
    entry_criteria=["User authenticated"],
    exit_criteria=["PDF processed and saved"],
    telemetry_events=["pdf_tools_load", "pdf_merged", "pdf_split", "pdf_annotated"],
)

CONTRACT_DOCUMENT_CONVERTER = PageContract(
    page_id="document_converter",
    title="Document Converter",
    route="/document-converter",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User converts documents between formats for court filing.",
    scope_of_use="Document format conversion for filing compatibility.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Document converted successfully"],
    telemetry_events=["converter_load", "document_converted", "format_selected", "conversion_downloaded"],
)

CONTRACT_CONTACTS = PageContract(
    page_id="contacts",
    title="Contacts",
    route="/contacts",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["help_contacts"],
    secondary_groups=["functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User manages legal aid contacts, advocates, and court contacts.",
    scope_of_use="Contact management for case-related parties.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Contact added, updated, or used"],
    telemetry_events=["contacts_load", "contact_added", "contact_called", "contact_searched"],
)

CONTRACT_CORRESPONDENCE = PageContract(
    page_id="correspondence",
    title="Correspondence",
    route="/correspondence",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User composes, tracks, and archives correspondence with landlord and courts.",
    scope_of_use="Formal communication management for case documentation.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Letter composed, sent, or archived"],
    telemetry_events=["correspondence_load", "letter_composed", "letter_sent", "correspondence_archived"],
)

CONTRACT_LETTER_BUILDER = PageContract(
    page_id="letter_builder",
    title="Letter Builder",
    route="/letter-builder",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User builds formal letters using templates for tenant rights situations.",
    scope_of_use="Template-based formal letter drafting for tenants.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Letter drafted and saved or sent"],
    telemetry_events=["letter_builder_load", "template_selected", "letter_drafted", "letter_finalized"],
)


# =============================================================================
# Document Delivery Process Group
# =============================================================================

CONTRACT_DOCUMENT_DELIVERY_INBOX = PageContract(
    page_id="document_delivery_inbox",
    title="Document Delivery Inbox",
    route="/delivery/inbox",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "output_delivery"],
    secondary_groups=["functions_actions", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Tenant receiving documents, or sender checking status.",
    expectations=(
        "Tenant views PENDING documents sent by advocates, legal, or managers. "
        "Each item shows: sender identity, role, timestamp, delivery type (review/sign). "
        "Tenant must accept/sign or reject each document. Documents never auto-merge into vault. "
        "Read receipts recorded only if sender required them."
    ),
    scope_of_use=(
        "Inbound document delivery only. Stateless — documents stored in vault as PENDING items, "
        "not server-side. Tenant owns accept/reject decision. Signature overlays stored in tenant vault."
    ),
    entry_criteria=[
        "Tenant: has PENDING documents in vault",
        "Sender: checking delivery status of sent documents",
    ],
    exit_criteria=[
        "Tenant reviewed all pending items",
        "Tenant accepted/signed or rejected document(s)",
        "Sender verified delivery status",
    ],
    telemetry_events=[
        "delivery_inbox_load",
        "pending_document_viewed",
        "document_accepted",
        "document_rejected",
        "signature_required_shown",
        "read_receipt_recorded",
        "all_pending_cleared",
    ],
)

CONTRACT_DOCUMENT_DELIVERY_SEND = PageContract(
    page_id="document_delivery_send",
    title="Send Document",
    route="/delivery/send",
    roles_supported=[UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["output_delivery", "functions_actions"],
    secondary_groups=["documentation", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_NA,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Advocate, Legal, Manager, or Admin sending documents to tenant.",
    expectations=(
        "Sender selects document from vault, chooses tenant recipient, sets delivery type. "
        "Three delivery types: REVIEW REQUIRED (optional read receipt), "
        "SIGNATURE REQUIRED (always tracked, tenant must sign or reject), "
        "PROCESS SERVER (future: formal legal service). "
        "Document appears in tenant inbox as PENDING. Sender identity and timestamp recorded."
    ),
    scope_of_use=(
        "Outbound document delivery only. Legal professionals sending to tenants. "
        "Attorney access is invite-only for tenant documents but can send. "
        "All delivery metadata stored in sender and recipient vaults (stateless)."
    ),
    entry_criteria=[
        "Sender authenticated with advocate/legal/manager/admin role",
        "Document exists in sender vault",
        "Tenant recipient identified",
    ],
    exit_criteria=[
        "Document queued for delivery to tenant inbox",
        "Delivery record created in both vaults",
        "Tenant notified of pending document",
    ],
    telemetry_events=[
        "delivery_send_load",
        "recipient_selected",
        "document_selected",
        "delivery_type_set",
        "read_receipt_enabled",
        "document_sent",
        "delivery_confirmed",
    ],
)

CONTRACT_DOCUMENT_SIGNATURE = PageContract(
    page_id="document_signature",
    title="Document Signature",
    route="/delivery/sign",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["functions_actions", "output_delivery"],
    secondary_groups=["documentation", "security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Tenant signing document sent by advocate/legal, or witness/co-signer.",
    expectations=(
        "Tenant reviews document in full. Chooses to sign or reject. "
        "Signature captured via browser fill-and-sign or typed name. "
        "Signature overlay created in tenant vault with timestamp, signer identity, hash. "
        "Rejection also recorded with optional reason. "
        "Signed document becomes tenant-owned copy in vault; original PENDING cleared."
    ),
    scope_of_use=(
        "Signature capture only. Stateless — signature overlay stored in tenant vault, "
        "not server-side. Signed document is new document owned by tenant. "
        "Rejection recorded as overlay without creating new document."
    ),
    entry_criteria=[
        "Tenant has SIGNATURE REQUIRED document in inbox",
        "Document preview loaded",
    ],
    exit_criteria=[
        "Document signed and saved to vault",
        "Signature overlay created",
        "Or: document rejected with optional reason",
        "Pending item cleared from inbox",
    ],
    telemetry_events=[
        "signature_page_load",
        "document_reviewed",
        "signature_captured",
        "signature_type_selected",
        "document_signed",
        "signature_overlay_created",
        "document_rejected",
        "rejection_reason_recorded",
    ],
)

CONTRACT_DOCUMENT_REJECTION = PageContract(
    page_id="document_rejection",
    title="Document Rejection Flow",
    route="/delivery/reject",
    roles_supported=[UserRole.USER],
    primary_groups=["documentation", "functions_actions"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Tenant declining a SIGNATURE REQUIRED document from inbox.",
    expectations=(
        "Tenant declines to sign/receive a document with optional reason. "
        "Rejection is final and recorded: timestamp + reason (if provided) + tenant identity. "
        "Uploader (professional) is notified of rejection. "
        "Document remains in vault as REJECTED overlay — cannot be re-sent without new upload."
    ),
    scope_of_use=(
        "Explicit rejection pathway via Communication System. Tenant control over what they accept. "
        "Rejection is a valid, final action — no penalty to tenant. "
        "Stateless — rejection record stored as COMMUNICATION overlay in tenant vault at "
        "Semptify5.0/Vault/communications/rejections/ with 'DOCUMENT REJECTED' watermark."
    ),
    entry_criteria=[
        "Authenticated tenant",
        "SIGNATURE REQUIRED document selected from inbox",
        "Document in PENDING state",
    ],
    exit_criteria=[
        "Rejection submitted with optional reason",
        "Rejection recorded in vault as COMMUNICATION overlay with watermark",
        "Conversation message sent to uploader",
        "Pending item cleared from inbox",
    ],
    telemetry_events=[
        "rejection_flow_load",
        "rejection_reason_entered",
        "document_rejected_confirmed",
        "uploader_notified_via_conversation",
        "rejection_overlay_created",
    ],
    status=STATUS_ACTIVE,  # IMPLEMENTED 2026-04-21 via Communication System
)


# =============================================================================
# Settings / Setup
# =============================================================================

CONTRACT_SETTINGS = PageContract(
    page_id="settings",
    title="Settings",
    route="/settings",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["system_admin_monitoring"],
    secondary_groups=["security_validation"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Authenticated user.",
    expectations="User configures account, privacy, and notification preferences.",
    scope_of_use="User-scoped settings and preferences management.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Settings saved"],
    telemetry_events=["settings_load", "privacy_setting_changed", "notification_setting_changed", "settings_saved"],
)

CONTRACT_SETUP_WIZARD = PageContract(
    page_id="setup_wizard",
    title="Setup Wizard",
    route="/setup",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["welcome", "security_validation"],
    secondary_groups=["system_admin_monitoring"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_ACTIVE,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Authenticated new user completing initial setup.",
    expectations="User completes onboarding steps: storage, profile, case setup.",
    scope_of_use="First-time setup flow for new users.",
    entry_criteria=["User authenticated", "Setup not yet completed"],
    exit_criteria=["All setup steps completed"],
    telemetry_events=["setup_wizard_load", "setup_step_completed", "setup_skipped", "setup_complete"],
)


# =============================================================================
# Help / Info
# =============================================================================

CONTRACT_HELP = PageContract(
    page_id="help",
    title="Help",
    route="/help",
    roles_supported=list(UserRole),
    primary_groups=["help_contacts"],
    secondary_groups=["research_knowledge"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Public access.",
    expectations="User finds answers to questions and locates support resources.",
    scope_of_use="Help documentation, FAQs, and support contacts.",
    entry_criteria=["No auth required"],
    exit_criteria=["Question answered or support requested"],
    telemetry_events=["help_load", "help_topic_opened", "help_search", "support_requested"],
)

CONTRACT_ABOUT = PageContract(
    page_id="about",
    title="About",
    route="/about",
    roles_supported=list(UserRole),
    primary_groups=["help_contacts"],
    secondary_groups=[],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Public access.",
    expectations="User reads about Semptify's mission and team.",
    scope_of_use="Static informational page.",
    entry_criteria=["No auth required"],
    exit_criteria=["Page read"],
    telemetry_events=["about_load", "mission_section_viewed"],
)

CONTRACT_PRIVACY = PageContract(
    page_id="privacy",
    title="Privacy Policy",
    route="/privacy",
    roles_supported=list(UserRole),
    primary_groups=["help_contacts"],
    secondary_groups=[],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Public access.",
    expectations="User reviews privacy practices and data handling.",
    scope_of_use="Privacy policy and data rights disclosure.",
    entry_criteria=["No auth required"],
    exit_criteria=["Policy read"],
    telemetry_events=["privacy_load", "privacy_section_viewed"],
)


# =============================================================================
# Specialized Modules
# =============================================================================

CONTRACT_FRAUD_EXPOSURE = PageContract(
    page_id="fraud_exposure",
    title="Fraud Exposure",
    route="/fraud-exposure",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["output_delivery", "documentation"],
    secondary_groups=["research_knowledge", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user with documented fraud evidence.",
    expectations="User organizes fraud evidence and generates exposure report.",
    scope_of_use="Documenting and reporting landlord fraud.",
    entry_criteria=["User authenticated", "Fraud evidence present"],
    exit_criteria=["Fraud report generated or filed"],
    telemetry_events=["fraud_exposure_load", "fraud_evidence_added", "fraud_type_classified", "fraud_report_generated"],
)

CONTRACT_PUBLIC_EXPOSURE = PageContract(
    page_id="public_exposure",
    title="Public Exposure",
    route="/public-exposure",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["output_delivery"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user who has completed an exposure report.",
    expectations="User reviews public-facing exposure summary before sharing.",
    scope_of_use="Public accountability reporting for landlord violations.",
    entry_criteria=["User authenticated", "Exposure report completed"],
    exit_criteria=["Exposure published or saved"],
    telemetry_events=["public_exposure_load", "exposure_reviewed", "exposure_published", "exposure_shared"],
)

CONTRACT_COMPLAINTS = PageContract(
    page_id="complaints",
    title="Complaints",
    route="/complaints",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["output_delivery", "functions_actions"],
    secondary_groups=["documentation", "help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_LINKED,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User files complaints with housing authorities, HUD, or local agencies.",
    scope_of_use="Regulatory complaint filing and tracking.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Complaint filed or drafted"],
    telemetry_events=["complaints_load", "complaint_type_selected", "complaint_drafted", "complaint_submitted"],
)

CONTRACT_COMMAND_CENTER = PageContract(
    page_id="command_center",
    title="Command Center",
    route="/command-center",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER, UserRole.LEGAL],
    primary_groups=["system_admin_monitoring", "functions_actions"],
    secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Role in (admin, manager, legal).",
    expectations="Operator monitors system status, triggers workflows, reviews alerts.",
    scope_of_use="System operations dashboard for platform management.",
    entry_criteria=["Admin or manager authenticated"],
    exit_criteria=["Action taken or status reviewed"],
    telemetry_events=["command_center_load", "workflow_triggered", "alert_reviewed", "system_action_taken"],
)

CONTRACT_BRAIN = PageContract(
    page_id="brain",
    title="Positronic Brain",
    route="/brain",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions", "research_knowledge"],
    secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User interacts with AI copilot for case guidance and research.",
    scope_of_use="AI-assisted case guidance and tenant rights education.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Guidance received or action taken"],
    telemetry_events=["brain_load", "query_submitted", "guidance_received", "action_suggested"],
)

CONTRACT_MESH_NETWORK = PageContract(
    page_id="mesh_network",
    title="Mesh Network",
    route="/mesh-network",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER],
    primary_groups=["system_admin_monitoring"],
    secondary_groups=["functions_actions"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_NA,
        system_admin_monitoring=COVERAGE_ACTIVE,
    ),
    qualification="Role in (admin, manager).",
    expectations="Operator visualizes positronic mesh workflow status and triggers.",
    scope_of_use="Mesh infrastructure monitoring and control.",
    entry_criteria=["Admin authenticated"],
    exit_criteria=["Mesh status reviewed or workflow triggered"],
    telemetry_events=["mesh_network_load", "mesh_node_viewed", "workflow_status_checked", "mesh_action_triggered"],
)

CONTRACT_REGISTER = PageContract(
    page_id="register",
    title="Register",
    route="/register",
    roles_supported=list(UserRole),
    primary_groups=["welcome", "security_validation"],
    secondary_groups=[],
    group_coverage=_full_coverage(
        welcome=COVERAGE_ACTIVE,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Public access for new user registration.",
    expectations="User creates a new Semptify account.",
    scope_of_use="Account registration only.",
    entry_criteria=["No auth required"],
    exit_criteria=["Account created, user redirected"],
    telemetry_events=["register_load", "registration_submitted", "registration_success", "registration_error"],
)

CONTRACT_HOME = PageContract(
    page_id="home",
    title="Home",
    route="/home",
    roles_supported=list(UserRole),
    primary_groups=["welcome", "security_validation"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_ACTIVE,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification=(
        "Primary landing page after onboarding and after storage setup. "
        "Also the universal fallback destination when something goes wrong anywhere in the app. "
        "Vault is always accessible from this page as a permanent fixture."
    ),
    expectations=(
        "On load, home always validates session and token health before rendering. "
        "Three possible states: "
        "(1) Cookie valid + token valid → normal home load, vault accessible. "
        "(2) Cookie missing or corrupt → look for rehome.html in client's storage root. If found: read account_id, account_type, provider → skip role selection → go to /storage-reconnect pre-filled. If NOT found: genuinely new device → redirect to /choose-role. "
        "(3) Cookie valid but storage token expired/revoked → save oauth_return_to='/home' → redirect to /storage-reconnect. "
        "Home never renders in a broken state — it always self-heals or reroutes."
    ),
    scope_of_use=(
        "Central hub and safety net. Every page in the app can fall back to /home safely. "
        "Home is the first page with full vault access visible. "
        "Vault lives as a permanent element on every page from here onward."
    ),
    entry_criteria=[
        "Reached after successful storage setup (from /storage-connecting)",
        "OR: reached as fallback from any broken or error state anywhere in the app",
        "Session health check runs on every load",
    ],
    exit_criteria=[
        "User navigates to their role area, vault, or any app section",
        "OR: health check fails → rehome.html lookup → /storage-reconnect (known user) or /choose-role (new device)",
    ],
    telemetry_events=[
        "home_load",
        "home_session_valid",
        "home_cookie_missing",
        "home_rehome_lookup_started",
        "home_rehome_found",
        "home_rehome_not_found",
        "home_token_expired",
        "home_cta_clicked",
        "home_nav_used",
        "home_vault_opened",
    ],
)

CONTRACT_FUNDING_SEARCH = PageContract(
    page_id="funding_search",
    title="Funding Search",
    route="/funding-search",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["help_contacts", "research_knowledge"],
    secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User searches for emergency housing funds, grants, and assistance programs.",
    scope_of_use="Funding and financial aid resource search.",
    entry_criteria=["User authenticated"],
    exit_criteria=["Resource found or application started"],
    telemetry_events=["funding_search_load", "funding_searched", "funding_resource_opened", "funding_applied"],
)

CONTRACT_HUD_FUNDING = PageContract(
    page_id="hud_funding",
    title="HUD Funding",
    route="/hud-funding",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["help_contacts", "research_knowledge"],
    secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_ACTIVE,
        functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED,
        help_contacts=COVERAGE_ACTIVE,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Authenticated user.",
    expectations="User explores HUD-specific funding programs and eligibility.",
    scope_of_use="HUD housing assistance and funding resources.",
    entry_criteria=["User authenticated"],
    exit_criteria=["HUD resource found or application started"],
    telemetry_events=["hud_funding_load", "hud_program_searched", "hud_eligibility_checked", "hud_resource_opened"],
)

# Low-priority / admin / dev tool contracts — minimal telemetry
CONTRACT_FOCUS = PageContract(
    page_id="focus", title="Focus Mode", route="/focus",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.", expectations="User enters distraction-free work mode.",
    scope_of_use="Focus mode workspace.",
    entry_criteria=["User authenticated"], exit_criteria=["Focus session ended"],
    telemetry_events=["focus_load", "focus_session_started", "focus_session_ended"],
)

CONTRACT_CAMPAIGN = PageContract(
    page_id="campaign", title="Campaign", route="/campaign",
    roles_supported=[UserRole.ADVOCATE, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["output_delivery"], secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Role in (advocate, manager, admin).", expectations="User manages tenant rights campaigns.",
    scope_of_use="Advocacy campaign management.",
    entry_criteria=["Advocate authenticated"], exit_criteria=["Campaign created or updated"],
    telemetry_events=["campaign_load", "campaign_created", "campaign_updated"],
)

CONTRACT_AUTO_ANALYSIS = PageContract(
    page_id="auto_analysis_summary", title="Auto Analysis Summary", route="/auto-analysis",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions", "output_delivery"], secondary_groups=["documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_LINKED, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.", expectations="User reviews automated document analysis results.",
    scope_of_use="Auto-analysis summary display.",
    entry_criteria=["User authenticated", "Analysis completed"], exit_criteria=["Analysis reviewed"],
    telemetry_events=["auto_analysis_load", "analysis_reviewed", "analysis_exported"],
)

CONTRACT_EVALUATION_REPORT = PageContract(
    page_id="evaluation_report", title="Evaluation Report", route="/evaluation-report",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER, UserRole.LEGAL],
    primary_groups=["system_admin_monitoring", "output_delivery"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Role in (admin, manager, legal).", expectations="Admin reviews system evaluation metrics.",
    scope_of_use="Evaluation and quality reporting.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Report reviewed"],
    telemetry_events=["evaluation_report_load", "metric_reviewed", "report_exported"],
)

CONTRACT_RECOGNITION = PageContract(
    page_id="recognition", title="Recognition", route="/recognition",
    roles_supported=list(UserRole),
    primary_groups=["help_contacts"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_ACTIVE, system_admin_monitoring=COVERAGE_NA),
    qualification="Public access.", expectations="User views partner and contributor recognition.",
    scope_of_use="Recognition and attribution page.",
    entry_criteria=["No auth required"], exit_criteria=["Page read"],
    telemetry_events=["recognition_load", "recognition_viewed"],
)

CONTRACT_REGISTER_SUCCESS = PageContract(
    page_id="register_success", title="Registration Success", route="/register/success",
    roles_supported=list(UserRole),
    primary_groups=["welcome"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_ACTIVE, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Reached post-registration.", expectations="User sees confirmation and is guided to next step.",
    scope_of_use="Post-registration confirmation.",
    entry_criteria=["Registration just completed"], exit_criteria=["User proceeds to onboarding"],
    telemetry_events=["register_success_load", "onboarding_started"],
)

# Minimal admin/dev tool contracts
_ADMIN_ROLES = [UserRole.ADMIN, UserRole.MANAGER]

CONTRACT_AUTO_MODE_DEMO = PageContract(
    page_id="auto_mode_demo", title="Auto Mode Demo", route="/auto-mode-demo",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin tests auto-mode features.",
    scope_of_use="Dev/admin demo tool.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Demo completed"],
    telemetry_events=["auto_mode_demo_load", "demo_action_triggered"],
)

CONTRACT_AUTO_MODE_PANEL = PageContract(
    page_id="auto_mode_panel", title="Auto Mode Panel", route="/auto-mode-panel",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin controls auto-mode configuration.",
    scope_of_use="Auto-mode control panel.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Mode configured"],
    telemetry_events=["auto_mode_panel_load", "mode_changed"],
)

CONTRACT_GUI_NAV_HUB = PageContract(
    page_id="gui_navigation_hub", title="GUI Navigation Hub", route="/gui-navigation",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin navigates system modules.",
    scope_of_use="Admin navigation hub.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Navigation complete"],
    telemetry_events=["gui_nav_hub_load", "module_navigated"],
)

CONTRACT_PAGE_EDITOR = PageContract(
    page_id="page_editor", title="Page Editor", route="/page-editor",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin edits page content.",
    scope_of_use="Page content editor.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Page saved"],
    telemetry_events=["page_editor_load", "page_edited", "page_saved"],
)

CONTRACT_LAYOUT_BUILDER = PageContract(
    page_id="layout_builder", title="Layout Builder", route="/layout-builder",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin builds page layouts.",
    scope_of_use="Layout design tool.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Layout saved"],
    telemetry_events=["layout_builder_load", "layout_changed", "layout_saved"],
)

CONTRACT_STYLE_EDITOR = PageContract(
    page_id="style_editor", title="Style Editor", route="/style-editor",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin edits visual styles.",
    scope_of_use="Visual style customization.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Styles saved"],
    telemetry_events=["style_editor_load", "style_changed", "style_saved"],
)

CONTRACT_MODULE_CONVERTER = PageContract(
    page_id="module_converter", title="Module Converter", route="/module-converter",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin converts modules between formats.",
    scope_of_use="Module format conversion tool.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Module converted"],
    telemetry_events=["module_converter_load", "module_converted"],
)

CONTRACT_COMPONENT_CONVERTER = PageContract(
    page_id="component_converter", title="Component Converter", route="/component-converter",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin converts UI components.",
    scope_of_use="Component conversion tool.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Component converted"],
    telemetry_events=["component_converter_load", "component_converted"],
)

CONTRACT_BATCH_ANALYSIS = PageContract(
    page_id="batch_analysis_results", title="Batch Analysis Results", route="/batch-analysis",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER, UserRole.LEGAL],
    primary_groups=["output_delivery", "system_admin_monitoring"], secondary_groups=["documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin or manager.", expectations="Admin reviews batch document analysis results.",
    scope_of_use="Batch analysis result review.",
    entry_criteria=["Admin authenticated", "Batch job completed"], exit_criteria=["Results reviewed"],
    telemetry_events=["batch_analysis_load", "batch_result_viewed", "batch_exported"],
)

CONTRACT_PAGE_INDEX = PageContract(
    page_id="page_index", title="Page Index", route="/page-index",
    roles_supported=_ADMIN_ROLES, primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.", expectations="Admin browses the full page catalog.",
    scope_of_use="Internal page index/catalog.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Page navigated"],
    telemetry_events=["page_index_load", "page_index_navigated"],
)

CONTRACT_MODE_SELECTOR = PageContract(
    page_id="mode_selector", title="Mode Selector", route="/mode-selector",
    roles_supported=list(UserRole),
    primary_groups=["welcome"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_ACTIVE, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Any user.", expectations="User selects application mode.",
    scope_of_use="Mode selection UI.",
    entry_criteria=["No auth required"], exit_criteria=["Mode selected"],
    telemetry_events=["mode_selector_load", "mode_selected"],
)

CONTRACT_CRAWLER = PageContract(
    page_id="crawler", title="Court Record Crawler", route="/crawler",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER, UserRole.LEGAL, UserRole.ADVOCATE],
    primary_groups=["research_knowledge", "functions_actions"], secondary_groups=["documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_ACTIVE, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authorized user.", expectations="User initiates court record crawl for case data.",
    scope_of_use="Court record research via web crawler.",
    entry_criteria=["User authenticated"], exit_criteria=["Crawl completed or results reviewed"],
    telemetry_events=["crawler_load", "crawl_started", "crawl_completed", "crawl_result_viewed"],
)

CONTRACT_ERROR = PageContract(
    page_id="error", title="Error", route="/error",
    roles_supported=list(UserRole),
    primary_groups=["help_contacts"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_ACTIVE, system_admin_monitoring=COVERAGE_NA),
    qualification="Public access — error handler.", expectations="User sees error details and recovery path.",
    scope_of_use="Error display page.",
    entry_criteria=["Error condition triggered"], exit_criteria=["User navigates away"],
    telemetry_events=["error_page_load", "error_recovery_clicked"],
)

CONTRACT_INDEX = PageContract(
    page_id="index", title="Index", route="/index",
    roles_supported=list(UserRole),
    primary_groups=["welcome"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_ACTIVE, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Public access.", expectations="User navigates from index to their area.",
    scope_of_use="Static navigation index.",
    entry_criteria=["No auth required"], exit_criteria=["User navigates"],
    telemetry_events=["index_load", "index_nav_clicked"],
)


# =============================================================================
# Remaining Manifest Pages
# =============================================================================

CONTRACT_TENANT_DASHBOARD = PageContract(
    page_id="tenant_dashboard", title="Tenant Dashboard", route="/tenant-dashboard",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["output_delivery", "help_contacts"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_LINKED, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated tenant user.",
    expectations="Tenant reviews case status, deadlines, and next steps.",
    scope_of_use="Tenant-specific case dashboard.",
    entry_criteria=["User authenticated", "Tenant role"], exit_criteria=["Action taken or status reviewed"],
    telemetry_events=["tenant_dashboard_load", "case_status_viewed", "deadline_checked", "next_step_selected"],
)

CONTRACT_FUNCTIONX = PageContract(
    page_id="functionx", title="Function X", route="/functionx",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions"], secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User accesses experimental or extended function module.",
    scope_of_use="Extended function execution context.",
    entry_criteria=["User authenticated"], exit_criteria=["Function executed"],
    telemetry_events=["functionx_load", "function_executed", "function_result_viewed"],
)

CONTRACT_COURT_LEARNING = PageContract(
    page_id="court_learning", title="Court Learning", route="/court-learning",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["research_knowledge", "help_contacts"], secondary_groups=["documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_ACTIVE, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_ACTIVE, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User learns about court procedures, rights, and what to expect.",
    scope_of_use="Educational content about court processes.",
    entry_criteria=["User authenticated"], exit_criteria=["Module completed or saved"],
    telemetry_events=["court_learning_load", "lesson_opened", "lesson_completed", "module_bookmarked"],
)

CONTRACT_COMPLETE_JOURNEY = PageContract(
    page_id="complete_journey", title="Complete Journey", route="/complete-journey",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["welcome", "output_delivery"], secondary_groups=["documentation", "functions_actions"],
    group_coverage=_full_coverage(welcome=COVERAGE_ACTIVE, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_LINKED, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User reviews completed journey summary and outcomes.",
    scope_of_use="End-of-journey summary and next steps.",
    entry_criteria=["User authenticated", "Journey completed"], exit_criteria=["Summary reviewed"],
    telemetry_events=["complete_journey_load", "journey_summary_viewed", "outcome_exported"],
)

CONTRACT_INTERACTIVE_TIMELINE = PageContract(
    page_id="interactive_timeline", title="Interactive Timeline", route="/interactive-timeline",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User interacts with a visual case timeline.",
    scope_of_use="Interactive visual timeline for case events.",
    entry_criteria=["User authenticated"], exit_criteria=["Timeline reviewed or event added"],
    telemetry_events=["interactive_timeline_load", "event_added", "event_edited", "timeline_exported"],
)

CONTRACT_TIMELINE_BUILDER = PageContract(
    page_id="timeline_builder", title="Timeline Builder", route="/timeline-builder",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User builds a structured timeline from case events.",
    scope_of_use="Manual timeline construction for case facts.",
    entry_criteria=["User authenticated"], exit_criteria=["Timeline built and saved"],
    telemetry_events=["timeline_builder_load", "event_added", "timeline_saved", "timeline_exported"],
)

CONTRACT_TIMELINE_AUTO_BUILD = PageContract(
    page_id="timeline_auto_build", title="Timeline Auto-Build", route="/timeline-auto-build",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["functions_actions", "output_delivery"], secondary_groups=["documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="System auto-generates timeline from uploaded documents.",
    scope_of_use="Automated timeline extraction from case documents.",
    entry_criteria=["User authenticated", "Documents available"], exit_criteria=["Timeline generated"],
    telemetry_events=["timeline_auto_build_load", "auto_build_started", "timeline_generated", "timeline_reviewed"],
)

CONTRACT_DOCUMENT_CALENDAR = PageContract(
    page_id="document_calendar", title="Document Calendar", route="/document-calendar",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["output_delivery"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User views documents and deadlines on a calendar view.",
    scope_of_use="Calendar-based document and deadline visualization.",
    entry_criteria=["User authenticated"], exit_criteria=["Deadline or document reviewed"],
    telemetry_events=["document_calendar_load", "deadline_viewed", "document_opened_from_calendar"],
)

CONTRACT_MY_TENANCY = PageContract(
    page_id="my_tenancy", title="My Tenancy", route="/my-tenancy",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["research_knowledge"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_LINKED, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated tenant user.",
    expectations="User reviews and manages their tenancy profile and facts.",
    scope_of_use="Tenancy profile management page.",
    entry_criteria=["User authenticated"], exit_criteria=["Tenancy facts reviewed or updated"],
    telemetry_events=["my_tenancy_load", "tenancy_fact_updated", "lease_viewed", "tenancy_saved"],
)

CONTRACT_SAMPLE_CERTIFICATE = PageContract(
    page_id="sample_certificate", title="Sample Certificate", route="/sample-certificate",
    roles_supported=list(UserRole),
    primary_groups=["output_delivery"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_NA),
    qualification="Public or authenticated user.",
    expectations="User views a sample certificate output.",
    scope_of_use="Sample/demo output display.",
    entry_criteria=["No auth required"], exit_criteria=["Sample viewed"],
    telemetry_events=["sample_certificate_load", "sample_viewed"],
)

CONTRACT_SIDEBAR_AUTO_MODE = PageContract(
    page_id="sidebar_with_auto_mode", title="Sidebar with Auto Mode", route="/sidebar-auto-mode",
    roles_supported=_ADMIN_ROLES,
    primary_groups=["system_admin_monitoring"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin only.",
    expectations="Admin configures sidebar with auto-mode options.",
    scope_of_use="Sidebar/auto-mode configuration interface.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Sidebar configured"],
    telemetry_events=["sidebar_auto_mode_load", "sidebar_configured"],
)

CONTRACT_ROLES = PageContract(
    page_id="roles", title="Roles", route="/roles",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER],
    primary_groups=["system_admin_monitoring", "security_validation"], secondary_groups=[],
    group_coverage=_full_coverage(welcome=COVERAGE_NA, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Admin or manager.",
    expectations="Admin manages role assignments and permissions.",
    scope_of_use="Role management administration.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Role changes saved"],
    telemetry_events=["roles_load", "role_assigned", "role_revoked", "roles_saved"],
)

CONTRACT_ENTERPRISE_DASHBOARD = PageContract(
    page_id="enterprise_dashboard", title="Enterprise Dashboard", route="/enterprise-dashboard",
    roles_supported=[UserRole.ADMIN, UserRole.MANAGER, UserRole.LEGAL],
    primary_groups=["system_admin_monitoring", "output_delivery"], secondary_groups=["functions_actions"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_ACTIVE, help_contacts=COVERAGE_NA, system_admin_monitoring=COVERAGE_ACTIVE),
    qualification="Role in (admin, manager, legal).",
    expectations="Admin reviews enterprise-level metrics, org-wide case summary, resource allocation.",
    scope_of_use="Org-level operations dashboard.",
    entry_criteria=["Admin authenticated"], exit_criteria=["Metrics reviewed"],
    telemetry_events=["enterprise_dashboard_load", "metric_viewed", "org_report_exported"],
)

CONTRACT_INTAKE = PageContract(
    page_id="intake", title="Intake", route="/intake",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["documentation", "functions_actions"], secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_ACTIVE, research_knowledge=COVERAGE_NA, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User completes intake interview to establish their situation.",
    scope_of_use="Initial intake form and case context capture.",
    entry_criteria=["User authenticated"], exit_criteria=["Intake completed"],
    telemetry_events=["intake_load", "intake_step_completed", "intake_submitted", "intake_saved"],
)

CONTRACT_RESEARCH_MODULE = PageContract(
    page_id="research_module", title="Research Module", route="/research-module",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER, UserRole.ADMIN],
    primary_groups=["research_knowledge"], secondary_groups=["output_delivery", "documentation"],
    group_coverage=_full_coverage(welcome=COVERAGE_LINKED, security_validation=COVERAGE_NA,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_ACTIVE, functions_actions=COVERAGE_LINKED,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User accesses a focused research module for specific legal topics.",
    scope_of_use="Modular legal research context.",
    entry_criteria=["User authenticated"], exit_criteria=["Research module completed or saved"],
    telemetry_events=["research_module_load", "module_topic_selected", "research_completed", "research_saved"],
)

CONTRACT_JOURNEY = PageContract(
    page_id="journey", title="Journey", route="/journey",
    roles_supported=[UserRole.USER, UserRole.ADVOCATE, UserRole.LEGAL, UserRole.MANAGER],
    primary_groups=["welcome", "functions_actions"], secondary_groups=["documentation", "output_delivery"],
    group_coverage=_full_coverage(welcome=COVERAGE_ACTIVE, security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_LINKED, research_knowledge=COVERAGE_LINKED, functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_LINKED, help_contacts=COVERAGE_LINKED, system_admin_monitoring=COVERAGE_NA),
    qualification="Authenticated user.",
    expectations="User navigates their guided case journey from start to resolution.",
    scope_of_use="Guided step-by-step case journey.",
    entry_criteria=["User authenticated"], exit_criteria=["Journey step completed or journey finished"],
    telemetry_events=["journey_load", "journey_step_started", "journey_step_completed", "journey_finished"],
)

# =============================================================================
# Onboarding Flow — New Sequence
# =============================================================================

CONTRACT_ROLE_SELECTION = PageContract(
    page_id="role_selection",
    title="Choose Your Role",
    route="/choose-role",
    roles_supported=list(UserRole),
    primary_groups=["welcome", "security_validation"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_ACTIVE,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Public access — no login required. Reached from the Welcome page.",
    expectations=(
        "User sees all available roles on one screen, each with a single-sentence description. "
        "They tap their role and are routed to the storage info page."
    ),
    scope_of_use=(
        "First step of onboarding after the Welcome screen. "
        "All roles are presented equally — Tenant, Advocate, Legal, Admin. "
        "No deep explanations here; just enough to choose confidently."
    ),
    entry_criteria=[
        "User arrived from Welcome page",
        "No role cookie set yet (or role cookie was cleared)",
    ],
    exit_criteria=[
        "Exactly one role selected",
        "Role stored in session cookie",
        "User routed to /storage-info",
    ],
    telemetry_events=[
        "role_selection_load",
        "role_option_viewed",
        "role_selected",
        "role_confirmed",
    ],
)

CONTRACT_STORAGE_INFO = PageContract(
    page_id="storage_info",
    title="Connect Your Storage",
    route="/storage-info",
    roles_supported=list(UserRole),
    primary_groups=["security_validation", "welcome"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification="Reached from role selection. No login required yet.",
    expectations=(
        "User sees a short, plain-language explanation of why storage is needed and their privacy is protected. "
        "All three storage providers (Google Drive, OneDrive, Dropbox) are shown on one page. "
        "User picks one and proceeds to OAuth. "
        "On connection failure: after 2 attempts the page reloads with cookie cleared and a 'try a different provider' prompt. "
        "After 4 total failed loops the page shows a 'Contact tech support' message instead of the provider list."
    ),
    scope_of_use=(
        "Storage provider selection and education. Short and reassuring — no walls of text. "
        "Retry loop lives here: attempt 1-2 = retry same provider, attempt 3-4 = try different provider, "
        "attempt 5+ = tech support screen. "
        "TODO (FUTURE — separate process group): Storage reconnect / re-authentication is its own "
        "process group and will NOT be handled here. If a user's token expires or is revoked, "
        "the reconnect flow re-invokes OAuth independently without touching onboarding state. "
        "Design and contracts for the reconnect process group to be defined separately."
    ),
    entry_criteria=[
        "Role cookie is set",
        "Storage not yet connected (no vault token in session)",
        "Attempt counter < 5 (otherwise route to tech support screen)",
    ],
    exit_criteria=[
        "Provider selected and user sent to OAuth",
        "OR: attempt counter >= 5 and tech support message displayed",
    ],
    telemetry_events=[
        "storage_info_load",
        "storage_provider_viewed",
        "storage_provider_selected",
        "oauth_redirect_initiated",
        "storage_retry_loop",
        "storage_cookie_cleared",
        "storage_attempt_count_exceeded",
        "storage_tech_support_shown",
    ],
)

CONTRACT_STORAGE_CONNECTING = PageContract(
    page_id="storage_connecting",
    title="Setting Up Your Storage…",
    route="/storage-connecting",
    roles_supported=list(UserRole),
    primary_groups=["security_validation", "welcome"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_LINKED,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_NA,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification=(
        "Reached automatically after successful OAuth callback. "
        "User takes no action here — this is a wait-with-narrative screen."
    ),
    expectations=(
        "User lands here immediately after granting OAuth access. "
        "The page shows a calm, step-by-step progress narrative while the backend: "
        "validates the token, creates the Semptify folder, and runs the first sync. "
        "Steps are shown progressively (e.g. 'Connected → Creating your folder → First sync → All set!'). "
        "On success: auto-redirect to /home. "
        "On failure: show friendly error and link back to /storage-info to try again."
    ),
    scope_of_use=(
        "Interstitial reassurance page only. No user input is collected here. "
        "Its entire job is to hold the user's attention calmly during backend storage setup "
        "so they do not think the app has frozen or failed. "
        "Vault is not launched from here — user goes to Home and vault is always accessible from there. "
        "Document upload and vault access is a separate rework and is NOT connected to this page."
    ),
    entry_criteria=[
        "OAuth callback received with valid token",
        "Backend storage setup job has been queued",
    ],
    exit_criteria=[
        "Storage setup job reports success → auto-redirect to /home",
        "OR: setup job reports failure → show error + link to /storage-info",
    ],
    telemetry_events=[
        "storage_connecting_load",
        "storage_token_validated",
        "storage_folder_created",
        "storage_first_sync_started",
        "storage_first_sync_complete",
        "storage_setup_success",
        "storage_setup_failed",
        "storage_setup_retry_clicked",
    ],
)

# =============================================================================
# Reconnect Process Group
# =============================================================================

CONTRACT_STORAGE_RECONNECT = PageContract(
    page_id="storage_reconnect_prompt",
    title="Reconnect Your Storage",
    route="/storage-reconnect",
    roles_supported=list(UserRole),
    primary_groups=["security_validation"],
    secondary_groups=["help_contacts"],
    group_coverage=_full_coverage(
        welcome=COVERAGE_NA,
        security_validation=COVERAGE_ACTIVE,
        documentation=COVERAGE_NA,
        research_knowledge=COVERAGE_NA,
        functions_actions=COVERAGE_ACTIVE,
        output_delivery=COVERAGE_NA,
        help_contacts=COVERAGE_LINKED,
        system_admin_monitoring=COVERAGE_NA,
    ),
    qualification=(
        "Shown when a user's refresh token is missing or revoked, OR when cookie recovery via rehome.html lookup succeeds. "
        "Never shown during normal onboarding — that is a separate process group. "
        "User identity is always pre-known here: role, provider, and account_id sourced from cookie or rehome.html."
    ),
    expectations=(
        "User sees a calm, brief message explaining their storage connection needs renewal. "
        "Their provider, account_type, and account_id are pre-known — from session cookie or rehome.html. "
        "One button: reconnect with their provider — no provider or role selection needed. "
        "Before redirecting to OAuth, current URL saved to session as oauth_return_to. "
        "After OAuth callback, cookie is rebuilt from rehome.html data plus new token. "
        "User returned to exact page they came from. Fallback to /home if return_to not set."
    ),
    scope_of_use=(
        "Reconnect process group only. Completely separate from onboarding. "
        "Silent token refresh (using existing refresh token) is handled in the backend — "
        "this page is only shown when silent refresh is impossible (token revoked or missing). "
        "Return-to-origin is handled via session key oauth_return_to set before OAuth redirect "
        "and consumed by the OAuth callback handler after success."
    ),
    entry_criteria=[
        "User identity known via session cookie OR rehome.html lookup in storage root",
        "Access token expired AND refresh token missing or revoked",
        "oauth_return_to saved to session before OAuth redirect",
    ],
    exit_criteria=[
        "User clicks reconnect → sent to OAuth",
        "OR: user dismisses → sent to /home with storage-limited mode notice",
    ],
    telemetry_events=[
        "storage_reconnect_prompt_load",
        "storage_reconnect_initiated",
        "storage_reconnect_dismissed",
        "storage_reconnect_success",
        "storage_reconnect_failed",
        "storage_return_to_origin",
    ],
)

# =============================================================================
# Registry & Lookup
# =============================================================================

PAGE_CONTRACTS: dict[str, PageContract] = {
    c.page_id: c
    for c in [
        # Original 21
        CONTRACT_WELCOME,
        CONTRACT_TENANT,
        CONTRACT_TENANT_HELP,
        CONTRACT_PROFESSIONAL,
        CONTRACT_ADMIN,
        CONTRACT_LEGAL,
        CONTRACT_FUNCTIONX,
        CONTRACT_DASHBOARD,
        CONTRACT_DOCUMENTS,
        CONTRACT_VAULT,
        CONTRACT_COURT_PACKET,
        CONTRACT_EVICTION_ANSWER,
        CONTRACT_HEARING_PREP,
        CONTRACT_STORAGE_SETUP,
        CONTRACT_CRISIS_INTAKE,
        CONTRACT_TIMELINE,
        CONTRACT_CALENDAR,
        CONTRACT_DOCUMENT_VIEWER,
        CONTRACT_ZOOM_COURT,
        CONTRACT_MOTIONS,
        CONTRACT_LEGAL_ANALYSIS,
        # Guided journeys
        CONTRACT_TENANCY,
        CONTRACT_ADVOCATE_PORTAL,
        CONTRACT_ADMIN_PORTAL,
        CONTRACT_MANAGER_PORTAL,
        CONTRACT_LEGAL_PORTAL,
        # Legal / research
        CONTRACT_LAW_LIBRARY,
        CONTRACT_RESEARCH,
        CONTRACT_LEGAL_TRAILS,
        # Document management
        CONTRACT_DOCUMENT_INTAKE,
        # Court / legal actions
        CONTRACT_COUNTERCLAIM,
        CONTRACT_CASE_BUILDER,
        CONTRACT_BRIEFCASE,
        CONTRACT_DAKOTA_DEFENSE,
        # Utility / tools
        CONTRACT_PDF_TOOLS,
        CONTRACT_DOCUMENT_CONVERTER,
        CONTRACT_CONTACTS,
        CONTRACT_CORRESPONDENCE,
        CONTRACT_LETTER_BUILDER,
        # Document Delivery Process Group
        CONTRACT_DOCUMENT_DELIVERY_INBOX,
        CONTRACT_DOCUMENT_DELIVERY_SEND,
        CONTRACT_DOCUMENT_SIGNATURE,
        CONTRACT_DOCUMENT_REJECTION,  # status=active via Communication System
        # Settings / setup
        CONTRACT_SETTINGS,
        CONTRACT_SETUP_WIZARD,
        # Help / info
        CONTRACT_HELP,
        CONTRACT_ABOUT,
        CONTRACT_PRIVACY,
        CONTRACT_RECOGNITION,
        # Specialized modules
        CONTRACT_FRAUD_EXPOSURE,
        CONTRACT_PUBLIC_EXPOSURE,
        CONTRACT_COMPLAINTS,
        CONTRACT_COMMAND_CENTER,
        CONTRACT_BRAIN,
        CONTRACT_MESH_NETWORK,
        CONTRACT_FUNDING_SEARCH,
        CONTRACT_HUD_FUNDING,
        CONTRACT_CRAWLER,
        # Onboarding / registration
        CONTRACT_REGISTER,
        CONTRACT_REGISTER_SUCCESS,
        CONTRACT_HOME,
        CONTRACT_INDEX,
        CONTRACT_MODE_SELECTOR,
        # Admin / dev tools
        CONTRACT_AUTO_MODE_DEMO,
        CONTRACT_AUTO_MODE_PANEL,
        CONTRACT_GUI_NAV_HUB,
        CONTRACT_PAGE_EDITOR,
        CONTRACT_LAYOUT_BUILDER,
        CONTRACT_STYLE_EDITOR,
        CONTRACT_MODULE_CONVERTER,
        CONTRACT_COMPONENT_CONVERTER,
        CONTRACT_BATCH_ANALYSIS,
        CONTRACT_PAGE_INDEX,
        CONTRACT_AUTO_ANALYSIS,
        CONTRACT_EVALUATION_REPORT,
        CONTRACT_FOCUS,
        CONTRACT_CAMPAIGN,
        # System
        CONTRACT_ERROR,
        # Reconnect process group
        CONTRACT_STORAGE_RECONNECT,
        # Onboarding flow
        CONTRACT_ROLE_SELECTION,
        CONTRACT_STORAGE_INFO,
        CONTRACT_STORAGE_CONNECTING,
        # Remaining manifest pages
        CONTRACT_TENANT_DASHBOARD,
        CONTRACT_FUNCTIONX,
        CONTRACT_COURT_LEARNING,
        CONTRACT_COMPLETE_JOURNEY,
        CONTRACT_INTERACTIVE_TIMELINE,
        CONTRACT_TIMELINE_BUILDER,
        CONTRACT_TIMELINE_AUTO_BUILD,
        CONTRACT_DOCUMENT_CALENDAR,
        CONTRACT_MY_TENANCY,
        CONTRACT_SAMPLE_CERTIFICATE,
        CONTRACT_SIDEBAR_AUTO_MODE,
        CONTRACT_ROLES,
        CONTRACT_ENTERPRISE_DASHBOARD,
        CONTRACT_INTAKE,
        CONTRACT_RESEARCH_MODULE,
        CONTRACT_JOURNEY,
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


# =============================================================================
# COMING SOON REGISTRY - Planned Features & Todo Tracking
# =============================================================================

@dataclass
class ComingSoonFeature:
    """A planned feature with tracking for completion."""
    feature_id: str
    description: str
    page_id: str | None = None          # Links to PageContract if applicable
    depends_on: list[str] = None        # List of feature_ids that must complete first
    eta: str | None = None              # Expected completion (e.g., "Q2 2026")
    todo_items: list[str] = None        # Checklist of items to complete
    completed_items: list[str] = None   # Items already done
    notes: str = ""                     # Additional context

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.todo_items is None:
            self.todo_items = []
        if self.completed_items is None:
            self.completed_items = []

    @property
    def is_ready(self) -> bool:
        """Check if all dependencies are completed."""
        return len(self.completed_items) >= len(self.todo_items)

    @property
    def progress_pct(self) -> float:
        """Return completion percentage."""
        if not self.todo_items:
            return 0.0
        return len(self.completed_items) / len(self.todo_items) * 100


# Global coming soon registry
COMING_SOON_REGISTRY: dict[str, ComingSoonFeature] = {}


def register_coming_soon(feature: ComingSoonFeature) -> ComingSoonFeature:
    """Register a planned feature."""
    COMING_SOON_REGISTRY[feature.feature_id] = feature
    return feature


def mark_todo_complete(feature_id: str, todo_item: str) -> bool:
    """
    Mark a todo item as complete for a coming soon feature.
    Returns True if item was found and marked, False otherwise.
    """
    if feature_id not in COMING_SOON_REGISTRY:
        return False

    feature = COMING_SOON_REGISTRY[feature_id]
    if todo_item in feature.todo_items and todo_item not in feature.completed_items:
        feature.completed_items.append(todo_item)

        # Auto-promote to active if all todos done and linked to contract
        if feature.is_ready and feature.page_id:
            contract = PAGE_CONTRACTS.get(feature.page_id)
            if contract and contract.status == STATUS_COMING_SOON:
                # Note: This doesn't auto-change the contract status
                # That requires explicit user decision
                pass

        return True
    return False


def get_coming_soon_status() -> dict:
    """Get status report of all coming soon features."""
    return {
        feature_id: {
            "description": f.description,
            "progress": f"{f.progress_pct:.0f}%",
            "completed": len(f.completed_items),
            "total": len(f.todo_items),
            "ready": f.is_ready,
            "page_id": f.page_id,
        }
        for feature_id, f in COMING_SOON_REGISTRY.items()
    }


# =============================================================================
# PRE-REGISTERED COMING SOON FEATURES
# =============================================================================

# Document Rejection Flow - IMPLEMENTED via Communication System
DOCUMENT_REJECTION_COMING_SOON = register_coming_soon(
    ComingSoonFeature(
        feature_id="document_rejection_flow",
        description="Tenant can reject signature-required documents with optional reason - STORED IN VAULT",
        page_id="document_rejection",  # Links to CONTRACT_DOCUMENT_REJECTION (status=active via comms)
        eta="COMPLETE - 2026-04-21",
        depends_on=["document_delivery_send", "document_signature"],
        todo_items=[
            "Create CONTRACT_DOCUMENT_REJECTION page contract",
            "Add rejection flow to delivery router",
            "Implement rejection overlay in vault",
            "Add uploader notification on rejection",
            "Create rejection UI in static HTML",
        ],
        completed_items=[
            "Create CONTRACT_DOCUMENT_REJECTION page contract",  # ✅ Done 2026-04-21
            "Add rejection flow to delivery router",  # ✅ /api/delivery/{id}/reject
            "Implement rejection overlay in vault",  # ✅ COMMUNICATION type overlay with watermark
            "Create rejection UI in static HTML",  # ✅ document_signer.html modal
        ],
        notes="COMPLETE: Rejection records saved as COMMUNICATION overlays with 'DOCUMENT REJECTED' watermark in Semptify5.0/Vault/communications/rejections/",
    )
)

# Process Server - Future legal service feature
PROCESS_SERVER_COMING_SOON = register_coming_soon(
    ComingSoonFeature(
        feature_id="process_server",
        description="Formal legal service of process with full legal service record",
        eta="Future - legal integration required",
        depends_on=["document_delivery_system"],
        todo_items=[
            "Legal compliance review",
            "Process server integration",
            "Service of process record format",
            "Court acceptance verification",
        ],
        notes="Future feature for formal legal document service. Not in current scope.",
    )
)
