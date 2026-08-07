"""Capabilities module registration helper — FunctionGroupContracts.

The capabilities module manages per-user module capabilities and overlays.
Admins can grant/revoke modules and attach overlay modules to users.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_list",
        title="Capabilities List (SSOT)",
        description="CANONICAL list all capabilities for a user. Returns enabled modules and overlays.",
        inputs=("user_id",),
        outputs=("capabilities",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_grant",
        title="Capabilities Grant Module (SSOT)",
        description="CANONICAL grant a module to a user. Admin-only. Adds the module to the user's enabled list.",
        inputs=("user_id", "module_name"),
        outputs=("success",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_revoke",
        title="Capabilities Revoke Module (SSOT)",
        description="CANONICAL revoke a module from a user. Admin-only. Removes the module from the user's enabled list.",
        inputs=("user_id", "module_name"),
        outputs=("success",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_overlay_get",
        title="Capabilities Get Overlay (SSOT)",
        description="CANONICAL get overlay modules attached to a user. Returns list of overlay module names.",
        inputs=("user_id",),
        outputs=("overlays",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_overlay_attach",
        title="Capabilities Attach Overlay (SSOT)",
        description="CANONICAL attach an overlay module to a user. Admin-only. Adds the overlay to the user.",
        inputs=("user_id", "overlay_module"),
        outputs=("success",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="capabilities",
        group_name="capabilities_overlay_detach",
        title="Capabilities Detach Overlay (SSOT)",
        description="CANONICAL detach an overlay module from a user. Admin-only. Removes the overlay from the user.",
        inputs=("user_id", "overlay_module"),
        outputs=("success",),
        dependencies=("app.modules.capabilities.router",),
        deterministic=False,
    )
)
