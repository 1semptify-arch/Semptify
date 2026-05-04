"""
email_service.py — Transactional email via Resend API.

Usage:
    from app.services.email_service import send_email, send_support_notification

Set RESEND_API_KEY and FROM_EMAIL in environment / Render Dashboard.
No email is sent if RESEND_API_KEY is absent — the call is logged and silently
skipped so the app runs fine in development without credentials.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
_FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@semptify.org")
_SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@semptify.org")
_RESEND_SEND_URL = "https://api.resend.com/emails"


async def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    from_address: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """
    Send a transactional email via Resend.

    Returns True on success, False on failure or if no API key is configured.
    Never raises — failures are logged and swallowed so they don't break user flows.
    """
    if not _RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s: %s", to, subject)
        return False

    recipients = [to] if isinstance(to, str) else to
    payload: dict = {
        "from": from_address or _FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _RESEND_SEND_URL,
                headers={
                    "Authorization": f"Bearer {_RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code in (200, 201):
            logger.info("Email sent to %s | subject: %s", recipients, subject)
            return True
        logger.error(
            "Resend API error %s for email to %s: %s",
            resp.status_code,
            recipients,
            resp.text[:300],
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("HTTP error sending email to %s: %s", recipients, exc)
        return False


async def send_support_notification(
    subject: str,
    body_html: str,
    reply_to: Optional[str] = None,
) -> bool:
    """Send an internal notification to the support inbox."""
    return await send_email(
        to=_SUPPORT_EMAIL,
        subject=f"[Semptify] {subject}",
        html=body_html,
        reply_to=reply_to,
    )


async def send_feedback_email(
    user_email: Optional[str],
    feedback_text: str,
    page: Optional[str] = None,
) -> bool:
    """Forward a user feedback submission to the support inbox."""
    source = f"<p><strong>Page:</strong> {page}</p>" if page else ""
    user_line = (
        f"<p><strong>From:</strong> {user_email}</p>"
        if user_email
        else "<p><strong>From:</strong> anonymous</p>"
    )
    html = f"""
    <h2>Semptify User Feedback</h2>
    {user_line}
    {source}
    <p><strong>Feedback:</strong></p>
    <blockquote style="border-left:4px solid #7c3aed;padding-left:1rem;margin-left:0;color:#374151">
      {feedback_text}
    </blockquote>
    """
    return await send_support_notification(
        subject="New Feedback Submission",
        body_html=html,
        reply_to=user_email,
    )


async def send_contact_email(
    sender_name: str,
    sender_email: str,
    message: str,
) -> bool:
    """Forward a contact form submission to the support inbox."""
    html = f"""
    <h2>Semptify Contact Form</h2>
    <p><strong>Name:</strong> {sender_name}</p>
    <p><strong>Email:</strong> {sender_email}</p>
    <p><strong>Message:</strong></p>
    <blockquote style="border-left:4px solid #7c3aed;padding-left:1rem;margin-left:0;color:#374151">
      {message}
    </blockquote>
    """
    return await send_support_notification(
        subject=f"Contact: {sender_name}",
        body_html=html,
        reply_to=sender_email,
    )
