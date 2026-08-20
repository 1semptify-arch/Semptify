"""Page Shell module registration.

Page Shell is registered in `app/core/product_manifest.py` as a CORE module.
The /api/page-shell routes are admin-only introspection, but the renderer is
used directly by Page Composer's tenant-facing routes.
"""

from __future__ import annotations

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="page_shell",
        group_name="render_page",
        title="Page Shell — Render Page",
        description=(
            "Render a validated PageConfig to HTML. Returns a single .page-shell "
            "grid with four zones (RECORD, KNOW, ACT, GOVERN). Does not fetch data, "
            "pick blends, or compute intensity — pure data-driven renderer."
        ),
        inputs=("page_config",),
        outputs=("html",),
        dependencies=("app.modules.page_shell.renderer",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="page_shell",
        group_name="load_page_config",
        title="Page Shell — Load Page Config",
        description=(
            "Validate a raw dict and apply GOVERN floor/override rules. Returns a "
            "validated PageConfig and a GOVERN report."
        ),
        inputs=("raw_config",),
        outputs=("page_config", "govern_report"),
        dependencies=("app.modules.page_shell.loader", "app.modules.page_shell.govern"),
        deterministic=True,
    )
)
