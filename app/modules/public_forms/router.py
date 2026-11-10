"""
Public Forms Router
===================
Backend for the contact and feedback forms in static/public/.

Endpoints:
  POST /api/feedback   — /feedback page submits here
  POST /api/contact    — contact form submissions (future form)

Email is sent via Resend (app/services/email_service.py).
If RESEND_API_KEY is not set, submissions are logged and silently accepted
so the form still shows success to the user (no broken UX in dev).
"""
# Migrated from app/routers/public_forms.py into the public_forms SDK module.
# All imports remain absolute since public_forms is a CORE module.

import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Public Forms"])


# =============================================================================
# Request Models
# =============================================================================


class FeedbackRequest(BaseModel):
    type: str
    message: str
    email: str | None = None
    page: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Feedback message cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        allowed = {"bug", "missing", "confusing", "content", "positive", "other"}
        if v not in allowed:
            raise ValueError(f"Invalid feedback type. Must be one of: {sorted(allowed)}")
        return v


class ToolRequestCreate(BaseModel):
    """Anonymous public tool request — no name, no email, by design."""

    message: str

    @field_validator("message")
    @classmethod
    def message_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Request cannot be empty")
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Request must be 2000 characters or fewer")
        return v


class VoicePostCreate(BaseModel):
    """Anonymous public Your Voice post — no name, no email, by design."""

    kind: str
    message: str

    @field_validator("kind")
    @classmethod
    def kind_valid(cls, v: str) -> str:
        allowed = {"question", "opinion"}
        if v not in allowed:
            raise ValueError(f"Invalid post kind. Must be one of: {sorted(allowed)}")
        return v

    @field_validator("message")
    @classmethod
    def message_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Post cannot be empty")
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Post must be 2000 characters or fewer")
        return v


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    subject: str | None = None

    @field_validator("name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# Flag reasons mirror the decline rows of the moderation standard
# (MODERATION.md decision table). A fixed set keeps anonymous reports
# aggregable in the review lane and leaves no room for free text that
# could carry personal details.
VOICE_FLAG_REASONS = {
    "personal_details",
    "threat",
    "hate",
    "spam",
    "illegal",
    "impersonation",
    "other",
}


class VoicePostFlag(BaseModel):
    """Anonymous report that a published board post breaks the standard."""

    reason: str

    @field_validator("reason")
    @classmethod
    def reason_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VOICE_FLAG_REASONS:
            raise ValueError(f"Invalid reason. Must be one of: {sorted(VOICE_FLAG_REASONS)}")
        return v


# Story subjects: a short fixed set keeps anonymous posts aggregable for
# policy work without inviting free-text that could carry personal details.
STORY_SUBJECTS = {
    "repairs",
    "deposit",
    "eviction",
    "rent",
    "notices",
    "retaliation",
    "discrimination",
    "other",
}


class StoryCreate(BaseModel):
    """Anonymous public tenant story — no name, no email, by design."""

    subject: str
    title: str
    body: str
    outcome: str = "avoided_court"
    jurisdiction: str = "MN"

    @field_validator("subject")
    @classmethod
    def subject_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in STORY_SUBJECTS:
            raise ValueError(f"Invalid subject. Must be one of: {sorted(STORY_SUBJECTS)}")
        return v

    @field_validator("title")
    @classmethod
    def title_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if len(v) > 200:
            raise ValueError("Title must be 200 characters or fewer")
        return v

    @field_validator("body")
    @classmethod
    def body_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Story cannot be empty")
        if len(v) > 8000:
            raise ValueError("Story must be 8000 characters or fewer")
        return v

    @field_validator("outcome")
    @classmethod
    def outcome_valid(cls, v: str) -> str:
        from app.modules.context_engine.stories import VALID_OUTCOMES

        if v not in VALID_OUTCOMES:
            raise ValueError(f"Invalid outcome. Must be one of: {sorted(VALID_OUTCOMES)}")
        return v

    @field_validator("jurisdiction")
    @classmethod
    def jurisdiction_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("Jurisdiction must be a two-letter state code")
        return v


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    """
    Receive a feedback form submission from /feedback.
    Forwards to support inbox via Resend. Always returns success so
    the form UX is not broken if email is unconfigured.
    """
    from app.services.email_service import send_feedback_email

    label_map = {
        "bug": "Bug Report",
        "missing": "Missing Feature",
        "confusing": "UX Issue",
        "content": "Content Issue",
        "positive": "Positive Feedback",
        "other": "General Feedback",
    }
    type_label = label_map.get(body.type, body.type)

    full_message = f"[{type_label}]\n\n{body.message}"

    sent = await send_feedback_email(
        user_email=body.email,
        feedback_text=full_message,
        page=body.page,
    )

    if not sent:
        logger.info(
            "Feedback logged (email not sent — RESEND_API_KEY not set): type=%s email=%s",
            body.type,
            body.email or "anonymous",
        )

    return JSONResponse({"status": "ok", "received": True})


async def load_tenant_autofill(user_id: str) -> dict:
    """
    Resolve pre-fill data for any form from the tenant's own cloud storage.

    Priority:
    1. Cloud vault — profile.json + case.json (PII lives here, not DB)
    2. DB Contact table — landlord name/address only (PII-free fallback)
    3. TenantBriefcase — user_name only (last resort)

    Returns a dict with keys: tenant_name, property_address, landlord_name,
    landlord_address, email. Empty string for any unresolved field.

    This function is callable from any module (e.g. court_forms router).
    The /tenant/autofill endpoint delegates to it.
    """
    result = {
        "tenant_name": "",
        "property_address": "",
        "landlord_name": "",
        "landlord_address": "",
        "email": "",
    }

    if not user_id:
        return result

    # -------------------------------------------------------------------------
    # Layer 1: Cloud vault — profile.json + case.json (PII lives here, not DB)
    # -------------------------------------------------------------------------
    cloud_loaded = False
    try:
        from app.core.database import get_db_session
        from app.modules.cloud_sync.service import UserCloudSync
        from app.modules.storage.router import get_valid_session

        async with get_db_session() as db:
            session = await get_valid_session(db, user_id)

        if session:
            provider = session.get("provider")
            access_token = session.get("access_token")
            storage = None

            if provider == "google_drive":
                from app.services.storage.google_drive import GoogleDriveProvider

                storage = GoogleDriveProvider(access_token)
            elif provider == "dropbox":
                from app.services.storage.dropbox import DropboxProvider

                storage = DropboxProvider(access_token)
            elif provider == "onedrive":
                from app.services.storage.onedrive import OneDriveProvider

                storage = OneDriveProvider(access_token)

            if storage:
                sync = UserCloudSync(storage, user_id)
                profile = await sync.load_profile()
                case = await sync.load_case()

                if profile:
                    if profile.display_name:
                        result["tenant_name"] = profile.display_name
                    if profile.email:
                        result["email"] = profile.email

                if case:
                    if case.tenant_name and not result["tenant_name"]:
                        result["tenant_name"] = case.tenant_name
                    if case.property_address:
                        result["property_address"] = case.property_address
                    if case.landlord_name:
                        result["landlord_name"] = case.landlord_name
                    if case.landlord_address:
                        result["landlord_address"] = case.landlord_address

                cloud_loaded = True
                logger.debug("autofill: cloud vault loaded for %s", user_id[:8])

    except Exception as exc:
        logger.debug("autofill: cloud vault unavailable for %s: %s", user_id[:8], exc)

    # -------------------------------------------------------------------------
    # Layer 2: Vault contacts — landlord only (no PII, fills any cloud gaps)
    # -------------------------------------------------------------------------
    if not result["landlord_name"] or not result["property_address"]:
        try:
            from app.modules.contacts.service import list_contacts_for_user_id

            landlord_overlays, _total = await list_contacts_for_user_id(
                user_id, contact_type="landlord"
            )
            landlord = (
                max(landlord_overlays, key=lambda o: o.created_at) if landlord_overlays else None
            )
            if landlord:
                p = landlord.payload
                if p.get("name") and not result["landlord_name"]:
                    result["landlord_name"] = p.get("name")
                if not result["property_address"]:
                    addr_parts = [
                        p.get("address_line1"),
                        p.get("city"),
                        p.get("state"),
                        p.get("zip_code"),
                    ]
                    addr = ", ".join(part for part in addr_parts if part)
                    if addr:
                        result["property_address"] = addr
        except Exception as exc:
            logger.warning("autofill: vault contacts fallback error for %s: %s", user_id[:8], exc)

    # -------------------------------------------------------------------------
    # Layer 3: TenantBriefcase — user_name only (last resort for tenant name)
    # -------------------------------------------------------------------------
    if not result["tenant_name"]:
        try:
            from app.core.tenant_briefcase import get_tenant_briefcase

            briefcase = await get_tenant_briefcase(user_id)
            if briefcase and briefcase.user_name:
                result["tenant_name"] = briefcase.user_name
        except Exception as exc:
            logger.debug("autofill: briefcase unavailable for %s: %s", user_id[:8], exc)

    logger.debug(
        "autofill: resolved fields=%s cloud=%s user=%s",
        [k for k, v in result.items() if v],
        cloud_loaded,
        user_id[:8],
    )
    return result


@router.post("/tenant/autofill")
@limiter.limit("30/minute")
async def tenant_autofill(request: Request):
    """
    Return pre-fill data for letter forms from the tenant's own cloud storage.
    Delegates to load_tenant_autofill() — callable from any module.
    POST to prevent CSRF.
    """
    from app.core.cookie_auth import extract_user_id

    user_id = extract_user_id(request) or ""
    result = await load_tenant_autofill(user_id)
    return JSONResponse(result)


@router.post("/tool-request")
@limiter.limit("5/minute")
async def submit_tool_request(request: Request, body: ToolRequestCreate):
    """
    Receive an anonymous public tool request from /tool-requests.

    No name or email is accepted — Semptify takes no names and tracks no
    one. The request is stored and published on /tool-requests with our
    response after a review pass that removes personal details.
    """
    import uuid

    from app.core.database import get_db_session
    from app.models.models import ToolRequest

    async with get_db_session() as db:
        db.add(ToolRequest(id=str(uuid.uuid4()), request_text=body.message))

    return JSONResponse({"status": "ok", "received": True})


@router.get("/tool-requests")
async def list_tool_requests():
    """
    List published tool requests with our responses — public, no auth.
    Newest first, capped at 200.
    """
    from sqlalchemy import select

    from app.core.database import get_db_session
    from app.models.models import ToolRequest

    async with get_db_session() as db:
        result = await db.execute(
            select(ToolRequest)
            .where(ToolRequest.is_published.is_(True))
            .order_by(ToolRequest.created_at.desc())
            .limit(200)
        )
        rows = result.scalars().all()
        pending = await db.execute(
            select(ToolRequest.id).where(ToolRequest.status == "received")
        )
        pending_count = len(pending.scalars().all())

    return JSONResponse(
        {
            "requests": [
                {
                    "id": r.id,
                    "request": r.request_text,
                    "response": r.response_text,
                    "status": r.status,
                    "date": r.created_at.date().isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "awaiting_review": pending_count,
        }
    )


@router.post("/voice-post")
@limiter.limit("5/minute")
async def submit_voice_post(request: Request, body: VoicePostCreate):
    """
    Receive an anonymous public question or opinion from /your-voice.

    No name or email is accepted — Semptify takes no names and tracks no
    one. The post is stored and published on /your-voice with an answer
    after a review pass that removes personal details.
    """
    import uuid

    from app.core.database import get_db_session
    from app.models.models import VoicePost

    async with get_db_session() as db:
        db.add(
            VoicePost(
                id=str(uuid.uuid4()),
                kind=body.kind,
                post_text=body.message,
            )
        )

    return JSONResponse({"status": "ok", "received": True})


@router.get("/voice-posts")
async def list_voice_posts():
    """
    List published Your Voice posts with answers — public, no auth.
    Newest first, capped at 200.
    """
    from sqlalchemy import select

    from app.core.database import get_db_session
    from app.models.models import VoicePost

    async with get_db_session() as db:
        result = await db.execute(
            select(VoicePost)
            .where(VoicePost.is_published.is_(True))
            .order_by(VoicePost.created_at.desc())
            .limit(200)
        )
        rows = result.scalars().all()
        pending = await db.execute(
            select(VoicePost.id).where(VoicePost.status == "received")
        )
        pending_count = len(pending.scalars().all())

    return JSONResponse(
        {
            "posts": [
                {
                    "id": r.id,
                    "kind": r.kind,
                    "post": r.post_text,
                    "response": r.response_text,
                    "responder": r.responder_label,
                    "status": r.status,
                    "date": r.created_at.date().isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "awaiting_review": pending_count,
        }
    )


@router.post("/voice-posts/{post_id}/flag")
@limiter.limit("5/minute")
async def flag_voice_post(post_id: str, request: Request, body: VoicePostFlag):
    """
    Report a published board post that breaks the review standard.

    Anonymous like the board itself — no name, no identity, just a reason
    code. The post stays published while flagged (the bias is toward
    hearing it); the flag surfaces it in the same /admin/public-voice
    review queue for a deliberate human re-check.
    """
    from sqlalchemy import select

    from app.core.database import get_db_session
    from app.core.utc import utc_now
    from app.models.models import VoicePost

    async with get_db_session() as db:
        result = await db.execute(select(VoicePost).where(VoicePost.id == post_id))
        post = result.scalars().first()
        # Only published posts are flaggable — nothing else is on the
        # board. Missing and unpublished both 404 so existence isn't leaked.
        if not post or not post.is_published:
            return JSONResponse({"status": "not_found"}, status_code=404)

        post.flag_count = (post.flag_count or 0) + 1
        reasons = dict(post.flag_reasons or {})
        reasons[body.reason] = reasons.get(body.reason, 0) + 1
        post.flag_reasons = reasons  # reassign — JSON columns don't track in-place edits
        post.flagged_at = utc_now()

    logger.info(
        "voice post flagged: %s reason=%s count=%s",
        post_id[:8],
        body.reason,
        post.flag_count,
    )
    return JSONResponse({"status": "ok", "flagged": True})


@router.post("/story")
@limiter.limit("5/minute")
async def submit_public_story(request: Request, body: StoryCreate):
    """
    Receive an anonymous public tenant story from /tell-your-story.

    No name or email is accepted — Semptify takes no names and tracks no
    one. The story is stored for moderation and published on
    /tell-your-story after a review pass that removes personal details.
    """
    from app.modules.context_engine.stories import submit_story

    await submit_story(
        subject=body.subject,
        title=body.title,
        body=body.body,
        jurisdiction=body.jurisdiction,
        outcome=body.outcome,
        submitted_by=None,
    )

    return JSONResponse({"status": "ok", "received": True})


@router.get("/stories")
async def list_stories(subject: str | None = None):
    """
    List published, moderated tenant stories — public, no auth.
    Newest first, capped at 50. Optional ?subject= filter.
    """
    from sqlalchemy import and_, select

    from app.core.database import get_db_session
    from app.modules.context_engine.models import TenantStory

    conditions = [
        TenantStory.is_published.is_(True),
        TenantStory.is_moderated.is_(True),
    ]
    if subject:
        conditions.append(TenantStory.subject == subject.strip().lower())

    async with get_db_session() as db:
        result = await db.execute(
            select(TenantStory)
            .where(and_(*conditions))
            .order_by(TenantStory.moderated_at.desc())
            .limit(50)
        )
        rows = result.scalars().all()
        pending = await db.execute(
            select(TenantStory.id).where(TenantStory.is_moderated.is_(False))
        )
        pending_count = len(pending.scalars().all())

    return JSONResponse(
        {
            "stories": [
                {
                    "id": s.id,
                    "subject": s.subject,
                    "jurisdiction": s.jurisdiction,
                    "title": s.title,
                    "body": s.body,
                    "outcome": s.outcome,
                    "date": s.moderated_at.date().isoformat() if s.moderated_at else None,
                }
                for s in rows
            ],
            "awaiting_review": pending_count,
        }
    )


@router.post("/contact")
async def submit_contact(body: ContactRequest):
    """
    Receive a contact form submission.
    Forwards to support inbox via Resend.
    """
    from app.services.email_service import send_contact_email


    sent = await send_contact_email(
        sender_name=body.name,
        sender_email=body.email,
        message=body.message,
    )

    if not sent:
        logger.info(
            "Contact form logged (email not sent — RESEND_API_KEY not set): name=%s email=%s",
            body.name,
            body.email,
        )

    return JSONResponse({"status": "ok", "received": True})
