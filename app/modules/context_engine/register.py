"""Context Engine module registration helper."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="context_engine",
        group_name="context_query",
        title="Context Query (SSOT)",
        description=(
            "CANONICAL query for cached context facts by subject + jurisdiction. "
            "Returns verified facts with source URLs — no hallucination. "
            "Does NOT gather new facts; use context_refresh for that."
        ),
        inputs=("subject", "jurisdiction?", "limit?"),
        outputs=("facts",),
        dependencies=("app.modules.context_engine.cache",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="context_engine",
        group_name="context_refresh",
        title="Context Refresh (SSOT)",
        description=(
            "CANONICAL gather fresh facts from external sources for a subject. "
            "Admin only. Writes results into context_facts cache. "
            "Repurposes free_api_pack.py fetchers. Every fact has a source URL."
        ),
        inputs=("subject", "jurisdiction?", "query?", "admin_user_id"),
        outputs=("new_count",),
        dependencies=("app.modules.context_engine.gatherer", "app.modules.free_api_pack"),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="context_engine",
        group_name="story_submit",
        title="Story Submit (SSOT)",
        description=(
            "CANONICAL submit a tenant story. Anonymized by default. "
            "Pending moderation — not published until admin reviews. "
            "Story frame: avoided_court is the hero, not 'I won'."
        ),
        inputs=("subject", "title", "body", "jurisdiction?", "outcome?", "submitted_by"),
        outputs=("story_id",),
        dependencies=("app.modules.context_engine.stories",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="context_engine",
        group_name="story_moderate",
        title="Story Moderate (SSOT)",
        description=(
            "CANONICAL moderate a tenant story. Admin only. "
            "Optionally edits title/body, then publishes or unpublishes. "
            "Sets moderated_by + moderated_at."
        ),
        inputs=("story_id", "publish", "title?", "body?", "admin_user_id"),
        outputs=("story_id", "is_published"),
        dependencies=("app.modules.context_engine.stories",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="context_engine",
        group_name="explanation_entry",
        title="Explanation Entry (SSOT)",
        description=(
            "CANONICAL curated Layer 1 explanation store. Admin create/update/delete; "
            "authenticated read. Each entry has subject, jurisdiction, UPL risk tier, "
            "pillar, review_status, and four variant slots (trust, mechanics, "
            "reinforcement, minimal)."
        ),
        inputs=("subject", "jurisdiction?", "upl_risk_tier", "pillar", "review_status", "admin_user_id?"),
        outputs=("entry_id", "entry"),
        dependencies=("app.modules.context_engine.explanation_entries",),
        deterministic=True,
    )
)
