"""Preview module registration helper — FunctionGroupContracts.

The preview module generates document previews (thumbnails, full-page)
in multiple formats. Used by the documents module to render previews.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_generate",
    title="Preview Generate (SSOT)",
    description=(
        "CANONICAL generate a preview for a document. Returns a cache_key "
        "that can be used to serve the preview. Supports thumbnail and "
        "full-page preview types."
    ),
    inputs=("document_id", "preview_type?", "user_id"),
    outputs=("cache_key", "preview_url"),
    dependencies=("app.modules.preview.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_serve",
    title="Preview Serve (SSOT)",
    description=(
        "CANONICAL serve a generated preview by cache_key. Returns the "
        "preview content (image, HTML, or text)."
    ),
    inputs=("cache_key",),
    outputs=("content", "content_type"),
    dependencies=("app.modules.preview.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_text",
    title="Preview Text (SSOT)",
    description=(
        "CANONICAL get a text preview of a document. Returns the extracted "
        "text content for the document."
    ),
    inputs=("document_id", "user_id"),
    outputs=("text",),
    dependencies=("app.modules.preview.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_info",
    title="Preview Info (SSOT)",
    description=(
        "CANONICAL get preview metadata for a document. Returns preview "
        "availability, cache status, and supported preview types."
    ),
    inputs=("document_id", "user_id"),
    outputs=("info",),
    dependencies=("app.modules.preview.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_cache_clear",
    title="Preview Cache Clear (SSOT)",
    description=(
        "CANONICAL clear the preview cache for a specific document. "
        "Forces regeneration on next preview request."
    ),
    inputs=("document_id", "user_id"),
    outputs=("cleared",),
    dependencies=("app.modules.preview.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_statistics",
    title="Preview Statistics (SSOT)",
    description=(
        "CANONICAL preview cache statistics. Returns cache size, hit rate, "
        "and document count. Admin-only."
    ),
    inputs=("user_id",),
    outputs=("stats",),
    dependencies=("app.modules.preview.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_batch_generate",
    title="Preview Batch Generate (SSOT)",
    description=(
        "CANONICAL batch-generate previews for multiple documents. Returns "
        "cache_keys for all successfully generated previews."
    ),
    inputs=("document_ids", "preview_type?", "user_id"),
    outputs=("cache_keys", "failed"),
    dependencies=("app.modules.preview.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_supported_formats",
    title="Preview Supported Formats (SSOT)",
    description=(
        "CANONICAL list of supported document formats for preview. Returns "
        "format codes and descriptions."
    ),
    inputs=(),
    outputs=("formats",),
    dependencies=("app.modules.preview.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="preview",
    group_name="preview_cache_clear_all",
    title="Preview Cache Clear All (SSOT)",
    description=(
        "CANONICAL clear all preview cache. Admin-only. Removes all "
        "cached previews, forcing regeneration."
    ),
    inputs=("user_id",),
    outputs=("cleared",),
    dependencies=("app.modules.preview.router",),
    deterministic=False,
))
