"""Settlement Awareness models — verified housing-litigation outcome records.

Mirrors the Part 3B Structured Fact Sourcing Contract
(docs/admin/SEMPTIFY_BUILD_CONTRACT.md): a record is a resolved *reference*
to a real public outcome, never a model-authored interpretation.

Hard gates (enforced at write AND at read):
  - ``resolution_status`` is ``Resolved`` / ``Unresolved`` / ``Disputed``;
    only ``Resolved`` records may surface.
  - ``source_url`` must be populated and ``fabrication_check`` true.
  - ``ai_generated`` must be ``False`` and ``attested_by`` must name a human.
  - ``news_*`` source authorities additionally require ``primary_source_url``.
  - Records stale >90 days since ``last_verified_date`` auto-hide (ADR-0009).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.utc import utc_now

RECORD_KINDS = (
    "settlement",
    "judgment",
    "consent_decree",
    "enforcement_action",
    "pending_case",
)

RESOLUTION_STATUSES = ("Resolved", "Unresolved", "Disputed")

# Source authorities beginning with this prefix are secondary (news) sources —
# held back from Resolved until a primary source URL is also populated.
SECONDARY_AUTHORITY_PREFIX = "news"


def _naive_utc_now() -> datetime:
    """Return current UTC time without tzinfo for TIMESTAMP WITHOUT TIME ZONE columns."""
    return utc_now().replace(tzinfo=None)


class SettlementOrCaseRecord(Base):
    """A verified pointer to a real, public housing-litigation outcome.

    Never user-facing until every Part 3B gate field is satisfied; the
    surfacing query re-checks the gates so a record that regresses
    (unverified, stale) stops surfacing without any code path having to
    remember to hide it.
    """

    __tablename__ = "settlement_or_case_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(255), unique=True, index=True,
                                           nullable=False)
    record_kind: Mapped[str] = mapped_column(String(40), nullable=False,
                                             default="settlement")

    # Identity of the public outcome
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    parties: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True,
                                              nullable=False, default="MN")
    citation: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    # Tag-matching key — a taxonomy.py Subject value (e.g. "deposit",
    # "eviction", "habitability")
    subject: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # Human-attested factual text only — pointers, not interpretation.
    headline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    relief_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sourcing (Part 3B shape)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    primary_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_authority: Mapped[str | None] = mapped_column(String(100),
                                                        nullable=True)

    # Resolution gate
    resolution_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Unresolved")
    resolution_method: Mapped[str | None] = mapped_column(String(100),
                                                         nullable=True)
    resolved_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Freshness machinery (90-day rolling recheck; stale auto-hides)
    last_verified_date: Mapped[str | None] = mapped_column(String(20),
                                                          nullable=True)
    next_recheck_date: Mapped[str | None] = mapped_column(String(20),
                                                         nullable=True,
                                                         index=True)

    # Attestation (hard gate — named human, same posture as Part 3)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False,
                                               nullable=False)
    attested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fabrication_check: Mapped[bool] = mapped_column(Boolean, default=False,
                                                    nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False,
                                              nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime,
                                                       nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                default=_naive_utc_now,
                                                nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_naive_utc_now, onupdate=_naive_utc_now,
        nullable=False)

    __table_args__ = (
        Index("ix_settlement_records_surface", "subject", "resolution_status"),
    )
