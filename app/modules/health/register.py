"""Health module registration helper — FunctionGroupContracts.

The health module provides liveness, readiness, and metrics endpoints
for deployment probes and monitoring. NOT a tenant-facing module.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_liveness",
    title="Health Liveness (SSOT)",
    description=(
        "CANONICAL liveness probe. Returns 200 if the app process is "
        "running. Used by Kubernetes/Render liveness checks."
    ),
    inputs=(),
    outputs=("status", "timestamp"),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_readiness",
    title="Health Readiness (SSOT)",
    description=(
        "CANONICAL readiness probe. Returns 200 if the app is ready to "
        "serve traffic (database connected, migrations applied). "
        "Used by Kubernetes/Render readiness checks."
    ),
    inputs=(),
    outputs=("status", "checks"),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_metrics",
    title="Health Metrics (SSOT)",
    description=(
        "CANONICAL Prometheus-compatible metrics endpoint. Returns app "
        "metrics in Prometheus text format. Used by monitoring systems."
    ),
    inputs=(),
    outputs=("metrics",),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_metrics_json",
    title="Health Metrics JSON (SSOT)",
    description=(
        "CANONICAL JSON metrics endpoint for non-Prometheus consumers. "
        "Returns the same metrics as the Prometheus endpoint but as JSON."
    ),
    inputs=(),
    outputs=("metrics",),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_system_dashboard",
    title="Health System Dashboard (SSOT)",
    description=(
        "CANONICAL visual system dashboard. Returns an HTML page showing "
        "all system capabilities and health status. Admin-only."
    ),
    inputs=(),
    outputs=("html",),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="health",
    group_name="health_api_summary",
    title="Health API Summary (SSOT)",
    description=(
        "CANONICAL JSON summary of all API capabilities. Returns a "
        "programmatic summary of all endpoints and their status. "
        "Used for API discovery."
    ),
    inputs=(),
    outputs=("summary",),
    dependencies=("app.modules.health.router",),
    deterministic=True,
))
