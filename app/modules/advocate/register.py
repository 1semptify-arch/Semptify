"""Advocate module registration helper."""

from app.core.product_manifest import ModuleEntry, ProductTier, ModuleOrigin, LifecycleStage
from app.core.module_contracts import FunctionGroupContract, register_function_group


MODULE = ModuleEntry(
    module_path="app.modules.advocate.router",
    tier=ProductTier.ADVOCATE,
    origin=ModuleOrigin.INTERNAL,
    lifecycle=LifecycleStage.BETA,
    tags=("Advocate", "Clients", "Case Management"),
)


register_function_group(FunctionGroupContract(
    module="advocate",
    group_name="advocate_clients_list",
    title="Advocate Client List (SSOT)",
    description="Returns all clients linked to the current advocate via UserRelationship.ADVOCACY.",
    inputs=("advocate_user_id",),
    outputs=("clients",),
    dependencies=("app.models.models.UserRelationship", "app.models.models.User"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="advocate",
    group_name="advocate_client_detail",
    title="Advocate Client Detail (SSOT)",
    description="Returns a single client's profile, document count, and timeline event count.",
    inputs=("advocate_user_id", "client_user_id"),
    outputs=("client", "stats"),
    dependencies=("app.models.models.UserRelationship", "app.models.models.User", "app.models.models.Document", "app.models.models.TimelineEvent"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="advocate",
    group_name="advocate_case_queue",
    title="Advocate Case Queue (SSOT)",
    description="Returns urgent and pending cases across all linked clients, sorted by urgency and recency.",
    inputs=("advocate_user_id",),
    outputs=("queue",),
    dependencies=("app.models.models.UserRelationship", "app.models.models.TimelineEvent"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="advocate",
    group_name="advocate_intake",
    title="Advocate New Intake (SSOT)",
    description="Creates an ADVOCACY UserRelationship between advocate and a new or existing tenant user.",
    inputs=("advocate_user_id", "tenant_user_id", "notes?"),
    outputs=("relationship_id",),
    dependencies=("app.models.models.UserRelationship", "app.models.models.User"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="advocate",
    group_name="advocate_client_timeline",
    title="Advocate Multi-Tenant Timeline (SSOT)",
    description="Returns merged timeline events across all linked clients, sorted by date descending.",
    inputs=("advocate_user_id", "client_user_id?"),
    outputs=("events",),
    dependencies=("app.models.models.UserRelationship", "app.models.models.TimelineEvent"),
    deterministic=True,
))
