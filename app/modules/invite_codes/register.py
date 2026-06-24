"""Invite Codes module registration helper — FunctionGroupContracts.

The invite codes module handles organization invite codes. Advocates
validate codes during onboarding; managers/admins create and manage them.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_validate",
    title="Invite Codes Validate (SSOT)",
    description="CANONICAL validate an invite code during onboarding. Returns whether the code is valid and active.",
    inputs=("code",),
    outputs=("valid", "organization_id?"),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_redeem",
    title="Invite Codes Redeem (SSOT)",
    description="CANONICAL redeem an invite code. Marks the code as used and links the user to the organization.",
    inputs=("code", "user_id"),
    outputs=("success", "organization_id"),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_create",
    title="Invite Codes Create (SSOT)",
    description="CANONICAL create a new invite code. Manager/admin only. Returns the new code.",
    inputs=("manager_user_id", "organization_id", "max_uses?", "expires_at?"),
    outputs=("code",),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_list",
    title="Invite Codes List (SSOT)",
    description="CANONICAL list all invite codes for the current user's organization. Manager/admin only.",
    inputs=("manager_user_id",),
    outputs=("codes",),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_delete",
    title="Invite Codes Deactivate (SSOT)",
    description="CANONICAL deactivate an invite code. Manager/admin only. Marks the code as inactive.",
    inputs=("code", "manager_user_id"),
    outputs=("success",),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="invite_codes",
    group_name="invite_codes_stats",
    title="Invite Codes Stats (SSOT)",
    description="CANONICAL get detailed statistics about a specific invite code. Manager/admin only.",
    inputs=("code", "manager_user_id"),
    outputs=("stats",),
    dependencies=("app.modules.invite_codes.router",),
    deterministic=True,
))
