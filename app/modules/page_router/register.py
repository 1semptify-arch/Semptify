"""Page Router module registration.

Unified page router — dynamically serves every template page declared in the
page manifest (app/core/page_manifest.py) that doesn't already have a
dedicated route handler elsewhere. Routes are registered at import time from
PAGE_MANIFEST, so there is no static allowed_routes list — the manifest is the
route SSOT, and per-page access is enforced by PAGE_CONTRACTS guards inside
the handler (auth cookie, storage validity, role check).
"""

from __future__ import annotations

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="page_router",
        group_name="serve_manifest_page",
        title="Page Router - Serve Manifest Page",
        description=(
            "Serve a template page declared in the page manifest. Applies the "
            "PAGE_CONTRACTS guard (user cookie, valid storage session, role "
            "membership) before rendering; redirects via SSOT navigation on "
            "denial. Renders the Jinja2 template with standard context "
            "(page_id, page_title, contract, user info); falls back to a "
            "placeholder page when the template file does not exist yet. "
            "Routes are generated dynamically from PAGE_MANIFEST at import "
            "time — routes already owned by dedicated handlers are skipped."
        ),
        inputs=("request",),
        outputs=("html_or_redirect",),
        dependencies=(
            "app.core.page_manifest",
            "app.core.page_contracts",
            "app.core.ssot_guard",
            "app.core.user_id",
            "app.core.storage_middleware",
            "app.core.workflow_engine",
        ),
        deterministic=True,
    )
)
