"""Admin API router — elevated admin operations.

These endpoints live under /admin/api and require a valid admin elevation cookie.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.admin_elevation import require_elevation
from app.core.logging_service import set_log_level
from app.core.module_registry_loader import run_sync_and_verify

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.put("/admin/api/logs/level")
async def admin_set_log_level(level: str, admin_uid: str = Depends(require_elevation)):
    """Set the runtime root log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)."""
    return {"level": set_log_level(level)}


@router.post("/admin/api/verify")
async def admin_verify_api(admin_uid: str = Depends(require_elevation)):
    """Run sync_registry + verify_modules and return the updated registry."""
    return await run_sync_and_verify()


# =============================================================================
# Public voice review-and-respond lane
#
# Backs the screen at /admin/public-voice: one queue for everything the
# public submits anonymously — Your Voice posts, tool requests, and tenant
# stories. All endpoints inherit AdminNetworkMiddleware (private-network
# only) plus the elevation cookie check via require_elevation.
# =============================================================================


class VoicePostReview(BaseModel):
    """Action on one voice post: publish, answer, decline, unpublish,
    or dismiss — dismiss clears reader flags without changing the post."""

    action: str
    response_text: str | None = None
    responder_label: str | None = None

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        allowed = {"publish", "answer", "decline", "unpublish", "dismiss"}
        if v not in allowed:
            raise ValueError(f"Invalid action. Must be one of: {sorted(allowed)}")
        return v

    @field_validator("response_text")
    @classmethod
    def response_valid(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 4000:
            raise ValueError("Response must be 4000 characters or fewer")
        return v.strip() if v else v

    @field_validator("responder_label")
    @classmethod
    def label_valid(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 80:
            raise ValueError("Responder label must be 80 characters or fewer")
        return v.strip() if v else v


class ToolRequestReview(BaseModel):
    """Action on one tool request: publish, answer, decline, or unpublish."""

    action: str
    response_text: str | None = None

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        allowed = {"publish", "answer", "decline", "unpublish"}
        if v not in allowed:
            raise ValueError(f"Invalid action. Must be one of: {sorted(allowed)}")
        return v

    @field_validator("response_text")
    @classmethod
    def response_valid(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 4000:
            raise ValueError("Response must be 4000 characters or fewer")
        return v.strip() if v else v


class StoryReview(BaseModel):
    """Moderate one story: publish or unpublish, with optional anonymizing edits."""

    action: str
    title: str | None = None
    body: str | None = None

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        allowed = {"publish", "unpublish"}
        if v not in allowed:
            raise ValueError(f"Invalid action. Must be one of: {sorted(allowed)}")
        return v

    @field_validator("title")
    @classmethod
    def title_ok(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 200:
            raise ValueError("Title must be 200 characters or fewer")
        return v.strip() if v else v


@router.get("/admin/api/public-forms/pending")
async def admin_list_pending(admin_uid: str = Depends(require_elevation)):
    """
    Everything awaiting the review pass — unpublished posts and any
    published post a reader flagged — plus the most recent published
    items per queue so they can be pulled back down if needed.
    """
    from sqlalchemy import or_, select

    from app.core.database import get_db_session
    from app.models.models import ToolRequest, VoicePost
    from app.modules.context_engine.models import TenantStory

    async with get_db_session() as db:
        voice_pending = (
            (
                await db.execute(
                    select(VoicePost)
                    .where(
                        or_(
                            VoicePost.is_published.is_(False),
                            VoicePost.flag_count > 0,
                        )
                    )
                    .order_by(
                        (VoicePost.flag_count > 0).desc(),
                        VoicePost.created_at.asc(),
                    )
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        voice_published = (
            (
                await db.execute(
                    select(VoicePost)
                    .where(VoicePost.is_published.is_(True))
                    .order_by(VoicePost.created_at.desc())
                    .limit(25)
                )
            )
            .scalars()
            .all()
        )
        tool_pending = (
            (
                await db.execute(
                    select(ToolRequest)
                    .where(ToolRequest.is_published.is_(False))
                    .order_by(ToolRequest.created_at.asc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        tool_published = (
            (
                await db.execute(
                    select(ToolRequest)
                    .where(ToolRequest.is_published.is_(True))
                    .order_by(ToolRequest.created_at.desc())
                    .limit(25)
                )
            )
            .scalars()
            .all()
        )
        story_pending = (
            (
                await db.execute(
                    select(TenantStory)
                    .where(TenantStory.is_moderated.is_(False))
                    .order_by(TenantStory.created_at.asc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        story_published = (
            (
                await db.execute(
                    select(TenantStory)
                    .where(TenantStory.is_published.is_(True))
                    .order_by(TenantStory.moderated_at.desc())
                    .limit(25)
                )
            )
            .scalars()
            .all()
        )

    def _date(dt):
        return dt.date().isoformat() if dt else None

    def _voice(r):
        return {
            "id": r.id,
            "kind": r.kind,
            "post": r.post_text,
            "response": r.response_text,
            "responder": r.responder_label,
            "status": r.status,
            "is_published": r.is_published,
            "flag_count": r.flag_count or 0,
            "flag_reasons": r.flag_reasons or {},
            "flagged_at": _date(r.flagged_at),
            "date": _date(r.created_at),
        }

    def _tool(r):
        return {
            "id": r.id,
            "request": r.request_text,
            "response": r.response_text,
            "status": r.status,
            "date": _date(r.created_at),
        }

    def _story(r):
        return {
            "id": r.id,
            "subject": r.subject,
            "jurisdiction": r.jurisdiction,
            "title": r.title,
            "body": r.body,
            "outcome": r.outcome,
            "is_published": r.is_published,
            "date": _date(r.created_at),
        }

    return JSONResponse(
        {
            "voice_posts": [_voice(r) for r in voice_pending],
            "tool_requests": [_tool(r) for r in tool_pending],
            "stories": [_story(r) for r in story_pending],
            "published": {
                "voice_posts": [_voice(r) for r in voice_published],
                "tool_requests": [_tool(r) for r in tool_published],
                "stories": [_story(r) for r in story_published],
            },
        }
    )


@router.post("/admin/api/public-forms/voice-posts/{post_id}")
async def admin_review_voice_post(
    post_id: str,
    body: VoicePostReview,
    admin_uid: str = Depends(require_elevation),
):
    """Publish, answer, decline, or unpublish one Your Voice post."""
    from sqlalchemy import select

    from app.core.database import get_db_session
    from app.models.models import VoicePost

    if body.action == "answer" and not (body.response_text and body.response_text.strip()):
        raise HTTPException(status_code=422, detail="An answer requires response_text")

    async with get_db_session() as db:
        result = await db.execute(select(VoicePost).where(VoicePost.id == post_id))
        post = result.scalars().first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if body.action == "answer":
            post.response_text = body.response_text.strip()
            post.responder_label = (
                body.responder_label if body.responder_label else "Semptify"
            )
            post.status = "answered"
            post.is_published = True
        elif body.action == "publish":
            post.status = "published"
            post.is_published = True
        elif body.action == "decline":
            post.status = "declined"
            post.is_published = False
        elif body.action == "unpublish":
            post.status = "received"
            post.is_published = False
        # dismiss: no status change — the post was looked at and stays
        # as it is; only the flag state resets below.

        # Every review action is a human re-check of the post, so reader
        # flags resolve here regardless of which action was taken.
        post.flag_count = 0
        post.flag_reasons = None
        post.flagged_at = None

    logger.info(
        "public-forms review: voice post %s -> %s (by %s)",
        post_id[:8],
        body.action,
        admin_uid[:6],
    )
    return JSONResponse({"status": "ok", "action": body.action, "id": post_id})


@router.post("/admin/api/public-forms/tool-requests/{request_id}")
async def admin_review_tool_request(
    request_id: str,
    body: ToolRequestReview,
    admin_uid: str = Depends(require_elevation),
):
    """Publish, answer, decline, or unpublish one tool request."""
    from sqlalchemy import select

    from app.core.database import get_db_session
    from app.models.models import ToolRequest

    if body.action == "answer" and not (body.response_text and body.response_text.strip()):
        raise HTTPException(status_code=422, detail="An answer requires response_text")

    async with get_db_session() as db:
        result = await db.execute(select(ToolRequest).where(ToolRequest.id == request_id))
        req = result.scalars().first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")

        if body.action == "answer":
            req.response_text = body.response_text.strip()
            req.status = "answered"
            req.is_published = True
        elif body.action == "publish":
            req.status = "published"
            req.is_published = True
        elif body.action == "decline":
            req.status = "declined"
            req.is_published = False
        else:  # unpublish
            req.status = "received"
            req.is_published = False

    logger.info(
        "public-forms review: tool request %s -> %s (by %s)",
        request_id[:8],
        body.action,
        admin_uid[:6],
    )
    return JSONResponse({"status": "ok", "action": body.action, "id": request_id})


@router.post("/admin/api/public-forms/stories/{story_id}")
async def admin_review_story(
    story_id: int,
    body: StoryReview,
    admin_uid: str = Depends(require_elevation),
):
    """Moderate one story — publish or unpublish, with optional edits that
    remove personal details before it goes public."""
    from app.modules.context_engine.stories import moderate_story

    try:
        story = await moderate_story(
            story_id=story_id,
            moderated_by=admin_uid,
            publish=body.action == "publish",
            title=body.title,
            body=body.body,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Story not found") from None

    logger.info(
        "public-forms review: story %s -> %s (by %s)",
        story_id,
        body.action,
        admin_uid[:6],
    )
    return JSONResponse({"status": "ok", "action": body.action, "id": story.id})
