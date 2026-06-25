"""Manager module registration helper."""

from app.core.product_manifest import ModuleEntry, ProductTier
from app.core.module_contracts import FunctionGroupContract, register_function_group


MODULE = ModuleEntry(
    module_path="app.modules.manager.router",
    tier=ProductTier.ADMIN,
    origin="internal",
    lifecycle="beta",
    tags=("Manager", "Case Assignment", "Reporting", "Bulk Ops"),
)

register_function_group(FunctionGroupContract(
    module="manager",
    group_name="manager_assign_case",
    title="Manager Assign Case (SSOT)",
    description="Assigns an advocate to a tenant case via UserRelationship.ADVOCACY.",
    inputs=("manager_user_id", "tenant_user_id", "advocate_user_id"),
    outputs=("relationship_id",),
    dependencies=("app.models.models.UserRelationship",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="manager",
    group_name="manager_bulk_export",
    title="Manager Bulk Export (SSOT)",
    description="Exports case summary data for a set of tenant user_ids as JSON (or CSV via accept header).",
    inputs=("manager_user_id", "tenant_user_ids"),
    outputs=("export_data", "format"),
    dependencies=("app.models.models.User", "app.models.models.Document", "app.models.models.TimelineEvent"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="manager",
    group_name="manager_reports_cases",
    title="Manager Case Report (SSOT)",
    description="Generates an aggregate report of all cases in the manager's organization.",
    inputs=("manager_user_id",),
    outputs=("report",),
    dependencies=("app.models.models.User", "app.models.models.Document"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="manager",
    group_name="manager_reports_staff",
    title="Manager Staff Productivity Report (SSOT)",
    description="Generates per-staff productivity metrics (cases handled, docs reviewed, events created).",
    inputs=("manager_user_id",),
    outputs=("report",),
    dependencies=("app.models.models.User", "app.models.models.UserRelationship", "app.models.models.Document"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="manager",
    group_name="manager_update_staff_role",
    title="Manager Update Staff Role (SSOT)",
    description="Updates a staff member's default_role. Manager can set advocate or user roles only.",
    inputs=("manager_user_id", "staff_user_id", "new_role"),
    outputs=("success",),
    dependencies=("app.models.models.User",),
    deterministic=False,
))
