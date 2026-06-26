"""Register UI Composer function group contracts.

Contracts registered:
    - ui_composer::page_compose     — compose a full page
    - ui_composer::fragment_render  — render a single component fragment
    - ui_composer::process_status   — get workflow status for process indicator
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
    module="ui_composer",
    group_name="page_compose",
    title="UI Composer — Page Compose (SSOT)",
    description=(
        "Compose a full page as a list of components based on user context and page intent. "
        "Returns {page_title, pillar, components:[{type, data}]}. "
        "Valid intents: landing, timeline, library, documents, tools, workflow_step. "
        "Does NOT render HTML — returns structured data for the generic template."
    ),
    inputs=("user_id", "page_intent", "context?"),
    outputs=("page_title", "pillar", "components"),
    dependencies=("app.services.ui_composer",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="ui_composer",
    group_name="fragment_render",
    title="UI Composer — Fragment Render (SSOT)",
    description=(
        "Render a single component as a fragment dict {type, data} for HTMX swaps. "
        "Valid component types are defined in COMPONENT_TYPES. "
        "Does NOT render HTML — returns the fragment data for the router to render."
    ),
    inputs=("component_type", "data"),
    outputs=("type", "data"),
    dependencies=("app.services.ui_composer",),
    deterministic=True,
))

register_function_group(FunctionGroupContract(
    module="ui_composer",
    group_name="process_status",
    title="UI Composer — Process Status (SSOT)",
    description=(
        "Get the current status of a workflow for the process indicator. "
        "Returns {step_label, state, progress_pct}. "
        "Reads from the Positronic Mesh if available; falls back to a generic running state."
    ),
    inputs=("workflow_id",),
    outputs=("step_label", "state", "progress_pct"),
    dependencies=("app.services.ui_composer", "app.core.positronic_mesh"),
    deterministic=True,
))
