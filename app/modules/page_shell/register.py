"""Page Shell module registration.

Page Shell is registered in `app/core/product_manifest.py` as a CORE module.
The /api/page-shell routes are admin-only introspection, but the renderer is
used directly by Page Composer's tenant-facing routes.
"""

from __future__ import annotations

from app.core.module_contract import ModuleContract
from app.core.module_contract_registry import register_module_contract
from app.core.module_contracts import FunctionGroupContract, register_function_group

register_module_contract(
    ModuleContract(
        module_path="app.modules.page_shell",
        title="Page Shell — Data-driven page renderer",
        description=(
            "Validates and renders a PageConfig to a four-zone HTML shell "
            "(RECORD, KNOW, ACT, GOVERN). Used by Page Composer and other "
            "guide-page surfaces."
        ),
        pillar="record",
        roles=["tenant", "advocate", "admin"],
        lifecycle="stable",
        inputs=[
            {"name": "page_config", "kind": "input", "data_type": "PageConfig", "required": True}
        ],
        outputs=[
            {"name": "html", "kind": "output", "data_type": "str"}
        ],
        dependencies=[
            "app.modules.page_shell.renderer",
            "app.modules.page_shell.loader",
            "app.modules.page_shell.govern",
        ],
        acceptance_test="Render each sample PageConfig and assert no console errors.",
        rollback_plan="Revert to previous PageShell renderer version and re-register.",
        function_group_ids=["page_shell::render_page", "page_shell::load_page_config"],
        upl_risk_tier="none",
        fees_policy="no_fees",
    )
)

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
