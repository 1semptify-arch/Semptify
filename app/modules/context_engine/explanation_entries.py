"""Layer 1 curated explanation entries for the Information Orchestrator.

These are short, human-written explanation fragments that sit *above* raw facts.
Each entry has multiple variant slots so the same guidance can be served with
varying depth depending on tenant familiarity, intensity level, and journey
stage. Entries are global/curated, never keyed to a single tenant.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, get_db_session
from app.core.database_types import AsymmetricVector
from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.modules.context_engine.embedding_model import EMBEDDING_DIMENSIONS, embed_text
from app.modules.context_engine.taxonomy import ALL_SUBJECTS


class ContextExplanationEntry(Base):
    """Curated explanation entry with multiple variant slots.

    Subject + jurisdiction + pillar + review_status define the retrieval filter.
    UPL risk tier helps the router decide when an entry may need attorney review.
    """

    __tablename__ = "context_explanation_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), index=True, nullable=False, default="MN")
    upl_risk_tier: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="LOW",
    )
    pillar: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(10),
        index=True,
        nullable=False,
        default="BETA",
    )

    # Four variant slots. Each slot is plain text; HTML is not allowed.
    variant_trust: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    variant_mechanics: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    variant_reinforcement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    variant_minimal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    # Pre-computed all-MiniLM-L6-v2 embedding of the entry's content. Stored as
    # pgvector(384) in PostgreSQL and JSON in SQLite so dev and prod share the
    # same code path.
    embedding: Mapped[list[float] | None] = mapped_column(
        AsymmetricVector(EMBEDDING_DIMENSIONS),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: utc_now().replace(tzinfo=None),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: utc_now().replace(tzinfo=None),
        onupdate=lambda: utc_now().replace(tzinfo=None),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_explanation_entries_lookup", "subject", "jurisdiction", "pillar", "review_status"),
    )


UPL_RISK_TIERS = {"LOW", "MEDIUM", "HIGH"}
REVIEW_STATUSES = {"BETA", "VETTED"}
PILLAR_NAMES = {"RECORD", "KNOW", "ACT", "GOVERN"}


def _validate_subject(subject: str) -> None:
    if subject not in ALL_SUBJECTS:
        raise ValueError(f"subject must be one of: {', '.join(ALL_SUBJECTS)}")


def _validate_upl_risk_tier(upl_risk_tier: str) -> None:
    if upl_risk_tier not in UPL_RISK_TIERS:
        raise ValueError(f"upl_risk_tier must be one of: {', '.join(sorted(UPL_RISK_TIERS))}")


def _validate_pillar(pillar: str) -> None:
    if pillar not in PILLAR_NAMES:
        raise ValueError(f"pillar must be one of: {', '.join(sorted(PILLAR_NAMES))}")


def _validate_review_status(review_status: str) -> None:
    if review_status not in REVIEW_STATUSES:
        raise ValueError(f"review_status must be one of: {', '.join(sorted(REVIEW_STATUSES))}")


def _explanation_embedding_text(
    subject: str,
    variant_trust: str,
    variant_mechanics: str,
    variant_reinforcement: str,
    variant_minimal: str,
) -> str:
    """Return the text that gets embedded for a Layer 1 entry.

    The subject and all four variants are concatenated so the embedding
    captures both the topic and every depth of explanation.
    """
    return f"{subject} {variant_trust} {variant_mechanics} {variant_reinforcement} {variant_minimal}"


async def _compute_explanation_embedding(
    subject: str,
    variant_trust: str,
    variant_mechanics: str,
    variant_reinforcement: str,
    variant_minimal: str,
) -> list[float] | None:
    text = _explanation_embedding_text(
        subject, variant_trust, variant_mechanics, variant_reinforcement, variant_minimal
    )
    return await embed_text(text)


async def create_explanation_entry(
    subject: str,
    jurisdiction: str,
    upl_risk_tier: str,
    pillar: str,
    review_status: str,
    variant_trust: str,
    variant_mechanics: str,
    variant_reinforcement: str,
    variant_minimal: str,
) -> ContextExplanationEntry:
    """Create a new curated explanation entry. Admin-only in the router."""
    _validate_subject(subject)
    _validate_upl_risk_tier(upl_risk_tier)
    _validate_pillar(pillar)
    _validate_review_status(review_status)

    embedding = await _compute_explanation_embedding(
        subject, variant_trust, variant_mechanics, variant_reinforcement, variant_minimal
    )

    entry = ContextExplanationEntry(
        entry_id=make_id("exp"),
        subject=subject,
        jurisdiction=jurisdiction,
        upl_risk_tier=upl_risk_tier,
        pillar=pillar,
        review_status=review_status,
        variant_trust=variant_trust,
        variant_mechanics=variant_mechanics,
        variant_reinforcement=variant_reinforcement,
        variant_minimal=variant_minimal,
        embedding=embedding,
        created_at=utc_now().replace(tzinfo=None),
        updated_at=utc_now().replace(tzinfo=None),
    )
    async with get_db_session() as db:
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
    return entry


async def get_explanation_entries(
    subject: str | None = None,
    jurisdiction: str = "MN",
    pillar: str | None = None,
    review_status: str | None = None,
    limit: int = 50,
) -> list[ContextExplanationEntry]:
    """List curated explanation entries for a subject/jurisdiction/pillar."""
    if subject is not None:
        _validate_subject(subject)
    if pillar is not None:
        _validate_pillar(pillar)
    if review_status is not None:
        _validate_review_status(review_status)

    async with get_db_session() as db:
        stmt = select(ContextExplanationEntry).where(
            ContextExplanationEntry.jurisdiction == jurisdiction,
        )
        if subject:
            stmt = stmt.where(ContextExplanationEntry.subject == subject)
        if pillar:
            stmt = stmt.where(ContextExplanationEntry.pillar == pillar)
        if review_status:
            stmt = stmt.where(ContextExplanationEntry.review_status == review_status)

        stmt = stmt.order_by(ContextExplanationEntry.review_status.desc(), ContextExplanationEntry.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_explanation_entry_by_id(entry_id: str) -> ContextExplanationEntry | None:
    """Fetch a single explanation entry by its public entry_id."""
    async with get_db_session() as db:
        result = await db.execute(
            select(ContextExplanationEntry).where(ContextExplanationEntry.entry_id == entry_id)
        )
        return result.scalars().first()


async def update_explanation_entry(
    entry_id: str,
    **kwargs,
) -> ContextExplanationEntry:
    """Update one or more fields of an existing explanation entry."""
    if "subject" in kwargs:
        _validate_subject(kwargs["subject"])
    if "upl_risk_tier" in kwargs:
        _validate_upl_risk_tier(kwargs["upl_risk_tier"])
    if "pillar" in kwargs:
        _validate_pillar(kwargs["pillar"])
    if "review_status" in kwargs:
        _validate_review_status(kwargs["review_status"])

    allowed_fields = {
        "subject",
        "jurisdiction",
        "upl_risk_tier",
        "pillar",
        "review_status",
        "variant_trust",
        "variant_mechanics",
        "variant_reinforcement",
        "variant_minimal",
    }
    unknown = set(kwargs) - allowed_fields
    if unknown:
        raise ValueError(f"Cannot update unknown fields: {', '.join(unknown)}")

    async with get_db_session() as db:
        result = await db.execute(
            select(ContextExplanationEntry).where(ContextExplanationEntry.entry_id == entry_id)
        )
        entry = result.scalars().first()
        if not entry:
            raise FileNotFoundError(f"Explanation entry {entry_id} not found")

        for key, value in kwargs.items():
            setattr(entry, key, value)

        # Recompute embedding if any content that feeds the embedding changed.
        embedding_fields = {
            "subject",
            "variant_trust",
            "variant_mechanics",
            "variant_reinforcement",
            "variant_minimal",
        }
        if embedding_fields.intersection(kwargs):
            entry.embedding = await _compute_explanation_embedding(
                entry.subject,
                entry.variant_trust,
                entry.variant_mechanics,
                entry.variant_reinforcement,
                entry.variant_minimal,
            )

        entry.updated_at = utc_now().replace(tzinfo=None)

        await db.commit()
        await db.refresh(entry)
        return entry


async def delete_explanation_entry(entry_id: str) -> bool:
    """Delete an explanation entry. Returns True if deleted."""
    async with get_db_session() as db:
        result = await db.execute(
            select(ContextExplanationEntry).where(ContextExplanationEntry.entry_id == entry_id)
        )
        entry = result.scalars().first()
        if not entry:
            return False
        await db.delete(entry)
        await db.commit()
        return True


__all__ = [
    "ContextExplanationEntry",
    "UPL_RISK_TIERS",
    "REVIEW_STATUSES",
    "PILLAR_NAMES",
    "create_explanation_entry",
    "get_explanation_entries",
    "get_explanation_entry_by_id",
    "update_explanation_entry",
    "delete_explanation_entry",
]
