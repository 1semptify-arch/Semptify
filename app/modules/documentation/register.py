"""Documentation module registration helper — FunctionGroupContracts.

The documentation module provides API documentation endpoints: OpenAPI
spec, Postman collection, Swagger UI, ReDoc, developer portal, API
reference, code examples, SDKs, support resources, and changelog.
Admin-only.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_public_api_docs",
        title="Public API Docs Surface (SSOT)",
        description=(
            "CANONICAL public API documentation surface — FastAPI-mounted "
            "Swagger UI, ReDoc UI, and the filtered public OpenAPI schema at "
            "/api/docs, /api/redoc, /api/openapi.json. Exposed without a "
            "session per the 2026-11-02 decision (whitelisted in "
            "StorageRequirementMiddleware.PUBLIC_PATHS; the schema is "
            "filtered to public paths only in app.main)."
        ),
        inputs=(),
        outputs=("html", "spec"),
        dependencies=(
            "app.main",
            "app.core.storage_middleware",
        ),
        deterministic=True,
        allowed_routes=(
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        ),
        allowed_prefixes=(
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        ),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_openapi",
        title="Documentation OpenAPI Spec (SSOT)",
        description=("CANONICAL OpenAPI 3.0 specification. Returns the full API spec as JSON. Admin-only."),
        inputs=(),
        outputs=("spec",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/openapi.json",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_postman",
        title="Documentation Postman Collection (SSOT)",
        description=(
            "CANONICAL Postman collection. Returns the API as a Postman collection for import into Postman. Admin-only."
        ),
        inputs=(),
        outputs=("collection",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/postman",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_swagger",
        title="Documentation Swagger UI (SSOT)",
        description=("CANONICAL Swagger UI. Returns an HTML page with interactive API documentation. Admin-only."),
        inputs=(),
        outputs=("html",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/swagger",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_redoc",
        title="Documentation ReDoc UI (SSOT)",
        description=("CANONICAL ReDoc UI. Returns an HTML page with ReDoc interactive API documentation. Admin-only."),
        inputs=(),
        outputs=("html",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/redoc",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_portal",
        title="Documentation Developer Portal (SSOT)",
        description=(
            "CANONICAL developer portal. Returns an HTML page with links to all documentation resources. Admin-only."
        ),
        inputs=(),
        outputs=("html",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_reference",
        title="Documentation API Reference (SSOT)",
        description=(
            "CANONICAL API reference documentation. Returns a structured "
            "reference of all endpoints, schemas, and examples."
        ),
        inputs=(),
        outputs=("reference",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/reference",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_module_reference",
        title="Documentation Module Reference (SSOT)",
        description=(
            "CANONICAL API reference for a specific module. Returns the "
            "endpoints, schemas, and examples for the given module."
        ),
        inputs=("module_id",),
        outputs=("reference",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/reference/{module_id}",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_examples",
        title="Documentation Code Examples (SSOT)",
        description=(
            "CANONICAL code examples. Returns example code for using the API, filterable by language and category."
        ),
        inputs=("language?", "category?"),
        outputs=("examples",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/examples",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_example",
        title="Documentation Code Example (SSOT)",
        description=("CANONICAL single code example by ID. Returns the full example with code and explanation."),
        inputs=("example_id",),
        outputs=("example",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/examples/{example_id}",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_sdks",
        title="Documentation SDKs (SSOT)",
        description=(
            "CANONICAL list of available SDKs and tools. Returns SDK names, "
            "languages, download links, and documentation links."
        ),
        inputs=(),
        outputs=("sdks",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/sdks",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_support",
        title="Documentation Support Resources (SSOT)",
        description=("CANONICAL support resources. Returns links to docs, community, and contact info for support."),
        inputs=(),
        outputs=("resources",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/support",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_changelog",
        title="Documentation Changelog (SSOT)",
        description=("CANONICAL API changelog and version history. Returns all changes organized by version."),
        inputs=(),
        outputs=("changelog",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/changelog",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="documentation",
        group_name="documentation_statistics",
        title="Documentation Statistics (SSOT)",
        description=(
            "CANONICAL documentation statistics and usage metrics. Returns "
            "page views, downloads, and SDK usage. Admin-only."
        ),
        inputs=(),
        outputs=("statistics",),
        dependencies=("app.modules.documentation.router",),
        deterministic=True,
        allowed_routes=("/api/docs/statistics",),
    )
)
