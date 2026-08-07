"""Eviction Defense module registration helper — FunctionGroupContracts.

The eviction defense module is the KNOW pillar's defense layer. It provides
eviction defense forms, motions, procedures, counterclaims, and document-informed
analysis. Facts only — not legal advice. Tenants use this to understand their
options and prepare documentation.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_list_forms",
    title="Eviction Defense List Forms (SSOT)",
    description=(
        "CANONICAL list of eviction defense forms. Supports filtering by "
        "category and case stage. Returns form templates with instructions."
    ),
    inputs=("category?", "stage?"),
    outputs=("forms", "total"),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_get_form",
    title="Eviction Defense Get Form (SSOT)",
    description=(
        "CANONICAL detailed view of a single eviction defense form. Returns "
        "the form template, fields, and filing instructions."
    ),
    inputs=("form_id",),
    outputs=("form",),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_list_motions",
    title="Eviction Defense List Motions (SSOT)",
    description=(
        "CANONICAL list of eviction defense motions. Supports filtering by "
        "motion type. Returns motion templates with requirements."
    ),
    inputs=("motion_type?"),
    outputs=("motions", "total"),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_list_procedures",
    title="Eviction Defense List Procedures (SSOT)",
    description=(
        "CANONICAL list of eviction defense procedures. Supports filtering by "
        "category. Returns step-by-step procedure guides."
    ),
    inputs=("category?"),
    outputs=("procedures", "total"),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_list_counterclaims",
    title="Eviction Defense List Counterclaims (SSOT)",
    description=(
        "CANONICAL list of counterclaim templates. Returns all available "
        "counterclaims a tenant may raise in an eviction case."
    ),
    inputs=(),
    outputs=("counterclaims",),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_list_defenses",
    title="Eviction Defense List Defenses (SSOT)",
    description=(
        "CANONICAL list of all available eviction defenses with explanations. "
        "Returns defense names, descriptions, and when they apply. "
        "Facts only — not a recommendation to use a specific defense."
    ),
    inputs=(),
    outputs=("defenses",),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_calculate_deadlines",
    title="Eviction Defense Calculate Deadlines (SSOT)",
    description=(
        "CANONICAL calculation of eviction case deadlines from a start date "
        "and case type. Returns all deadlines with dates and descriptions."
    ),
    inputs=("start_date", "case_type?"),
    outputs=("deadlines",),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_case_checklist",
    title="Eviction Defense Case Checklist (SSOT)",
    description=(
        "CANONICAL checklist for an eviction case at a given stage. Returns "
        "the list of steps, documents, and deadlines for the stage."
    ),
    inputs=("stage",),
    outputs=("checklist",),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_analyze",
    title="Eviction Defense Analyze Case (SSOT)",
    description=(
        "CANONICAL analysis of an eviction case based on the tenant's documents. "
        "Returns suggested defenses, counterclaims, and deadlines based on "
        "what was found in uploaded documents. Facts only — not legal advice."
    ),
    inputs=("user_id", "case_data?"),
    outputs=("defenses", "counterclaims", "deadlines", "suggested_actions"),
    dependencies=("app.modules.eviction_defense.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_quick_status",
    title="Eviction Defense Quick Status (SSOT)",
    description=(
        "CANONICAL quick status for dashboard display. Returns counts of "
        "available defenses, upcoming deadlines, and case stage. "
        "Used by the tenant dashboard's eviction defense section."
    ),
    inputs=("user_id",),
    outputs=("available_defenses", "upcoming_deadlines", "case_stage"),
    dependencies=("app.modules.eviction_defense.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_from_documents_defenses",
    title="Eviction Defense From Documents — Defenses (SSOT)",
    description=(
        "CANONICAL defense recommendations based on uploaded documents. "
        "Analyzes the tenant's documents and returns defenses that may apply "
        "based on detected issues. Facts only — not legal advice."
    ),
    inputs=("user_id",),
    outputs=("defenses",),
    dependencies=("app.modules.eviction_defense.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_from_documents_counterclaims",
    title="Eviction Defense From Documents — Counterclaims (SSOT)",
    description=(
        "CANONICAL counterclaim recommendations based on uploaded documents. "
        "Analyzes the tenant's documents and returns counterclaims that may "
        "apply. Facts only — not legal advice."
    ),
    inputs=("user_id",),
    outputs=("counterclaims",),
    dependencies=("app.modules.eviction_defense.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_from_documents_deadlines",
    title="Eviction Defense From Documents — Deadlines (SSOT)",
    description=(
        "CANONICAL deadlines calculated from uploaded documents. Returns "
        "all deadlines found in the tenant's documents, sorted by date."
    ),
    inputs=("user_id",),
    outputs=("deadlines",),
    dependencies=("app.modules.eviction_defense.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="eviction_defense",
    group_name="eviction_defense_from_documents_analysis",
    title="Eviction Defense From Documents — Full Analysis (SSOT)",
    description=(
        "CANONICAL comprehensive eviction defense analysis based on uploaded "
        "documents. Returns defenses, counterclaims, deadlines, and suggested "
        "actions in one call. Facts only — not legal advice."
    ),
    inputs=("user_id",),
    outputs=("defenses", "counterclaims", "deadlines", "suggested_actions"),
    dependencies=("app.modules.eviction_defense.router", "app.modules.documents.router"),
    deterministic=False,
))
