"""Legal Analysis module registration helper — FunctionGroupContracts.

The legal analysis module provides AI-assisted legal analysis of documents:
evidence classification, consistency checking, corroboration analysis,
timeline analysis, merit assessment, hearsay analysis, and binding status.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_classify_evidence",
    title="Legal Analysis Classify Evidence (SSOT)",
    description="CANONICAL classify a document for legal purposes. Returns evidence type and legal status.",
    inputs=("document",),
    outputs=("evidence_type", "legal_status", "confidence"),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_classify_evidence_batch",
    title="Legal Analysis Classify Evidence Batch (SSOT)",
    description="CANONICAL classify multiple documents at once. Returns evidence types and legal statuses for each.",
    inputs=("documents",),
    outputs=("classifications",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_check_consistency",
    title="Legal Analysis Check Consistency (SSOT)",
    description="CANONICAL check consistency across multiple documents and events. Returns inconsistencies and conflicts.",
    inputs=("documents", "events?"),
    outputs=("inconsistencies", "conflicts"),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_corroboration",
    title="Legal Analysis Corroboration (SSOT)",
    description="CANONICAL analyze how well evidence supports a specific claim. Returns corroboration score and supporting evidence.",
    inputs=("claim", "evidence_items"),
    outputs=("corroboration_score", "supporting_evidence"),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_corroboration_multi",
    title="Legal Analysis Corroboration Multi (SSOT)",
    description="CANONICAL analyze how well evidence supports multiple claims. Returns corroboration scores for each claim.",
    inputs=("claims", "evidence_items"),
    outputs=("scores",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_timeline",
    title="Legal Analysis Timeline (SSOT)",
    description="CANONICAL analyze timeline for legal compliance. Returns timeline gaps, conflicts, and compliance issues.",
    inputs=("events", "jurisdiction?"),
    outputs=("gaps", "conflicts", "compliance_issues"),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_assess_merit",
    title="Legal Analysis Assess Merit (SSOT)",
    description="CANONICAL comprehensive assessment of legal merit. Returns merit score, strengths, and weaknesses.",
    inputs=("case_data",),
    outputs=("merit_score", "strengths", "weaknesses"),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_assess_merit_from_case",
    title="Legal Analysis Assess Merit From Case (SSOT)",
    description="CANONICAL assess legal merit from an existing case. Returns merit score from the case's evidence and timeline.",
    inputs=("case_id", "perspective?"),
    outputs=("merit_score", "assessment"),
    dependencies=("app.modules.legal_analysis.router", "app.modules.case_builder.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_hearsay",
    title="Legal Analysis Hearsay (SSOT)",
    description="CANONICAL analyze documents for hearsay content. Returns hearsay flags and explanations.",
    inputs=("documents",),
    outputs=("hearsay_flags",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_binding_status",
    title="Legal Analysis Binding Status (SSOT)",
    description="CANONICAL analyze which documents are legally binding. Returns binding status for each document.",
    inputs=("documents",),
    outputs=("binding_statuses",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_quick_check",
    title="Legal Analysis Quick Case Check (SSOT)",
    description="CANONICAL quick legal health check for a case. Returns a summary of legal strengths and risks.",
    inputs=("case_id",),
    outputs=("health_score", "risks"),
    dependencies=("app.modules.legal_analysis.router", "app.modules.case_builder.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_evidence_types",
    title="Legal Analysis Evidence Types (SSOT)",
    description="CANONICAL list of all evidence type classifications. Returns evidence types and descriptions.",
    inputs=(),
    outputs=("evidence_types",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_legal_statuses",
    title="Legal Analysis Legal Statuses (SSOT)",
    description="CANONICAL list of all document legal status classifications. Returns statuses and descriptions.",
    inputs=(),
    outputs=("legal_statuses",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_analysis",
    group_name="legal_analysis_mn_eviction_requirements",
    title="Legal Analysis MN Eviction Requirements (SSOT)",
    description="CANONICAL Minnesota eviction notice requirements. Returns notice periods and statutory requirements.",
    inputs=(),
    outputs=("requirements",),
    dependencies=("app.modules.legal_analysis.router",),
    deterministic=True,
))
