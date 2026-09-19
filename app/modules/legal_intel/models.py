"""Legal Intel models — entity/attorney registry, court cases, dockets,
and entity relationships.

Ported data model from app-legal-intel ("who owns this LLC" intelligence):
landlord entities with Secretary-of-State identifiers, their attorneys,
the cases connecting them, and docket entries that pattern analysis reads.

Operator/research workbench data — public-record-sourced, no tenant PII.
``subject_id`` optionally links an entity to an accountability_ledger
subject so intel and the ledger tell one story about the same actor.
"""

from datetime import date as _date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utc import utc_now


class IntelEntity(Base):
    """A business entity — landlord LLC, property manager, shell company."""

    __tablename__ = "legal_intel_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)  # llc, corp, lp, individual
    sos_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)  # Secretary of State filing id
    registered_agent: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("accountability_subjects.id"), index=True, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class IntelAttorney(Base):
    """An attorney who appears for entities in housing cases."""

    __tablename__ = "legal_intel_attorneys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bar_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    firm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class IntelCase(Base):
    """A court case linking an entity and (optionally) its attorney."""

    __tablename__ = "legal_intel_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    court: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    case_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    case_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    case_type: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    filing_date: Mapped[_date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attorney_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("legal_intel_attorneys.id"), index=True, nullable=True
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("legal_intel_entities.id"), index=True, nullable=True
    )
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    attorney: Mapped["IntelAttorney | None"] = relationship(lazy="raise")
    entity: Mapped["IntelEntity | None"] = relationship(lazy="raise")
    dockets: Mapped[list["IntelDocket"]] = relationship(
        back_populates="case", lazy="raise", order_by="IntelDocket.date"
    )


class IntelDocket(Base):
    """One docket entry — the raw text pattern analysis reads."""

    __tablename__ = "legal_intel_dockets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("legal_intel_cases.id"), index=True, nullable=False
    )
    date: Mapped[_date | None] = mapped_column(Date, nullable=True)
    entry_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped["IntelCase"] = relationship(back_populates="dockets", lazy="raise")


class IntelRelationship(Base):
    """A declared link between two entities (parent/subsidiary, shared agent, etc.)."""

    __tablename__ = "legal_intel_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("legal_intel_entities.id"), index=True, nullable=False
    )
    related_entity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("legal_intel_entities.id"), index=True, nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
