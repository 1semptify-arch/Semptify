"""Unified page router — serves all manifest template pages with contract guards.

This router dynamically registers a GET route for every template page in the
page manifest that doesn't already have a dedicated route handler elsewhere.

Each route:
1. Applies the contract-based guard (auth + role check) via _guard_by_contract
2. Injects standard context (page_id, page_title, contract, user info)
3. Renders the Jinja2 template
4. Falls back to a placeholder page if the template file doesn't exist yet

This is the single entry point for all converted pages.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.page_manifest import PAGE_MANIFEST, PageManifestEntry
from app.core.page_contracts import PAGE_CONTRACTS, PageContract
from app.core.ssot_guard import ssot_redirect
from app.core.user_id import COOKIE_USER_ID, get_role_from_user_id

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pages"])

BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_DIR = BASE_PATH / "app" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Re-expose the same globals that main.py sets up so templates work identically
try:
    from app.core.navigation import navigation
    templates.env.globals["navigation"] = navigation
except ImportError:
    logger.warning("navigation module not available to page_router")

try:
    from app.core.i18n import SUPPORTED_LOCALES, _jinja2_gettext, get_locale
    templates.env.globals["_"] = _jinja2_gettext
    templates.env.globals["supported_locales"] = SUPPORTED_LOCALES
    templates.env.globals["get_locale"] = get_locale
except ImportError:
    logger.warning("i18n module not available to page_router")

try:
    from app.core.subject_starters import get_subject_starters as _get_subject_starters
    templates.env.globals["subject_starters"] = _get_subject_starters()
except ImportError:
    pass


# =============================================================================
# Guard logic — mirrors _guard_by_contract from main.py
# =============================================================================

async def _guard_page(request: Request, page_id: str) -> Optional[RedirectResponse]:
    """Guard a page using its PageContract. Returns redirect if denied, None if OK."""
    contract = PAGE_CONTRACTS.get(page_id)
    if not contract:
        return None  # No contract = public access

    from app.core.storage_middleware import is_valid_storage_user
    from app.core.workflow_engine import route_user as _route_user

    _raw = request.cookies.get(COOKIE_USER_ID)
    user_id = str(_raw) if _raw is not None else None
    if not user_id:
        # No cookie — new user to welcome page
        from app.core.navigation import navigation
        root_stage = navigation.get_stage("root")
        root_path = root_stage.path if root_stage else "/"
        return ssot_redirect(root_path, context=f"page_router:{page_id} no user cookie")
    if not is_valid_storage_user(user_id):
        # Has cookie but invalid — returning user needs reconnect
        from app.core.navigation import navigation
        reconnect_stage = navigation.get_stage("storage_reconnect")
        reconnect_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"
        return ssot_redirect(reconnect_path, context=f"page_router:{page_id} reconnect required")

    current_role = get_role_from_user_id(user_id) or ""
    allowed_roles = {r.value for r in contract.roles_supported}
    if current_role not in allowed_roles:
        return ssot_redirect(await _route_user(user_id), context=f"page_router:{page_id} role mismatch")

    return None


# =============================================================================
# Context builder
# =============================================================================

def _build_context(request: Request, entry: PageManifestEntry) -> Dict[str, Any]:
    """Build standard context for a page render."""
    contract = PAGE_CONTRACTS.get(entry.page_id)
    ctx: Dict[str, Any] = {
        "page_id": entry.page_id,
        "page_title": contract.title if contract else entry.page_id.replace("_", " ").title(),
        "page_contract": contract,
        "route": entry.route,
        "request": request,
    }

    # Try to get user info
    user_id = request.cookies.get(COOKIE_USER_ID)
    if user_id:
        ctx["user_id"] = user_id
        ctx["user_role"] = get_role_from_user_id(user_id) or ""

    return ctx


# =============================================================================
# Placeholder template — used when the real template doesn't exist yet
# =============================================================================

_PLACEHOLDER_TEMPLATE = """{% extends "base.html" %}
{% block title %}{{ page_title }} - Semptify{% endblock %}

{% block content %}
<div class="container container--narrow" style="padding-top: 2rem;">
    <section class="page-info" style="margin-bottom: 2rem;">
        <h1>{{ page_title }}</h1>
        <p class="text-secondary">This page is part of the Semptify unified page system.</p>
    </section>

    <section class="page-info" style="margin-bottom: 2rem;">
        <h2>What this is</h2>
        <p>{{ page_contract.expectations if page_contract else "Page content is being prepared." }}</p>
    </section>

    <section class="page-info" style="margin-bottom: 2rem;">
        <h2>Why it matters</h2>
        <p>{{ page_contract.qualification if page_contract else "" }}</p>
    </section>

    <section class="page-action" style="margin-bottom: 2rem;">
        <h2>What to do next</h2>
        <p>This page is being assembled. Content will appear here once the page is fully converted.</p>
        <a href="/" class="btn btn--secondary">Back to Home</a>
    </section>
</div>
{% endblock %}
"""


def _render_placeholder(request: Request, entry: PageManifestEntry) -> HTMLResponse:
    """Render a placeholder page when the template file doesn't exist yet."""
    ctx = _build_context(request, entry)
    # Use from_string to render the placeholder inline
    template = templates.env.from_string(_PLACEHOLDER_TEMPLATE)
    html = template.render(**ctx)
    return HTMLResponse(content=html)


# =============================================================================
# Dynamic route registration
# =============================================================================

# Pages that already have dedicated route handlers elsewhere — don't register duplicates
_SKIP_ROUTES = {
    "/",  # welcome — handled in main.py
    "/tenant", "/tenant/",  # tenant root — handled in main.py
    "/home",  # home — handled in main.py
    "/advocate",  # advocate — handled in main.py
    "/admin",  # admin — handled in main.py
    "/legal", "/legal/",  # legal — handled in main.py
    "/help",  # help — stays static
    "/office",  # office — handled in main.py
    "/library",  # library — handled in main.py
    "/tools",  # tools — handled in main.py
    "/law-library",  # law_library — handled by law_library module
    "/calendar",  # calendar — handled in main.py
    "/timeline",  # timeline — handled in main.py
    "/documents",  # documents — handled in main.py
    "/vault",  # vault — handled in main.py
    "/complaints",  # complaints — handled in main.py
    "/command-center",  # command_center — handled in main.py
    "/auto-analysis",  # auto_analysis_summary — handled in main.py
    "/manager",  # manager — handled by manager module
    "/register",  # register — handled by auth module
    "/tenant/help",  # tenant_help — handled in main.py
}


def _template_exists(source_file: str) -> bool:
    """Check if a template file exists on disk."""
    full_path = BASE_PATH / source_file
    return full_path.is_file()


def _create_page_handler(entry: PageManifestEntry):
    """Create a route handler function for a manifest entry."""

    async def _page_handler(request: Request):
        # Guard
        guard_redirect = await _guard_page(request, entry.page_id)
        if guard_redirect:
            return guard_redirect

        # Check if template exists
        if _template_exists(entry.source_file):
            ctx = _build_context(request, entry)
            template_name = entry.source_file.replace("app/templates/", "")
            try:
                return templates.TemplateResponse(request, template_name, ctx)
            except Exception as e:
                logger.warning("Template render failed for %s: %s — using placeholder", entry.page_id, e)
                return _render_placeholder(request, entry)
        else:
            # Template doesn't exist yet — render placeholder
            return _render_placeholder(request, entry)

    _page_handler.__name__ = f"page_{entry.page_id}"
    _page_handler.__doc__ = f"Serve the {entry.page_id} page (route {entry.route})."
    return _page_handler


# Register routes for all template pages that don't already have a handler
_registered_count = 0
_skipped_count = 0

for _entry in PAGE_MANIFEST:
    if _entry.page_type != "template":
        continue
    if _entry.route in _SKIP_ROUTES:
        _skipped_count += 1
        continue

    _handler = _create_page_handler(_entry)
    router.add_api_route(
        _entry.route,
        _handler,
        methods=["GET"],
        response_class=HTMLResponse,
        name=f"page_{_entry.page_id}",
    )
    _registered_count += 1

logger.info(
    "Unified page router: %d routes registered, %d skipped (already handled elsewhere)",
    _registered_count,
    _skipped_count,
)
