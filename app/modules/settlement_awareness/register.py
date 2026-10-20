"""Settlement Awareness module registration - FunctionGroupContracts.

Surfaces verified, human-attested housing-litigation outcomes alongside
matching citations in the Law Linker pop-out. Every record must pass the
Part 3B gate (source URL, fabrication check, human attestation, freshness)
before it can reach a tenant — see service.surfaceable.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="settlement_awareness",
        group_name="settlement_awareness_related",
        title="Settlement Awareness Related Records (SSOT)",
        description=(
            "CANONICAL tag/citation-matched read surface. Returns only records "
            "that pass every Part 3B gate (Resolved, source_url, fabrication "
            "check, human attestation, fresh <90 days). Stale or unverifiable "
            "records auto-hide — never a placeholder, never stale data."
        ),
        inputs=("citation", "subject"),
        outputs=("records", "count"),
        dependencies=("app.modules.settlement_awareness.router",),
        deterministic=True,
        allowed_routes=("/api/settlement-awareness/related",),
        allowed_prefixes=("/api/settlement-awareness",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="settlement_awareness",
        group_name="settlement_awareness_records",
        title="Settlement Awareness Intake & Resolution (SSOT)",
        description=(
            "CANONICAL operator intake, resolve, and recheck writes. Intake "
            "always lands Unresolved; resolve refuses on any unmet gate; "
            "recheck with a dead source flips is_verified off (auto-hide)."
        ),
        inputs=("record_id", "attested_by", "source_still_live"),
        outputs=("record_id", "resolution_status", "is_verified"),
        dependencies=("app.modules.settlement_awareness.router",),
        deterministic=True,
        allowed_routes=(
            "/api/settlement-awareness/records",
            "/api/settlement-awareness/recheck",
        ),
        allowed_prefixes=("/api/settlement-awareness",),
    )
)
