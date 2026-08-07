"""Context Engine API router.

Endpoints:
- GET  /api/context/subjects               — list all 13 subjects with labels
- GET  /api/context/facts                  — list cached facts (subject, jurisdiction)
- POST /api/context/facts/refresh          — gather fresh facts for a subject
- GET  /api/context/stories                — list published stories
- POST /api/context/stories                — submit a new story (anonymized, pending moderation)
- GET  /api/context/stories/pending        — admin: list pending moderation
- POST /api/context/stories/{id}/moderate  — admin: moderate + publish/unpublish
- POST /api/context/verify                 — admin: verify facts for a subject
- GET  /api/context/overview               — admin: subjects + fact counts
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id
from app.modules.context_engine import cache as ctx_cache, stories as ctx_stories
from app.modules.context_engine.gatherer import gather_for_subject
from app.modules.context_engine.taxonomy import ALL_SUBJECTS, SUBJECT_LABELS
from app.modules.context_engine.verifier import verify_subject

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["Context Engine"])


# =============================================================================
# Guards
# =============================================================================


def _require_admin(user_id: str) -> None:
    role = get_role_from_user_id(user_id)
    if role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only.")


def _require_authenticated(user_id: str) -> None:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")


# =============================================================================
# Request Models
# =============================================================================


class RefreshRequest(BaseModel):
    subject: str = Field(..., description="One of the 13 subjects")
    jurisdiction: str = Field(default="MN")
    query: str | None = None


class StorySubmitRequest(BaseModel):
    subject: str = Field(...)
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=5000)
    jurisdiction: str = Field(default="MN")
    outcome: str = Field(default="avoided_court")


class ModerateStoryRequest(BaseModel):
    publish: bool
    title: str | None = None
    body: str | None = None


class VerifyRequest(BaseModel):
    subject: str
    jurisdiction: str = Field(default="MN")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/subjects")
async def list_subjects():
    """List all 13 subjects with human labels."""
    return {
        "subjects": [{"value": s, "label": SUBJECT_LABELS.get(s, s)} for s in ALL_SUBJECTS],
        "count": len(ALL_SUBJECTS),
    }


@router.get("/facts")
async def get_facts(
    request: Request,
    subject: str = Query(..., description="Subject filter"),
    jurisdiction: str = Query(default="MN"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """List cached facts for a subject + jurisdiction. No hallucination — all cited."""
    user_id = require_request_user_id(request)
    _require_authenticated(user_id)
    if subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {subject}")
    facts = await ctx_cache.get_facts(subject, jurisdiction, limit)
    return {
        "subject": subject,
        "jurisdiction": jurisdiction,
        "count": len(facts),
        "facts": [
            {
                "id": f.id,
                "claim": f.claim,
                "source_url": f.source_url,
                "source_name": f.source_name,
                "citation": f.citation,
                "is_verified": f.is_verified,
                "verified_at": f.verified_at.isoformat() if f.verified_at else None,
            }
            for f in facts
        ],
    }


@router.post("/facts/refresh")
async def refresh_facts(body: RefreshRequest, request: Request):
    """Gather fresh facts from external sources. Admin only."""
    user_id = require_request_user_id(request)
    _require_admin(user_id)
    if body.subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {body.subject}")
    new_facts = await gather_for_subject(
        subject=body.subject,
        jurisdiction=body.jurisdiction,
        query=body.query,
    )
    logger.info("Context refresh: %s/%s -> %d facts", body.subject, body.jurisdiction, len(new_facts))
    return {
        "status": "refreshed",
        "subject": body.subject,
        "jurisdiction": body.jurisdiction,
        "new_count": len(new_facts),
    }


@router.get("/stories")
async def get_stories(
    request: Request,
    subject: str | None = Query(default=None),
    jurisdiction: str = Query(default="MN"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """List published, moderated stories. Anyone authenticated can read."""
    user_id = require_request_user_id(request)
    _require_authenticated(user_id)
    if subject and subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {subject}")
    stories = await ctx_stories.get_published_stories(
        subject=subject,
        jurisdiction=jurisdiction,
        limit=limit,
    )
    return {
        "count": len(stories),
        "stories": [
            {
                "id": s.id,
                "subject": s.subject,
                "title": s.title,
                "body": s.body,
                "outcome": s.outcome,
                "jurisdiction": s.jurisdiction,
                "moderated_at": s.moderated_at.isoformat() if s.moderated_at else None,
            }
            for s in stories
        ],
    }


@router.post("/stories")
async def submit_story(body: StorySubmitRequest, request: Request):
    """Submit a tenant story. Anonymized, pending moderation."""
    user_id = require_request_user_id(request)
    _require_authenticated(user_id)
    if body.subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {body.subject}")
    try:
        story = await ctx_stories.submit_story(
            subject=body.subject,
            title=body.title,
            body=body.body,
            jurisdiction=body.jurisdiction,
            outcome=body.outcome,
            submitted_by=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info("Story %d submitted by %s for subject=%s", story.id, user_id, body.subject)
    return {
        "status": "submitted",
        "story_id": story.id,
        "message": "Story submitted for moderation. Thank you — it will appear once reviewed.",
    }


@router.get("/stories/pending")
async def list_pending_stories(request: Request):
    """Admin: list stories pending moderation."""
    user_id = require_request_user_id(request)
    _require_admin(user_id)
    pending = await ctx_stories.get_pending_stories()
    return {
        "count": len(pending),
        "stories": [
            {
                "id": s.id,
                "subject": s.subject,
                "title": s.title,
                "body": s.body,
                "outcome": s.outcome,
                "submitted_by": s.submitted_by,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in pending
        ],
    }


@router.post("/stories/{story_id}/moderate")
async def moderate_story(story_id: int, body: ModerateStoryRequest, request: Request):
    """Admin: moderate a story — optionally edit, then publish/unpublish."""
    user_id = require_request_user_id(request)
    _require_admin(user_id)
    try:
        story = await ctx_stories.moderate_story(
            story_id=story_id,
            moderated_by=user_id,
            publish=body.publish,
            title=body.title,
            body=body.body,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    logger.info("Story %d moderated by %s (publish=%s)", story_id, user_id, body.publish)
    return {
        "status": "moderated",
        "story_id": story.id,
        "is_published": story.is_published,
    }


@router.post("/verify")
async def verify_facts(body: VerifyRequest, request: Request):
    """Admin: verify facts for a subject (checks source URLs still resolve)."""
    user_id = require_request_user_id(request)
    _require_admin(user_id)
    if body.subject not in ALL_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Unknown subject: {body.subject}")
    result = await verify_subject(body.subject, body.jurisdiction)
    return result


@router.get("/overview")
async def overview(request: Request):
    """Admin: overview of all subjects with fact counts."""
    user_id = require_request_user_id(request)
    _require_admin(user_id)
    counts = await ctx_cache.list_subjects_with_counts()
    return {
        "subjects": [
            {"value": s, "label": SUBJECT_LABELS.get(s, s), "fact_count": counts.get(s, 0)} for s in ALL_SUBJECTS
        ],
        "total_subjects": len(ALL_SUBJECTS),
    }
