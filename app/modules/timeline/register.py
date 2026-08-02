"""Timeline module registration helper — FunctionGroupContracts.

The timeline is the RECORD pillar's chronology layer. It assembles every event
in the tenant's case into a single chronological view — document uploads,
detected issues, journal entries, deadlines, and manual events. This is the
tenant's "story of what happened" and is the home page of the tenant GUI.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="timeline",
        group_name="timeline_unified_view",
        title="Timeline Unified View (SSOT)",
        description=(
            "CANONICAL unified timeline view. Assembles events from all sources "
            "(documents, journal, deadlines, issues, manual entries) into a single "
            "chronological list with filtering by date range, source, and severity. "
            "This is the primary view for the tenant timeline page."
        ),
        inputs=("user_id", "start_date?", "end_date?", "sources?", "severity?"),
        outputs=("events", "total", "date_range"),
        dependencies=("app.modules.timeline.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="timeline",
        group_name="timeline_date_range",
        title="Timeline Date Range Info (SSOT)",
        description=(
            "CANONICAL date range metadata for the user's timeline. Returns the "
            "earliest and latest event dates, plus the span in days. "
            "Used by the timeline UI for navigation and default view."
        ),
        inputs=("user_id",),
        outputs=("earliest_date", "latest_date", "span_days"),
        dependencies=("app.modules.timeline.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="timeline",
        group_name="timeline_create_event",
        title="Timeline Create Event (SSOT)",
        description=(
            "CANONICAL manual creation of a timeline event. The tenant can add "
            "events that aren't from documents — conversations, phone calls, "
            "visits, observations. Each event has a date, title, description, "
            "and optional severity."
        ),
        inputs=("user_id", "date", "title", "description?", "severity?", "source?"),
        outputs=("event_id", "created_at"),
        dependencies=("app.modules.timeline.router",),
        deterministic=False,
    )
)
