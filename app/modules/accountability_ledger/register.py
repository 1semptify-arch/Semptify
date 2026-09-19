"""Accountability Ledger module registration — FunctionGroupContracts.

The accountability ledger is the foundation data model for the accountability
platform. It provides the subject registry, documented patterns, and
political alignments that the housing_accountability pattern engine and the
future political_tracker module reference.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="accountability_ledger",
        group_name="accountability_subject_lookup",
        title="Accountability Subject Lookup (SSOT)",
        description=(
            "CANONICAL lookup of accountability subjects (landlords, LLCs, "
            "judges, politicians, agencies) by type, jurisdiction, or name. "
            "Returns the subject registry entries — public-record entity data only."
        ),
        inputs=("subject_type?", "jurisdiction?"),
        outputs=("subjects", "total"),
        dependencies=("app.modules.accountability_ledger.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/accountability-ledger/subjects",
            "/api/accountability-ledger/subjects/{subject_id}",
        ),
        allowed_prefixes=("/api/accountability-ledger",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="accountability_ledger",
        group_name="accountability_pattern_lookup",
        title="Accountability Pattern Lookup (SSOT)",
        description=(
            "CANONICAL lookup of documented, evidence-backed accountability "
            "patterns by subject, type, or jurisdiction. Every pattern ties "
            "to public-record references — no narrative, no accusations."
        ),
        inputs=("subject_id?", "pattern_type?"),
        outputs=("patterns", "total"),
        dependencies=("app.modules.accountability_ledger.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/accountability-ledger/patterns",
        ),
        allowed_prefixes=("/api/accountability-ledger",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="accountability_ledger",
        group_name="accountability_alignment_lookup",
        title="Accountability Political Alignment Lookup (SSOT)",
        description=(
            "CANONICAL lookup of political alignments (campaign donations, "
            "voting records, ruling patterns, public statements) for "
            "politicians and judges. Each entry ties to a public-record source."
        ),
        inputs=("subject_id?", "alignment_type?"),
        outputs=("alignments", "total"),
        dependencies=("app.modules.accountability_ledger.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/accountability-ledger/alignments",
        ),
        allowed_prefixes=("/api/accountability-ledger",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="accountability_ledger",
        group_name="accountability_record_requests",
        title="Accountability Public-Records Request Tracking (SSOT)",
        description=(
            "CANONICAL FOIA / Data Practices / Sunshine request tracker "
            "(workflow ported from app-pmas). File a request against an "
            "agency, record the statutory deadline, and track the lifecycle "
            "submitted -> acknowledged -> fulfilled/denied/withdrawn; "
            "overdue is computed on read, never stored. Operator workbench "
            "data — not tenant documents."
        ),
        inputs=("agency_target", "records_requested", "deadline_date?", "subject_id?"),
        outputs=("requests", "effective_status"),
        dependencies=("app.modules.accountability_ledger.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/accountability-ledger/requests",
            "/api/accountability-ledger/requests/{request_id}",
        ),
        allowed_prefixes=("/api/accountability-ledger",),
    )
)
