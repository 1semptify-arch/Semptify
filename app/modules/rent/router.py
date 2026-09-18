"""
Rent Ledger router — full account ledger for rent payments, fees, deposits,
and credits with a running balance.

Endpoints:
- POST   /api/rent/payments       — Create a ledger entry
- GET    /api/rent/payments       — List current user's ledger entries
- GET    /api/rent/payments/:id   — Get a single ledger entry
- PUT    /api/rent/payments/:id   — Update a ledger entry
- DELETE /api/rent/payments/:id   — Delete a ledger entry
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db_session
from app.core.security import can_access, require_user
from app.core.user_context import UserContext
from app.models.unified_overlay_models import UnifiedOverlay
from app.modules.rent import service
from app.services.calendar_sync import sync_calendar_for_user

VALID_ENTRY_TYPES = {"payment", "fee", "deposit", "credit", "charge"}
VALID_SOURCES = {"user_entered", "ocr_extracted"}
VALID_PAYMENT_STATUS = {"paid", "late", "partial", "missed"}


async def _validate_access(user: UserContext, target_user_id: str) -> None:
    """Validate that the current user can access target_user_id's resources."""
    if user.user_id == target_user_id:
        return
    if user.is_impersonating and user.acting_as == target_user_id:
        async with get_db_session() as db:
            allowed = await can_access(user.user_id, target_user_id, db)
            if not allowed:
                raise HTTPException(status_code=403, detail="Access denied: no active relationship")
        return
    raise HTTPException(status_code=403, detail="Access denied")


router = APIRouter()


class RentPaymentCreate(BaseModel):
    """Create a rent ledger entry."""

    entry_type: str = Field("payment", description="payment, fee, deposit, credit, or charge")
    amount: float = Field(..., gt=0, description="Entry amount in dollars (e.g. 950.00)")
    payment_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    due_date: str | None = Field(None, description="ISO date string YYYY-MM-DD")
    period_covered: str | None = Field(None, description="Period the entry covers, e.g. 2026-07")
    status: str | None = Field("paid", description="paid, late, partial, missed (payment entries)")
    payment_method: str | None = Field(None, description="check, cash, venmo, etc.")
    source: str = Field("user_entered", description="user_entered or ocr_extracted")
    receipt_document_id: str | None = None
    overlay_link: str | None = Field(None, description="Overlay highlight ID if entry came from a document")
    notes: str | None = None


class RentPaymentUpdate(BaseModel):
    """Update a rent ledger entry."""

    entry_type: str | None = None
    amount: float | None = Field(None, gt=0, description="Entry amount in dollars")
    payment_date: str | None = None
    due_date: str | None = None
    period_covered: str | None = None
    status: str | None = None
    payment_method: str | None = None
    source: str | None = None
    receipt_document_id: str | None = None
    overlay_link: str | None = None
    notes: str | None = None


class RentPaymentResponse(BaseModel):
    """Rent ledger entry response, including running balance."""

    payment_id: str
    entry_type: str
    amount: float
    payment_date: str
    due_date: str | None
    period_covered: str | None
    status: str | None
    payment_method: str | None
    source: str
    receipt_document_id: str | None
    overlay_link: str | None
    notes: str | None
    running_balance: float
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


def _entry_sign(entry_type: str) -> int:
    """Return +1 for tenant-favorable entries, -1 for charges."""
    return 1 if entry_type in {"payment", "deposit", "credit"} else -1


def _to_cents(dollars: float) -> int:
    """Convert dollar amount to cents."""
    return int(round(dollars * 100))


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse a YYYY-MM-DD date string to a UTC datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from exc


def _validate_entry_type(entry_type: str | None) -> str:
    """Validate and normalize an entry type."""
    if not entry_type:
        return "payment"
    value = entry_type.lower().strip()
    if value not in VALID_ENTRY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entry_type. Must be one of: {', '.join(sorted(VALID_ENTRY_TYPES))}",
        )
    return value


def _validate_source(source: str | None) -> str:
    """Validate and normalize a source value."""
    if not source:
        return "user_entered"
    value = source.lower().strip()
    if value not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(sorted(VALID_SOURCES))}",
        )
    return value


def _validate_status(status: str | None) -> str | None:
    """Validate payment status if provided."""
    if not status:
        return None
    value = status.lower().strip()
    if value not in VALID_PAYMENT_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_PAYMENT_STATUS))}",
        )
    return value


def _compute_running_balances(entries: list[UnifiedOverlay]) -> dict[str, int]:
    """Compute running balance in cents after each entry in chronological order."""
    balance = 0
    balances: dict[str, int] = {}
    for entry in entries:
        p = entry.payload
        balance += _entry_sign(p.get("entry_type") or "payment") * int(p.get("amount") or 0)
        balances[entry.overlay_id] = balance
    return balances


def _format_date(value) -> str | None:
    """Format an ISO date/datetime string (or datetime) as YYYY-MM-DD."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _to_response(entry: UnifiedOverlay, running_balance_cents: int) -> RentPaymentResponse:
    """Convert a ledger overlay to a response model."""
    p = entry.payload
    return RentPaymentResponse(
        payment_id=entry.overlay_id,
        entry_type=p.get("entry_type") or "payment",
        amount=(p.get("amount") or 0) / 100.0,
        payment_date=_format_date(p.get("payment_date")) or "",
        due_date=_format_date(p.get("due_date")),
        period_covered=p.get("period_covered"),
        status=p.get("status"),
        payment_method=p.get("payment_method"),
        source=p.get("source") or "user_entered",
        receipt_document_id=p.get("receipt_document_id"),
        overlay_link=p.get("overlay_link"),
        notes=p.get("notes"),
        running_balance=running_balance_cents / 100.0,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        updated_at=entry.updated_at.isoformat() if entry.updated_at else None,
    )


@router.post("/payments")
async def create_payment(
    body: RentPaymentCreate,
    user: UserContext = Depends(require_user),
):
    """Create a new rent ledger entry."""
    await _validate_access(user, user.get_effective_user_id())

    entry_type = _validate_entry_type(body.entry_type)
    source = _validate_source(body.source)
    status = _validate_status(body.status)
    payment_dt = _parse_date(body.payment_date)
    if not payment_dt:
        raise HTTPException(status_code=400, detail="payment_date is required")
    due_dt = _parse_date(body.due_date)

    payment = await service.create_entry(
        user,
        entry_type=entry_type,
        amount_cents=_to_cents(body.amount),
        payment_date=payment_dt.isoformat(),
        due_date=due_dt.isoformat() if due_dt else None,
        period_covered=body.period_covered,
        status=status,
        payment_method=body.payment_method,
        source=source,
        receipt_document_id=body.receipt_document_id,
        overlay_link=body.overlay_link,
        notes=body.notes,
    )

    # Auto-sync calendar with rent due dates and late-fee triggers.
    try:
        await sync_calendar_for_user(user.get_effective_user_id())
    except Exception as sync_exc:
        import logging

        logging.getLogger(__name__).warning("Calendar sync failed after rent payment create: %s", sync_exc)

    all_entries, _total = await service.list_entries(user)
    balances = _compute_running_balances(all_entries)
    balance_cents = balances.get(payment.overlay_id, 0)

    return {"success": True, "payment_id": payment.overlay_id, "payment": _to_response(payment, balance_cents)}


@router.get("/payments")
async def list_payments(
    user: UserContext = Depends(require_user),
):
    """List all rent ledger entries for the current user, newest first, with running balances."""
    await _validate_access(user, user.get_effective_user_id())
    all_entries, _total = await service.list_entries(user)
    balances = _compute_running_balances(all_entries)
    sorted_entries = sorted(
        all_entries,
        key=lambda p: (p.payload.get("payment_date") or "", p.payload.get("id") or p.overlay_id),
        reverse=True,
    )
    payments = [_to_response(p, balances[p.overlay_id]) for p in sorted_entries]

    return {"payments": payments}


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Get a single rent ledger entry by ID with its running balance."""
    await _validate_access(user, user.get_effective_user_id())
    payment = await service.get_entry(user, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    all_entries, _total = await service.list_entries(user)
    balances = _compute_running_balances(all_entries)
    balance_cents = balances.get(payment.overlay_id, 0)

    return {"payment": _to_response(payment, balance_cents)}


@router.put("/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    body: RentPaymentUpdate,
    user: UserContext = Depends(require_user),
):
    """Update a rent ledger entry."""
    await _validate_access(user, user.get_effective_user_id())

    fields: dict = {}
    if body.entry_type is not None:
        fields["entry_type"] = _validate_entry_type(body.entry_type)
    if body.amount is not None:
        fields["amount"] = _to_cents(body.amount)
    if body.payment_date is not None:
        payment_dt = _parse_date(body.payment_date)
        if not payment_dt:
            raise HTTPException(status_code=400, detail="payment_date is required")
        fields["payment_date"] = payment_dt.isoformat()
    if body.due_date is not None:
        due_dt = _parse_date(body.due_date)
        fields["due_date"] = due_dt.isoformat() if due_dt else None
    if body.period_covered is not None:
        fields["period_covered"] = body.period_covered
    if body.status is not None:
        fields["status"] = _validate_status(body.status)
    if body.payment_method is not None:
        fields["payment_method"] = body.payment_method
    if body.source is not None:
        fields["source"] = _validate_source(body.source)
    if body.receipt_document_id is not None:
        fields["receipt_document_id"] = body.receipt_document_id
    if body.overlay_link is not None:
        fields["overlay_link"] = body.overlay_link
    if body.notes is not None:
        fields["notes"] = body.notes

    payment = await service.update_entry(user, payment_id, fields)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Auto-sync calendar with updated rent dates.
    try:
        await sync_calendar_for_user(user.get_effective_user_id())
    except Exception as sync_exc:
        import logging

        logging.getLogger(__name__).warning("Calendar sync failed after rent payment update: %s", sync_exc)

    all_entries, _total = await service.list_entries(user)
    balances = _compute_running_balances(all_entries)
    balance_cents = balances.get(payment.overlay_id, 0)

    return {"success": True, "payment": _to_response(payment, balance_cents)}


@router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Delete a rent ledger entry."""
    await _validate_access(user, user.get_effective_user_id())
    deleted = await service.delete_entry(user, payment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Auto-sync calendar after ledger deletion to remove orphaned rent events.
    try:
        await sync_calendar_for_user(user.get_effective_user_id())
    except Exception as sync_exc:
        import logging

        logging.getLogger(__name__).warning("Calendar sync failed after rent payment delete: %s", sync_exc)

    return {"success": True, "deleted": payment_id}
