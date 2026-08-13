"""Advocate module registration helper."""

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.core.product_manifest import ModuleEntry, ProductTier

MODULE = ModuleEntry(
    module_path="app.modules.advocate.router",
    tier=ProductTier.ADVOCATE,
    origin="internal",
    lifecycle="beta",
    tags=("Advocate", "Clients", "Case Management"),
)


register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_clients_list",
        title="Advocate Client List (SSOT)",
        description="Returns all clients linked to the current advocate via UserRelationship.ADVOCACY.",
        inputs=("advocate_user_id",),
        outputs=("clients",),
        dependencies=("app.models.models.UserRelationship", "app.models.models.User"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_client_detail",
        title="Advocate Client Detail (SSOT)",
        description="Returns a single client's profile, document count, and timeline event count.",
        inputs=("advocate_user_id", "client_user_id"),
        outputs=("client", "stats"),
        dependencies=(
            "app.models.models.UserRelationship",
            "app.models.models.User",
            "app.models.models.Document",
            "app.models.models.TimelineEvent",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_case_queue",
        title="Advocate Case Queue (SSOT)",
        description="Returns urgent and pending cases across all linked clients, sorted by urgency and recency.",
        inputs=("advocate_user_id",),
        outputs=("queue",),
        dependencies=("app.models.models.UserRelationship", "app.models.models.TimelineEvent"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_intake",
        title="Advocate New Intake (SSOT)",
        description="Creates an ADVOCACY UserRelationship between advocate and a new or existing tenant user.",
        inputs=("advocate_user_id", "tenant_user_id", "notes?"),
        outputs=("relationship_id",),
        dependencies=("app.models.models.UserRelationship", "app.models.models.User"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_client_timeline",
        title="Advocate Multi-Tenant Timeline (SSOT)",
        description="Returns merged timeline events across all linked clients, sorted by date descending.",
        inputs=("advocate_user_id", "client_user_id?"),
        outputs=("events",),
        dependencies=("app.models.models.UserRelationship", "app.models.models.TimelineEvent"),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_annotate_document",
        title="Advocate Annotate Document (SSOT)",
        description=(
            "CANONICAL advocate annotation creation. Creates an overlay (NOTE, HIGHLIGHT, "
            "FOOTNOTE, or TRACKED_EDIT) on a client's document. Overlay is stored in the "
            "TENANT's cloud storage with created_by = advocate's user_id. "
            "Uses UnifiedOverlayManager.create_overlay() with real CreateOverlayRequest fields: "
            "overlay_type, document_id, vault_path, payload, metadata, ephemeral. "
            "FORBIDDEN fields: vault_id, user_id, overlay_path, overlay_data."
        ),
        inputs=("advocate_user_id", "client_user_id", "document_id", "overlay_type", "payload", "metadata?"),
        outputs=("overlay_id", "overlay_type", "document_id"),
        dependencies=(
            "app.services.unified_overlay_manager.UnifiedOverlayManager",
            "app.models.unified_overlay_models.CreateOverlayRequest",
            "app.core.overlay_types.OverlayType",
            "app.core.auto_refresh.ensure_valid_token",
            "app.services.storage.get_provider",
        ),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_list_overlays",
        title="Advocate List Document Overlays (SSOT)",
        description=(
            "CANONICAL overlay query for advocate document review. Returns all overlays on "
            "a client's document (by any creator). Uses UnifiedOverlayManager.get_overlays() "
            "with document_id filter. NO get_overlays_by_type or get_overlays_by_path methods."
        ),
        inputs=("advocate_user_id", "client_user_id", "document_id"),
        outputs=("overlays", "count"),
        dependencies=("app.services.unified_overlay_manager.UnifiedOverlayManager",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_delete_annotation",
        title="Advocate Delete Annotation (SSOT)",
        description=(
            "CANONICAL overlay deletion for advocate annotations. Only the overlay's creator "
            "(the advocate) can delete it. Uses UnifiedOverlayManager.delete_overlay(overlay_id). "
            "Original vault document is NEVER touched."
        ),
        inputs=("advocate_user_id", "client_user_id", "overlay_id"),
        outputs=("success",),
        dependencies=("app.services.unified_overlay_manager.UnifiedOverlayManager",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="advocate_invite_codes",
        title="Advocate Invite Codes (SSOT)",
        description=(
            "CANONICAL invite code listing for advocates. Advocates cannot create codes "
            "(only managers/admins can via /api/invite-codes/create). Advocates view codes "
            "from their organization via TEAM_MEMBER relationship to their manager. "
            "Codes are filtered to active, non-expired, with remaining uses."
        ),
        inputs=("advocate_user_id",),
        outputs=("codes", "count", "organization_id"),
        dependencies=(
            "app.models.models.UserRelationship",
            "app.models.models.InviteCode",
            "app.models.models.RelationshipType",
        ),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="tenant_link_advocate",
        title="Tenant Link to Advocate (SSOT)",
        description=(
            "CANONICAL tenant-initiated case sharing. Tenant enters advocate's user_id "
            "to create an ADVOCACY relationship (from=advocate, to=tenant). "
            "Verifies target user has advocate role. Idempotent: reactivates if "
            "relationship already exists but inactive. NO advocate role check on caller."
        ),
        inputs=("tenant_user_id", "advocate_user_id", "notes?"),
        outputs=("success", "message"),
        dependencies=(
            "app.models.models.UserRelationship",
            "app.models.models.RelationshipType",
            "app.core.user_context.get_role_from_user_id",
            "app.core.user_context.UserRole",
        ),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="tenant_list_advocates",
        title="Tenant List Linked Advocates (SSOT)",
        description=(
            "CANONICAL tenant query of their linked advocates. Returns all active "
            "ADVOCACY relationships where current user is the tenant (to_user_id). "
            "Includes initiated_by metadata so tenant knows who started the link."
        ),
        inputs=("tenant_user_id",),
        outputs=("advocates", "count"),
        dependencies=("app.models.models.UserRelationship",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="advocate",
        group_name="tenant_revoke_advocate",
        title="Tenant Revoke Advocate Access (SSOT)",
        description=(
            "CANONICAL tenant revocation of advocate access. Deactivates the "
            "ADVOCACY relationship. Advocate can no longer see tenant's data. "
            "Can be reactivated later via tenant_link_advocate. NO deletion of "
            "relationship record (preserved for audit)."
        ),
        inputs=("tenant_user_id", "advocate_user_id"),
        outputs=("success", "message"),
        dependencies=("app.models.models.UserRelationship",),
        deterministic=False,
    )
)
