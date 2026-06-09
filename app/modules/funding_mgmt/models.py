"""
Funding Management Database Models
"""

from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base


class FundingSourceType(str, PyEnum):
    """Types of funding sources."""
    FEDERAL_GRANT = "federal_grant"
    FOUNDATION_GRANT = "foundation_grant"
    CORPORATE_SPONSORSHIP = "corporate_sponsorship"
    INDIVIDUAL_DONOR = "individual_donor"
    STATE_LOCAL_GRANT = "state_local_grant"
    IN_KIND = "in_kind"
    OTHER = "other"


class ApplicationStatus(str, PyEnum):
    """Application lifecycle stages."""
    PROSPECT_IDENTIFIED = "prospect_identified"
    RESEARCH_COMPLETE = "research_complete"
    APPLICATION_DRAFT = "application_draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    AWARDED = "awarded"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class FundingSource(Base):
    """Represents a potential or actual funding source."""
    
    __tablename__ = "funding_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    source_type = Column(Enum(FundingSourceType), nullable=False)
    
    # Contact information
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    website = Column(String(500))
    
    # Details
    description = Column(Text)
    requirements = Column(Text)
    deadlines = Column(Text)
    
    # Financial
    min_amount = Column(Float)
    max_amount = Column(Float)
    currency = Column(String(3), default="USD")
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=5)  # 1-10, 1 = highest
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)


class FundingApplication(Base):
    """Tracks a specific funding application."""
    
    __tablename__ = "funding_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    funding_source_id = Column(Integer, nullable=False)
    
    # Application details
    project_name = Column(String(255), nullable=False)
    requested_amount = Column(Float)
    proposed_budget = Column(Text)  # JSON breakdown
    
    # Status tracking
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PROSPECT_IDENTIFIED)
    submission_date = Column(DateTime)
    expected_decision_date = Column(DateTime)
    actual_decision_date = Column(DateTime)
    
    # Outcome
    awarded_amount = Column(Float)
    award_start_date = Column(DateTime)
    award_end_date = Column(DateTime)
    
    # Documents
    application_url = Column(String(500))  # Link to stored application
    supporting_docs = Column(Text)  # JSON array of document URLs
    
    # Tracking
    assigned_to = Column(String(100))  # Admin user name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)


class FundingTask(Base):
    """Tasks related to funding applications."""
    
    __tablename__ = "funding_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    funding_application_id = Column(Integer)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
