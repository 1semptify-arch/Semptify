"""Guided Intake module registration helper — FunctionGroupContracts.

The guided intake module walks the tenant through a guided intake flow
to collect case information. Saves intake summaries and tracks status.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="guided_intake",
    group_name="guided_intake_save",
    title="Guided Intake Save (SSOT)",
    description="CANONICAL save intake information. Returns the intake summary with ID.",
    inputs=("data", "user_id"),
    outputs=("intake_id", "summary"),
    dependencies=("app.modules.guided_intake.router",),
    deterministic=False,
))

register_function_group(FunctionGroupContract(
    module="guided_intake",
    group_name="guided_intake_summary",
    title="Guided Intake Summary (SSOT)",
    description="CANONICAL get the intake summary for the current user. Returns the saved intake data.",
    inputs=("user_id",),
    outputs=("summary",),
    dependencies=("app.modules.guided_intake.router",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="guided_intake",
    group_name="guided_intake_status",
    title="Guided Intake Status (SSOT)",
    description="CANONICAL get the intake status for the current user. Returns whether intake is complete.",
    inputs=("user_id",),
    outputs=("status", "progress"),
    dependencies=("app.modules.guided_intake.router",),
    deterministic=True,
))
