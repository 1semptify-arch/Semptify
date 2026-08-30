"""UI Composer router — HTTP endpoints for self-assembling pages.

Endpoints:
    GET /api/ui/page/{intent}        — composed page as HTML (server-rendered)
    GET /api/ui/fragment/{ctype}     — single fragment for HTMX swaps
    GET /api/ui/process/{workflow_id} — process indicator fragment

All endpoints return server-rendered HTML (Jinja2) for HTMX or direct browser use.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.services.ui_composer import (
    COMPONENT_TYPES,
    PAGE_INTENTS,
    compose_page,
    get_process_status,
    render_fragment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ui", tags=["UI Composer"])


def _get_user_id_from_request(request: Request) -> str:
    """Extract user_id from the signed cookie on the request.

    Falls back to empty string if not authenticated — the UI Composer
    degrades gracefully to an empty state for unauthenticated requests.
    """
    try:
        from app.core.cookie_auth import verify_user_id

        user_id_cookie = request.cookies.get("semptify_uid", "")
        if not user_id_cookie:
            return ""
        return verify_user_id(user_id_cookie) or ""
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("UI Composer: no user_id on request: %s", e)
        return ""


@router.get("/page/{intent}", response_class=HTMLResponse)
async def compose_page_endpoint(
    intent: str,
    request: Request,
    document_count: int = Query(default=0, ge=0),
):
    """Compose and render a page for the given intent.

    Returns server-rendered HTML built from the UI Composer's component list.
    The generic template loops through components and renders each via Jinja macros.
    """
    if intent not in PAGE_INTENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown page intent: {intent}. Valid: {sorted(PAGE_INTENTS)}",
        )

    user_id = _get_user_id_from_request(request)

    # Build a minimal context from query params (real context comes from Context Loop)
    from app.core.module_gate import get_module_access

    access = get_module_access(request)
    context: dict[str, Any] = {
        "document_count": document_count,
        "resolved_module_paths": access.resolved_module_paths,
    }

    try:
        page = compose_page(user_id, intent, context=context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Render via the generic template
    from app.main import templates

    return templates.TemplateResponse(
        request,
        "generic_page.html",
        {
            "page_title": page["page_title"],
            "pillar": page["pillar"],
            "components": page["components"],
        },
    )


@router.get("/fragment/{component_type}", response_class=HTMLResponse)
async def render_fragment_endpoint(
    component_type: str,
    request: Request,
):
    """Render a single component as an HTML fragment (for HTMX swaps).

    Query params are forwarded to the component as data. For example:
    /api/ui/fragment/timeline_group?type=documents&date_label=Today

    The fragment is rendered via the component macro from the library.
    """
    if component_type not in COMPONENT_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown component type: {component_type}. Valid: {sorted(COMPONENT_TYPES)}",
        )

    # Build data dict from query params
    data: dict[str, Any] = dict(request.query_params)

    try:
        fragment = render_fragment(component_type, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Render just the component fragment
    from app.main import templates

    return templates.TemplateResponse(
        request,
        "components/component_fragment.html",
        {"component": fragment},
    )


@router.get("/process/{workflow_id}", response_class=HTMLResponse)
async def process_status_endpoint(
    workflow_id: str,
    request: Request,
):
    """Return the current workflow step as an HTML fragment (process indicator).

    Used by HTMX polling: hx-get="/api/ui/process/{workflow_id}" hx-trigger="every 2s"
    """
    status = get_process_status(workflow_id)

    fragment = render_fragment(
        "process_indicator",
        {
            "workflow_id": workflow_id,
            "step_label": status["step_label"],
            "state": status["state"],
            "progress_pct": status["progress_pct"],
        },
    )

    from app.main import templates

    return templates.TemplateResponse(
        request,
        "components/component_fragment.html",
        {"component": fragment},
    )
