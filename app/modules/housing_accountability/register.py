"""Housing Accountability module registration helper — FunctionGroupContracts.

The housing accountability module is the KNOW pillar's enforcement layer. It
helps tenants detect violation patterns, generate oversight packets for
regulatory agencies, and build coalition actions. Facts and documentation only
— no legal advice, no opinions.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_detect_patterns",
        title="Accountability Detect Patterns (SSOT)",
        description=(
            "CANONICAL detection of housing violation patterns from a tenant's "
            "documents. Analyzes uploaded documents for repeated violations "
            "(repeated fees, repeated entry without notice, etc.). Returns "
            "detected patterns with severity and evidence references."
        ),
        inputs=("user_id", "documents?"),
        outputs=("patterns", "total"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_oversight_packet",
        title="Accountability Oversight Packet (SSOT)",
        description=(
            "CANONICAL generation of an oversight packet for regulatory submission. "
            "Assembles detected patterns, evidence, and timeline into a formatted "
            "packet for agencies. The tenant downloads and submits it themselves."
        ),
        inputs=("user_id", "patterns", "agency?"),
        outputs=("packet", "format", "download_url"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_coalition_build",
        title="Accountability Coalition Action (SSOT)",
        description=(
            "CANONICAL build a coalition action for community organizing. "
            "Creates an anonymized summary of violations for sharing with "
            "tenant rights groups. No PII, no addresses, no names."
        ),
        inputs=("user_id", "patterns"),
        outputs=("action_summary", "share_token"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_evidence_intake",
        title="Accountability Evidence Intake (SSOT)",
        description=(
            "CANONICAL process evidence intake for housing cases. Accepts "
            "evidence descriptions and documents, categorizes them, and links "
            "them to detected patterns."
        ),
        inputs=("user_id", "evidence"),
        outputs=("processed", "linked_patterns"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_public_records_search",
        title="Accountability Public Records Search (SSOT)",
        description=(
            "CANONICAL search of public records for housing cases. Searches "
            "court records, property records, and code violations. Returns "
            "publicly available facts only."
        ),
        inputs=("query", "jurisdiction?"),
        outputs=("records", "total"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_press_release",
        title="Accountability Press Release (SSOT)",
        description=(
            "CANONICAL build a press release for housing rights advocacy. "
            "Creates an anonymized, fact-based press release from detected "
            "patterns. No PII. Tenant reviews and edits before publishing."
        ),
        inputs=("user_id", "patterns"),
        outputs=("press_release", "format"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="housing_accountability",
        group_name="accountability_dashboard",
        title="Accountability Dashboard (SSOT)",
        description=(
            "CANONICAL dashboard view of housing accountability data. Returns "
            "detected patterns, oversight packets, and coalition actions for "
            "the user. Used by the accountability dashboard page."
        ),
        inputs=("user_id",),
        outputs=("patterns", "packets", "coalitions"),
        dependencies=("app.modules.housing_accountability.router",),
        deterministic=True,
    )
)
