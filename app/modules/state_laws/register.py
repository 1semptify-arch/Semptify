"""State Laws module registration helper — FunctionGroupContracts.

The state_laws module is the KNOW pillar's jurisdiction layer. It provides
housing law information for each US state. Tenants select their state to get
relevant laws, rights, and protections. This is facts-only, no opinions.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="state_laws",
    group_name="state_laws_list",
    title="State Laws List (SSOT)",
    description=(
        "CANONICAL list of all states with basic housing law information. "
        "Returns state code, name, and summary of tenant protections. "
        "Used by the state selector in the tenant UI."
    ),
    inputs=(),
    outputs=("states",),
    dependencies=("app.modules.state_laws.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="state_laws",
    group_name="state_laws_get",
    title="State Laws Get (SSOT)",
    description=(
        "CANONICAL detailed housing law information for a specific state. "
        "Returns full state details including security deposit limits, "
        "eviction procedures, tenant rights, and landlord obligations. "
        "Used by the tenant rights page."
    ),
    inputs=("state_code",),
    outputs=("state_code", "name", "security_deposit_limit", "eviction_procedure", "tenant_rights", "landlord_obligations"),
    dependencies=("app.modules.state_laws.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="state_laws",
    group_name="state_laws_nearby",
    title="State Laws Nearby Search (SSOT)",
    description=(
        "CANONICAL find nearby states by latitude/longitude. Returns states "
        "sorted by distance with their housing law summaries. "
        "Used when the tenant's location is detected via IP."
    ),
    inputs=("lat", "lon"),
    outputs=("states",),
    dependencies=("app.modules.state_laws.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="state_laws",
    group_name="state_laws_detect",
    title="State Laws Detect by Location (SSOT)",
    description=(
        "CANONICAL detect the user's likely state based on IP geolocation. "
        "Returns the detected state code and confidence. "
        "Used to auto-select the state on first visit."
    ),
    inputs=("request",),
    outputs=("state_code", "confidence"),
    dependencies=("app.modules.state_laws.router",),
    deterministic=False,
))
