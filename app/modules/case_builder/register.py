"""Case Builder module registration helper — FunctionGroupContracts.

The case builder is the tenant's eviction defense case builder. It
manages cases, timeline events, evidence, counterclaims, motions,
deadlines, defenses, and templates.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_info",
        title="Case Builder Info (SSOT)",
        description="CANONICAL case builder module information. Returns version and capabilities.",
        inputs=(),
        outputs=("info",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

# --- Cases ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_cases_list",
        title="Case Builder List Cases (SSOT)",
        description="CANONICAL list all cases for the authenticated user with computed status and progress.",
        inputs=("user_id",),
        outputs=("cases", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_case_get",
        title="Case Builder Get Case (SSOT)",
        description="CANONICAL get a specific case by ID. Returns full case details.",
        inputs=("case_id", "user_id"),
        outputs=("case",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_case_create",
        title="Case Builder Create Case (SSOT)",
        description="CANONICAL create a new case for the authenticated user.",
        inputs=("case", "user_id"),
        outputs=("case_id", "case"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_case_update",
        title="Case Builder Update Case (SSOT)",
        description="CANONICAL update a case belonging to the authenticated user.",
        inputs=("case_id", "updates", "user_id"),
        outputs=("case",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_case_delete",
        title="Case Builder Delete Case (SSOT)",
        description="CANONICAL delete a case belonging to the authenticated user.",
        inputs=("case_id", "user_id"),
        outputs=("success",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Validation ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_validate_freshness",
        title="Case Builder Validate Freshness (SSOT)",
        description="CANONICAL validate case legal accuracy and freshness. Returns issues and recommendations.",
        inputs=("case_data", "user_id"),
        outputs=("valid", "issues"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_validate_minnesota",
        title="Case Builder Validate Minnesota Requirements (SSOT)",
        description="CANONICAL validate Minnesota-specific legal requirements for a case.",
        inputs=("case_data", "user_id"),
        outputs=("valid", "issues"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_validate_court_forms",
        title="Case Builder Validate Court Forms (SSOT)",
        description="CANONICAL validate that case data is complete for court form generation.",
        inputs=("case_data", "user_id"),
        outputs=("valid", "issues"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_freshness_recommendations",
        title="Case Builder Freshness Recommendations (SSOT)",
        description="CANONICAL get recommendations for improving case legal freshness.",
        inputs=("case_data", "user_id"),
        outputs=("recommendations",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

# --- Intake ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_intake_complaint",
        title="Case Builder Intake Complaint (SSOT)",
        description="CANONICAL create a case from a complaint document. Simple intake flow.",
        inputs=("intake", "user_id"),
        outputs=("case_id", "case"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Timeline Events ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_timeline_get",
        title="Case Builder Get Timeline (SSOT)",
        description="CANONICAL get all timeline events for a case.",
        inputs=("case_id", "user_id"),
        outputs=("timeline", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_timeline_add",
        title="Case Builder Add Timeline Event (SSOT)",
        description="CANONICAL add a timeline event to a case.",
        inputs=("case_id", "event", "user_id"),
        outputs=("event_id", "event"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_timeline_delete",
        title="Case Builder Delete Timeline Event (SSOT)",
        description="CANONICAL delete a timeline event from a case.",
        inputs=("case_id", "event_id", "user_id"),
        outputs=("success",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Evidence ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_evidence_get",
        title="Case Builder Get Evidence (SSOT)",
        description="CANONICAL get all evidence for a case.",
        inputs=("case_id", "user_id"),
        outputs=("evidence", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_evidence_add",
        title="Case Builder Add Evidence (SSOT)",
        description="CANONICAL add evidence to a case.",
        inputs=("case_id", "evidence", "user_id"),
        outputs=("evidence_id",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Counterclaims ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_counterclaims_get",
        title="Case Builder Get Counterclaims (SSOT)",
        description="CANONICAL get all counterclaims for a case.",
        inputs=("case_id", "user_id"),
        outputs=("counterclaims", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_counterclaim_add",
        title="Case Builder Add Counterclaim (SSOT)",
        description="CANONICAL add a counterclaim to a case.",
        inputs=("case_id", "claim", "user_id"),
        outputs=("counterclaim_id",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Motions ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_motions_get",
        title="Case Builder Get Motions (SSOT)",
        description="CANONICAL get all motions for a case.",
        inputs=("case_id", "user_id"),
        outputs=("motions", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_motion_add",
        title="Case Builder Add Motion (SSOT)",
        description="CANONICAL add a motion to a case.",
        inputs=("case_id", "motion", "user_id"),
        outputs=("motion_id",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Deadlines ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_deadlines_get",
        title="Case Builder Get Deadlines (SSOT)",
        description="CANONICAL get all deadlines for a case.",
        inputs=("case_id", "user_id"),
        outputs=("deadlines", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_deadline_add",
        title="Case Builder Add Deadline (SSOT)",
        description="CANONICAL add a deadline to a case.",
        inputs=("case_id", "deadline", "user_id"),
        outputs=("deadline_id", "deadline"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_deadline_complete",
        title="Case Builder Complete Deadline (SSOT)",
        description="CANONICAL mark a deadline as complete for a case.",
        inputs=("case_id", "deadline_id", "user_id"),
        outputs=("success",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Defenses ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_defenses_get",
        title="Case Builder Get Defenses (SSOT)",
        description="CANONICAL get all defense strategies for a case.",
        inputs=("case_id", "user_id"),
        outputs=("defenses", "count"),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_defense_add",
        title="Case Builder Add Defense (SSOT)",
        description="CANONICAL add a defense strategy to a case.",
        inputs=("case_id", "defense", "user_id"),
        outputs=("defense_id",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=False,
    )
)

# --- Templates ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_templates_defenses",
        title="Case Builder Defense Templates (SSOT)",
        description="CANONICAL list of available defense templates. Returns defense types and descriptions.",
        inputs=(),
        outputs=("templates",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

# --- Attorney Intake Packet Export ---

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_intake_packet_export",
        title="Case Builder Attorney Intake Packet Export (SSOT)",
        description=(
            "CANONICAL export a streamlined, chronological, evidence-labeled "
            "intake packet for first-time attorney review. Facts and dates only. "
            "Distinct from court_packet module export (which is court-filing-ready). "
            "Returns: case identification, chronological timeline, evidence index, "
            "pending deadlines. No recommendations, no editorializing."
        ),
        inputs=("case_id", "user_id"),
        outputs=("packet",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_intake_packet_export_pdf",
        title="Case Builder Attorney Intake Packet Export PDF (SSOT)",
        description=(
            "CANONICAL download the intake packet as a formatted PDF. "
            "Facts and dates only — no recommendations or editorializing."
        ),
        inputs=("case_id", "user_id"),
        outputs=("pdf_bytes",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_intake_packet_export_zip",
        title="Case Builder Attorney Intake Packet Export ZIP (SSOT)",
        description=(
            "CANONICAL download the intake packet as a ZIP containing the JSON "
            "packet, a formatted PDF, and a plain-text evidence index. "
            "Facts and dates only — no recommendations or editorializing."
        ),
        inputs=("case_id", "user_id"),
        outputs=("zip_bytes",),
        dependencies=("app.modules.case_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="case_builder",
        group_name="case_builder_curated_packet_export",
        title="Case Builder Curated Packet Export (SSOT)",
        description=(
            "CANONICAL export a curated packet ZIP from case evidence. "
            "Produces clean/ original copies, marked/ copies with highlight/note/footnote "
            "annotations appended, and a summary/ report. "
            "Overlay types are configurable; document_ids can be supplied or inferred from case evidence."
        ),
        inputs=(
            "case_id",
            "user_id",
            "document_ids?",
            "include_clean?",
            "include_marked?",
            "include_summary?",
            "overlay_types?",
        ),
        outputs=("zip_bytes", "filename"),
        dependencies=("app.modules.case_builder.router", "app.modules.case_builder.packet_export"),
        deterministic=True,
    )
)
