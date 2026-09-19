"""Accountability Ledger models — subject registry, documented patterns,
and political alignments.

This is the canonical data model for the accountability platform. It resolves
the ``subject_id`` placeholder on ``EvictionTimelineEvent`` (see
``app/models/models.py``) and the open decision from the 2026-09-08 handoff
(``handoffs/filedored-housing-accountability-options-2026-09-08.md``).

SSOT DATABASE BOUNDARY RULE applies: Postgres holds pointers and structure
only. These tables store entity names, pattern types, public-record
references, and political data — all explicitly allowed as "landlord/entity
data for admin/research tools." No narrative, no PII, no case text.
"""

from datetime import datetime

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now


class AccountabilitySubject(Base):
    """A subject of accountability — a landlord, LLC, judge, politician, or agency.

    The canonical entity that patterns and political alignments reference.
    Aliases collapse alternate names / DBAs / LLC shell names to one row.
    """

    __tablename__ = "accountability_subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_type: Mapped[str] = mapped_column(
        String(30), index=True, nullable=False
    )  # landlord, llc, judge, politician, agency, property_manager
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # JSON array of alternate names
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="MN")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # bar number, office held, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AccountabilityPattern(Base):
    """A documented, evidence-backed pattern of behavior for a subject.

    Every pattern ties to public-record references (court filing IDs, code
    violation IDs, FEC report IDs). No narrative — pointers only. The
    ``status`` field tracks verification: ``documented`` (sourced but
    unverified), ``verified`` (cross-checked), ``disputed`` (subject contests).
    """

    __tablename__ = "accountability_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accountability_subjects.id"), index=True, nullable=False
    )
    pattern_type: Mapped[str] = mapped_column(
        String(40), index=True, nullable=False
    )  # repeated_fees, retaliatory_eviction, serial_eviction, code_violations,
       # court_weaponization, price_gouging, subsidy_interference, court_order_violation
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    instance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # array of public-record pointers
    first_observed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_observed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="MN")
    legal_basis: Mapped[str | None] = mapped_column(String(255), nullable=True)  # statute reference
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="documented")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class PoliticalAlignment(Base):
    """How a politician or judge relates to landlord interests.

    Covers campaign donations, voting records, ruling patterns, and public
    statements. Each row ties to a public-record source (FEC, state disclosure,
    legislative tracker, court records). The ``amount`` field is for donations;
    ``null`` for votes/rulings/statements.
    """

    __tablename__ = "political_alignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accountability_subjects.id"), index=True, nullable=False
    )
    alignment_type: Mapped[str] = mapped_column(
        String(30), index=True, nullable=False
    )  # campaign_donation, voting_record, ruling_pattern, public_statement
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    # fec, state_disclosure, leg_tracker, court_records
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # specific record reference
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # donations only
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)  # short label only

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


__all__ = ["AccountabilitySubject", "AccountabilityPattern", "PoliticalAlignment"]


class PublicRecordsRequest(Base):
    """A tracked public-records request (FOIA / Data Practices Act / Sunshine).

    Ported workflow from app-pmas — file a request with an agency, record the
    statutory deadline, and track the lifecycle: submitted → acknowledged →
    fulfilled / denied / withdrawn. ``overdue`` is computed on read, never
    stored — an open request past its deadline reports overdue.

    Operator workbench data (advocate/researcher tier), not tenant documents.
    ``subject_id`` optionally links the target agency to a registered
    accountability subject.
    """

    __tablename__ = "accountability_record_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_target: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    records_requested: Mapped[str] = mapped_column(Text, nullable=False)
    date_submitted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deadline_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default="submitted"
    )  # submitted / acknowledged / fulfilled / denied / withdrawn
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("accountability_subjects.id"), index=True, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    OPEN_STATUSES = ("submitted", "acknowledged")

    def effective_status(self, now: datetime | None = None) -> str:
        """Status as of ``now`` — open requests past deadline report overdue."""
        deadline = self.deadline_date
        if self.status in self.OPEN_STATUSES and deadline:
            now = now or utc_now()
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=now.tzinfo)
            if deadline < now:
                return "overdue"
        return self.status
