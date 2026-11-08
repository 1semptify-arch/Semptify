"""Executive Administration module registration — FunctionGroupContracts.

The nonprofit's own back office: formation roadmap, compliance calendar,
board governance, policies, books of record, and grant readiness. Every
route requires admin elevation (TOTP cookie or admin token); all data is
org-level — no tenant data ever enters these tables.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="executive_overview",
        title="Executive Administration Overview (SSOT)",
        description=(
            "CANONICAL org-state rollup: objective, where formation stands, "
            "the single next action, attention warnings, fiscal-year ledger "
            "summary, and grant-readiness checklist in one response."
        ),
        inputs=(),
        outputs=("objective", "where_it_stands", "next_action", "attention", "formation_progress", "profile", "roadmap", "calendar", "ledger_summary", "grant_readiness"),
        dependencies=("app.modules.executive_admin.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/",
            "/admin/executive/health",
            "/admin/executive/api/overview",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="formation_roadmap",
        title="MN + Federal 501(c)(3) Formation Roadmap (SSOT)",
        description=(
            "CANONICAL formation path: Minnesota Chapter 317A incorporation, "
            "EIN, Form 1023-EZ, Attorney General registration, sales tax "
            "exemption, annual renewal — plus cost paths. Step statuses are "
            "org records; every rule carries its source and verify date."
        ),
        inputs=("step_id", "status", "done_on?", "note?"),
        outputs=("roadmap", "steps", "cost_paths"),
        dependencies=("app.modules.executive_admin.router", "app.modules.executive_admin.knowledge"),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/api/profile",
            "/admin/executive/api/steps/{step_id}",
            "/admin/executive/api/knowledge",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="compliance_calendar",
        title="Nonprofit Compliance Calendar (SSOT)",
        description=(
            "CANONICAL dated-obligation engine: MN annual renewal, IRS 990 "
            "class, 990-T, AG annual report, 1023-EZ 27-month window, AG "
            "registration trigger, board-meeting cadence, payroll forms, and "
            "custom deadlines — computed from the ledger and profile."
        ),
        inputs=("obligation_id", "done_on?", "title?", "due?", "note?"),
        outputs=("items", "today"),
        dependencies=("app.modules.executive_admin.router", "app.modules.executive_admin.compliance"),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/api/calendar",
            "/admin/executive/api/calendar/{obligation_id}/done",
            "/admin/executive/api/deadlines",
            "/admin/executive/api/deadlines/{deadline_id}",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="board_governance",
        title="Board, Meetings, Minutes, Written Actions (SSOT)",
        description=(
            "CANONICAL governance record: board roster, quorum and notice "
            "checks (Minn. Stat. ch. 317A), meeting agendas and minutes "
            "drafts, motion tallies with recusal, and unanimous written "
            "actions."
        ),
        inputs=("member fields", "meeting fields", "action fields"),
        outputs=("members", "meetings", "actions", "check"),
        dependencies=("app.modules.executive_admin.router", "app.modules.executive_admin.governance"),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/api/board",
            "/admin/executive/api/board/{member_id}",
            "/admin/executive/api/meetings",
            "/admin/executive/api/meetings/{meeting_id}",
            "/admin/executive/api/meetings/{meeting_id}/agenda",
            "/admin/executive/api/meetings/{meeting_id}/minutes",
            "/admin/executive/api/written-actions",
            "/admin/executive/api/written-actions/{action_id}",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="org_policies",
        title="Governance Policies (SSOT)",
        description=(
            "CANONICAL policy checklist: bylaws, conflict of interest, "
            "whistleblower, document retention, gift acceptance, financial "
            "controls — outlines, sources, and adoption status."
        ),
        inputs=("policy_id", "status", "adopted_on?", "location?", "next_review?"),
        outputs=("policies",),
        dependencies=("app.modules.executive_admin.router", "app.modules.executive_admin.knowledge"),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/api/policies",
            "/admin/executive/api/policies/{policy_id}",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="books_of_record",
        title="Books of Record — 990 Ledger, Funds, Donor Receipts (SSOT)",
        description=(
            "CANONICAL bookkeeping ledger: income/expense entries in cents "
            "with IRS 990 categories, functional expense classes, and "
            "restricted-fund tagging; fiscal-year summaries shaped like the "
            "Form 990 money sections; donor acknowledgment letters; CSV "
            "export."
        ),
        inputs=("entry fields", "fiscal_year_end?"),
        outputs=("entries", "summary", "needs_acknowledgment", "csv"),
        dependencies=("app.modules.executive_admin.router", "app.modules.executive_admin.ledger"),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/admin/executive/api/ledger",
            "/admin/executive/api/ledger/{entry_id}",
            "/admin/executive/api/ledger/summary",
            "/admin/executive/api/ledger/export.csv",
            "/admin/executive/api/ledger/{entry_id}/acknowledgment",
        ),
        allowed_prefixes=("/admin/executive",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="executive_admin",
        group_name="grant_readiness",
        title="Grant Readiness Checklist (SSOT)",
        description=(
            "CANONICAL funder-readiness gate: entity filed, EIN, exemption "
            "or fiscal sponsor, board of three, bylaws and COI adopted, bank "
            "account, budget, books kept, AG registration, mission written — "
            "each item computed from live org state."
        ),
        inputs=(),
        outputs=("items", "ready", "total", "pipeline_note"),
        dependencies=("app.modules.executive_admin.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/admin/executive/api/grant-readiness",),
        allowed_prefixes=("/admin/executive",),
    )
)
