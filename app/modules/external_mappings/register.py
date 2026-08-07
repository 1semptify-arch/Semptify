"""External Mappings module registration helper — FunctionGroupContracts.

The external mappings module links Semptify entities to external system
IDs: court cases, properties, agencies. Used for cross-system reference.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_mapping_create",
    title="External Mappings Create Mapping (SSOT)",
    description="CANONICAL create a new external mapping for a Semptify entity.",
    inputs=("user_id", "mapping"),
    outputs=("mapping_id",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_list",
    title="External Mappings List (SSOT)",
    description="CANONICAL list user's external mappings with optional type and status filters.",
    inputs=("user_id", "mapping_type?", "status?"),
    outputs=("mappings",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_get",
    title="External Mappings Get (SSOT)",
    description="CANONICAL get a specific external mapping by ID.",
    inputs=("user_id", "mapping_id"),
    outputs=("mapping",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_update_status",
    title="External Mappings Update Status (SSOT)",
    description="CANONICAL update the status of an external mapping.",
    inputs=("user_id", "mapping_id", "status"),
    outputs=("success",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_court_case_create",
    title="External Mappings Create Court Case (SSOT)",
    description="CANONICAL create a court case external mapping.",
    inputs=("user_id", "case"),
    outputs=("mapping_id",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_court_cases_list",
    title="External Mappings List Court Cases (SSOT)",
    description="CANONICAL list court case mappings with optional case_type and case_status filters.",
    inputs=("user_id", "case_type?", "case_status?"),
    outputs=("court_cases",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_property_create",
    title="External Mappings Create Property (SSOT)",
    description="CANONICAL create a property external mapping.",
    inputs=("user_id", "property"),
    outputs=("mapping_id",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_properties_list",
    title="External Mappings List Properties (SSOT)",
    description="CANONICAL list property mappings with optional county and is_primary filters.",
    inputs=("user_id", "county?", "is_primary?"),
    outputs=("properties",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_agency_create",
    title="External Mappings Create Agency (SSOT)",
    description="CANONICAL create an agency external mapping.",
    inputs=("user_id", "agency"),
    outputs=("mapping_id",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_agencies_list",
    title="External Mappings List Agencies (SSOT)",
    description="CANONICAL list agency mappings with optional agency_code and complaint_type filters.",
    inputs=("user_id", "agency_code?", "complaint_type?"),
    outputs=("agencies",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="external_mappings",
    group_name="external_mappings_search",
    title="External Mappings Search (SSOT)",
    description="CANONICAL search across all external mappings by query with optional type filter.",
    inputs=("user_id", "query", "mapping_type?"),
    outputs=("results",),
    dependencies=("app.modules.external_mappings.router",),
    deterministic=True,
))
