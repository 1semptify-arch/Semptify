"""Layer 2 semantic retrieval — hybrid metadata + embedding matching.

Adopts the asymmetric architecture from ADR-0008 Problem A:
  - pgvector / cosine_distance on PostgreSQL (production)
  - JSON blob + pure-Python cosine similarity on SQLite (dev)

The model (all-MiniLM-L6-v2) is loaded once as a singleton; see
``app/modules/context_engine/embedding_model.py``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, and_, select
from sqlalchemy.sql.expression import bindparam

from app.core.database import get_engine
from app.modules.context_engine.embedding_model import embed_text, get_embedding_model
from app.modules.context_engine.explanation_entries import (
    ContextExplanationEntry,
    get_explanation_entries,
)
from app.modules.context_engine.vector_math import cosine_similarity

if TYPE_CHECKING:
    from app.core.context_envelope import ObjectEnvelope

logger = logging.getLogger(__name__)

# Confidence threshold for Layer 2 semantic retrieval.
# Calibrated empirically against realistic Object Envelope queries and a
# representative Layer 1 corpus. all-MiniLM-L6-v2 cosine scores for genuine
# matches commonly fall in the 0.45-0.75 range, not near 1.0. We err on the
# stricter side because silence is safer than a weak match.
LAYER2_CONFIDENCE_THRESHOLD = 0.45


class RetrievalResult(BaseModel):
    """A single Layer 1 entry returned by Layer 2 retrieval."""

    model_config = ConfigDict(from_attributes=True)

    entry_id: str
    subject: str
    jurisdiction: str
    upl_risk_tier: str
    pillar: str
    review_status: str
    score: float = Field(..., ge=0.0, le=1.0)
    variant_trust: str
    variant_mechanics: str
    variant_reinforcement: str
    variant_minimal: str


def _query_text(obj: ObjectEnvelope) -> str:
    """Build a single query string from the Object Envelope.

    ``subject_tags`` carry the primary semantic signal; ``why`` is appended as
    context so the meaning of the object reinforces the tags rather than
    overwhelming them.
    """
    parts = list(obj.subject_tags)
    if obj.why:
        parts.append(obj.why)
    return " ".join(parts)


def _explanation_text(entry: ContextExplanationEntry) -> str:
    """Reconstruct the text the entry's embedding was generated from."""
    return (
        f"{entry.subject} {entry.variant_trust} {entry.variant_mechanics} "
        f"{entry.variant_reinforcement} {entry.variant_minimal}"
    )


def _result_from_entry(entry: ContextExplanationEntry, score: float) -> RetrievalResult:
    return RetrievalResult(
        entry_id=entry.entry_id,
        subject=entry.subject,
        jurisdiction=entry.jurisdiction,
        upl_risk_tier=entry.upl_risk_tier,
        pillar=entry.pillar,
        review_status=entry.review_status,
        score=round(score, 4),
        variant_trust=entry.variant_trust,
        variant_mechanics=entry.variant_mechanics,
        variant_reinforcement=entry.variant_reinforcement,
        variant_minimal=entry.variant_minimal,
    )


def _sort_and_limit(results: list[RetrievalResult], limit: int) -> list[RetrievalResult]:
    results.sort(
        key=lambda r: (
            r.score,
            1 if r.review_status == "VETTED" else 0,
            r.entry_id,
        ),
        reverse=True,
    )
    return results[:limit]


async def _score_with_python(
    query_embedding: list[float],
    obj: ObjectEnvelope,
    jurisdiction: str,
    threshold: float,
    limit: int,
) -> list[RetrievalResult]:
    """SQLite/dev path: metadata pre-filter, then pure-Python cosine similarity."""
    # Metadata pre-filter: jurisdiction + pillar. We do not require an exact
    # subject match — the point of semantic retrieval is to bridge tags that
    # mean the same thing (e.g. "late fee" and "penalty charge").
    candidates = await get_explanation_entries(
        jurisdiction=jurisdiction,
        pillar=obj.pillar,
        limit=1000,
    )

    results: list[RetrievalResult] = []
    for entry in candidates:
        embedding = entry.embedding
        if embedding is None:
            logger.debug("Skipping entry %s with no embedding", entry.entry_id)
            continue
        score = cosine_similarity(query_embedding, embedding)
        if score >= threshold:
            results.append(_result_from_entry(entry, score))

    return _sort_and_limit(results, limit)


async def _score_with_pgvector(
    query_embedding: list[float],
    obj: ObjectEnvelope,
    jurisdiction: str,
    threshold: float,
    limit: int,
) -> list[RetrievalResult] | None:
    """PostgreSQL path: use pgvector's native <=> cosine-distance operator.

    Returns ``None`` if the pgvector path cannot be used so the caller can
    fall back to the pure-Python path.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    try:
        from app.core.database import get_db_session
    except ImportError:  # pragma: no cover
        return None

    try:
        from pgvector.sqlalchemy import VECTOR as PgVector

        # The pgvector `<=>` operator is cosine distance; similarity = 1 - distance.
        distance_expr = ContextExplanationEntry.embedding.op("<=>", return_type=Float)(
            bindparam("query_vec", query_embedding, type_=PgVector(len(query_embedding)))
        )
        similarity_expr = 1 - distance_expr

        stmt = (
            select(ContextExplanationEntry, similarity_expr.label("score"))
            .where(
                and_(
                    ContextExplanationEntry.jurisdiction == jurisdiction,
                    ContextExplanationEntry.pillar == obj.pillar,
                    ContextExplanationEntry.embedding.is_not(None),
                    similarity_expr >= threshold,
                )
            )
            .order_by(distance_expr)
            .limit(limit * 2)
        )

        results: list[RetrievalResult] = []
        async with get_db_session() as db:
            rows = await db.execute(stmt)
            for entry, score in rows:
                results.append(_result_from_entry(entry, float(score)))
        return _sort_and_limit(results, limit)
    except Exception as e:
        logger.warning("pgvector retrieval failed, falling back to Python: %s", e)
        return None


async def retrieve_explanations(
    obj: ObjectEnvelope,
    *,
    jurisdiction: str = "MN",
    limit: int = 5,
) -> list[RetrievalResult]:
    """Rank Layer 1 explanation entries against an Object Envelope.

    Returns only results with a semantic score >= LAYER2_CONFIDENCE_THRESHOLD,
    sorted highest-first.
    """
    query_text = _query_text(obj)
    if not query_text.strip():
        return []

    query_embedding = await embed_text(query_text)
    if query_embedding is None:
        logger.warning("Embedding model not available; returning empty Layer 2 results")
        return []

    threshold = LAYER2_CONFIDENCE_THRESHOLD
    engine = get_engine()

    if engine.dialect.name == "postgresql":
        pg_results = await _score_with_pgvector(
            query_embedding, obj, jurisdiction, threshold, limit
        )
        if pg_results is not None:
            return pg_results

    return await _score_with_python(
        query_embedding, obj, jurisdiction, threshold, limit
    )


def select_tapered_variant(result: RetrievalResult, exposure_count: int) -> str:
    """Pick the right Layer 1 variant for this exposure count.

    Tapering rules from ADR-0008 §2.4:
      - 1st exposure: full (mechanics — what actually happens)
      - 2nd exposure: different angle (trust — why it matters)
      - 3rd exposure: different angle (reinforcement — short reminder)
      - 4th+: minimal/status-only with tap-to-expand
    """
    if exposure_count <= 0:
        exposure_count = 1

    if exposure_count == 1:
        return result.variant_mechanics
    if exposure_count == 2:
        return result.variant_trust
    if exposure_count == 3:
        return result.variant_reinforcement
    return result.variant_minimal


__all__ = [
    "LAYER2_CONFIDENCE_THRESHOLD",
    "RetrievalResult",
    "retrieve_explanations",
    "select_tapered_variant",
]
