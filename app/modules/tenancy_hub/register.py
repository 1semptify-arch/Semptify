"""Tenancy Hub module registration helper — FunctionGroupContracts.

The tenancy hub is a unified case management system. It aggregates
parties, property, lease, payments, documents, events, issues, and
legal cases into a single tenancy case.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# --- Case Management ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_case_create",
        title="Tenancy Hub Create Case (SSOT)",
        description="CANONICAL create a new tenancy case. Returns the new case with ID.",
        inputs=("user_id", "case_data"),
        outputs=("case_id", "case"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_cases_list",
        title="Tenancy Hub List Cases (SSOT)",
        description="CANONICAL list all tenancy cases for a user. Returns cases sorted by date.",
        inputs=("user_id",),
        outputs=("cases",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_case_get",
        title="Tenancy Hub Get Case (SSOT)",
        description="CANONICAL get a tenancy case by ID. Returns full case details.",
        inputs=("case_id",),
        outputs=("case",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_case_summary",
        title="Tenancy Hub Case Summary (SSOT)",
        description="CANONICAL get a summary of a tenancy case. Returns a condensed view with key info.",
        inputs=("case_id",),
        outputs=("summary",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Parties ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_party_add",
        title="Tenancy Hub Add Party (SSOT)",
        description="CANONICAL add a party to a tenancy case. Party can be landlord, tenant, witness, etc.",
        inputs=("case_id", "party"),
        outputs=("success", "party_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_parties_list",
        title="Tenancy Hub List Parties (SSOT)",
        description="CANONICAL list all parties in a tenancy case. Supports filtering by role.",
        inputs=("case_id", "role?"),
        outputs=("parties",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Property ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_property_set",
        title="Tenancy Hub Set Property (SSOT)",
        description="CANONICAL set the property for a tenancy case. Includes address, unit, and property details.",
        inputs=("case_id", "property"),
        outputs=("success", "property"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_property_get",
        title="Tenancy Hub Get Property (SSOT)",
        description="CANONICAL get the property for a tenancy case.",
        inputs=("case_id",),
        outputs=("property",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Lease ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_lease_set",
        title="Tenancy Hub Set Lease (SSOT)",
        description="CANONICAL set the lease terms for a tenancy case. Includes rent, deposit, term, etc.",
        inputs=("case_id", "lease"),
        outputs=("success", "lease"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_lease_get",
        title="Tenancy Hub Get Lease (SSOT)",
        description="CANONICAL get the lease terms for a tenancy case.",
        inputs=("case_id",),
        outputs=("lease",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Payments ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_payment_add",
        title="Tenancy Hub Add Payment (SSOT)",
        description="CANONICAL add a payment record to a tenancy case. Includes amount, date, and type.",
        inputs=("case_id", "payment"),
        outputs=("success", "payment_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_payments_list",
        title="Tenancy Hub List Payments (SSOT)",
        description="CANONICAL list payments in a tenancy case. Supports filtering by payment type.",
        inputs=("case_id", "payment_type?"),
        outputs=("payments",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Documents ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_document_add",
        title="Tenancy Hub Add Document (SSOT)",
        description="CANONICAL add a document to a tenancy case. Links an existing vault document to the case.",
        inputs=("case_id", "document"),
        outputs=("success", "document_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_documents_list",
        title="Tenancy Hub List Documents (SSOT)",
        description="CANONICAL list documents in a tenancy case. Supports filtering by category.",
        inputs=("case_id", "category?"),
        outputs=("documents",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Events & Timeline ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_event_add",
        title="Tenancy Hub Add Event (SSOT)",
        description="CANONICAL add an event to a tenancy case timeline.",
        inputs=("case_id", "event"),
        outputs=("success", "event_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_timeline_get",
        title="Tenancy Hub Get Timeline (SSOT)",
        description="CANONICAL get the timeline for a tenancy case. Supports date range filtering.",
        inputs=("case_id", "start_date?", "end_date?"),
        outputs=("timeline",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_deadlines_get",
        title="Tenancy Hub Get Deadlines (SSOT)",
        description="CANONICAL get deadlines for a tenancy case. Supports including completed deadlines.",
        inputs=("case_id", "include_completed?"),
        outputs=("deadlines",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Issues ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_issue_add",
        title="Tenancy Hub Add Issue (SSOT)",
        description="CANONICAL add an issue to a tenancy case. Issues track problems and their resolution.",
        inputs=("case_id", "issue"),
        outputs=("success", "issue_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_issues_list",
        title="Tenancy Hub List Issues (SSOT)",
        description="CANONICAL list issues in a tenancy case. Supports filtering by status.",
        inputs=("case_id", "status?"),
        outputs=("issues",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Legal Cases ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_legal_case_add",
        title="Tenancy Hub Add Legal Case (SSOT)",
        description="CANONICAL add a legal case to a tenancy case. Links a court case to the tenancy case.",
        inputs=("case_id", "legal_case"),
        outputs=("success", "legal_case_id"),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_legal_cases_list",
        title="Tenancy Hub List Legal Cases (SSOT)",
        description="CANONICAL list all legal cases in a tenancy case. Supports filtering by status.",
        inputs=("case_id", "status?"),
        outputs=("legal_cases",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Search & Cross-Reference ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_case_search",
        title="Tenancy Hub Search Case (SSOT)",
        description="CANONICAL search across all entities in a tenancy case. Returns matching parties, documents, events, etc.",
        inputs=("case_id", "query"),
        outputs=("results",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_cross_reference",
        title="Tenancy Hub Cross-Reference (SSOT)",
        description="CANONICAL get all entities that reference the given entity in a tenancy case.",
        inputs=("case_id", "entity_type", "entity_id"),
        outputs=("references",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Context Packs ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_context_pack",
        title="Tenancy Hub Context Pack (SSOT)",
        description="CANONICAL get a context-specific pack of information for a tenancy case. Used for exports and summaries.",
        inputs=("case_id", "context_type"),
        outputs=("pack",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

# --- Metadata ---

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_enums",
        title="Tenancy Hub Enums (SSOT)",
        description="CANONICAL list of all available enum values for the tenancy hub (party roles, issue statuses, etc.).",
        inputs=(),
        outputs=("enums",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="tenancy_hub",
        group_name="tenancy_hub_context_types",
        title="Tenancy Hub Context Types (SSOT)",
        description="CANONICAL list of available context pack types for the tenancy hub.",
        inputs=(),
        outputs=("context_types",),
        dependencies=("app.modules.tenancy_hub.router",),
        deterministic=True,
    )
)
