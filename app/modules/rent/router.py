"""
Rent Ledger router — payment tracking and rent history.

Endpoints:
- POST   /api/rent/payments       — Create a payment record
- GET    /api/rent/payments       — List current user's payments
- GET    /api/rent/payments/:id   — Get a single payment
- PUT    /api/rent/payments/:id   — Update a payment
- DELETE /api/rent/payments/:id   — Delete a payment
"""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.user_context import UserContext
from app.core.security import get_current_user, require_user, can_access
from app.core.database import get_db_session
from app.core.utc import utc_now
from app.models.models import RentPayment


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
    amount: float = Field(..., gt=0, description="Payment amount in dollars (e.g. 950.00)")
    payment_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    due_date: Optional[str] = Field(None, description="ISO date string YYYY-MM-DD")
    status: str = Field("paid", description="paid, late, partial, missed")
    payment_method: Optional[str] = Field(None, description="check, cash, venmo, etc.")
    notes: Optional[str] = None
    receipt_document_id: Optional[str] = None


class RentPaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0, description="Payment amount in dollars")
    payment_date: Optional[str] = Field(None, description="ISO date string YYYY-MM-DD")
    due_date: Optional[str] = Field(None, description="ISO date string YYYY-MM-DD")
    status: Optional[str] = Field(None, description="paid, late, partial, missed")
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    receipt_document_id: Optional[str] = None


class RentPaymentResponse(BaseModel):
    payment_id: str
    amount: float
    payment_date: str
    due_date: Optional[str]
    status: str
    payment_method: Optional[str]
    notes: Optional[str]
    receipt_document_id: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


def _to_response(p: RentPayment) -> RentPaymentResponse:
    return RentPaymentResponse(
        payment_id=p.id,
        amount=p.amount / 100.0,
        payment_date=p.payment_date.strftime("%Y-%m-%d") if p.payment_date else "",
        due_date=p.due_date.strftime("%Y-%m-%d") if p.due_date else None,
        status=p.status,
        payment_method=p.payment_method,
        notes=p.notes,
        receipt_document_id=p.receipt_document_id,
        created_at=p.created_at.isoformat() if p.created_at else "",
    )


@router.post("/api/rent/payments")
async def create_payment(
    body: RentPaymentCreate,
    user: UserContext = Depends(require_user),
):
    """Create a new rent payment record."""
    await _validate_access(user, user.get_effective_user_id())
    try:
        payment_dt = datetime.strptime(body.payment_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment_date format. Use YYYY-MM-DD.")

    due_dt = None
    if body.due_date:
        try:
            due_dt = datetime.strptime(body.due_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_date format. Use YYYY-MM-DD.")

    payment = RentPayment(
        id=str(uuid.uuid4()),
        user_id=user.get_effective_user_id(),
        amount=int(body.amount * 100),  # store cents
        payment_date=payment_dt,
        due_date=due_dt,
        status=body.status,
        payment_method=body.payment_method,
        notes=body.notes,
        receipt_document_id=body.receipt_document_id,
        created_at=utc_now(),
    )

    async with get_db_session() as db:
        db.add(payment)
        await db.commit()

    return {"success": True, "payment_id": payment.id, "payment": _to_response(payment)}


@router.get("/api/rent/payments")
async def list_payments(
    user: UserContext = Depends(require_user),
):
    """List all rent payments for the current user."""
    await _validate_access(user, user.get_effective_user_id())
    async with get_db_session() as db:
        result = await db.execute(
            select(RentPayment)
            .where(RentPayment.user_id == user.get_effective_user_id())
            .order_by(RentPayment.payment_date.desc())
        )
        payments = list(result.scalars().all())

    return {"payments": [_to_response(p) for p in payments]}


@router.get("/api/rent/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Get a single rent payment by ID."""
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

    return {"payment": _to_response(payment)}


@router.put("/api/rent/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    body: RentPaymentUpdate,
    user: UserContext = Depends(require_user),
):
    """Update a rent payment record."""
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

        if body.amount is not None:
            payment.amount = int(body.amount * 100)
        if body.payment_date is not None:
            try:
                payment.payment_date = datetime.strptime(body.payment_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid payment_date format. Use YYYY-MM-DD.")
        if body.due_date is not None:
            try:
                payment.due_date = datetime.strptime(body.due_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid due_date format. Use YYYY-MM-DD.")
        if body.status is not None:
            payment.status = body.status
        if body.payment_method is not None:
            payment.payment_method = body.payment_method
        if body.notes is not None:
            payment.notes = body.notes
        if body.receipt_document_id is not None:
            payment.receipt_document_id = body.receipt_document_id

        await db.commit()

    return {"success": True, "payment": _to_response(payment)}


@router.delete("/api/rent/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    user: UserContext = Depends(require_user),
):
    """Delete a rent payment record."""
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
