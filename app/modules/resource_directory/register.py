"""Resource Directory module registration - FunctionGroupContracts.

Community resource directory for tenant housing-rights support. Public
list/read endpoints plus Tailscale-gated admin CRUD and CSV import.
last_verified staleness tracking is a safety requirement.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_list",
        title="Resource List (SSOT)",
        description=(
            "CANONICAL public list of community resources with category/state "
            "filters. No tenant data."
        ),
        inputs=("category?", "state?", "query?"),
        outputs=("resources", "total"),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/resources",),
        allowed_prefixes=("/api/resources", "/admin/resources"),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_get",
        title="Resource Get (SSOT)",
        description="CANONICAL public read of a single resource by ID.",
        inputs=("resource_id",),
        outputs=("resource",),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/resources/{resource_id}",),
        allowed_prefixes=("/api/resources",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_create",
        title="Resource Create (SSOT)",
        description="CANONICAL admin create of a community resource listing.",
        inputs=("resource",),
        outputs=("resource",),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=False,
        tier="T0",
        allowed_routes=("/admin/resources",),
        allowed_prefixes=("/admin/resources",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_update",
        title="Resource Update (SSOT)",
        description="CANONICAL admin update of a community resource listing.",
        inputs=("resource_id", "resource"),
        outputs=("resource",),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=False,
        tier="T0",
        allowed_routes=("/admin/resources/{resource_id}",),
        allowed_prefixes=("/admin/resources",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_delete",
        title="Resource Delete (SSOT)",
        description="CANONICAL admin delete of a community resource listing.",
        inputs=("resource_id",),
        outputs=("deleted",),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=False,
        tier="T0",
        allowed_routes=("/admin/resources/{resource_id}",),
        allowed_prefixes=("/admin/resources",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_import",
        title="Resource Bulk Import (SSOT)",
        description="CANONICAL admin bulk CSV import of community resources.",
        inputs=("csv_data",),
        outputs=("imported", "skipped", "errors"),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=False,
        tier="T0",
        allowed_routes=("/admin/resources/import",),
        allowed_prefixes=("/admin/resources",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="resource_directory",
        group_name="resource_stale_list",
        title="Resource Stale List (SSOT)",
        description=(
            "CANONICAL list of resources whose last_verified exceeds the "
            "staleness window. Feeds the weekly review."
        ),
        inputs=("days?",),
        outputs=("stale_resources",),
        dependencies=("app.modules.resource_directory.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/admin/resources/stale",),
        allowed_prefixes=("/admin/resources",),
    )
)
