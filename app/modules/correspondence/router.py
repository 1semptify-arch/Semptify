"""
Correspondence Router
=====================

Admin-only module for the Correspondence hub tile (Semptify-originated emails
and templates). This first wiring pass is intentionally PII-free:
- Templates are static metadata.
- /logs returns an empty list placeholder.
- /send returns 501; the actual sending surface will be added when the
  data model, retention policy, and legal-handoff rules are designed.

All routes require admin authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_admin

router = APIRouter(
    prefix="/api/admin/correspondence",
    tags=["Correspondence"],
    dependencies=[Depends(require_admin)],
)


# In-memory catalog of Semptify email templates. These are metadata only — no
# recipient data, no PII. The actual templates live in app/services/email_service.py.
_CORRESPONDENCE_TEMPLATES: list[dict[str, str]] = [
    {
        "id": "feedback_ack",
        "name": "Feedback Acknowledgment",
        "description": "Sent to users after submitting feedback.",
    },
    {
        "id": "contact_forward",
        "name": "Contact Form Forward",
        "description": "Forwards contact form submissions to support.",
    },
    {
        "id": "deadline_notice",
        "name": "Deadline Notice",
        "description": "Deadline reminder for calendar events.",
    },
]


@router.get("/health")
async def correspondence_health() -> dict[str, Any]:
    """Admin health check for the correspondence module."""
    return {
        "status": "ok",
        "service": "correspondence",
        "pii_exposure": "none",
        "templates_available": len(_CORRESPONDENCE_TEMPLATES),
    }


@router.get("/templates")
async def list_templates() -> dict[str, Any]:
    """List correspondence templates (metadata only, no PII)."""
    return {
        "templates": _CORRESPONDENCE_TEMPLATES,
        "count": len(_CORRESPONDENCE_TEMPLATES),
    }


@router.get("/logs")
async def list_logs() -> dict[str, Any]:
    """Placeholder for the correspondence log.

    When implemented, this will return Semptify-originated emails with admin-only
    access and T2 tenant-PII handling. For now it returns an empty list so no
    PII is exposed while the wiring is validated.
    """
    return {
        "logs": [],
        "count": 0,
        "note": "correspondence log is a placeholder; T2 data model pending",
    }


@router.post("/send")
async def send_correspondence() -> dict[str, Any]:
    """Placeholder for sending correspondence.

    The real implementation will use app.services.email_service, require a
    data-sensitivity review, and enforce admin-only T2 handling. This wiring
    commit exposes no PII and does not send email.
    """
    raise HTTPException(
        status_code=501,
        detail="Correspondence sending not yet implemented",
    )
