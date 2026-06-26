"""Register Tenant Feed function group contract.

Contract registered:
    - tenant_feed::feed_aggregate — aggregate all feed sources into one chronological list
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="tenant_feed",
    group_name="feed_aggregate",
    title="Tenant Feed — Aggregator (SSOT)",
    description=(
        "Merge timeline events + documents + journal + deadlines + letters into a single "
        "chronological feed (newest first). Filterable by type. "
        "All sources are existing endpoints — this is pure aggregation, no new storage. "
        "Returns a list of feed item dicts: "
        "{type, title, subtitle, timestamp_iso, timestamp_label, icon, link, metadata}."
    ),
    inputs=("user_id", "type_filter?"),
    outputs=("items", "total_count"),
    dependencies=("app.modules.tenant_feed.service",),
    deterministic=True,
))
