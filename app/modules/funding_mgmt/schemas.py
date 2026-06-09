"""
Pydantic Schemas for Funding Management API
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from .models import FundingSourceType, ApplicationStatus


class FundingSourceBase(BaseModel):
    """Base schema for funding source."""
    name: str = Field(..., min_length=1, max_length=255)
    organization: str = Field(..., min_length=1, max_length=255)
    source_type: FundingSourceType
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    deadlines: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"
    is_active: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    notes: Optional[str] = None


class FundingSourceCreate(FundingSourceBase):
    """Schema for creating a funding source."""
    pass


class FundingSourceUpdate(BaseModel):
    """Schema for updating a funding source."""
    name: Optional[str] = None
    organization: Optional[str] = None
    source_type: Optional[FundingSourceType] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    deadlines: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None


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
    requested_amount: Optional[float] = None
    proposed_budget: Optional[str] = None  # JSON string
    status: ApplicationStatus = ApplicationStatus.PROSPECT_IDENTIFIED
    submission_date: Optional[datetime] = None
    expected_decision_date: Optional[datetime] = None
    actual_decision_date: Optional[datetime] = None
    awarded_amount: Optional[float] = None
    award_start_date: Optional[datetime] = None
    award_end_date: Optional[datetime] = None
    application_url: Optional[str] = None
    supporting_docs: Optional[str] = None  # JSON array
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class FundingApplicationCreate(FundingApplicationBase):
    """Schema for creating a funding application."""
    pass


class FundingApplicationUpdate(BaseModel):
    """Schema for updating a funding application."""
    project_name: Optional[str] = None
    requested_amount: Optional[float] = None
    proposed_budget: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    submission_date: Optional[datetime] = None
    expected_decision_date: Optional[datetime] = None
    actual_decision_date: Optional[datetime] = None
    awarded_amount: Optional[float] = None
    award_start_date: Optional[datetime] = None
    award_end_date: Optional[datetime] = None
    application_url: Optional[str] = None
    supporting_docs: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class FundingApplicationResponse(FundingApplicationBase):
    """Schema for funding application response."""
    id: int
    created_at: datetime
    updated_at: datetime
    funding_source: Optional[FundingSourceResponse] = None
    
    class Config:
        from_attributes = True


class FundingDashboardStats(BaseModel):
    """Dashboard statistics."""
    active_sources: int
    pending_applications: int
    awarded_count: int
    total_awarded_amount: float
    total_requested_amount: float
