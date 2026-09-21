"""Info Donation router — post-resolution opt-in info donation API.

Tenant-facing (T2) JSON API under /api/info-donation. Every endpoint is
gated by the feature-module capability check plus auth. The donation page
itself lives at /help-the-next-tenant (registered in app/main.py).

Spec: docs/blueprints/info_donation_blueprint.md +
handoffs/info-donation-possibilities-2026-09-19.md.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import require_capability
from app.core.database import get_db
from app.core.event_bus import EventType, publish_event
from app.core.security import UserContext, require_tier
from app.core.user_context import UserRole
from app.modules.info_donation import service
from app.modules.info_donation.catalog import CONSENT_TEXT, CONSENT_VERSION, public_items

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Info Donation"],
    dependencies=[Depends(require_capability("app.modules.info_donation.router"))],
)


def _require_admin(user: UserContext) -> None:
    """Reviewer gate — moderation is Brad + designated reviewers (admin)."""
    if user.get_effective_role() != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={"error": "admin_required", "message": "Review is limited to moderators."},
        )


def _item_to_dict(item) -> dict[str, Any]:
    import json

    return {
        "id": item.id,
        "item_key": item.item_key,
        "value": json.loads(item.value_json),
        "moderation": item.moderation,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health", dependencies=[Depends(require_tier("T2"))])
async def info_donation_health() -> dict[str, Any]:
    """Module health check."""
    return {"status": "ok", "module": "info_donation"}


# ---------------------------------------------------------------------------
# Gate state
# ---------------------------------------------------------------------------


@router.get("/status")
async def donation_status(
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Current gate state for the signed-in tenant."""
    return await service.get_status(db, user.user_id)


@router.get("/catalog")
async def donation_catalog(
    user: UserContext = Depends(require_tier("T2")),
) -> dict[str, Any]:
    """The donation item catalog + consent text the page renders."""
    return {
        "consent_version": CONSENT_VERSION,
        "consent_text": CONSENT_TEXT,
        "items": public_items(),
    }


class ResolvedRequest(BaseModel):
    source: str = Field("self_reported", max_length=60)


@router.post("/resolved")
async def mark_resolved(
    body: ResolvedRequest,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """The resolution event: the tenant marks their situation resolved.
    Also publishes ISSUE_RESOLVED so other modules can react."""
    await service.mark_resolved(db, user.user_id, source=body.source)
    await publish_event(
        EventType.ISSUE_RESOLVED,
        {"source": body.source},
        source="info_donation",
        user_id=user.user_id,
    )
    return {"ok": True, "resolved": True}


@router.post("/dismiss")
async def dismiss_prompt(
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Permanently dismiss the donation ask for this tenant."""
    await service.dismiss(db, user.user_id)
    return {"ok": True, "dismissed": True}


# ---------------------------------------------------------------------------
# Consent + donation
# ---------------------------------------------------------------------------


class ConsentRequest(BaseModel):
    consent_version: str = Field(..., max_length=40)


@router.post("/consent")
async def record_consent(
    body: ConsentRequest,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record informed consent for server-side aggregate storage."""
    try:
        await service.record_consent(db, user.user_id, body.consent_version)
    except service.DonationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "consented": True, "consent_version": CONSENT_VERSION}


class DonateRequest(BaseModel):
    items: dict[str, Any] = Field(..., min_length=1)


@router.post("/donate")
async def donate(
    body: DonateRequest,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Store the tenant's selected donation items (validated, screened)."""
    try:
        stored = await service.submit_items(db, user.user_id, body.items)
    except service.DonationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "stored": [_item_to_dict(i) for i in stored]}


@router.get("/mine")
async def list_mine(
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Everything this tenant has donated — their data, always visible to
    them, always removable."""
    items = await service.list_mine(db, user.user_id)
    return {"items": [_item_to_dict(i) for i in items]}


@router.delete("/mine/{item_id}")
async def withdraw_item(
    item_id: str,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Take back one donated item."""
    removed = await service.withdraw_item(db, user.user_id, item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Donation item not found.")
    return {"ok": True, "removed": item_id}


@router.post("/withdraw-all")
async def withdraw_all(
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Take back everything and withdraw consent."""
    removed = await service.withdraw_all(db, user.user_id)
    return {"ok": True, "removed_count": removed}


# ---------------------------------------------------------------------------
# Review surface (Brad + beta reviewers — admin-gated)
# ---------------------------------------------------------------------------


@router.get("/review/pending")
async def review_pending(
    user: UserContext = Depends(require_tier("T3")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List free-text donations awaiting review."""
    _require_admin(user)
    items = await service.list_pending_review(db)
    return {"items": [_item_to_dict(i) for i in items]}


class ModerationRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")


@router.post("/review/{item_id}")
async def review_decision(
    item_id: str,
    body: ModerationRequest,
    user: UserContext = Depends(require_tier("T3")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve or reject a pending free-text donation."""
    _require_admin(user)
    try:
        item = await service.moderate_item(db, item_id, body.decision, user.user_id)
    except service.DonationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if item is None:
        raise HTTPException(status_code=404, detail="Donation item not found.")
    return {"ok": True, "item": _item_to_dict(item)}
