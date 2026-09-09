"""Sticky Notes module registration helper - FunctionGroupContracts.

The Sticky Notes module is a per-user scratch-pad for quick thoughts,
source references, and temporary highlights. Notes are stored as
overlay-only UnifiedOverlays, not certified documents.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="sticky_notes",
        group_name="sticky_notes_create",
        title="Sticky Notes Create (SSOT)",
        description=(
            "CANONICAL create a new sticky note in the user's scratch-pad. "
            "Accepts text and an optional source reference."
        ),
        inputs=("text", "source?"),
        outputs=("note",),
        dependencies=("app.modules.sticky_notes.router",),
        deterministic=False,
        allowed_routes=("/api/sticky-notes",),
        allowed_prefixes=("/api/sticky-notes",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="sticky_notes",
        group_name="sticky_notes_list",
        title="Sticky Notes List (SSOT)",
        description=(
            "CANONICAL list all sticky notes for the current user, newest first."
        ),
        inputs=(),
        outputs=("notes",),
        dependencies=("app.modules.sticky_notes.router",),
        deterministic=True,
        allowed_routes=("/api/sticky-notes",),
        allowed_prefixes=("/api/sticky-notes",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="sticky_notes",
        group_name="sticky_notes_update",
        title="Sticky Notes Update (SSOT)",
        description=(
            "CANONICAL update the text of an existing sticky note by ID."
        ),
        inputs=("note_id", "text"),
        outputs=("note",),
        dependencies=("app.modules.sticky_notes.router",),
        deterministic=False,
        allowed_routes=("/api/sticky-notes/{note_id}",),
        allowed_prefixes=("/api/sticky-notes",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="sticky_notes",
        group_name="sticky_notes_delete",
        title="Sticky Notes Delete (SSOT)",
        description=(
            "CANONICAL delete a sticky note by ID."
        ),
        inputs=("note_id",),
        outputs=("ok",),
        dependencies=("app.modules.sticky_notes.router",),
        deterministic=False,
        allowed_routes=("/api/sticky-notes/{note_id}",),
        allowed_prefixes=("/api/sticky-notes",),
    )
)

register_function_group(
    FunctionGroupContract(
        module="sticky_notes",
        group_name="sticky_notes_page",
        title="Sticky Notes Page (SSOT)",
        description=(
            "CANONICAL render the tenant notepad page at /record/notes."
        ),
        inputs=(),
        outputs=("html",),
        dependencies=("app.modules.sticky_notes.router",),
        deterministic=True,
        allowed_routes=("/record/notes",),
        allowed_prefixes=("/record/notes",),
    )
)
