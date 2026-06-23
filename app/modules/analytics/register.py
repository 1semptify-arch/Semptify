"""Analytics module registration helper — FunctionGroupContracts.

The analytics module tracks events, pageviews, and document uploads, and
provides metrics aggregation, export, and dashboard summaries. Admin-only
for all endpoints except track (which accepts events from any user).
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


# --- Event Tracking ---

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_track_event",
    title="Analytics Track Event (SSOT)",
    description=(
        "CANONICAL track a custom event. Accepts event type, properties, "
        "and user context. Used by the frontend for event tracking."
    ),
    inputs=("user_id", "event_type", "properties?"),
    outputs=("tracked", "event_id"),
    dependencies=("app.modules.analytics.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_track_pageview",
    title="Analytics Track Pageview (SSOT)",
    description=(
        "CANONICAL track a page view. Records the page URL, referrer, "
        "and user context. Used by the frontend for pageview tracking."
    ),
    inputs=("user_id", "page", "referrer?"),
    outputs=("tracked",),
    dependencies=("app.modules.analytics.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_track_document_upload",
    title="Analytics Track Document Upload (SSOT)",
    description=(
        "CANONICAL track a document upload event. Records the document "
        "ID, type, and upload context. Called after successful upload."
    ),
    inputs=("document_id", "doc_type?"),
    outputs=("tracked",),
    dependencies=("app.modules.analytics.router",),
    deterministic=False,
))

# --- Metrics & Aggregation ---

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_metrics",
    title="Analytics Metrics (SSOT)",
    description=(
        "CANONICAL aggregated metrics for a time period. Returns event "
        "counts, pageview counts, and document upload counts. "
        "Admin-only. Used by the analytics dashboard."
    ),
    inputs=("period?", "hours?"),
    outputs=("events", "pageviews", "uploads"),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_realtime_metrics",
    title="Analytics Realtime Metrics (SSOT)",
    description=(
        "CANONICAL realtime metrics. Returns current active users, "
        "events in the last minute, and pageviews in the last minute. "
        "Admin-only."
    ),
    inputs=(),
    outputs=("active_users", "events_per_minute", "pageviews_per_minute"),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_user_metrics",
    title="Analytics User Metrics (SSOT)",
    description=(
        "CANONICAL metrics for a specific user. Returns event count, "
        "pageview count, and document upload count for the user over "
        "a given time range. Admin-only."
    ),
    inputs=("user_id", "days?"),
    outputs=("events", "pageviews", "uploads"),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

# --- Events Query ---

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_recent_events",
    title="Analytics Recent Events (SSOT)",
    description=(
        "CANONICAL list of recent events. Supports filtering by event "
        "type and limit. Admin-only. Used by the analytics events viewer."
    ),
    inputs=("event_type?", "limit?"),
    outputs=("events",),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

# --- Export ---

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_export_json",
    title="Analytics Export JSON (SSOT)",
    description=(
        "CANONICAL export analytics data as JSON. Returns events and "
        "metrics for the given time range. Admin-only."
    ),
    inputs=("days?"),
    outputs=("data",),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_export_csv",
    title="Analytics Export CSV (SSOT)",
    description=(
        "CANONICAL export analytics data as CSV. Returns events and "
        "metrics for the given time range in CSV format. Admin-only."
    ),
    inputs=("days?"),
    outputs=("csv",),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

# --- Statistics & Dashboard ---

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_statistics",
    title="Analytics Statistics (SSOT)",
    description=(
        "CANONICAL analytics statistics summary. Returns total events, "
        "total users, total pageviews, and total uploads. Admin-only."
    ),
    inputs=(),
    outputs=("total_events", "total_users", "total_pageviews", "total_uploads"),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="analytics",
    group_name="analytics_dashboard",
    title="Analytics Dashboard (SSOT)",
    description=(
        "CANONICAL analytics dashboard summary. Returns aggregated "
        "metrics, recent events, and top pages. Admin-only. "
        "Used by the admin analytics dashboard page."
    ),
    inputs=(),
    outputs=("metrics", "recent_events", "top_pages"),
    dependencies=("app.modules.analytics.router",),
    deterministic=True,
))
