"""
Pydantic Schemas for Funding Management API
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .models import ApplicationStatus, FundingSourceType


class FundingSourceBase(BaseModel):
    """Base schema for funding source."""
    name: str = Field(..., min_length=1, max_length=255)
    organization: str = Field(..., min_length=1, max_length=255)
    source_type: FundingSourceType
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    requirements: str | None = None
    deadlines: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str = "USD"
    is_active: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    notes: str | None = None


class FundingSourceCreate(FundingSourceBase):
    """Schema for creating a funding source."""
    pass


class FundingSourceUpdate(BaseModel):
    """Schema for updating a funding source."""
    name: str | None = None
    organization: str | None = None
    source_type: FundingSourceType | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    description: str | None = None
    requirements: str | None = None
    deadlines: str | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    is_active: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = None


class FundingSourceResponse(FundingSourceBase):
    """Schema for funding source response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FundingApplicationBase(BaseModel):
    """Base schema for funding application."""
    funding_source_id: int
    project_name: str = Field(..., min_length=1, max_length=255)
    requested_amount: float | None = None
    proposed_budget: str | None = None  # JSON string
    status: ApplicationStatus = ApplicationStatus.PROSPECT_IDENTIFIED
    submission_date: datetime | None = None
    expected_decision_date: datetime | None = None
    actual_decision_date: datetime | None = None
    awarded_amount: float | None = None
    award_start_date: datetime | None = None
    award_end_date: datetime | None = None
    application_url: str | None = None
    supporting_docs: str | None = None  # JSON array
    assigned_to: str | None = None
    notes: str | None = None


class FundingApplicationCreate(FundingApplicationBase):
    """Schema for creating a funding application."""
    pass


class FundingApplicationUpdate(BaseModel):
    """Schema for updating a funding application."""
    project_name: str | None = None
    requested_amount: float | None = None
    proposed_budget: str | None = None
    status: ApplicationStatus | None = None
    submission_date: datetime | None = None
    expected_decision_date: datetime | None = None
    actual_decision_date: datetime | None = None
    awarded_amount: float | None = None
    award_start_date: datetime | None = None
    award_end_date: datetime | None = None
    application_url: str | None = None
    supporting_docs: str | None = None
    assigned_to: str | None = None
    notes: str | None = None


class FundingApplicationResponse(FundingApplicationBase):
    """Schema for funding application response."""
    id: int
    created_at: datetime
    updated_at: datetime
    funding_source: FundingSourceResponse | None = None

    class Config:
        from_attributes = True


class FundingDashboardStats(BaseModel):
    """Dashboard statistics."""
    active_sources: int
    pending_applications: int
    awarded_count: int
    total_awarded_amount: float
    total_requested_amount: float
