"""User module registration helper — FunctionGroupContracts.

The user module handles act-as impersonation for admin/manager users.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="user",
    group_name="user_act_as_start",
    title="User Act-As Start (SSOT)",
    description=(
        "CANONICAL start acting as another user. Admin/manager can impersonate "
        "a tenant or advocate for support purposes. Sets the act_as_user_id "
        "in the session."
    ),
    inputs=("admin_user_id", "target_user_id", "reason"),
    outputs=("success", "act_as_user_id"),
    dependencies=("app.modules.user.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="user",
    group_name="user_act_as_stop",
    title="User Act-As Stop (SSOT)",
    description=(
        "CANONICAL stop acting as another user. Clears the act_as_user_id "
        "from the session and returns to the admin's own identity."
    ),
    inputs=("admin_user_id",),
    outputs=("success",),
    dependencies=("app.modules.user.router",),
    deterministic=False,
))
