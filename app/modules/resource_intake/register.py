"""Resource Intake & Integrity Engine — FunctionGroupContract registration."""

from __future__ import annotations

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="resource_intake",
        group_name="validate_pool",
        title="Resource Intake & Integrity Engine — validate the Composer resource pool",
        description=(
            "CANONICAL: Loads data/composer_resources.json and confirms every "
            "released item is human-approved, fact-checked, and not AI-generated. "
            "This is the build-time gate for the Part 3 resource sourcing contract."
        ),
        inputs=("pool_path",),
        outputs=("status", "count", "violations"),
        dependencies=("app.modules.resource_intake.engine",),
        deterministic=True,
    )
)
