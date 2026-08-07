"""Journal module registration helper — FunctionGroupContracts."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_create",
        title="Journal Create Entry (SSOT)",
        description=(
            "CANONICAL create a free-form journal entry. Tenants log conversations, "
            "incidents, repair requests, and notes with a title, content, timestamp, "
            "and optional tags."
        ),
        inputs=(
            "user_id",
            "entry_type",
            "title",
            "content?",
            "occurred_at?",
            "is_urgent?",
            "involved_party?",
            "tags?",
            "document_link?",
        ),
        outputs=("entry_id", "entry"),
        dependencies=("app.modules.journal.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_list",
        title="Journal List Entries (SSOT)",
        description=(
            "CANONICAL list of journal entries for a user. Returns entries sorted "
            "by occurrence time, newest first, with optional filters and pagination."
        ),
        inputs=("user_id", "entry_type?", "is_urgent?", "skip?", "limit?"),
        outputs=("entries", "total"),
        dependencies=("app.modules.journal.router",),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_get",
        title="Journal Get Entry (SSOT)",
        description=("CANONICAL get a single journal entry by ID. Enforces ownership."),
        inputs=("entry_id", "user_id"),
        outputs=("entry",),
        dependencies=("app.modules.journal.router",),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_update",
        title="Journal Update Entry (SSOT)",
        description=("CANONICAL update a journal entry. Enforces ownership."),
        inputs=("entry_id", "user_id", "updates"),
        outputs=("entry",),
        dependencies=("app.modules.journal.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_delete",
        title="Journal Delete Entry (SSOT)",
        description=("CANONICAL delete a journal entry. Enforces ownership."),
        inputs=("entry_id", "user_id"),
        outputs=("deleted",),
        dependencies=("app.modules.journal.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="journal",
        group_name="journal_summary",
        title="Journal Summary (SSOT)",
        description=(
            "CANONICAL dashboard summary of journal entries. Returns total count, "
            "urgent count, and the most recent entries."
        ),
        inputs=("user_id",),
        outputs=("total_entries", "urgent_entries", "recent_entries"),
        dependencies=("app.modules.journal.router",),
        deterministic=True,
    )
)
