"""Location module registration helper — FunctionGroupContracts.

The location module is the KNOW pillar's context layer. It determines the
tenant's jurisdiction (state + county) and provides jurisdiction-aware legal
resources, eviction timelines, and county-specific information. Minnesota is
the default and most complete jurisdiction.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_current",
    title="Location Current (SSOT)",
    description=(
        "CANONICAL get the user's current location. Returns state code, "
        "county (if known), and whether it was auto-detected or manually set. "
        "Defaults to Minnesota if no location is set."
    ),
    inputs=("user_id",),
    outputs=("state_code", "county", "source"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_update",
    title="Location Update (SSOT)",
    description=(
        "CANONICAL update the user's location. The tenant can manually set "
        "their state and county. This drives jurisdiction-aware content "
        "throughout the app."
    ),
    inputs=("user_id", "state_code", "county?"),
    outputs=("state_code", "county"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_clear",
    title="Location Clear (SSOT)",
    description=(
        "CANONICAL clear the user's saved location. Resets to Minnesota "
        "default. Used when the tenant moves or wants to reset."
    ),
    inputs=("user_id",),
    outputs=("success",),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_supported_states",
    title="Location Supported States (SSOT)",
    description=(
        "CANONICAL list of states supported by the location service. "
        "Returns state codes and names. Used by the state selector dropdown."
    ),
    inputs=(),
    outputs=("states",),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_state_info",
    title="Location State Info (SSOT)",
    description=(
        "CANONICAL state information for a specific state code. Returns "
        "state name, supported counties, and available resources."
    ),
    inputs=("state_code",),
    outputs=("state_code", "name", "counties", "resources_available"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_legal_resources",
    title="Location Legal Resources (SSOT)",
    description=(
        "CANONICAL jurisdiction-aware legal resources for the user. Returns "
        "legal aid organizations, tenant rights groups, and government agencies "
        "for the user's state and county. Facts only, no recommendations."
    ),
    inputs=("user_id",),
    outputs=("resources",),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_eviction_timeline",
    title="Location Eviction Timeline (SSOT)",
    description=(
        "CANONICAL eviction procedure timeline for the user's jurisdiction. "
        "Returns the steps, notice periods, and deadlines for an eviction "
        "in the user's state. Facts only — not legal advice."
    ),
    inputs=("user_id",),
    outputs=("timeline", "state_code"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_mn_counties",
    title="Location MN Counties (SSOT)",
    description=(
        "CANONICAL list of Minnesota counties. MN is the default and most "
        "complete jurisdiction. Returns county names and codes."
    ),
    inputs=(),
    outputs=("counties",),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_county_info",
    title="Location County Info (SSOT)",
    description=(
        "CANONICAL county-specific information. Returns county details, "
        "court locations, and local resources for the given county."
    ),
    inputs=("county", "state_code?"),
    outputs=("county", "state_code", "court_location", "local_resources"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="location",
    group_name="location_context",
    title="Location Context (SSOT)",
    description=(
        "CANONICAL full location context for the user. Returns state, county, "
        "legal resources, eviction timeline, and jurisdiction metadata in one "
        "call. Used by the tenant dashboard to populate jurisdiction-aware sections."
    ),
    inputs=("user_id",),
    outputs=("state_code", "county", "resources", "eviction_timeline", "jurisdiction_metadata"),
    dependencies=("app.modules.location.router", "app.modules.location.service"),
    deterministic=True,
))
