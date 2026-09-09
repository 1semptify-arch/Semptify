"""
Law Linker Router
=================
Tenant-facing pop-out for legal citations.

  - GET /law-linker/pop-out?citation=...   HTML pop-out page
  - GET /api/law-linker/citation?citation=...  JSON for the pop-out / JS

The scratch-pad save action reuses /api/sticky-notes from app.modules.sticky_notes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.capabilities import require_capability
from app.core.security import yellow_access
from app.core.user_context import UserContext
from app.modules.law_linker import service as law_linker_service

logger = logging.getLogger(__name__)


capability_key = "app.modules.law_linker.router"

router = APIRouter(
    dependencies=[Depends(require_capability(capability_key))],
)


class CitationRequest(BaseModel):
    """Citation string for the pop-out or API."""

    citation: str = Field(..., min_length=1)


# =============================================================================
# JSON API
# =============================================================================


@router.get(
    "/api/law-linker/citation",
    tags=["Law Linker"],
)
async def get_citation(
    citation: str = Query(..., min_length=1, description="The citation text"),
):
    """Resolve a citation and return official source + fetched text."""
    result = await law_linker_service.resolve_and_fetch(citation)
    return JSONResponse(content=result)


# =============================================================================
# Pop-out page
# =============================================================================


@router.get(
    "/law-linker/pop-out",
    response_class=HTMLResponse,
    tags=["Law Linker"],
)
async def pop_out(
    request: Request,
    citation: str = Query(..., min_length=1),
    user: UserContext = Depends(yellow_access),
):
    """Render the citation pop-out page."""
    from app.main import templates

    result = await law_linker_service.resolve_and_fetch(citation)
    return templates.TemplateResponse(
        request,
        "pages/law_linker_popout.html",
        {
            "request": request,
            "user": user,
            "citation": result,
        },
    )
