"""Page Composer module registration helper."""

from app.core.module_contracts import FunctionGroupContract, register_function_group


register_function_group(FunctionGroupContract(
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
))
