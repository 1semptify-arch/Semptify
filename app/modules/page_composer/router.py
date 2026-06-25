"""Page Composer API router.

Endpoints:
- GET /api/page/{subject}          — compose unified page view for a subject
- GET /api/page/{subject}/preview  — compose without user case data (public preview)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.request_utils import require_request_user_id
from app.modules.context_engine.taxonomy import ALL_SUBJECTS, SUBJECT_LABELS
from app.modules.page_composer.service import compose_page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/page", tags=["Page Composer"])


def _require_authenticated(user_id: str) -> None:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")


@router.get("/{subject}")
async def get_composed_page(
    subject: str,
    request: Request,
    jurisdiction: str = Query(default="MN"),
    fact_limit: int = Query(default=10, ge=1, le=50),
    story_limit: int = Query(default=5, ge=1, le=20),
):
    """Compose a unified page view for a subject.

    Returns verified facts, published tenant stories, and the user's own
    case data for this subject. All facts include source URLs (no hallucination).
    """
    user_id = require_request_user_id(request)
    _require_authenticated(user_id)
    if subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {subject}")
    try:
        page = await compose_page(
            subject=subject,
            jurisdiction=jurisdiction,
            user_id=user_id,
            fact_limit=fact_limit,
            story_limit=story_limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Page composed: %s/%s for user %s***", subject, jurisdiction, user_id[:6])
    return page


@router.get("/{subject}/preview")
async def get_page_preview(
    subject: str,
    jurisdiction: str = Query(default="MN"),
    fact_limit: int = Query(default=5, ge=1, le=20),
    story_limit: int = Query(default=3, ge=1, le=10),
):
    """Compose a preview page view without user case data.

    Public endpoint — no auth required. Returns facts + stories only.
    Useful for landing pages and marketing.
    """
    if subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {subject}")
    try:
        page = await compose_page(
            subject=subject,
            jurisdiction=jurisdiction,
            user_id=None,
            fact_limit=fact_limit,
            story_limit=story_limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Page preview composed: %s/%s", subject, jurisdiction)
    return page


@router.get("/")
async def list_composable_pages():
    """List all subjects that can be composed into pages."""
    return {
        "subjects": [
            {"value": s, "label": SUBJECT_LABELS.get(s, s)}
            for s in ALL_SUBJECTS
        ],
        "count": len(ALL_SUBJECTS),
    }
