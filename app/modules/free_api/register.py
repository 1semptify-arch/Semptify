"""Free API module registration helper — FunctionGroupContracts.

The free API module provides free public API lookups for tenants:
property parcels, landlord business records, court records, violations,
inspections, and statutes. Minnesota-focused.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_property_parcel",
        title="Free API Property Parcel Lookup (SSOT)",
        description="CANONICAL lookup parcel by county and parcel ID. Returns property parcel data.",
        inputs=("county", "parcel_id"),
        outputs=("parcel",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_property_address",
        title="Free API Property Address Lookup (SSOT)",
        description="CANONICAL lookup property by county and address. Returns property data.",
        inputs=("county", "address"),
        outputs=("property",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_landlord_business",
        title="Free API Landlord Business Lookup (SSOT)",
        description="CANONICAL search MN Secretary of State business records. Returns business filings.",
        inputs=("name",),
        outputs=("businesses",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_landlord_owner",
        title="Free API Landlord Owner Lookup (SSOT)",
        description="CANONICAL lookup property owner via HUD/county records. Returns owner info.",
        inputs=("property_id",),
        outputs=("owner",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_court_evictions",
        title="Free API Court Evictions Search (SSOT)",
        description="CANONICAL search MN court eviction records by party name. Returns eviction cases.",
        inputs=("name",),
        outputs=("evictions",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_court_federal",
        title="Free API Federal Court Search (SSOT)",
        description="CANONICAL search federal court cases via CourtListener. Returns federal cases.",
        inputs=("query",),
        outputs=("cases",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_violations_city",
        title="Free API City Violations Lookup (SSOT)",
        description="CANONICAL lookup city inspection violations for an address. Returns violations.",
        inputs=("city", "address"),
        outputs=("violations",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_violations_environment",
        title="Free API Environmental Violations Lookup (SSOT)",
        description="CANONICAL lookup EPA/MPCA environmental violations. Returns violations for the facility.",
        inputs=("facility",),
        outputs=("violations",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_inspections_hud",
        title="Free API HUD Inspection Lookup (SSOT)",
        description="CANONICAL lookup HUD REAC inspection scores. Returns inspection scores for the property.",
        inputs=("property_id",),
        outputs=("inspection",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_inspections_local",
        title="Free API Local Inspection Lookup (SSOT)",
        description="CANONICAL lookup local inspection records. Returns inspection history for the address.",
        inputs=("city", "address"),
        outputs=("inspections",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="free_api",
        group_name="free_api_statutes",
        title="Free API Statute Lookup (SSOT)",
        description="CANONICAL retrieve MN statute text by section number. Returns the statute text.",
        inputs=("section",),
        outputs=("statute",),
        dependencies=("app.modules.free_api.router",),
        deterministic=True,
    )
)
