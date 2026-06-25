"""Plan Maker module registration helper — FunctionGroupContracts.

The plan maker module creates accountability plans with entities,
evidence, and next steps. Plans can be exported as Markdown or JSON.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_plan_create",
    title="Plan Maker Create Plan (SSOT)",
    description="CANONICAL create a new accountability plan. Returns the new plan with ID.",
    inputs=("user_id", "plan_data"),
    outputs=("plan_id", "plan"),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_plan_view",
    title="Plan Maker View Plan (SSOT)",
    description="CANONICAL view a plan from submitted state. Returns the plan details.",
    inputs=("plan_id", "user_id"),
    outputs=("plan",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_plan_export",
    title="Plan Maker Export Plan (SSOT)",
    description="CANONICAL export a plan as Markdown or JSON. Returns the exported content.",
    inputs=("plan_id", "format", "user_id"),
    outputs=("content", "filename"),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_entity_add",
    title="Plan Maker Add Entity (SSOT)",
    description="CANONICAL add an entity (organization, person) to the plan.",
    inputs=("plan_id", "entity", "user_id"),
    outputs=("plan",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_evidence_add",
    title="Plan Maker Add Evidence (SSOT)",
    description="CANONICAL add an evidence item to the plan.",
    inputs=("plan_id", "evidence", "user_id"),
    outputs=("plan",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_step_add",
    title="Plan Maker Add Step (SSOT)",
    description="CANONICAL add a next step / action item to the plan.",
    inputs=("plan_id", "step", "user_id"),
    outputs=("plan",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_step_complete",
    title="Plan Maker Complete Step (SSOT)",
    description="CANONICAL mark a step as complete in the plan.",
    inputs=("plan_id", "step_index", "user_id"),
    outputs=("plan",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="plan_maker",
    group_name="plan_maker_default_steps",
    title="Plan Maker Default Steps (SSOT)",
    description="CANONICAL get the default next-step templates pre-populated when creating a new plan.",
    inputs=(),
    outputs=("steps",),
    dependencies=("app.modules.plan_maker.router",),
    deterministic=True,
))
