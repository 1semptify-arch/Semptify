"""Search module registration helper — FunctionGroupContracts.

The search module provides full-text and metadata search across the
tenant's vault documents. It indexes documents on upload and provides
quick, advanced, and suggestion search endpoints.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_global",
    title="Search Global (SSOT)",
    description=(
        "CANONICAL global search across all of the tenant's documents. "
        "Returns results grouped by category (documents, timeline, contacts). "
        "Used by the tenant search bar."
    ),
    inputs=("q", "limit?"),
    outputs=("results", "total"),
    dependencies=("app.modules.search.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_advanced",
    title="Search Advanced (SSOT)",
    description=(
        "CANONICAL advanced search with type filtering. Supports "
        "full_text, metadata, content, and hybrid search modes. "
        "Used by the advanced search page."
    ),
    inputs=("q", "search_type?"),
    outputs=("results", "total"),
    dependencies=("app.modules.search.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_suggestions",
    title="Search Suggestions (SSOT)",
    description=(
        "CANONICAL search suggestions for autocomplete. Returns partial "
        "matches as the user types. Used by the search bar's typeahead."
    ),
    inputs=("q", "limit?"),
    outputs=("suggestions", "total"),
    dependencies=("app.modules.search.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_statistics",
    title="Search Statistics (SSOT)",
    description=(
        "CANONICAL search index statistics. Returns index size, document "
        "count, and last indexed timestamp. Admin-only."
    ),
    inputs=("user_id",),
    outputs=("index_stats", "document_count"),
    dependencies=("app.modules.search.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_index_document",
    title="Search Index Document (SSOT)",
    description=(
        "CANONICAL index a document for search. Called after document "
        "processing to add the document's text and metadata to the search "
        "index."
    ),
    inputs=("document_id", "user_id"),
    outputs=("indexed", "document_id"),
    dependencies=("app.modules.search.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_remove_from_index",
    title="Search Remove From Index (SSOT)",
    description=(
        "CANONICAL remove a document from the search index. Called when "
        "a document is deleted from the vault."
    ),
    inputs=("document_id", "user_id"),
    outputs=("removed", "document_id"),
    dependencies=("app.modules.search.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="search",
    group_name="search_quick",
    title="Search Quick (SSOT)",
    description=(
        "CANONICAL quick search for lightweight queries. Returns top "
        "results without full ranking. Used by the sidebar search."
    ),
    inputs=("q", "user_id"),
    outputs=("results",),
    dependencies=("app.modules.search.router",),
    deterministic=True,
))
