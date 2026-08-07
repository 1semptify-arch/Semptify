"""Dashboard module registration helper — FunctionGroupContracts.

The dashboard module assembles data from multiple modules into a single
unified view for the tenant home page. It's the orchestrator for the
tenant dashboard page.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="dashboard",
    group_name="dashboard_unified",
    title="Dashboard Unified (SSOT)",
    description=(
        "CANONICAL unified dashboard data in a single call. Assembles "
        "document summary, timeline events, upcoming deadlines, urgent "
        "issues, and contacts into one response. Used by the tenant "
        "dashboard page."
    ),
    inputs=("user_id",),
    outputs=("documents", "timeline", "deadlines", "urgent_issues", "contacts"),
    dependencies=("app.modules.dashboard.router", "app.modules.documents.router",
                  "app.modules.timeline.router", "app.modules.calendar.router"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="dashboard",
    group_name="dashboard_refresh",
    title="Dashboard Refresh (SSOT)",
    description=(
        "CANONICAL refresh dashboard with specific context. Called after "
        "a document upload or other action to refresh the affected sections. "
        "Returns only the sections that changed."
    ),
    inputs=("user_id", "context"),
    outputs=("refreshed_sections",),
    dependencies=("app.modules.dashboard.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="dashboard",
    group_name="dashboard_status_bar",
    title="Dashboard Status Bar (SSOT)",
    description=(
        "CANONICAL minimal status bar data for quick updates. Returns "
        "unread counts, urgent count, and next deadline. Used by the "
        "persistent status bar."
    ),
    inputs=("user_id",),
    outputs=("unread", "urgent", "next_deadline"),
    dependencies=("app.modules.dashboard.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="dashboard",
    group_name="dashboard_greeting",
    title="Dashboard Personalized Greeting (SSOT)",
    description=(
        "CANONICAL personalized greeting based on time of day and the "
        "user's emotional state. Returns a greeting string and optional "
        "encouragement message."
    ),
    inputs=("user_id",),
    outputs=("greeting", "encouragement?"),
    dependencies=("app.modules.dashboard.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="dashboard",
    group_name="dashboard_quick_stats",
    title="Dashboard Quick Stats (SSOT)",
    description=(
        "CANONICAL quick stats for display widgets. Returns document count, "
        "timeline event count, days active, and vault size. Used by the "
        "tenant dashboard's stats widgets."
    ),
    inputs=("user_id",),
    outputs=("document_count", "timeline_count", "days_active", "vault_size"),
    dependencies=("app.modules.dashboard.router",),
    deterministic=True,
))
