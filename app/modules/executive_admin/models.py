"""Executive Administration models — the organization's own records.

Two tables, both org-level data (never tenant data):

- ``exec_ledger_entries`` — the books of record. One row per money movement,
  amounts in integer cents, tagged with the IRS Form 990 revenue category or
  functional expense class, and the fund it belongs to (restricted or not).
- ``exec_records`` — everything else, one JSON document per record, keyed by
  ``kind``: profile, step status, board member, meeting, written action,
  policy status, filed obligation, custom deadline.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base
from app.core.utc import utc_now


class ExecLedgerEntry(Base):
    __tablename__ = "exec_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # income | expense
    kind: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # income: knowledge.INCOME_CATEGORIES key; expense: knowledge.EXPENSE_CATEGORIES key
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    # expense only: program | management_general | fundraising
    functional_class: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fund: Mapped[str] = mapped_column(String(80), nullable=False, default="unrestricted")
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # quid pro quo: fair value of goods/services the donor received
    goods_services_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ExecRecord(Base):
    __tablename__ = "exec_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
