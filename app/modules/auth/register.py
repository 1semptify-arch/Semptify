"""Auth module registration helper — FunctionGroupContracts.

The auth module handles authentication status, registration info, and
session validation. It's the identity layer — who is this user and are
they logged in?
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="auth",
        group_name="auth_status",
        title="Auth Status (SSOT)",
        description=(
            "CANONICAL authentication status check. Returns whether the user is "
            "authenticated, their user_id, role, and provider. Used by the "
            "frontend to determine if the user is logged in."
        ),
        inputs=("semptify_uid?",),
        outputs=("authenticated", "user_id", "role", "provider"),
        dependencies=("app.modules.auth.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="auth",
        group_name="auth_register_info",
        title="Auth Register Info (SSOT)",
        description=(
            "CANONICAL registration info endpoint. Returns information about "
            "how to register a new account. Used by the registration page."
        ),
        inputs=(),
        outputs=("info",),
        dependencies=("app.modules.auth.router",),
        deterministic=True,
    )
)
