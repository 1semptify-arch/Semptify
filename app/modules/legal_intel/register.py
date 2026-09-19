"""Legal Intel registration — FunctionGroupContracts.

Entity/attorney/shell-LLC intelligence ported from app-legal-intel.
Operator/research workbench: public-record-sourced records ingested via
API, pattern analysis over cases and dockets.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="legal_intel",
        group_name="legal_intel_entity_lookup",
        title="Legal Intel Entity Lookup (SSOT)",
        description=(
            "CANONICAL entity/attorney lookup — 'who owns this LLC'. Find "
            "entities by name or registered agent and attorneys by bar "
            "number, with SOS identifiers and accountability-ledger links."
        ),
        inputs=("entity_name?", "bar_number?", "registered_agent?"),
        outputs=("entities", "attorney"),
        dependencies=("app.modules.legal_intel.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/legal-intel/entities",
            "/api/legal-intel/intel/entity/by-name/{entity_name}",
            "/api/legal-intel/intel/attorney/by-bar/{bar_number}",
        ),
        allowed_prefixes=("/api/legal-intel",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_intel",
        group_name="legal_intel_pattern_analysis",
        title="Legal Intel Pattern Analysis (SSOT)",
        description=(
            "CANONICAL cross-entity court-pattern analysis. Per-attorney "
            "default/settlement rates and motion timing, per-entity "
            "litigation footprint and counsel, and shell-LLC clustering by "
            "shared registered agent or address. Facts from public-record "
            "dockets — not legal conclusions."
        ),
        inputs=("attorney_id?", "entity_id?"),
        outputs=("patterns", "clusters"),
        dependencies=(
            "app.modules.legal_intel.router",
            "app.modules.legal_intel.patterns",
        ),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/legal-intel/intel/patterns/attorney/{attorney_id}",
            "/api/legal-intel/intel/patterns/entity/{entity_id}",
            "/api/legal-intel/intel/clusters/shell-llcs",
        ),
        allowed_prefixes=("/api/legal-intel",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal_intel",
        group_name="legal_intel_records",
        title="Legal Intel Record Management (SSOT)",
        description=(
            "CANONICAL ingest and browse of legal-intel records — entities, "
            "attorneys, cases, docket entries, and relationships — sourced "
            "from public records. Operator workbench data, never tenant "
            "documents."
        ),
        inputs=("entity?", "attorney?", "case?", "docket?", "relationship?"),
        outputs=("record",),
        dependencies=("app.modules.legal_intel.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/legal-intel/entities",
            "/api/legal-intel/attorneys",
            "/api/legal-intel/cases",
            "/api/legal-intel/cases/{case_id}/dockets",
            "/api/legal-intel/relationships",
        ),
        allowed_prefixes=("/api/legal-intel",),
    )
)
