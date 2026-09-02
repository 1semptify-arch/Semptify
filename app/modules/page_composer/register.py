"""Page Composer module registration helper."""

from app.core.module_contract import ModuleContract
from app.core.module_contract_registry import register_module_contract
from app.core.module_contracts import FunctionGroupContract, register_function_group

register_module_contract(
    ModuleContract(
        module_path="app.modules.page_composer",
        title="Page Composer — Unified page assembly",
        description=(
            "Assembles a PageConfig from user context, subject, jurisdiction, "
            "and verified facts/stories. Falls back to contract-driven assembly "
            "when a PageContract is registered for the subject."
        ),
        pillar="record",
        roles=["tenant", "advocate"],
        lifecycle="stable",
        inputs=[
            {"name": "subject", "kind": "input", "data_type": "str", "required": True},
            {"name": "jurisdiction", "kind": "input", "data_type": "Jurisdiction", "required": False},
            {"name": "user_id", "kind": "input", "data_type": "str", "required": False},
        ],
        outputs=[
            {"name": "page", "kind": "output", "data_type": "HTMLResponse"},
            {"name": "page_config", "kind": "output", "data_type": "PageConfig"},
        ],
        dependencies=[
            "app.modules.context_engine.cache",
            "app.modules.context_engine.stories",
            "app.modules.case_builder",
            "app.modules.page_shell.renderer",
        ],
        acceptance_test="Render all proven guide pages and assert no regressions.",
        rollback_plan="Disable PageContract lookup and fall back to legacy assembly.",
        function_group_ids=["page_composer::page_compose", "page_composer::page_assemble"],
        upl_risk_tier="none",
        fees_policy="no_fees",
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_composer",
        group_name="page_compose",
        title="Page Compose (SSOT)",
        description=(
            "CANONICAL compose a unified page view for a subject + jurisdiction. "
            "Pulls verified facts from Context Engine cache, published tenant stories, "
            "and the user's case data from Case Builder (if available). "
            "All facts include source URLs — no hallucination. "
            "Does NOT gather new facts; use context_engine.context_refresh for that."
        ),
        inputs=("subject", "jurisdiction?", "user_id?", "fact_limit?", "story_limit?"),
        outputs=("page",),
        dependencies=(
            "app.modules.context_engine.cache",
            "app.modules.context_engine.stories",
            "app.modules.case_builder",
        ),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="page_composer",
        group_name="page_assemble",
        title="Page Assembly Formula",
        description=(
            "Deterministically assemble a PageConfig from user context, subject/intent, "
            "and jurisdiction. Applies blend selection, block gathering, GOVERN floor "
            "and override rules, and emits a legacy UI Composer component list."
        ),
        inputs=("subject", "jurisdiction?", "user_id?", "intent?", "user_context?"),
        outputs=("page_config", "components", "govern_report", "metadata"),
        dependencies=(
            "app.modules.page_composer.assembly",
            "app.modules.page_shell.blends",
            "app.modules.page_shell.govern",
            "app.modules.page_shell.models",
            "app.services.ui_composer",
        ),
        deterministic=True,
    )
)
