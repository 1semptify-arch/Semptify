"""User Concerns module registration - FunctionGroupContracts.

Admin-only support queue and flagged-issues tile behind
/api/admin/user-concerns. Wiring-only pass: list/summary endpoints return no
PII; write endpoints return 501 until the T2 data model and retention policy
are designed.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="user_concerns",
        group_name="user_concerns_health",
        title="User Concerns Health (SSOT)",
        description="CANONICAL health check for the User Concerns hub tile.",
        inputs=(),
        outputs=("status",),
        dependencies=("app.modules.user_concerns.router",),
        deterministic=True,
        tier="T0",
        allowed_routes=("/api/admin/user-concerns/health",),
        allowed_prefixes=("/api/admin/user-concerns",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="user_concerns",
        group_name="user_concerns_list",
        title="User Concerns List (SSOT)",
        description="CANONICAL list of flagged user concerns in the support queue.",
        inputs=(),
        outputs=("concerns",),
        dependencies=("app.modules.user_concerns.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/admin/user-concerns/concerns",),
        allowed_prefixes=("/api/admin/user-concerns",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="user_concerns",
        group_name="user_concerns_summary",
        title="User Concerns Summary (SSOT)",
        description="CANONICAL aggregate counts for the support queue.",
        inputs=(),
        outputs=("summary",),
        dependencies=("app.modules.user_concerns.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/admin/user-concerns/summary",),
        allowed_prefixes=("/api/admin/user-concerns",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="user_concerns",
        group_name="user_concerns_flag",
        title="User Concern Flag (SSOT)",
        description=(
            "CANONICAL flag a user concern for review. Currently a stub (501) "
            "until the T2 data model is designed."
        ),
        inputs=("concern",),
        outputs=("flag_result",),
        dependencies=("app.modules.user_concerns.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/admin/user-concerns/flag",),
        allowed_prefixes=("/api/admin/user-concerns",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="user_concerns",
        group_name="user_concerns_resolve",
        title="User Concern Resolve (SSOT)",
        description=(
            "CANONICAL resolve a flagged user concern. Currently a stub (501) "
            "until the T2 data model is designed."
        ),
        inputs=("concern_id",),
        outputs=("resolve_result",),
        dependencies=("app.modules.user_concerns.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/admin/user-concerns/resolve",),
        allowed_prefixes=("/api/admin/user-concerns",),
    )
)
