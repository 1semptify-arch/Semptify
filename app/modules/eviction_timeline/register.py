"""Eviction Timeline FunctionGroupContracts.

TIER CONFIRMATION — this module is registered as T2 because timeline events
reference tenant names, dates, filings, and case context. If specific fields
later link actual court filings or exhibits, those may need T3 handling.
Brad, please confirm or correct this tier in review before the data-model
commit is finalized.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="eviction_timeline",
        group_name="eviction_timeline_module",
        title="Eviction Timeline Module (SSOT)",
        description="CANONICAL module metadata. Returns health and capabilities. T2 module — timeline events reference tenant case context; filing-linked fields may need T3 later.",
        inputs=(),
        outputs=("health",),
        dependencies=("app.modules.eviction_timeline.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/eviction-timeline/health",),
        allowed_prefixes=("/api/eviction-timeline",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="eviction_timeline",
        group_name="eviction_timeline_list",
        title="Eviction Timeline List Events (SSOT)",
        description="CANONICAL list eviction timeline events for a subject/user. Returns event metadata; document content stays in cloud overlays.",
        inputs=("user_id", "subject_id"),
        outputs=("events", "count"),
        dependencies=("app.modules.eviction_timeline.router",),
        deterministic=True,
        tier="T2",
        allowed_routes=("/api/eviction-timeline/events",),
        allowed_prefixes=("/api/eviction-timeline",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="eviction_timeline",
        group_name="eviction_timeline_create",
        title="Eviction Timeline Add Event (SSOT)",
        description="CANONICAL add an eviction timeline event. Stores structure and pointers only; narrative content and filings are cloud overlays.",
        inputs=("event", "user_id", "subject_id"),
        outputs=("event_id", "event"),
        dependencies=("app.modules.eviction_timeline.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/eviction-timeline/events",),
        allowed_prefixes=("/api/eviction-timeline",),
    )
)
