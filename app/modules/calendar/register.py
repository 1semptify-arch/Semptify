"""Calendar module registration helper — FunctionGroupContracts.

The calendar module is the RECORD pillar's scheduling layer. It tracks
events, deadlines, and court dates. Events can be created manually or
synced from documents (extracted dates).
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_create_event",
    title="Calendar Create Event (SSOT)",
    description=(
        "CANONICAL create a calendar event. The tenant adds a court date, "
        "deadline, meeting, or other event with title, date, and description."
    ),
    inputs=("user_id", "title", "date", "description?", "event_type?"),
    outputs=("event_id", "event"),
    dependencies=("app.modules.calendar.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_list_events",
    title="Calendar List Events (SSOT)",
    description=(
        "CANONICAL list of calendar events in a date range. Returns events "
        "sorted by date. Used by the calendar view."
    ),
    inputs=("user_id", "start?", "end?"),
    outputs=("events", "total"),
    dependencies=("app.modules.calendar.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_upcoming_deadlines",
    title="Calendar Upcoming Deadlines (SSOT)",
    description=(
        "CANONICAL upcoming deadlines within a look-ahead window (default "
        "30 days, max 90). Returns deadlines sorted by date. "
        "Used by the tenant dashboard's deadlines section."
    ),
    inputs=("user_id", "days?"),
    outputs=("deadlines",),
    dependencies=("app.modules.calendar.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_get_event",
    title="Calendar Get Event (SSOT)",
    description=(
        "CANONICAL get a single calendar event by ID. Returns full event "
        "details."
    ),
    inputs=("event_id", "user_id"),
    outputs=("event",),
    dependencies=("app.modules.calendar.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_update_event",
    title="Calendar Update Event (SSOT)",
    description=(
        "CANONICAL update a calendar event. The tenant can edit title, "
        "date, description, or event type."
    ),
    inputs=("event_id", "user_id", "updates"),
    outputs=("event",),
    dependencies=("app.modules.calendar.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_delete_event",
    title="Calendar Delete Event (SSOT)",
    description=(
        "CANONICAL delete a calendar event. Removes the event from the "
        "calendar."
    ),
    inputs=("event_id", "user_id"),
    outputs=("status",),
    dependencies=("app.modules.calendar.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_from_documents",
    title="Calendar Events From Documents (SSOT)",
    description=(
        "CANONICAL list of events extracted from the tenant's documents. "
        "Returns dates found in documents that can be synced to the calendar."
    ),
    inputs=("user_id",),
    outputs=("events", "documents_analyzed"),
    dependencies=("app.modules.calendar.router", "app.modules.documents.router"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_sync_documents",
    title="Calendar Sync Document Events (SSOT)",
    description=(
        "CANONICAL sync events from documents to the calendar. Creates "
        "calendar events from dates extracted from documents. Optionally "
        "overwrites existing events with the same title."
    ),
    inputs=("user_id", "overwrite?"),
    outputs=("synced_event_ids",),
    dependencies=("app.modules.calendar.router", "app.modules.documents.router"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_deadline_summary",
    title="Calendar Deadline Summary (SSOT)",
    description=(
        "CANONICAL summary of upcoming deadlines. Returns counts by "
        "urgency (overdue, this week, this month). Used by the tenant "
        "dashboard's deadline summary widget."
    ),
    inputs=("user_id",),
    outputs=("overdue", "this_week", "this_month"),
    dependencies=("app.modules.calendar.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="calendar",
    group_name="calendar_notify_deadlines",
    title="Calendar Notify Deadlines (SSOT)",
    description=(
        "CANONICAL send deadline notifications. Triggers notifications "
        "for deadlines within the specified window (default 7 days)."
    ),
    inputs=("user_id", "days_ahead?"),
    outputs=("notified",),
    dependencies=("app.modules.calendar.router",),
    deterministic=False,
))
