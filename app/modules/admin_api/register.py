"""Admin API module contract."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="admin_api",
        group_name="admin_operations",
        title="Admin Operations (SSOT)",
        description=(
            "Elevated admin maintenance endpoints under /admin/api. "
            "PUT /admin/api/logs/level sets the runtime log level. "
            "POST /admin/api/verify runs registry sync and verification. "
            "Both require a valid admin elevation cookie."
        ),
        inputs=("level?",),
        outputs=("result",),
        dependencies=(
            "app.modules.admin_api.router",
            "app.core.admin_elevation",
            "app.core.logging_service",
            "app.core.module_registry_loader",
        ),
        deterministic=False,
        tier="T2",
        allowed_routes=(
            "/admin/api/logs/level",
            "/admin/api/verify",
        ),
        allowed_prefixes=("/admin/api",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="admin_api",
        group_name="admin_public_voice_review",
        title="Admin Public Voice Review Lane (SSOT)",
        description=(
            "Review-and-respond lane backing /admin/public-voice. "
            "GET /admin/api/public-forms/pending lists voice posts, tool "
            "requests, and tenant stories awaiting review plus recent "
            "published items. POST .../voice-posts/{id}, .../tool-requests/{id}, "
            "and .../stories/{id} publish, answer, decline, or unpublish. "
            "All require a valid admin elevation cookie."
        ),
        inputs=("action", "response_text?"),
        outputs=("pending", "result"),
        dependencies=(
            "app.modules.admin_api.router",
            "app.core.admin_elevation",
            "app.models.models",
            "app.modules.context_engine.stories",
        ),
        deterministic=False,
        tier="T2",
        allowed_routes=(
            "/admin/api/public-forms/pending",
            "/admin/api/public-forms/voice-posts/{post_id}",
            "/admin/api/public-forms/tool-requests/{request_id}",
            "/admin/api/public-forms/stories/{story_id}",
        ),
        allowed_prefixes=("/admin/api/public-forms",),
    )
)
