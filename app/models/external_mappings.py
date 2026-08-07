"""
External ID Mappings - Bridge between Semptify and external systems

This module provides mapping tables to connect Semptify internal IDs with:
- Court case numbers and filing references
- Property parcel IDs and addresses
- Attorney bar numbers and legal representation
- Housing court references
- Agency complaint numbers

All mappings are user-scoped and include audit trails.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class ExternalMapping(Base):
    """Base mapping between Semptify user and external system IDs."""

    __tablename__ = "external_mappings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User and context
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    mapping_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # court_case, property, attorney, agency

    # External system info
    external_system: Mapped[str] = mapped_column(String(50), nullable=False)  # mn_courts, hennepin_county, hud, etc.
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Court case number, parcel ID, etc.
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Link to external system

    # Semptify reference (what internal item this maps to)
    semptify_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # document, event, complaint
    semptify_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Mapping metadata
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Human-readable name
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive, resolved

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<ExternalMapping {self.mapping_type}={self.external_id[:20]}*** user={self.user_id[:6]}***>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mapping_type": self.mapping_type,
            "external_system": self.external_system,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "septify_entity_type": self.septify_entity_type,
            "septify_entity_id": self.septify_entity_id,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "verified": self.verified,
            "verification_source": self.verification_source,
        }


class CourtCaseMapping(Base):
    """Specific mapping for court cases with additional legal fields."""

    __tablename__ = "court_case_mappings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User and case info
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Court case details
    court_system: Mapped[str] = mapped_column(String(50), nullable=False)  # mn_state, hennepin_county, federal
    case_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)  # eviction, housing, small_claims
    case_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Court and judge info
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    judge_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    division: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Housing, Civil, etc.

    # Parties
    plaintiff: Mapped[str | None] = mapped_column(String(255), nullable=True)
    defendant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attorney_bar_numbers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Dates and status
    filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hearing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    case_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, active, settled, dismissed

    # External links
    case_portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_filing_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Semptify connections
    semptify_complaint_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    semptify_timeline_event_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<CourtCaseMapping {self.case_number} ({self.court_system})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "court_system": self.court_system,
            "case_number": self.case_number,
            "case_type": self.case_type,
            "case_title": self.case_title,
            "court_name": self.court_name,
            "judge_name": self.judge_name,
            "division": self.division,
            "plaintiff": self.plaintiff,
            "defendant": self.defendant,
            "attorney_bar_numbers": self.attorney_bar_numbers,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "hearing_date": self.hearing_date.isoformat() if self.hearing_date else None,
            "trial_date": self.trial_date.isoformat() if self.trial_date else None,
            "case_status": self.case_status,
            "case_portal_url": self.case_portal_url,
            "document_filing_url": self.document_filing_url,
            "septify_complaint_id": self.septify_complaint_id,
            "septify_timeline_event_ids": self.septify_timeline_event_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PropertyMapping(Base):
    """Mapping for property parcel IDs and addresses."""

    __tablename__ = "property_mappings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User and property
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Property identifiers
    parcel_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    county: Mapped[str] = mapped_column(String(50), nullable=False)  # hennepin, ramsey, dakota
    municipality: Mapped[str | None] = mapped_column(String(100), nullable=True)  # minneapolis, st paul

    # Address info
    street_address: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), default="MN")
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # Property details
    property_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # apartment, house, condo
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Tax parcel ID

    # External system links
    county_assessor_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    county_recorder_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gis_map_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Semptify connections
    semptify_lease_doc_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_primary_residence: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self):
        return f"<PropertyMapping {self.parcel_id} ({self.county})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "parcel_id": self.parcel_id,
            "county": self.county,
            "municipality": self.municipality,
            "street_address": self.street_address,
            "unit": self.unit,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "property_type": self.property_type,
            "tax_id": self.tax_id,
            "county_assessor_url": self.county_assessor_url,
            "county_recorder_url": self.county_recorder_url,
            "gis_map_url": self.gis_map_url,
            "septify_lease_doc_id": self.septify_lease_doc_id,
            "is_primary_residence": self.is_primary_residence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "verified": self.verified,
        }


class AgencyMapping(Base):
    """Mapping for agency complaint numbers and references."""

    __tablename__ = "agency_mappings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # User and agency
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Agency and complaint info
    agency_code: Mapped[str] = mapped_column(String(50), nullable=False)  # mn_ag_consumer, hud_fair_housing
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    complaint_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    complaint_type: Mapped[str] = mapped_column(String(50), nullable=False)  # discrimination, habitability

    # Submission details
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # online, mail, in_person

    # Status and resolution
    complaint_status: Mapped[str] = mapped_column(String(50), default="submitted")  # submitted, under_review, resolved
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)

    # External links
    agency_portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Semptify connections
    semptify_complaint_id: Mapped[str] = mapped_column(String(36), nullable=False)
    semptify_document_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<AgencyMapping {self.agency_code}:{self.complaint_number}>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agency_code": self.agency_code,
            "agency_name": self.agency_name,
            "complaint_number": self.complaint_number,
            "complaint_type": self.complaint_type,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "submission_method": self.submission_method,
            "complaint_status": self.complaint_status,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "resolution_outcome": self.resolution_outcome,
            "agency_portal_url": self.agency_portal_url,
            "tracking_url": self.tracking_url,
            "septify_complaint_id": self.septify_complaint_id,
            "septify_document_ids": self.septify_document_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Mapping management functions
def create_mapping(
    db_session,
    user_id: str,
    mapping_type: str,
    external_system: str,
    external_id: str,
    semptify_entity_type: str | None = None,
    semptify_entity_id: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    external_url: str | None = None,
    verification_source: str | None = None
) -> ExternalMapping:
    """Create a new external mapping."""
    mapping = ExternalMapping(
        user_id=user_id,
        mapping_type=mapping_type,
        external_system=external_system,
        external_id=external_id,
        semptify_entity_type=semptify_entity_type,
        semptify_entity_id=semptify_entity_id,
        display_name=display_name,
        description=description,
        external_url=external_url,
        created_at=utc_now(),
        updated_at=utc_now(),
        verified=bool(verification_source),
        verification_source=verification_source,
    )

    db_session.add(mapping)
    db_session.commit()
    return mapping


def get_user_mappings(
    db_session,
    user_id: str,
    mapping_type: str | None = None,
    status: str = "active"
) -> list[ExternalMapping]:
    """Get all mappings for a user, optionally filtered by type."""
    from sqlalchemy import and_, select

    query = select(ExternalMapping).where(
        and_(
            ExternalMapping.user_id == user_id,
            ExternalMapping.status == status
        )
    )

    if mapping_type:
        query = query.where(ExternalMapping.mapping_type == mapping_type)

    result = db_session.execute(query.order_by(ExternalMapping.created_at.desc()))
    return result.scalars().all()


def find_by_external_id(
    db_session,
    external_system: str,
    external_id: str,
    mapping_type: str | None = None
) -> ExternalMapping | None:
    """Find mapping by external system ID."""
    from sqlalchemy import and_, select

    query = select(ExternalMapping).where(
        and_(
            ExternalMapping.external_system == external_system,
            ExternalMapping.external_id == external_id
        )
    )

    if mapping_type:
        query = query.where(ExternalMapping.mapping_type == mapping_type)

    result = db_session.execute(query)
    return result.scalar_one_or_none()


def update_mapping_status(
    db_session,
    mapping_id: int,
    status: str,
    verification_source: str | None = None
) -> bool:
    """Update mapping status and verification."""
    from sqlalchemy import select

    result = db_session.execute(select(ExternalMapping).where(ExternalMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()

    if not mapping:
        return False

    mapping.status = status
    mapping.updated_at = utc_now()
    if verification_source:
        mapping.verified = True
        mapping.verification_source = verification_source

    db_session.commit()
    return True
