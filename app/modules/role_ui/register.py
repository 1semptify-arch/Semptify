"""Role UI module registration helper — FunctionGroupContracts.

The role_ui module is the routing layer after auth. It reads the user's
role and redirects them to the correct landing page. It also provides
role info, feature flags, and navigation menus per role.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_route",
    title="Role UI Route (SSOT)",
    description=(
        "CANONICAL post-auth redirect. Reads the user's role from the "
        "cookie and redirects to the role-appropriate landing page. "
        "This is the single source of truth for post-login routing."
    ),
    inputs=("user_id", "role"),
    outputs=("redirect",),
    dependencies=("app.routers.role_ui", "app.core.navigation"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_role_info",
    title="Role UI Role Info (SSOT)",
    description=(
        "CANONICAL role information for the current user. Returns role "
        "code, display name, description, and permissions. "
        "Used by the frontend for role display."
    ),
    inputs=("user_id",),
    outputs=("role", "display_name", "description", "permissions"),
    dependencies=("app.routers.role_ui",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_available_roles",
    title="Role UI Available Roles (SSOT)",
    description=(
        "CANONICAL list of all available roles with metadata. Used by "
        "the role selection page during onboarding."
    ),
    inputs=(),
    outputs=("roles",),
    dependencies=("app.routers.role_ui",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_features",
    title="Role UI Features (SSOT)",
    description=(
        "CANONICAL feature flags for the current user's role. Returns "
        "which features are enabled for the user based on their role "
        "and any admin overrides."
    ),
    inputs=("user_id",),
    outputs=("features",),
    dependencies=("app.routers.role_ui",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_navigation",
    title="Role UI Navigation Menu (SSOT)",
    description=(
        "CANONICAL navigation menu for the current user's role. Returns "
        "the menu structure with links, labels, and icons. "
        "Used by the frontend to render the nav."
    ),
    inputs=("user_id",),
    outputs=("menu",),
    dependencies=("app.routers.role_ui", "app.core.navigation"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_tool_page",
    title="Role UI Tool Page (SSOT)",
    description=(
        "CANONICAL tool page for a specific module. Returns the HTML "
        "page for the given module name, scoped to the user's role."
    ),
    inputs=("module_name", "user_id"),
    outputs=("html",),
    dependencies=("app.routers.role_ui",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="role_ui",
    group_name="role_ui_track_pageview",
    title="Role UI Track Pageview (SSOT)",
    description=(
        "CANONICAL pageview tracking stub. Accepts pageview pings "
        "silently. Full analytics enabled in ADMIN tier."
    ),
    inputs=("request",),
    outputs=("status",),
    dependencies=("app.routers.role_ui",),
    deterministic=True,
))
