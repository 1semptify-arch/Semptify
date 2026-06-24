"""Core System module registration helper — FunctionGroupContracts.

The core system module provides system health, status, config, session
management, logging, and statistics endpoints.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_health_check",
    title="Core System Health Check (SSOT)",
    description="CANONICAL health check endpoint for core system.",
    inputs=(),
    outputs=("status",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_status",
    title="Core System Status (SSOT)",
    description="CANONICAL get detailed system status.",
    inputs=("user_id",),
    outputs=("status",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_config_get",
    title="Core System Get Config (SSOT)",
    description="CANONICAL get system configuration (safe, non-sensitive).",
    inputs=("user_id",),
    outputs=("config",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_config_update",
    title="Core System Update Config (SSOT)",
    description="CANONICAL update system configuration.",
    inputs=("user_id", "config"),
    outputs=("success",),
    dependencies=("app.modules.core_system.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_session_create",
    title="Core System Create Session (SSOT)",
    description="CANONICAL create a new user session.",
    inputs=("session_request",),
    outputs=("session_id",),
    dependencies=("app.modules.core_system.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_session_validate",
    title="Core System Validate Session (SSOT)",
    description="CANONICAL validate a user session by ID.",
    inputs=("session_id",),
    outputs=("valid",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_session_destroy",
    title="Core System Destroy Session (SSOT)",
    description="CANONICAL destroy a user session by ID.",
    inputs=("session_id", "user_id"),
    outputs=("success",),
    dependencies=("app.modules.core_system.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_log_add",
    title="Core System Add Log (SSOT)",
    description="CANONICAL add a system log entry.",
    inputs=("user_id", "log_entry"),
    outputs=("success",),
    dependencies=("app.modules.core_system.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_logs_get",
    title="Core System Get Logs (SSOT)",
    description="CANONICAL get system logs with optional level, module, and limit filters.",
    inputs=("user_id", "level?", "module?", "limit?"),
    outputs=("logs",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="core_system",
    group_name="core_system_statistics",
    title="Core System Statistics (SSOT)",
    description="CANONICAL get system statistics.",
    inputs=("user_id",),
    outputs=("statistics",),
    dependencies=("app.modules.core_system.router",),
    deterministic=True,
))
