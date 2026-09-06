"""Correspondence module registration - FunctionGroupContracts.

Admin-only hub tile for Semptify-originated emails and templates behind
/api/admin/correspondence. Wiring-only pass: list endpoints return no PII;
send returns 501 until the data model and T2 handling are designed.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="correspondence",
        group_name="correspondence_health",
        title="Correspondence Health (SSOT)",
        description="CANONICAL health check for the Correspondence hub tile.",
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.correspondence.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/correspondence/health",),
        allowed_prefixes=("/api/admin/correspondence",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="correspondence",
        group_name="correspondence_templates_list",
        title="Correspondence Templates List (SSOT)",
        description="CANONICAL list of correspondence templates. No PII.",
        inputs=(),
        outputs=("templates",),
        dependencies=("app.modules.correspondence.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/admin/correspondence/templates",),
        allowed_prefixes=("/api/admin/correspondence",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="correspondence",
        group_name="correspondence_logs_list",
        title="Correspondence Logs List (SSOT)",
        description="CANONICAL list of correspondence send logs.",
        inputs=(),
        outputs=("logs",),
        dependencies=("app.modules.correspondence.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/admin/correspondence/logs",),
        allowed_prefixes=("/api/admin/correspondence",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="correspondence",
        group_name="correspondence_send",
        title="Correspondence Send (SSOT)",
        description=(
            "CANONICAL send a Semptify-originated correspondence. Currently a "
            "stub (501) until the data model and T2 handling are designed."
        ),
        inputs=("message",),
        outputs=("send_result",),
        dependencies=("app.modules.correspondence.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/admin/correspondence/send",),
        allowed_prefixes=("/api/admin/correspondence",),
    )
)
