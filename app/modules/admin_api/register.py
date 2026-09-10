"""Admin API module contract."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="admin_api",
        group_name="admin_operations",
        title="Admin Operations (SSOT)",
        description=(
            "Elevated admin maintenance endpoints under /admin/api. "
            "PUT /admin/api/logs/level sets the runtime log level. "
            "POST /admin/api/verify runs registry sync and verification. "
            "Both require a valid admin elevation cookie."
        ),
        inputs=("level?",),
        outputs=("result",),
        dependencies=(
            "app.modules.admin_api.router",
            "app.core.admin_elevation",
            "app.core.logging_service",
            "app.core.module_registry_loader",
        ),
        deterministic=False,
        tier="T2",
        allowed_routes=(
            "/admin/api/logs/level",
            "/admin/api/verify",
        ),
        allowed_prefixes=("/admin/api",),
    )
)
