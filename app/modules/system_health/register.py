"""System Health module registration - FunctionGroupContracts.

Admin-only API behind /api/admin/system for the System Health & Updates hub
tile. No PII.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="system_health",
        group_name="system_health_status",
        title="System Health Status (SSOT)",
        description="CANONICAL system health summary for the admin hub tile.",
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.system_health.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/system/health",),
        allowed_prefixes=("/api/admin/system",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="system_health",
        group_name="system_health_registry",
        title="System Registry Summary (SSOT)",
        description="CANONICAL module registry summary (module counts and status).",
        inputs=(),
        outputs=("registry_summary",),
        dependencies=("app.modules.system_health.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/system/registry",),
        allowed_prefixes=("/api/admin/system",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="system_health",
        group_name="system_health_verify",
        title="System Verify Trigger (SSOT)",
        description="CANONICAL trigger a system verification pass.",
        inputs=(),
        outputs=("verify_result",),
        dependencies=("app.modules.system_health.router",),
        deterministic=False,
        tier="T0",
        allowed_routes=("/api/admin/system/verify",),
        allowed_prefixes=("/api/admin/system",),
    )
)
