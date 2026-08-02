"""Legal module registration helper."""

from app.core.module_contracts import FunctionGroupContract, register_function_group
from app.core.product_manifest import ModuleEntry, ProductTier

MODULE = ModuleEntry(
    module_path="app.modules.legal.router",
    tier=ProductTier.EXTENDED,
    origin="internal",
    lifecycle="beta",
    tags=("Legal", "Court Filing", "Discovery", "Exhibits", "Workspace"),
)

register_function_group(
    FunctionGroupContract(
        module="legal",
        group_name="legal_workspace_list",
        title="Legal Workspace List (SSOT)",
        description="Returns all legal matters (workspaces) for the current legal user.",
        inputs=("legal_user_id",),
        outputs=("matters",),
        dependencies=("app.modules.legal.service",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal",
        group_name="legal_workspace_create",
        title="Legal Workspace Create (SSOT)",
        description="Creates a new legal matter (workspace) with optional linked tenant.",
        inputs=("legal_user_id", "title", "tenant_user_id?"),
        outputs=("matter_id",),
        dependencies=("app.modules.legal.service",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal",
        group_name="legal_court_filing_create",
        title="Legal Court Filing Create (SSOT)",
        description="Creates a court filing record (docket entry) for a matter.",
        inputs=("matter_id", "filing_type", "court", "filing_date?"),
        outputs=("filing_id",),
        dependencies=("app.modules.legal.service",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal",
        group_name="legal_discovery_track",
        title="Legal Discovery Tracking (SSOT)",
        description="Creates or updates a discovery request/response record for a matter.",
        inputs=("matter_id", "discovery_type", "served_date?"),
        outputs=("discovery_id",),
        dependencies=("app.modules.legal.service",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="legal",
        group_name="legal_exhibit_number",
        title="Legal Exhibit Numbering (SSOT)",
        description="Assigns the next sequential exhibit number for a matter and records exhibit metadata.",
        inputs=("matter_id", "description", "evidence_item_id?"),
        outputs=("exhibit_id", "exhibit_number"),
        dependencies=("app.modules.legal.service",),
        deterministic=False,
    )
)
