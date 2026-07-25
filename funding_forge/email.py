"""Funding Forge email sender.

Supports Resend API (via httpx) and SMTP (via stdlib smtplib in a thread).
If no provider is configured, emails are saved as drafts and not sent.
All email data is admin/system data and never contains tenant PII.
"""

import logging
from datetime import UTC, datetime
from email.message import EmailMessage as StdlibEmailMessage
from typing import Any

from funding_forge.config import settings

logger = logging.getLogger("funding_forge.email")


def _provider() -> str:
    """Return the active email provider name."""
    if settings.resend_configured:
        return "resend"
    if settings.smtp_configured:
        return "smtp"
    return "none"


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _send_resend(
    to: str,
    subject: str,
    body: str,
    html_body: str | None,
    from_address: str,
    reply_to: str | None,
) -> dict[str, Any]:
    """Send an email using the Resend API."""
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required for Resend email delivery") from exc

    payload: dict[str, Any] = {
        "from": from_address,
        "to": [to],
        "subject": subject,
    }
    if html_body:
        payload["html"] = html_body
        payload["text"] = body
    else:
        payload["text"] = body
    if reply_to:
        payload["reply_to"] = reply_to

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    data = resp.json()
    if resp.status_code in (200, 202):
        return {
            "status": "sent",
            "external_id": data.get("id", ""),
            "provider": "resend",
            "error": None,
            "sent_at": _now(),
        }
    return {
        "status": "failed",
        "external_id": None,
        "provider": "resend",
        "error": data.get("message", f"Resend returned {resp.status_code}"),
        "sent_at": None,
    }


async def _send_smtp(
    to: str,
    subject: str,
    body: str,
    html_body: str | None,
    from_address: str,
) -> dict[str, Any]:
    """Send an email using an SMTP server in a background thread."""
    import asyncio
    import smtplib
    import ssl

    def _sync_send() -> dict[str, Any]:
        msg = StdlibEmailMessage()
        msg["From"] = from_address
        msg["To"] = to
        msg["Subject"] = subject
        if html_body:
            msg.add_alternative(html_body, subtype="html")
            msg.add_alternative(body, subtype="plain")
        else:
            msg.set_content(body)

        try:
            context = ssl.create_default_context()
            if settings.smtp_use_tls and settings.smtp_port == 465:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                    if settings.smtp_username:
                        server.login(settings.smtp_username, settings.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    if settings.smtp_use_tls:
                        server.starttls(context=context)
                    if settings.smtp_username:
                        server.login(settings.smtp_username, settings.smtp_password)
                    server.send_message(msg)
            return {
                "status": "sent",
                "external_id": None,
                "provider": "smtp",
                "error": None,
                "sent_at": _now(),
            }
        except smtplib.SMTPException as exc:
            return {
                "status": "failed",
                "external_id": None,
                "provider": "smtp",
                "error": str(exc),
                "sent_at": None,
            }

    return await asyncio.to_thread(_sync_send)


async def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]:
    """Send an email using the configured provider.

    Returns a dict with status, provider, external_id, error, and sent_at.
    If no provider is configured, the email is stored as a draft.
    """
    from_addr = from_address or settings.from_email
    reply = reply_to or settings.reply_to_email or None
    provider = _provider()

    if provider == "none":
        logger.warning("No email provider configured — email to %s saved as draft", to)
        return {
            "status": "draft",
            "external_id": None,
            "provider": "none",
            "error": "No email provider configured",
            "sent_at": None,
        }

    if provider == "resend":
        result = await _send_resend(to, subject, body, html_body, from_addr, reply)
    elif provider == "smtp":
        result = await _send_smtp(to, subject, body, html_body, from_addr)
    else:
        result = {
            "status": "draft",
            "external_id": None,
            "provider": provider,
            "error": "No email provider configured",
            "sent_at": None,
        }

    if result["status"] == "sent":
        logger.info("Email sent to %s via %s", to, result["provider"])
    else:
        logger.error("Email to %s via %s failed: %s", to, result["provider"], result.get("error"))

    return result
