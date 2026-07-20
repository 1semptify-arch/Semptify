"""Packet Builder module contracts."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="packet_builder",
        group_name="packet_builder_build",
        title="Packet Builder Build (SSOT)",
        description=(
            "CANONICAL build a curated document packet. Accepts vault_ids, case_id, "
            "or folder_id. Returns packet_id, item_count, and download_url."
        ),
        inputs=(
            "user_id",
            "mode",
            "vault_ids?",
            "case_id?",
            "folder_id?",
            "include_highlights",
            "include_notes",
            "include_footnotes",
            "name?",
        ),
        outputs=("packet_id", "item_count", "download_url"),
        dependencies=("app.modules.packet_builder.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="packet_builder",
        group_name="packet_builder_get",
        title="Packet Builder Get (SSOT)",
        description="CANONICAL retrieve packet metadata by packet_id.",
        inputs=("packet_id", "user_id"),
        outputs=("packet_id", "name", "mode", "item_count", "created_at", "source", "documents"),
        dependencies=("app.modules.packet_builder.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="packet_builder",
        group_name="packet_builder_download",
        title="Packet Builder Download (SSOT)",
        description="CANONICAL download packet as zip or pdf.",
        inputs=("packet_id", "format", "mode?", "user_id"),
        outputs=("content", "filename", "media_type"),
        dependencies=("app.modules.packet_builder.router",),
        deterministic=True,
    )
)
