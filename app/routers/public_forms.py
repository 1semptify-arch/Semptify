"""
Public Forms Router
===================
Backend for the contact and feedback forms in static/public/.

Endpoints:
  POST /api/feedback   — feedback.html submits here
  POST /api/contact    — contact form submissions (future form)

Email is sent via Resend (app/services/email_service.py).
If RESEND_API_KEY is not set, submissions are logged and silently accepted
so the form still shows success to the user (no broken UX in dev).
"""

import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Public Forms"])


# =============================================================================
# Request Models
# =============================================================================

class FeedbackRequest(BaseModel):
    type: str
    message: str
    email: Optional[str] = None
    page: Optional[str] = None

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


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    subject: Optional[str] = None

    @field_validator("name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    """
    Receive a feedback form submission from /public/feedback.html.
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


@router.post("/contact")
async def submit_contact(body: ContactRequest):
    """
    Receive a contact form submission.
    Forwards to support inbox via Resend.
    """
    from app.services.email_service import send_contact_email

    subject = body.subject or f"Contact: {body.name}"

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
