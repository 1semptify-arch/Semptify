"""Info Donation models — consented, aggregate-only donation storage.

Two tables, both on ``app.core.database.Base``:

- ``info_donation_profiles`` — per-user state: when their situation was
  marked resolved, whether the donation ask was dismissed, and the
  versioned informed-consent record.
- ``info_donation_items`` — one row per donated answer. Rows are keyed to
  user_id ONLY so the tenant can review and withdraw them; nothing
  individual is ever shown publicly (aggregate-only per the spec).
  Withdrawal hard-deletes rows — the tenant's data is theirs.

PII boundary: no names, addresses, landlord names, or case numbers are
accepted (free text is pattern-screened in service.py and held in
``moderation=pending`` until a human reviews it).
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now


class InfoDonationProfile(Base):
    """Per-user donation state — resolution gate, dismissal, consent."""

    __tablename__ = "info_donation_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)

    # Resolution gate — set when the tenant marks their situation resolved
    # (self-report) or when an ISSUE_RESOLVED event arrives from elsewhere.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_source: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Permanent "not for me" — ends all donation asks for this tenant.
    prompt_dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Informed consent for the server-side aggregate. consent_version must
    # match catalog.CONSENT_VERSION at the moment consent is recorded.
    consent_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class InfoDonationItem(Base):
    """One donated answer. Categorical items are immediately aggregate-safe
    (``moderation="none"``); free-text items start ``pending`` and are never
    served until a reviewer marks them ``approved``."""

    __tablename__ = "info_donation_items"
    __table_args__ = (UniqueConstraint("user_id", "item_key", name="uq_info_donation_user_item"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(60), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)

    # none = aggregate-safe categorical answer; pending/approved/rejected =
    # free-text moderation lifecycle (reviewers: Brad + beta users).
    moderation: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    moderated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
