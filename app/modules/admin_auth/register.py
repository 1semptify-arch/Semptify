"""Admin authentication module contract."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="admin_auth",
        group_name="admin_login",
        title="Admin Login (SSOT)",
        description=(
            "Public-facing admin authentication endpoints. "
            "POST /admin/api/login-step1 validates credentials. "
            "POST /admin/api/login-step2 validates TOTP and issues the admin "
            "elevation cookie. No prior admin session is required."
        ),
        inputs=("username", "password", "totp_code?"),
        outputs=("auth_response",),
        dependencies=("app.modules.admin_auth.router", "app.core.admin_elevation"),
        deterministic=True,
        tier="T0",
        allowed_routes=(
            "/admin/api/login-step1",
            "/admin/api/login-step2",
        ),
        allowed_prefixes=("/admin/api",),
    )
)
