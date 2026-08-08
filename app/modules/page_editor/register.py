"""Page Editor module registration helper — FunctionGroupContracts.

The page editor module is an admin-only tool for editing static HTML
pages. It provides file listing, reading, saving, previewing, and
searching across the project's static files.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_list_files",
        title="Page Editor List Files (SSOT)",
        description=(
            "CANONICAL list of editable files in the project. Returns file paths, types, and sizes. Admin-only."
        ),
        inputs=("user_id",),
        outputs=("files",),
        dependencies=("app.modules.page_editor.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_get_file",
        title="Page Editor Get File (SSOT)",
        description=("CANONICAL get a file's content by path. Returns the file content as text. Admin-only."),
        inputs=("path", "user_id"),
        outputs=("content", "path"),
        dependencies=("app.modules.page_editor.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_save_file",
        title="Page Editor Save File (SSOT)",
        description=(
            "CANONICAL save a file's content. Writes the new content to the file at the given path. Admin-only."
        ),
        inputs=("path", "content", "user_id"),
        outputs=("saved", "path"),
        dependencies=("app.modules.page_editor.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_preview_file",
        title="Page Editor Preview File (SSOT)",
        description=(
            "CANONICAL preview a file with proposed changes. Returns a "
            "preview of how the file would look after saving. Admin-only."
        ),
        inputs=("path", "content", "user_id"),
        outputs=("preview",),
        dependencies=("app.modules.page_editor.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_search_files",
        title="Page Editor Search Files (SSOT)",
        description=("CANONICAL search across editable files. Returns matching files and line numbers. Admin-only."),
        inputs=("q", "type?", "user_id"),
        outputs=("results",),
        dependencies=("app.modules.page_editor.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_editor",
        group_name="page_editor_page",
        title="Page Editor Page (SSOT)",
        description=("CANONICAL redirect to the page editor UI. Admin-only."),
        inputs=(),
        outputs=("redirect",),
        dependencies=("app.modules.page_editor.router",),
        deterministic=True,
    )
)
