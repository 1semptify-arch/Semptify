"""Dispute Tracker FunctionGroupContracts.

TIER CONFIRMATION — this module is registered as T2 because dispute and
comparison records reference tenant PII (dispute descriptions, parties,
dates, fee/term details). Brad, please confirm or correct this tier in
review before the data-model commit is finalized.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="dispute_tracker",
        group_name="dispute_tracker_module",
        title="Dispute Tracker Module (SSOT)",
        description="CANONICAL module metadata. Returns health and capabilities. T2 module — tenant PII may appear in dispute/comparison records.",
        inputs=(),
        outputs=("health",),
        dependencies=("app.modules.dispute_tracker.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/dispute-tracker/health",),
        allowed_prefixes=("/api/dispute-tracker",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="dispute_tracker",
        group_name="dispute_tracker_list",
        title="Dispute Tracker List Disputes (SSOT)",
        description="CANONICAL list disputes for the authenticated user. Returns dispute metadata (no full PII content; content lives in cloud overlay per DB boundary rule).",
        inputs=("user_id",),
        outputs=("disputes", "count"),
        dependencies=("app.modules.dispute_tracker.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/dispute-tracker/disputes",),
        allowed_prefixes=("/api/dispute-tracker",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="dispute_tracker",
        group_name="dispute_tracker_create",
        title="Dispute Tracker Create Dispute (SSOT)",
        description="CANONICAL create a new dispute record. Stores pointers/structure only; PII content is written to the user's cloud overlay.",
        inputs=("dispute", "user_id"),
        outputs=("dispute_id", "dispute"),
        dependencies=("app.modules.dispute_tracker.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/dispute-tracker/disputes",),
        allowed_prefixes=("/api/dispute-tracker",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="dispute_tracker",
        group_name="dispute_tracker_compare",
        title="Dispute Tracker Compare (SSOT)",
        description="CANONICAL create or update a fee/term comparison entry attached to a dispute. Stores metadata and comparison summary; supporting documents are overlays.",
        inputs=("dispute_id", "comparison", "user_id"),
        outputs=("comparison_id", "comparison"),
        dependencies=("app.modules.dispute_tracker.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/dispute-tracker/compare",),
        allowed_prefixes=("/api/dispute-tracker",),
    )
)
