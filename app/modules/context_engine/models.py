"""Context Engine models — context_facts cache + tenant stories."""

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


def _naive_utc_now() -> datetime:
    """Return current UTC time without tzinfo for TIMESTAMP WITHOUT TIME ZONE columns."""
    return utc_now().replace(tzinfo=None)


class ContextFact(Base):
    """Cached verified fact from an external source (MN Revisor, HUD, EPA ECHO, etc.).

    Every fact has a source URL — no hallucination.
    """

    __tablename__ = "context_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="MN")
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_context_facts_subject_jur", "subject", "jurisdiction"),
    )


class TenantStory(Base):
    """Moderated tenant story. Anonymized. Surfaces after task completion.

    Story frame: `avoided_court` is the hero — documentation is the win, not litigation.
    """

    __tablename__ = "tenant_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="MN")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False, default="avoided_court")
    is_anonymized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_moderated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    submitted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    moderated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_naive_utc_now, onupdate=_naive_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_tenant_stories_subject_pub", "subject", "is_published"),
    )
