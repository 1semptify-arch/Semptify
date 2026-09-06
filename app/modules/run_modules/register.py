"""Run Modules registration - FunctionGroupContracts.

Admin-only execution surface behind /api/admin/run for operational module
health checks.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="run_modules",
        group_name="run_modules_list",
        title="Run Modules List (SSOT)",
        description="CANONICAL list of runnable module health checks.",
        inputs=(),
        outputs=("modules",),
        dependencies=("app.modules.run_modules.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/admin/run/modules",),
        allowed_prefixes=("/api/admin/run",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="run_modules",
        group_name="run_modules_run",
        title="Run Module (SSOT)",
        description="CANONICAL run a module health check by module_id.",
        inputs=("module_id",),
        outputs=("run_result",),
        dependencies=("app.modules.run_modules.router",),
        deterministic=False,
        tier="T1",
        allowed_routes=("/api/admin/run/modules/{module_id}",),
        allowed_prefixes=("/api/admin/run",),
    )
)
