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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.security import can_access, require_user
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.models.models import RentPayment

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


def _format_date(dt: datetime | None) -> str | None:
    """Format a datetime as YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d") if dt else None


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


async def _fetch_all_ledger_entries(db: AsyncSession, user_id: str) -> list[RentPayment]:
    """Fetch all ledger entries for a user, oldest first."""
    result = await db.execute(
        select(RentPayment)
        .where(RentPayment.user_id == user_id)
        .order_by(RentPayment.payment_date.asc(), RentPayment.id.asc())
    )
    return list(result.scalars().all())


def _compute_running_balances(entries: list[RentPayment]) -> dict[str, int]:
    """Compute running balance in cents after each entry in chronological order."""
    balance = 0
    balances: dict[str, int] = {}
    for entry in entries:
        balance += _entry_sign(entry.entry_type) * entry.amount
        balances[entry.id] = balance
    return balances


def _to_response(entry: RentPayment, running_balance_cents: int) -> RentPaymentResponse:
    """Convert a RentPayment row to a response model."""
    return RentPaymentResponse(
        payment_id=entry.id,
        entry_type=entry.entry_type,
        amount=entry.amount / 100.0,
        payment_date=_format_date(entry.payment_date) or "",
        due_date=_format_date(entry.due_date),
        period_covered=entry.period_covered,
        status=entry.status,
        payment_method=entry.payment_method,
        source=entry.source,
        receipt_document_id=entry.receipt_document_id,
        overlay_link=entry.overlay_link,
        notes=entry.notes,
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

    payment = RentPayment(
        id=make_id("rnt"),
        user_id=user.get_effective_user_id(),
        entry_type=entry_type,
        amount=_to_cents(body.amount),
        payment_date=payment_dt,
        due_date=due_dt,
        period_covered=body.period_covered,
        status=status,
        payment_method=body.payment_method,
        source=source,
        receipt_document_id=body.receipt_document_id,
        overlay_link=body.overlay_link,
        notes=body.notes,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    async with get_db_session() as db:
        db.add(payment)
        await db.commit()

    async with get_db_session() as db:
        all_entries = await _fetch_all_ledger_entries(db, user.get_effective_user_id())
        balances = _compute_running_balances(all_entries)
        balance_cents = balances.get(payment.id, 0)

    return {"success": True, "payment_id": payment.id, "payment": _to_response(payment, balance_cents)}


@router.get("/payments")
async def list_payments(
    user: UserContext = Depends(require_user),
):
    """List all rent ledger entries for the current user, newest first, with running balances."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        all_entries = await _fetch_all_ledger_entries(db, user.get_effective_user_id())
        balances = _compute_running_balances(all_entries)
        sorted_entries = sorted(
            all_entries,
            key=lambda p: (p.payment_date or datetime.min, p.id),
            reverse=True,
        )
        payments = [_to_response(p, balances[p.id]) for p in sorted_entries]

    return {"payments": payments}


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Get a single rent ledger entry by ID with its running balance."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(RentPayment).where(
                RentPayment.id == payment_id,
                RentPayment.user_id == user.get_effective_user_id(),
            )
        )
        payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    async with get_db_session() as db:
        all_entries = await _fetch_all_ledger_entries(db, user.get_effective_user_id())
        balances = _compute_running_balances(all_entries)
        balance_cents = balances.get(payment.id, 0)

    return {"payment": _to_response(payment, balance_cents)}


@router.put("/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    body: RentPaymentUpdate,
    user: UserContext = Depends(require_user),
):
    """Update a rent ledger entry."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(RentPayment).where(
                RentPayment.id == payment_id,
                RentPayment.user_id == user.get_effective_user_id(),
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if body.entry_type is not None:
            payment.entry_type = _validate_entry_type(body.entry_type)
        if body.amount is not None:
            payment.amount = _to_cents(body.amount)
        if body.payment_date is not None:
            payment_dt = _parse_date(body.payment_date)
            if not payment_dt:
                raise HTTPException(status_code=400, detail="payment_date is required")
            payment.payment_date = payment_dt
        if body.due_date is not None:
            payment.due_date = _parse_date(body.due_date)
        if body.period_covered is not None:
            payment.period_covered = body.period_covered
        if body.status is not None:
            payment.status = _validate_status(body.status)
        if body.payment_method is not None:
            payment.payment_method = body.payment_method
        if body.source is not None:
            payment.source = _validate_source(body.source)
        if body.receipt_document_id is not None:
            payment.receipt_document_id = body.receipt_document_id
        if body.overlay_link is not None:
            payment.overlay_link = body.overlay_link
        if body.notes is not None:
            payment.notes = body.notes

        payment.updated_at = utc_now()
        await db.commit()

    async with get_db_session() as db:
        all_entries = await _fetch_all_ledger_entries(db, user.get_effective_user_id())
        balances = _compute_running_balances(all_entries)
        balance_cents = balances.get(payment.id, 0)

    return {"success": True, "payment": _to_response(payment, balance_cents)}


@router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Delete a rent ledger entry."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(RentPayment).where(
                RentPayment.id == payment_id,
                RentPayment.user_id == user.get_effective_user_id(),
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        await db.delete(payment)
        await db.commit()

    return {"success": True, "deleted": payment_id}
