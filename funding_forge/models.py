"""Funding Forge SQLAlchemy models."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from funding_forge.database import Base


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


class Funder(Base):
    """A funding entity such as a fiscal sponsor, foundation, or platform."""

    __tablename__ = "funders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="researching", nullable=False, index=True)
    website = Column(String(500))
    focus = Column(Text)
    location = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    contacts = relationship("Contact", back_populates="funder", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="funder", cascade="all, delete-orphan")


class Contact(Base):
    """A person associated with a funding entity."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    funder_id = Column(Integer, ForeignKey("funders.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255))
    email = Column(String(255))
    phone = Column(String(100))
    status = Column(String(50), default="active", nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    funder = relationship("Funder", back_populates="contacts")
    interactions = relationship("Interaction", back_populates="contact", cascade="all, delete-orphan")


class Opportunity(Base):
    """A funding opportunity or application pipeline entry."""

    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    funder_id = Column(Integer, ForeignKey("funders.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    opportunity_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="prospect", nullable=False, index=True)
    amount = Column(String(100))
    deadline = Column(DateTime, nullable=True)
    decision_date = Column(DateTime, nullable=True)
    description = Column(Text)
    requirements = Column(Text)
    outcome = Column(String(50), default="pending")
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    funder = relationship("Funder", back_populates="opportunities")
    steps = relationship("OpportunityStep", back_populates="opportunity", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="opportunity", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="opportunity", cascade="all, delete-orphan")


class OpportunityStep(Base):
    """A checklist item inside an application process."""

    __tablename__ = "opportunity_steps"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending", nullable=False)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    opportunity = relationship("Opportunity", back_populates="steps")


class Interaction(Base):
    """A call, email, meeting, note, or task record tied to a contact or opportunity."""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True, index=True)
    interaction_type = Column(String(50), nullable=False, index=True)
    date = Column(DateTime, default=utc_now, nullable=False)
    subject = Column(String(500))
    notes = Column(Text)
    follow_up_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    contact = relationship("Contact", back_populates="interactions")
    opportunity = relationship("Opportunity", back_populates="interactions")


class Task(Base):
    """A standalone reminder or follow-up task."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    status = Column(String(50), default="open", nullable=False)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    related_type = Column(String(50), nullable=True)
    related_id = Column(Integer, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class Document(Base):
    """An uploaded file linked to an opportunity, funder, or contact."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    mime_type = Column(String(100))
    file_size = Column(Integer)
    description = Column(Text)
    related_type = Column(String(50), nullable=True)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    opportunity = relationship("Opportunity", back_populates="documents")


class Setting(Base):
    """Simple key/value store for workspace state such as seed status."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
