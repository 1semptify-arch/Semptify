"""Call Manager module registration — FunctionGroupContracts."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="call_manager",
        group_name="call_script_lookup",
        title="Call Script Lookup (SSOT)",
        description=(
            "CANONICAL interactive call scripts for tenant outreach "
            "(attorney intake, agency, court clerk, follow-up). Returns the "
            "script sections with say-blocks and tap-capture items."
        ),
        inputs=("script_key",),
        outputs=("script",),
        dependencies=("app.modules.call_manager.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/call-manager/scripts",
            "/api/call-manager/scripts/{key}",
        ),
        allowed_prefixes=("/api/call-manager",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="call_manager",
        group_name="call_log_write",
        title="Call Log Write (SSOT)",
        description=(
            "CANONICAL write path for outreach call records. One save "
            "persists the call log and fans out to journal, timeline, and "
            "(when a follow-up is set) calendar."
        ),
        inputs=("contact_name", "outcome", "key_facts?", "follow_up_days?"),
        outputs=("call_id", "follow_up_at"),
        dependencies=("app.modules.call_manager.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=("/api/call-manager/calls",),
        allowed_prefixes=("/api/call-manager",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="call_manager",
        group_name="call_history_lookup",
        title="Call History & Follow-ups (SSOT)",
        description=(
            "CANONICAL read of logged calls and pending follow-ups, "
            "filterable by contact and outcome."
        ),
        inputs=("contact_id?", "outcome?"),
        outputs=("calls", "follow_ups"),
        dependencies=("app.modules.call_manager.router",),
        deterministic=True,
        tier="T1",
        allowed_routes=(
            "/api/call-manager/calls",
            "/api/call-manager/follow-ups",
        ),
        allowed_prefixes=("/api/call-manager",),
    )
)
