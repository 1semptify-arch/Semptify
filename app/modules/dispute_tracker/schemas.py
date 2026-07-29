"""Dispute Tracker Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime


class DisputeType(StrEnum):
    FEES = "fees"
    LEASE_VIOLATION = "lease_violation"
    RETALIATION = "retaliation"
    HABITABILITY = "habitability"
    OTHER = "other"


class DisputeStatus(StrEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ON_HOLD = "on_hold"


class ComparisonType(StrEnum):
    FEE = "fee"
    TERM = "term"
    NOTICE = "notice"
    DEPOSIT = "deposit"


class Period(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class DisputeRecordBase(BaseModel):
    """Base fields for a dispute record."""

    landlord_entity: str | None = Field(None, max_length=255)
    property_name: str | None = Field(None, max_length=255)
    dispute_type: DisputeType = Field(...)
    status: DisputeStatus = Field(DisputeStatus.ACTIVE)
    jurisdiction: str = Field("MN", max_length=10)


class DisputeRecordCreate(DisputeRecordBase):
    """Create a new dispute record."""

    content_overlay_id: str | None = Field(None, max_length=36)
    evidence_overlay_id: str | None = Field(None, max_length=36)


class DisputeRecordRead(DisputeRecordBase):
    """Dispute record as returned by the API."""

    id: str
    user_id: str
    content_overlay_id: str | None
    evidence_overlay_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DisputeRecordUpdate(BaseModel):
    """Partial update of a dispute record."""

    landlord_entity: str | None = Field(None, max_length=255)
    property_name: str | None = Field(None, max_length=255)
    dispute_type: DisputeType | None = None
    status: DisputeStatus | None = None
    jurisdiction: str | None = Field(None, max_length=10)
    content_overlay_id: str | None = Field(None, max_length=36)
    evidence_overlay_id: str | None = Field(None, max_length=36)


class ComparisonEntryBase(BaseModel):
    """Base fields for a comparison entry."""

    comparison_type: ComparisonType = Field(...)
    fee_type: str | None = Field(None, max_length=50)
    amount_cents: int | None = Field(None, ge=0)
    period: Period | None = None
    effective_date: datetime | None = None


class ComparisonEntryCreate(ComparisonEntryBase):
    """Create a comparison entry."""

    source_overlay_id: str | None = Field(None, max_length=36)
    source_document_id: str | None = Field(None, max_length=36)


class ComparisonEntryRead(ComparisonEntryBase):
    """Comparison entry as returned by the API."""

    id: str
    dispute_record_id: str
    user_id: str
    source_overlay_id: str | None
    source_document_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComparisonEntryUpdate(BaseModel):
    """Partial update of a comparison entry."""

    comparison_type: ComparisonType | None = None
    fee_type: str | None = Field(None, max_length=50)
    amount_cents: int | None = Field(None, ge=0)
    period: Period | None = None
    effective_date: datetime | None = None
    source_overlay_id: str | None = Field(None, max_length=36)
    source_document_id: str | None = Field(None, max_length=36)
