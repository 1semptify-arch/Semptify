"""Legal Trails module registration helper — FunctionGroupContracts.

The legal trails module tracks violations, eviction threats, late fee
violations, broker oversight, legal claims, filing windows, and generates
complaints. It's the accountability tracker.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_overview",
    title="Legal Trails Overview (SSOT)",
    description="CANONICAL overview of all legal trails. Returns summary counts for each category.",
    inputs=(),
    outputs=("overview",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

# --- Violations ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_violation_add",
    title="Legal Trails Add Violation (SSOT)",
    description="CANONICAL log a new violation. Creates a violation record with type, perpetrator, and date.",
    inputs=("violation",),
    outputs=("violation_id",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_violations_list",
    title="Legal Trails List Violations (SSOT)",
    description="CANONICAL list violations with optional filters. Returns violations sorted by date.",
    inputs=("violation_type?", "perpetrator?"),
    outputs=("violations", "count"),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_violation_get",
    title="Legal Trails Get Violation (SSOT)",
    description="CANONICAL get a specific violation by ID. Returns full violation details.",
    inputs=("violation_id",),
    outputs=("violation",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

# --- Eviction Threats ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_eviction_threat_add",
    title="Legal Trails Add Eviction Threat (SSOT)",
    description="CANONICAL log an eviction threat. Creates a record of the threat with date and details.",
    inputs=("threat",),
    outputs=("threat_id",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_eviction_threats_list",
    title="Legal Trails List Eviction Threats (SSOT)",
    description="CANONICAL list all eviction threats. Returns threats sorted by date.",
    inputs=(),
    outputs=("threats",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

# --- Late Fee Violations ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_late_fee_add",
    title="Legal Trails Add Late Fee Violation (SSOT)",
    description="CANONICAL log a late fee violation. Records the overcharge amount and details.",
    inputs=("fee",),
    outputs=("fee_id",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_late_fees_list",
    title="Legal Trails List Late Fee Violations (SSOT)",
    description="CANONICAL list all late fee violations. Returns violations with total overcharged amount.",
    inputs=(),
    outputs=("late_fees", "total_overcharged"),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_late_fee_calculate",
    title="Legal Trails Calculate Late Fee Legal Max (SSOT)",
    description="CANONICAL calculate the legal maximum late fee for a given rent amount and days late.",
    inputs=("rent_amount", "days_late"),
    outputs=("legal_max", "calculation"),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

# --- Broker Oversight ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_broker_oversight_add",
    title="Legal Trails Add Broker Oversight (SSOT)",
    description="CANONICAL add a broker to track for oversight accountability.",
    inputs=("broker",),
    outputs=("success",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_broker_oversight_list",
    title="Legal Trails List Broker Oversight (SSOT)",
    description="CANONICAL list all brokers being tracked for oversight.",
    inputs=(),
    outputs=("brokers",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_broker_oversight_get",
    title="Legal Trails Get Broker Oversight (SSOT)",
    description="CANONICAL get broker oversight details by broker name.",
    inputs=("broker_name",),
    outputs=("broker",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_broker_link_violation",
    title="Legal Trails Link Violation To Broker (SSOT)",
    description="CANONICAL link a violation to a broker's oversight record.",
    inputs=("broker_name", "violation_id"),
    outputs=("success",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

# --- Legal Claims ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_claim_create",
    title="Legal Trails Create Legal Claim (SSOT)",
    description="CANONICAL create a formal legal claim. Returns the new claim with ID.",
    inputs=("claim",),
    outputs=("claim_id",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_claims_list",
    title="Legal Trails List Legal Claims (SSOT)",
    description="CANONICAL list all legal claims with optional status filter.",
    inputs=("status?"),
    outputs=("claims", "count"),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_claim_get",
    title="Legal Trails Get Legal Claim (SSOT)",
    description="CANONICAL get a specific legal claim by ID.",
    inputs=("claim_id",),
    outputs=("claim",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_claim_status_update",
    title="Legal Trails Update Claim Status (SSOT)",
    description="CANONICAL update the status of a legal claim.",
    inputs=("claim_id", "status"),
    outputs=("success",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

# --- Filing Windows ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_filing_windows",
    title="Legal Trails Calculate Filing Windows (SSOT)",
    description="CANONICAL calculate filing windows for a violation date. Returns deadlines for each claim type.",
    inputs=("violation_date",),
    outputs=("filing_windows",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))

# --- Complaint Generators ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_generate_retaliation_complaint",
    title="Legal Trails Generate Retaliation Complaint (SSOT)",
    description="CANONICAL generate a retaliation complaint from tenant and property info.",
    inputs=("tenant_name", "property_address", "details"),
    outputs=("complaint",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_generate_license_complaint",
    title="Legal Trails Generate License Complaint (SSOT)",
    description="CANONICAL generate a license complaint against a broker.",
    inputs=("broker_name", "license_number?"),
    outputs=("complaint",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_generate_hud_complaint",
    title="Legal Trails Generate HUD Complaint (SSOT)",
    description="CANONICAL generate a HUD complaint from tenant and property info.",
    inputs=("tenant_name", "property_address", "details"),
    outputs=("complaint",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=False,
))

# --- Attorney Resources ---

register_function_group(FunctionGroupContract(
    module="legal_trails",
    group_name="legal_trails_mn_attorneys",
    title="Legal Trails MN Tenant Attorneys (SSOT)",
    description="CANONICAL list of Minnesota tenant rights attorneys.",
    inputs=(),
    outputs=("attorneys",),
    dependencies=("app.modules.legal_trails.router",),
    deterministic=True,
))
