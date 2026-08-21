"""
Semptify Database Models
SQLAlchemy ORM models for all entities.

All datetime columns use DateTime(timezone=True) for proper UTC handling.
Use utc_now() from app.core.utc for all timestamp defaults.

=============================================================================
SSOT — DATABASE BOUNDARY RULE
=============================================================================
PostgreSQL holds: POINTERS and STRUCTURE only.
User's cloud storage holds: CONTENT and OVERLAYS.

Allowed in DB:  user_id, vault_id, sha256_hash, event_type, event_date,
                status flags, timestamps, short labels (255 chars max),
                landlord/entity data for admin/research tools.

NOT allowed:    complaint text, witness statements, contact PII (phone/
                email/address), annotation text, extracted document content,
                case narrative of any kind.

If a column stores what a tenant said, wrote, or what was found in their
document — it belongs in an overlay in their cloud, not here.
=============================================================================
"""

import enum
import logging
from datetime import datetime
from typing import Optional

from app.core.utc import utc_now

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
    from sqlalchemy.types import JSON

    JSONB = JSON  # Use generic JSON that works with both SQLite and PostgreSQL
    from sqlalchemy.orm import Mapped, mapped_column, relationship

    from app.core.database import Base

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    # Fallback stubs when SQLAlchemy not installed (test environment shim)
    class DateTime:
        def __init__(self, *args, **kwargs):
            pass  # Stub for test environment without SQLAlchemy

    class DummyColumnType:
        def __init__(self, *args, **kwargs):
            pass  # Stub for test environment without SQLAlchemy

    String = Text = Integer = ForeignKey = Boolean = Float = Enum = DummyColumnType

    # JSONB fallback for SQLite/non-PostgreSQL environments
    class JSONB(DummyColumnType):
        pass  # Stub for test environment without SQLAlchemy

    class Mapped:
        pass

    def mapped_column(*args, **kwargs):
        return None

    def relationship(*args, **kwargs):
        return None

    class Base:
        metadata = type("m", (), {"create_all": staticmethod(lambda *args, **kwargs: None)})  # noqa: ARG005

    SQLALCHEMY_AVAILABLE = False


# Type alias for timezone-aware DateTime columns
DateTimeTZ = DateTime(timezone=True)


# =============================================================================
# EventStatus Enum - Timeline Event Statuses
# =============================================================================


class EventStatus(enum.Enum):
    """
    Status values for timeline events tracking document/case lifecycle.
    """

    start = "start"  # Event initiates a process (lease signing, notice served)
    continued = "continued"  # Event continues/extends process (lease renewal, payment plan)
    finish = "finish"  # Event concludes process (case closed, eviction complete)
    reported = "reported"  # Issue/violation reported (maintenance request, complaint)
    invited = "invited"  # Meeting/hearing scheduled (court date, mediation)
    attended = "attended"  # Event was attended (hearing appearance)
    missed = "missed"  # Event was missed/no-show (missed court date)
    served = "served"  # Document delivered (notice served)
    received = "received"  # Document received (response received)
    filed = "filed"  # Document filed (court filing)
    responded = "responded"  # Response submitted (answer filed)
    pending = "pending"  # Awaiting action/decision (pending ruling)
    resolved = "resolved"  # Issue resolved (complaint resolved)
    escalated = "escalated"  # Issue escalated (appeal filed)
    used = "used"  # Evidence used in proceeding (document entered as exhibit)


# =============================================================================
# Urgency Enum - Event/Deadline Urgency Levels
# =============================================================================


class UrgencyLevel(enum.Enum):
    """
    Urgency levels for timeline events and deadlines.
    """

    critical = "critical"  # Immediate action required
    high = "high"  # Action needed soon
    normal = "normal"  # Standard priority
    low = "low"  # Can wait


# =============================================================================
# User Model (Storage-Based Auth)
# =============================================================================


class User(Base):
    """
    User account - storage-based authentication.

    Identity comes from cloud storage (Google Drive, Dropbox, OneDrive).
    The user_id is derived from provider:storage_user_id hash.

    This table stores:
    - Which provider they primarily use (for re-auth)
    - Their preferred role (to restore on return)

    SSOT PRIVACY RULE: No PII is stored in Semptify's database.
    Email, name, and all personal data live only in the user's cloud
    storage vault, accessed via overlay. Semptify is stateless.

    SSOT PRIVACY RULE (TENANT): Tenant user information must not be stored
    on Semptify servers beyond the provider metadata needed to reconnect.
    Tenant identity and personal data remain in the user's cloud storage vault.
    """

    __tablename__ = "users"

    # Primary key: stateless user_id (~66 chars), widened to 128
    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    # Storage provider info (to know where to look for token on return)
    primary_provider: Mapped[str] = mapped_column(String(20), index=True)  # google_drive, dropbox, onedrive
    storage_user_id: Mapped[str] = mapped_column(String(100))  # ID in the storage provider

    # Role preference (restored on return)
    default_role: Mapped[str] = mapped_column(String(20), default="user")  # user, manager, advocate, legal, admin

    # Legal sub-role (only meaningful when default_role == 'legal')
    # Sub-roles: attorney, judge, clerk, paralegal — all require bar_license_number
    legal_sub_role: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Bar license number (required for all legal sub-roles)
    # Stored as hashed reference — not PII, it's a public professional credential
    bar_license_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Intensity Engine (tenant-specific feature)
    intensity_level: Mapped[str] = mapped_column(String(10), default="low")  # low, medium, high

    # Permanent process completion record — written once per group, never re-verified from cloud.
    # Comma-separated group names, e.g. "storage_connected,vault_initialized"
    # Serial gating: each entry is written only after its ProcessGroup exit_criteria are verifiably met.
    completed_groups: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    last_login: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rent_payments: Mapped[list["RentPayment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    journal_entries: Mapped[list["JournalEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    linked_providers: Mapped[list["LinkedProvider"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# =============================================================================
# Linked Storage Providers (Multi-Provider Support)
# =============================================================================


class LinkedProvider(Base):
    """
    Additional storage providers linked to a user account.

    A user authenticates with one provider initially (becomes primary).
    They can later link additional providers for backup/sync.
    """

    __tablename__ = "linked_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Provider info
    provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive
    storage_user_id: Mapped[str] = mapped_column(String(100))  # ID in this provider

    # SSOT PRIVACY RULE: No email or display_name stored.
    # Personal data lives only in the user's cloud vault.

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    linked_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    last_used: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="linked_providers")


# =============================================================================
# Document Vault
# =============================================================================


class DeepOCRStatus(enum.StrEnum):
    """Status values for the Deep OCR pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    NEEDS_REPROCESS = "needs_reprocess"


class Document(Base):
    """
    Document stored in the vault with certification.

    Privilege Levels:
    - is_privileged=False: Normal tenant document (visible to tenant, advocate, attorney)
    - is_privileged=True: Attorney-client privileged (visible ONLY to creating attorney + client)
    - is_work_product=True: Attorney work product (protected from discovery)
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # File info
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))

    # Certification
    sha256_hash: Mapped[str] = mapped_column(String(64))
    certificate_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadata
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # lease, notice, photo, etc.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated

    # ==========================================================================
    # ATTORNEY-CLIENT PRIVILEGE FLAGS
    # ==========================================================================
    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    """Attorney-client privileged document. Only visible to creating attorney and the client."""

    is_work_product: Mapped[bool] = mapped_column(Boolean, default=False)
    """Attorney work product. Protected from discovery even in litigation."""

    created_by_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """Role of user who created this document (user, advocate, legal, admin)."""

    attorney_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    """If privileged, the attorney who created it (for privilege verification)."""

    privilege_waived: Mapped[bool] = mapped_column(Boolean, default=False)
    """If True, client has explicitly waived privilege on this document."""

    # Processing state
    deep_ocr_status: Mapped[str] = mapped_column(
        String(20),
        default=DeepOCRStatus.PENDING.value,
        nullable=False,
    )
    """Deep OCR pipeline status: pending, processing, complete, failed, needs_reprocess."""

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")


class DocumentPipelineIndex(Base):
    """
    Persistent metadata index used by DocumentPipeline.

    This stores analyzed document metadata in PostgreSQL so state survives
    server restarts without relying on local disk files.
    """

    __tablename__ = "document_pipeline_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(24), index=True)
    payload_json: Mapped[str] = mapped_column(Text)

    # Processing state
    deep_ocr_status: Mapped[str] = mapped_column(
        String(20),
        default=DeepOCRStatus.PENDING.value,
        nullable=False,
    )
    """Deep OCR pipeline status: pending, processing, complete, failed, needs_reprocess."""

    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Timeline Events
# =============================================================================


class TimelineEvent(Base):
    """
    Events in the tenant's timeline.
    Enhanced with event status, date ranges, event chaining, and annotation links.
    """

    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50))  # notice, payment, maintenance, communication, court
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When it happened (supports date ranges)
    event_date: Mapped[datetime] = mapped_column(DateTimeTZ, index=True)
    event_date_end: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)  # For date ranges

    # Event status (lifecycle tracking)
    event_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # EventStatus enum value

    # Event chaining (for linked events: start→continued→finish)
    parent_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # Links to parent event
    sequence_number: Mapped[int] = mapped_column(Integer, default=0)  # Order in chain

    # Annotation/Extraction links
    source_extraction_id: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "DT-3"
    footnote_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Link to annotation
    highlight_color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "date", "deadline", etc.

    # Urgency and deadline tracking
    urgency: Mapped[str] = mapped_column(String(20), default="normal")  # critical, high, normal, low
    is_deadline: Mapped[bool] = mapped_column(Boolean, default=False)  # Deadline flag

    # Linked document (optional) - stores doc ID from file-based pipeline, not FK
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Importance for court
    is_evidence: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="timeline_events")


# =============================================================================
# Rent Ledger
# =============================================================================


class RentPayment(Base):
    """
    Rent ledger entry (payment, fee, deposit, credit, or charge).

    The ledger supports a running balance across all entry types. Amounts are
    stored in cents to avoid floating point issues. The sign of an entry's
    effect on the running balance is determined by its entry_type:
      - positive: payment, deposit, credit
      - negative: fee, charge
    """

    __tablename__ = "rent_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Ledger entry details
    entry_type: Mapped[str] = mapped_column(String(20), default="payment")  # payment, fee, deposit, credit, charge
    amount: Mapped[int] = mapped_column(Integer)  # Store in cents to avoid float issues
    payment_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    due_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    period_covered: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "2026-07"

    # Status
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # paid, late, partial, missed

    # Method and confirmation
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Source of the entry
    source: Mapped[str] = mapped_column(String(20), default="user_entered")  # user_entered, ocr_extracted

    # Linked receipt document (stores doc ID from file-based pipeline, not FK)
    receipt_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Link to an overlay highlight when entry originates from a document
    overlay_link: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True, onupdate=utc_now)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="rent_payments")


# =============================================================================
# Calendar / Deadlines
# =============================================================================


class CalendarEvent(Base):
    """
    Calendar event or deadline.
    """

    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Event details
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    start_datetime: Mapped[datetime] = mapped_column(DateTimeTZ)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    # Type and urgency
    event_type: Mapped[str] = mapped_column(String(50))  # deadline, hearing, reminder, appointment
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)  # Affects intensity engine

    # Reminders (days before)
    reminder_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Source and linkage for auto-synced events
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # document_extraction, rent_ledger, manual
    linked_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # idempotency key for auto-sync

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True, onupdate=utc_now)


# =============================================================================
# Journal — Free-form tenant records
# =============================================================================


class JournalEntry(Base):
    """
    A free-form tenant journal entry.

    Tenants log contemporaneous records (verbal conversations with the landlord,
    incidents, observations, repair requests) that may not have a document yet.
    Entries are lightweight, timestamped, and optionally tagged.
    """

    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Entry content
    entry_type: Mapped[str] = mapped_column(String(50))  # note, conversation, incident, repair_request, other
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When the recorded event occurred (defaults to creation time)
    occurred_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)

    # Urgency and context
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    involved_party: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. landlord, manager
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated tags
    source: Mapped[str] = mapped_column(String(50), default="manual")

    # Optional link to a vault document (stored as vault_id, not a foreign key)
    document_link: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="journal_entries")


# =============================================================================
# Complaints
# =============================================================================


class Complaint(Base):
    """
    Formal complaint being filed with regulatory agencies.
    Extended for Complaint Wizard with full draft support.
    """

    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Agency info
    agency_id: Mapped[str] = mapped_column(String(50), index=True)  # e.g., mn_ag_consumer, hud_fair_housing

    # Type and status
    complaint_type: Mapped[str] = mapped_column(String(50))  # habitability, discrimination, retaliation, etc.
    status: Mapped[str] = mapped_column(
        String(20)
    )  # draft, ready, filed, acknowledged, investigating, resolved, closed

    # Subject and description
    subject: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(String(500), default="")
    detailed_description: Mapped[Text] = mapped_column(Text, default="")

    # Incident info
    incident_dates: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of dates
    damages_claimed: Mapped[float | None] = mapped_column(nullable=True)
    relief_sought: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Target/Respondent info
    target_type: Mapped[str] = mapped_column(String(50), default="landlord")  # landlord, property_manager, hoa
    target_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Evidence
    attached_document_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of doc IDs
    timeline_included: Mapped[bool] = mapped_column(Boolean, default=False)

    # Filing info
    filed_with: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Agency name
    filing_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Witness Statements
# =============================================================================


class WitnessStatement(Base):
    """
    Third-party witness statement.
    """

    __tablename__ = "witness_statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Witness info
    witness_name: Mapped[str] = mapped_column(String(255))
    witness_relationship: Mapped[str] = mapped_column(String(100))  # neighbor, family, friend, professional
    witness_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Statement
    statement_text: Mapped[Text] = mapped_column(Text)
    statement_date: Mapped[datetime] = mapped_column(DateTimeTZ)

    # Verification
    is_notarized: Mapped[bool] = mapped_column(Boolean, default=False)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # File-based doc ID

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Certified Mail Tracking
# =============================================================================


class CertifiedMail(Base):
    """
    Certified mail tracking record.
    """

    __tablename__ = "certified_mail"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Mail details
    tracking_number: Mapped[str] = mapped_column(String(50))
    recipient_name: Mapped[str] = mapped_column(String(255))
    recipient_address: Mapped[str] = mapped_column(Text)

    # Purpose
    mail_type: Mapped[str] = mapped_column(String(50))  # notice, demand_letter, complaint, other
    subject: Mapped[str] = mapped_column(String(255))

    # Status tracking
    status: Mapped[str] = mapped_column(String(50))  # sent, in_transit, delivered, returned
    sent_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    delivered_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Linked document (copy of what was sent) - stores file-based doc ID
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Session (Persistent OAuth Sessions)
# =============================================================================


class Session(Base):
    """
    Persistent OAuth session.

    Replaces in-memory SESSIONS dict so sessions survive server restarts.
    Tokens are stored encrypted using the user's derived key.
    """

    __tablename__ = "sessions"

    # Primary key is the user_id (one session per user)
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Provider info
    provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive

    # Encrypted tokens (encrypted with user-specific key)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session metadata
    authenticated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)

    # Role authorization tracking
    role_authorized_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)


# =============================================================================
# Storage Config (User's Storage Settings)
# =============================================================================


class StorageConfig(Base):
    """
    User's storage configuration.

    Persists storage-related settings so they survive across sessions:
    - Which cloud providers are connected
    - R2 bucket settings
    - Sync preferences
    - Default vault structure

    This is the key model that was missing - without it, users lose
    their storage configuration when sessions expire.
    """

    __tablename__ = "storage_configs"

    # Primary key is the user_id (one config per user), widened to 128
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)

    # Primary storage provider (where auth_token.enc lives)
    primary_provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive

    # R2 Configuration (for document storage)
    r2_bucket_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    r2_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    r2_access_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    r2_secret_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vault structure preferences
    vault_folder_path: Mapped[str] = mapped_column(String(500), default="/Semptify")  # Root folder in cloud storage
    auto_organize: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-organize by document type

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    last_sync: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Connected providers (JSON list of provider names)
    connected_providers: Mapped[str | None] = mapped_column(String(200), nullable=True)  # e.g., "google_drive,dropbox"

    # Feature flags
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Secondary provider for backup

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# OAuth State (CSRF Protection - DB-backed so server restarts don't break auth)
# =============================================================================


class OAuthState(Base):
    """
    Persistent OAuth CSRF state.

    Replaces the in-memory OAUTH_STATES dict so state tokens survive server
    restarts and multi-worker deployments.  Tokens are short-lived (15 min)
    and cleaned up after use or expiry.
    """

    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # the state token
    provider: Mapped[str] = mapped_column(String(50))
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    existing_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    return_to: Mapped[str | None] = mapped_column(String(512), nullable=True)
    force_fresh: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTimeTZ)


# =============================================================================
# Fraud Analysis Results
# =============================================================================


class FraudAnalysisResult(Base):
    """
    Results from fraud pattern analysis on landlord/property.
    """

    __tablename__ = "fraud_analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Analysis target
    analysis_type: Mapped[str] = mapped_column(String(50))  # hud, mortgage, habitability, eviction
    target_entity: Mapped[str] = mapped_column(String(255), index=True)  # landlord/company name
    property_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Results
    risk_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    risk_level: Mapped[str] = mapped_column(String(20), default="unknown")  # low, medium, high, critical
    findings: Mapped[Text] = mapped_column(Text, default="")  # JSON formatted findings
    indicators: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of indicators
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Evidence links
    evidence_doc_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of doc IDs
    related_complaints: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Status
    status: Mapped[str] = mapped_column(String(20), default="completed")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Press Release Records
# =============================================================================


class PressReleaseRecord(Base):
    """
    Press release generation and media campaign tracking.
    """

    __tablename__ = "press_release_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Content
    release_type: Mapped[str] = mapped_column(String(50))  # discrimination, code_violations, fraud, etc.
    title: Mapped[str] = mapped_column(String(500))
    headline: Mapped[str] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(10), default="en")  # en, es, hmn, so
    content: Mapped[Text] = mapped_column(Text, default="")

    # Targeting
    target_outlets: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of outlets
    target_region: Mapped[str] = mapped_column(String(100), default="Minnesota")

    # Media kit reference
    media_kit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, published, sent
    sent_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Research Profiles
# =============================================================================


class ResearchProfile(Base):
    """
    Landlord/entity research profile with aggregated findings.
    """

    __tablename__ = "research_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Entity identification
    entity_type: Mapped[str] = mapped_column(String(50))  # landlord, llc, property_manager
    entity_name: Mapped[str] = mapped_column(String(255), index=True)
    property_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Research data (JSON format)
    assessor_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorder_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    ucc_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatch_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    sos_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    bankruptcy_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    insurance_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aggregated findings
    normalized_profile: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    fraud_flags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    risk_score: Mapped[int] = mapped_column(Integer, default=0)

    # Sources tracking
    sources_checked: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress, complete, stale

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Contact Manager
# =============================================================================


class Contact(Base):
    """
    Contact management for case-related people and organizations.
    Tracks landlords, attorneys, witnesses, inspectors, agencies, etc.
    """

    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Contact Type
    contact_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: landlord, property_manager, attorney, witness, inspector,
    #        agency, court, legal_aid, tenant_org, other

    # Role in case
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Roles: opposing_party, opposing_counsel, my_witness, their_witness,
    #        inspector, caseworker, judge, mediator, etc.

    # Basic Info
    name: Mapped[str] = mapped_column(String(255), index=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Contact Details
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_alt: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Address
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Additional Info
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Comma-separated

    # Source tracking (where did this contact come from?)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Sources: manual, extracted, imported, agency_lookup

    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Interaction tracking
    last_contact_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class ThirdPartyEntityType(enum.Enum):
    """
    Allowed third-party entity types for the ThirdPartyContact table.
    Stored as a string value in the database to keep the fallback-stub path
    simple and to match the existing enum-as-string convention in this file.
    """

    landlord = "landlord"
    property_manager = "property_manager"
    agency = "agency"
    attorney = "attorney"
    other = "other"


class ThirdPartyContact(Base):
    """
    Third-party contacts linked to a tenant's case record.

    Stores landlord, property manager, agency, attorney, and other party
    contact data extracted from imports or entered manually. This is
    landlord/entity data permitted in the DB under the SSOT database boundary
    rule; it is distinct from the authenticating tenant's own PII, which must
    never be stored here.

    Fields:
    - user_id: ownership (who imported/entered this contact)
    - case_record_id: optional case linkage; stored as a string because the
      canonical case_records table is not yet implemented. A future migration
      can promote this to a real ForeignKey.
    - entity_type: landlord | property_manager | agency | attorney | other
    - name / email / phone / address: third-party contact points
    - source: how the contact was captured (manual_entry, email_import,
      call_log_import, sms_import, voicemail_import, agency_lookup)
    - source_document_id: trace back to the originating imported file/document
    - created_at / updated_at: audit timestamps
    """

    __tablename__ = "third_party_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Case linkage. Nullable because the canonical case_records table does not
    # exist yet; index it for fast lookup once the table is added.
    case_record_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Entity classification
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    # ThirdPartyEntityType enum value: landlord, property_manager, agency,
    # attorney, other

    # Contact details
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Audit/source trail
    source: Mapped[str] = mapped_column(String(100), index=True)
    # Sources: manual_entry, email_import, call_log_import, sms_import,
    #          voicemail_import, agency_lookup

    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # Originating file/document identifier, when source is an import.

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class ContactInteraction(Base):
    """
    Log of interactions with contacts (calls, emails, meetings).
    """

    __tablename__ = "contact_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)
    contact_id: Mapped[str] = mapped_column(String(36), ForeignKey("contacts.id"), index=True)

    # Interaction details
    interaction_type: Mapped[str] = mapped_column(String(50))
    # Types: phone_call, email, letter, in_person, court_appearance, voicemail

    direction: Mapped[str] = mapped_column(String(20))  # incoming, outgoing

    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dates
    interaction_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Attachments/Documents
    related_document_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    # Follow-up
    follow_up_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Document Annotations (Footnotes & Highlights Indexing)
# =============================================================================


class DocumentAnnotation(Base):
    """
    Tracks document annotations for footnote indexing system.
    Links highlights to timeline events and provides numbered markers.

    Supports both global sequential numbering (1, 2, 3...) and
    per-category numbering (DT-1, DT-2, PT-1...).
    """

    __tablename__ = "document_annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), index=True)  # Briefcase document ID
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Footnote numbering (dual system)
    footnote_number: Mapped[int] = mapped_column(Integer)  # Global: 1, 2, 3...
    category_number: Mapped[int] = mapped_column(Integer)  # Per-category: DT-1, DT-2...
    extraction_code: Mapped[str] = mapped_column(String(10))  # "DT", "PT", "$", etc.

    # Content
    highlight_text: Mapped[str] = mapped_column(Text)  # Selected text
    annotation_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # User's note

    # Position (for overlay rendering)
    page_number: Mapped[int] = mapped_column(Integer)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    position_width: Mapped[float] = mapped_column(Float, default=0.0)
    position_height: Mapped[float] = mapped_column(Float, default=0.0)

    # Timeline link
    linked_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # FK to timeline_events

    # Detection metadata
    detection_method: Mapped[str] = mapped_column(String(20), default="MANUAL")  # PATTERN, AI, MANUAL
    confidence: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 to 1.0

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# ALL-IN-ONE UNIFIED EVIDENCE VAULT (Semptify 5.0)
# =============================================================================
# Following the ALL-IN-ONE specification for unified evidence vault architecture
# with three-timestamp model and comprehensive metadata preservation.
# =============================================================================


class VaultItem(Base):
    """
    Unified evidence vault item following ALL-IN-ONE specification.

    Three-Timestamp Model (NON-NEGOTIABLE):
    - event_time: Factual time of event occurrence
    - record_time: When evidence was created/recorded
    - semptify_entry_time: When added to Semptify system

    Data Contract Rules:
    - Never discard metadata
    - Never flatten metadata
    - Never overwrite timestamps
    - Preserve nested JSON
    - If unknown → set null
    """

    __tablename__ = "vault_items"

    # Primary key
    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # ==========================================================================
    # THREE TIMESTAMPS (NON-NEGOTIABLE)
    # ==========================================================================
    event_time: Mapped[datetime] = mapped_column(
        DateTimeTZ, nullable=False, index=True, comment="Factual time of event occurrence"
    )
    record_time: Mapped[datetime] = mapped_column(
        DateTimeTZ, nullable=False, index=True, comment="When evidence was created/recorded"
    )
    semptify_entry_time: Mapped[datetime] = mapped_column(
        DateTimeTZ, nullable=False, default=utc_now, index=True, comment="When added to Semptify system"
    )

    # ==========================================================================
    # CLASSIFICATION & ORGANIZATION
    # ==========================================================================
    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Document type: lease, notice, photo, email, audio, etc."
    )
    folder: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Virtual folder path within vault")
    tags: Mapped[list[str] | None] = mapped_column(
        JSONB,  # Will use JSONB type from PostgreSQL
        nullable=True,
        comment="Array of searchable tags",
    )

    # ==========================================================================
    # RELATIONSHIPS & CONTEXT
    # ==========================================================================
    related_incident_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("incidents.incident_id"), nullable=True, index=True
    )
    source: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Source of evidence: upload, email, portal, extraction, etc."
    )
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="critical, high, normal, low")
    status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="pending, verified, disputed, archived"
    )

    # ==========================================================================
    # RICH METADATA (JSONB - Deep Searchable)
    # ==========================================================================
    location_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="GPS, address, coordinates, location context"
    )
    item_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="Complete preserved metadata (EXIF, headers, extracted fields)"
    )

    # ==========================================================================
    # CONTENT REFERENCES
    # ==========================================================================
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Path to stored file in cloud storage"
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI-generated or user-provided summary")

    # ==========================================================================
    # RELATIONSHIPS
    # ==========================================================================
    user: Mapped["User"] = relationship(back_populates="vault_items")
    incident: Mapped[Optional["Incident"]] = relationship(back_populates="vault_items")
    audit_logs: Mapped[list["VaultAuditLog"]] = relationship(back_populates="vault_item", cascade="all, delete-orphan")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class Incident(Base):
    """
    Incident/Case grouping for organizing related vault items.

    Incidents group related evidence, timeline events, and activities
    into coherent case narratives.
    """

    __tablename__ = "incidents"

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Incident details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Time boundaries
    start_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", comment="active, resolved, closed, archived")

    # Classification
    incident_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="habitability, discrimination, eviction, retaliation, etc."
    )
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="critical, high, normal, low")

    # Metadata
    incident_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Overlay pointer — actual case content lives in the user's cloud storage
    case_overlay_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="CASE_DATA overlay id in user cloud storage"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="incidents")
    vault_items: Mapped[list["VaultItem"]] = relationship(back_populates="incident")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class VaultAuditLog(Base):
    """
    Comprehensive audit trail for all vault item operations.

    Records before/after states for complete change tracking.
    """

    __tablename__ = "vault_audit_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("vault_items.item_id"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)

    # Action details
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="create, update, delete, view, export, verify"
    )
    action_context: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="API endpoint, background job, etc."
    )

    # Change tracking (JSONB for flexibility)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Complete state before change")
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Complete state after change")

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, index=True)

    # Relationship
    vault_item: Mapped["VaultItem"] = relationship(back_populates="audit_logs")


# =============================================================================
# Invite Code Model - For Advocate/Legal Role Validation
# =============================================================================


class InviteCode(Base):
    """
    Invite codes for validating Advocate and Legal roles.

    Organizations (managers) generate invite codes for advocates
    and legal professionals to join their organization.

    Codes can be:
    - One-time use (redeemed by a specific user)
    - Multi-use (multiple advocates from same org)
    - Time-limited (expires after date)
    - Role-specific (advocate vs legal vs admin)
    """

    __tablename__ = "invite_codes"

    # Primary key: code itself (readable, unique)
    code: Mapped[str] = mapped_column(String(32), primary_key=True)

    # Who created this code
    created_by: Mapped[str] = mapped_column(String(24), ForeignKey("users.id"), index=True)

    # Organization context (optional, for multi-tenant agencies)
    organization_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    organization_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Role this code grants
    role: Mapped[str] = mapped_column(String(20), default="advocate")  # advocate, legal, admin

    # Usage limits
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses_count: Mapped[int] = mapped_column(Integer, default=0)

    # Who has used this code (JSON array of user IDs)
    used_by: Mapped[list | None] = mapped_column(JSONB, default=list)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional note/description (e.g., "Summer 2024 intern batch")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)

    @property
    def is_expired(self) -> bool:
        """Check if code has expired."""
        if self.expires_at is None:
            return False
        return utc_now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if code can still be used."""
        return self.is_active and not self.is_expired and self.uses_count < self.max_uses

    @property
    def remaining_uses(self) -> int:
        """Number of remaining uses."""
        if not self.is_valid:
            return 0
        return self.max_uses - self.uses_count


# Update User model to include new relationships
User.vault_items = relationship("VaultItem", back_populates="user", cascade="all, delete-orphan")
User.incidents = relationship("Incident", back_populates="user", cascade="all, delete-orphan")


# =============================================================================
# MNDES Exhibit Package - Persistent storage for exhibit packages
# =============================================================================


class MNDESExhibitPackageDB(Base):
    """
    MNDES exhibit package stored in database for persistence.

    Replaces in-memory _packages dict in mndes_exhibit_service.py
    Packages survive server restarts and are queryable by user/case.
    """

    __tablename__ = "mndes_exhibit_packages"

    # Primary key - package ID (matches the in-memory package ID)
    package_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Ownership
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # Case information
    mn_case_number: Mapped[str] = mapped_column(String(50), index=True)
    case_type: Mapped[str] = mapped_column(String(50), default="eviction")
    case_caption: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Package metadata
    package_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Exhibits (stored as JSON array)
    exhibits_json: Mapped[str] = mapped_column(Text)

    # Compliance tracking
    requires_attestation: Mapped[bool] = mapped_column(Boolean, default=True)
    attestation_provided: Mapped[bool] = mapped_column(Boolean, default=False)
    attestation_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    attested_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status workflow
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, ready, submitted, confirmed

    # Submission tracking
    is_sealed_case: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class MNDESExhibitItemDB(Base):
    """
    Individual exhibit within a package (denormalized for queryability).

    Allows querying individual exhibits across packages.
    """

    __tablename__ = "mndes_exhibit_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # References
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("mndes_exhibit_packages.package_id"), index=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)
    vault_id: Mapped[str] = mapped_column(String(36), index=True)

    # Exhibit details
    exhibit_number: Mapped[str] = mapped_column(String(20))
    exhibit_name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(Integer)

    # Validation results (JSON)
    validation_json: Mapped[str] = mapped_column(Text)

    # Compliance flags
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Vault Index - Persistent index for vault documents
# =============================================================================


class VaultIndexDB(Base):
    """
    Persistent vault document index stored in database.

    Replaces in-memory _documents dict in vault_upload_service.py.
    Enables fast document lookup without relying on in-memory cache.
    """

    __tablename__ = "vault_index"

    # Primary key - vault_id (matches VaultDocument.vault_id)
    vault_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Ownership
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)

    # File information
    filename: Mapped[str] = mapped_column(String(255))
    safe_filename: Mapped[str] = mapped_column(String(255))
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))

    # Cloud storage location
    storage_path: Mapped[str] = mapped_column(String(500))
    # Provider-specific file id (e.g. Google Drive file ID) to avoid fragile name-based lookups
    provider_file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(50))  # google_drive, dropbox, onedrive, local

    # Classification
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated

    # Certification and integrity
    certificate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    registry_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    integrity_status: Mapped[str] = mapped_column(String(20), default="unverified")  # verified, tampered, unverified

    # Processing state
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source tracking
    source_module: Mapped[str] = mapped_column(String(50), default="direct")

    # Document Center review state (field confirmations/corrections and manual status)
    review_state_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)

    @property
    def is_certified(self) -> bool:
        """Check if document has completed registration."""
        return self.registry_id is not None and self.integrity_status == "verified"


class VaultUserIndexDB(Base):
    """
    Per-user vault index for fast user document listing.

    Replaces in-memory _user_index dict in vault_upload_service.py.
    """

    __tablename__ = "vault_user_index"

    # Composite primary key
    user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"), primary_key=True)
    vault_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Ordering
    added_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


class VaultHashIndexDB(Base):
    """
    SHA256 hash deduplication index.

    Replaces in-memory _hash_index dict in vault_upload_service.py.
    Maps content hash to vault_id for deduplication.
    """

    __tablename__ = "vault_hash_index"

    # Primary key - content hash
    sha256_hash: Mapped[str] = mapped_column(String(64), primary_key=True)

    # First vault document with this hash
    vault_id: Mapped[str] = mapped_column(String(36), ForeignKey("vault_index.vault_id"))
    user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"))

    # Reference count (how many times this hash appears)
    ref_count: Mapped[int] = mapped_column(Integer, default=1)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Document Shares — real Document Center sharing with recipient and scope
# =============================================================================


class DocumentShare(Base):
    """
    Tracks documents shared from the Document Center to a recipient.

    The recipient can be another Semptify user_id, an advocate/legal ID,
    or an email address. The scope controls what the recipient can do:
    view, comment, or download. Access is gated by share_token.
    """

    __tablename__ = "document_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True)
    vault_id: Mapped[str] = mapped_column(String(36), ForeignKey("vault_index.vault_id"), index=True)

    recipient_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)  # view, comment, download
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    share_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Admin Audit Log — Live admin action tracking
# =============================================================================


class AdminAuditLog(Base):
    """
    Comprehensive audit trail for all admin actions.

    Records every administrative operation with full details for compliance.
    """

    __tablename__ = "admin_audit_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Who performed the action
    admin_user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"), index=True)
    admin_role: Mapped[str] = mapped_column(String(50))

    # What was done
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_user: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)

    # Full details (JSON) - action-specific data
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Client info for security tracking
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamp with timezone
    timestamp: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, index=True)


class AdminErrorQueue(Base):
    """
    Error queue for admin dashboard errors reported to Cascade.

    Stores errors from the admin dashboard for automated tracking and fixing.
    """

    __tablename__ = "admin_error_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Error context
    section: Mapped[str] = mapped_column(String(100))  # e.g., "Audit Log", "User Management"
    endpoint: Mapped[str] = mapped_column(String(500))  # e.g., "/admin-console/api/audit"
    error_message: Mapped[str] = mapped_column(Text)  # Full error message

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, in_progress, completed, skipped
    priority: Mapped[str] = mapped_column(String(10), default="medium", index=True)  # low, medium, high

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Additional details (JSON)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# =============================================================================
# User Relationships — Role Hierarchy & Access Control
# =============================================================================


class RelationshipType(enum.Enum):
    """Types of relationships between users."""

    LEASE = "lease"  # Manager-tenant: property management relationship
    ADVOCACY = "advocacy"  # Advocate-client: legal representation
    ADMIN_OVERRIDE = "admin"  # Admin can impersonate any role for testing
    TEAM_MEMBER = "team"  # Same-organization team access


class UserRelationship(Base):
    """
    Relationships between users for hierarchical access control.

    Enables:
    - Admin role impersonation (acting_as)
    - Manager conditional access to tenant documents (if lease relationship exists)
    - Advocate conditional access to client documents (if engagement exists)
    """

    __tablename__ = "user_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # The user who has the relationship (can access the target)
    from_user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"), index=True)

    # The user being accessed (target of the relationship)
    to_user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"), index=True)

    # Type of relationship
    relationship_type: Mapped[str] = mapped_column(String(50), index=True)

    # Status of relationship
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Optional context data (JSON) - relationship-specific metadata
    # Examples: property_id for lease, case_id for advocacy
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True, index=True)

    # Who created this relationship (for audit)
    created_by: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships to User model
    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])


# =============================================================================
# User Capabilities — Per-user Feature Module Access Control
# =============================================================================


class UserCapability(Base):
    """
    Per-user capability record. Controls which Feature Modules a user has active.

    One row per (user_id, module_name) pair.
    Seeded with role defaults on first login.
    Can be granted/revoked by admin at any time.

    Rules:
    - Pipeline modules are never stored here — they are always on.
    - Only Feature Modules (user-loadable capabilities) get rows here.
    - source='role_default' means auto-seeded from product_manifest.py defaults.
    - source='admin_grant' means explicitly granted by an admin.
    - source='user_activated' means user opted in themselves.
    """

    __tablename__ = "user_capabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # The user this capability belongs to
    user_id: Mapped[str] = mapped_column(String(256), ForeignKey("users.id"), index=True)

    # Dotted module path matching ModuleEntry.module_path in product_manifest.py
    # e.g. "app.modules.case_builder.router"
    module_name: Mapped[str] = mapped_column(String(256), index=True)

    # Whether this capability is currently active for this user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # How this capability was granted
    source: Mapped[str] = mapped_column(
        String(50),
        default="role_default",
        index=True,
    )

    # Timestamps
    granted_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True, index=True)

    # Who granted this capability (for audit — null = system-seeded)
    granted_by: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationship to User model
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class ModuleRegistry(Base):
    """
    Module Registry — single source of truth for module status.

    Each module gets one row. Tracks:
    - status: unknown | active | beta | deprecated | broken
    - is_enabled: runtime toggle (can disable without code change)
    - dev_mode: when True, all requests get strict logging
    - version, route_prefix, depends_on for dependency management

    Core system code never changes — only these rows do.
    """

    __tablename__ = "module_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: unknown, active, beta, deprecated, broken
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")

    # Runtime toggle — can flip without restart
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Dev mode — enables strict request/response logging
    dev_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    route_prefix: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Array of module names this module depends on (JSON for SQLite compatibility)
    depends_on: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Admin notes for tracking issues, rollout status, etc.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str | None] = mapped_column(String(256), nullable=True)


class Resource(Base):
    """
    Community resource directory listings for tenant housing-rights support.

    These are neutral, factual, non-promotional listings of agencies and
    services directly relevant to tenant housing rights. Listings are
    admin-curated and bulk-imported; stale `last_verified` entries are
    surfaced for review because an outdated phone number can actively harm
    someone in crisis.
    """

    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Display and classification
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    # Category examples: legal_aid, housing_counseling, tenant_union,
    # emergency_shelter, rental_assistance, dispute_resolution

    # Service area: free-form geographic scope (e.g., "Hennepin County, MN",
    # "Minnesota", "National"). Indexed for filtering.
    service_area: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Languages offered, stored as a JSON array of ISO-639-1 codes.
    # Examples: ["en", "es", "so", "hmn"]
    languages: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Contact points: JSON object {phone, email, website, address}
    contact_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Provenance and freshness
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_verified: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Dispute Tracker
# =============================================================================


class DisputeRecord(Base):
    """Tenant dispute record — structure and pointers only, PII content in overlays.

    Tenant-facing, T2. Landlord/entity data is allowed per the DB boundary rule.
    Descriptions, witness statements, and tenant contact details are stored as
    overlay references, not in this table.
    """

    __tablename__ = "dispute_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True, nullable=False)

    # Allowed structural data
    landlord_entity: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    property_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dispute_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # fees, lease_violation, retaliation, habitability
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active, resolved, dismissed, on_hold
    jurisdiction: Mapped[str] = mapped_column(String(10), default="MN", nullable=False)

    # PII/content pointers (actual text lives in the user's cloud overlay)
    content_overlay_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evidence_overlay_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now, nullable=False)


class ComparisonEntry(Base):
    """Fee or term comparison entry attached to a dispute record.

    Amounts are stored in cents. The comparison rationale and any PII live in
    the source overlay.
    """

    __tablename__ = "comparison_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dispute_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dispute_records.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True, nullable=False)

    comparison_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fee, term, notice, deposit
    fee_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)  # monthly, yearly, one_time
    effective_date: Mapped[datetime | None] = mapped_column(DateTimeTZ, nullable=True)

    # Pointers to source content and evidence
    source_overlay_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now, nullable=False)


# =============================================================================
# Eviction Timeline
# =============================================================================


class EvictionTimelineEvent(Base):
    """Eviction-specific timeline event — structure and pointers only.

    Tenant-facing, T2. `subject_id` is a placeholder with no FK while the
    accountability_ledger boundary is deferred. The event narrative and any
    PII content are stored in the user''s cloud overlay.
    """

    __tablename__ = "eviction_timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id"), index=True, nullable=False)

    # Placeholder subject — no FK until accountability_ledger model is decided
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # notice, payment, maintenance, communication, court, filing
    event_date: Mapped[datetime] = mapped_column(DateTimeTZ, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual, document, court, email

    # Pointers only — content in overlays
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_overlay_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    jurisdiction: Mapped[str] = mapped_column(String(10), default="MN", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now, nullable=False)
