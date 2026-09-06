"""Advanced / Dev Tools module registration - FunctionGroupContracts.

Admin-only dev tools behind /api/admin/advanced: build orchestrator status,
guardrail runs, orchestrator sync, module verify, and the PII-free cost-guard
fee-metadata check.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_health",
        title="Advanced Health (SSOT)",
        description="CANONICAL health check for the Advanced hub tile.",
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.advanced.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/advanced/health",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_tools_list",
        title="Advanced Tools List (SSOT)",
        description="CANONICAL list of available advanced/dev tools.",
        inputs=(),
        outputs=("tools",),
        dependencies=("app.modules.advanced.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/admin/advanced/tools",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_build_status",
        title="Advanced Build Status (SSOT)",
        description="CANONICAL Build Orchestrator status for the Advanced tile.",
        inputs=(),
        outputs=("build_status",),
        dependencies=("app.modules.advanced.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/admin/advanced/build",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_guardrail_run",
        title="Advanced Guardrail Run (SSOT)",
        description="CANONICAL trigger a guardrail-engine run from the Advanced tile.",
        inputs=(),
        outputs=("guardrail_result",),
        dependencies=("app.modules.advanced.router",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/admin/advanced/guardrail",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_orchestrator_sync",
        title="Advanced Orchestrator Sync (SSOT)",
        description="CANONICAL trigger an orchestrator task sync from the Advanced tile.",
        inputs=(),
        outputs=("sync_result",),
        dependencies=("app.modules.advanced.router",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/admin/advanced/sync-orchestrator",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_verify",
        title="Advanced Module Verify (SSOT)",
        description="CANONICAL verify a single module by module_id from the Advanced tile.",
        inputs=("module_id?",),
        outputs=("verify_result",),
        dependencies=("app.modules.advanced.router",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/admin/advanced/verify",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="advanced",
        group_name="advanced_cost_guard",
        title="Advanced Cost Guard - Repeated Fees (SSOT)",
        description=(
            "CANONICAL detect repeated-fee patterns from fee metadata. "
            "Counting only, no identity data."
        ),
        inputs=("fees",),
        outputs=("detected_patterns",),
        dependencies=("app.modules.advanced.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/advanced/cost-guard/detect-repeated-fees",),
        allowed_prefixes=("/api/admin/advanced",),
    )
)
