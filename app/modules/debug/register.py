"""Debug module contract."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="debug",
        group_name="debug_maintenance",
        title="Debug Maintenance Endpoints (SSOT)",
        description=(
            "Dev-only maintenance endpoints gated by SECURITY_MODE=open. "
            "Force-migrate alembic, add legal columns, stamp alembic head, "
            "and seed a local test user. All routes return 404 when security "
            "mode is not open."
        ),
        inputs=("request",),
        outputs=("result",),
        dependencies=("app.modules.debug.router", "app.core.config"),
        deterministic=False,
        tier="T0",
        allowed_routes=(
            "/debug/force-migrate",
            "/debug/add-legal-columns",
            "/debug/stamp-alembic-head",
            "/debug/seed-test-user",
        ),
        allowed_prefixes=("/debug",),
    )
)
