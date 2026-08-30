"""Dispute Tracker router — list, add, and compare disputes.

T2 tenant-facing module. PII content is stored in cloud overlays; this router
only handles structure/pointers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.database import get_db
from app.core.id_gen import make_id
from app.core.navigation import navigation
from app.core.security import UserContext, require_tier
from app.core.ssot_guard import ssot_redirect
from app.core.utc import utc_now
from app.models.models import ComparisonEntry, DisputeRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(
    tags=["Dispute Tracker"],
)


def _user_id(user: UserContext | None) -> str | None:
    return user.user_id if user else None


@router.get("/health", dependencies=[Depends(require_tier("T2"))])
async def dispute_tracker_health() -> dict[str, Any]:
    """Module health check."""
    return {"status": "ok", "module": "dispute_tracker"}


@router.get("/", response_class=HTMLResponse)
async def dispute_tracker_page(
    request: Request,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Render the dispute tracker page (add dispute, list, add comparison)."""
    from app.main import templates

    result = await db.execute(
        select(DisputeRecord).where(DisputeRecord.user_id == _user_id(user)).order_by(DisputeRecord.created_at.desc())
    )
    disputes = result.scalars().all()

    cmp_result = await db.execute(
        select(ComparisonEntry)
        .where(ComparisonEntry.user_id == _user_id(user))
        .order_by(ComparisonEntry.created_at.desc())
    )
    comparisons = cmp_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "pages/dispute_tracker.html",
        {
            "disputes": disputes,
            "comparisons": comparisons,
            "user": user,
        },
    )


@router.post("/disputes")
async def create_dispute(
    request: Request,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
    dispute_type: str = Form(...),
    landlord_entity: str = Form(""),
    property_name: str = Form(""),
    status: str = Form("active"),
    jurisdiction: str = Form("MN"),
) -> Any:
    """Create a new dispute record and redirect back to the page."""
    record = DisputeRecord(
        id=make_id("dis"),
        user_id=_user_id(user),
        dispute_type=dispute_type,
        landlord_entity=landlord_entity or None,
        property_name=property_name or None,
        status=status,
        jurisdiction=jurisdiction,
        created_at=utc_now().replace(tzinfo=None),
        updated_at=utc_now().replace(tzinfo=None),
    )
    db.add(record)
    await db.commit()
    return ssot_redirect(navigation.get_stage("dispute_tracker_home").path, context="create dispute")


@router.post("/comparisons")
async def create_comparison(
    request: Request,
    user: UserContext = Depends(require_tier("T2")),
    db: AsyncSession = Depends(get_db),
    dispute_record_id: str = Form(...),
    comparison_type: str = Form(...),
    fee_type: str = Form(""),
    amount: str = Form(""),
    period: str = Form(""),
    effective_date: str = Form(""),
) -> Any:
    """Create a comparison entry attached to a dispute record."""
    amount_cents = None
    if amount:
        try:
            dollars = float(amount)
            amount_cents = int(round(dollars * 100))
        except ValueError:
            amount_cents = None

    eff_date = None
    if effective_date:
        try:
            eff_date = datetime.fromisoformat(effective_date).replace(tzinfo=UTC)
        except ValueError:
            eff_date = None

    entry = ComparisonEntry(
        id=make_id("cmp"),
        dispute_record_id=dispute_record_id,
        user_id=_user_id(user),
        comparison_type=comparison_type,
        fee_type=fee_type or None,
        amount_cents=amount_cents,
        period=period or None,
        effective_date=eff_date,
        created_at=utc_now().replace(tzinfo=None),
        updated_at=utc_now().replace(tzinfo=None),
    )
    db.add(entry)
    await db.commit()
    return ssot_redirect(navigation.get_stage("dispute_tracker_home").path, context="create comparison")
