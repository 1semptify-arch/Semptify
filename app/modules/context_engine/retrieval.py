"""Layer 2 retrieval — metadata matching between Object Envelopes and Layer 1 entries.

This is the pilot implementation of ADR-0008 §2.2. It does NOT use an
embedding model (that is todo-077/todo-078). Instead it ranks
`ContextExplanationEntry` rows by metadata overlap:

- subject overlap (ObjectEnvelope.subject_tags ∩ entry.subject)
- jurisdiction match
- pillar match
- review_status preference (VETTED over BETA)

The `LAYER2_CONFIDENCE_THRESHOLD` is a named tuning constant so the same
interface can later accept real cosine scores without touching callers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.context_envelope import ObjectEnvelope
from app.modules.context_engine.explanation_entries import (
    ContextExplanationEntry,
    get_explanation_entries,
)

# Tuning parameter: ADR-0008 §5 #3. With metadata-only scoring this acts as a
# score floor rather than a cosine threshold. Will be reused by real semantic
# scoring in todo-078 without interface changes.
LAYER2_CONFIDENCE_THRESHOLD = 0.75


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


async def retrieve_explanations(
    obj: ObjectEnvelope,
    *,
    jurisdiction: str = "MN",
    limit: int = 5,
) -> list[RetrievalResult]:
    """Rank Layer 1 explanation entries against an Object Envelope.

    Returns only results with a metadata score >= LAYER2_CONFIDENCE_THRESHOLD,
    sorted highest-first.
    """
    candidate_subjects = {tag for tag in obj.subject_tags}
    if not candidate_subjects:
        return []

    # Fetch all candidate entries that share any subject with the object.
    # We fetch per subject and then score; this keeps the query simple and
    # does not require a full-text engine.
    seen_ids: set[str] = set()
    candidates: list[ContextExplanationEntry] = []
    for subject in candidate_subjects:
        entries = await get_explanation_entries(
            subject=subject,
            jurisdiction=jurisdiction,
            pillar=obj.pillar,
            limit=100,
        )
        for entry in entries:
            if entry.entry_id not in seen_ids:
                seen_ids.add(entry.entry_id)
                candidates.append(entry)

    results: list[RetrievalResult] = []
    for entry in candidates:
        score = _score_entry(obj, jurisdiction, entry)
        if score >= LAYER2_CONFIDENCE_THRESHOLD:
            results.append(
                RetrievalResult(
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
            )

    # Highest score first; ties broken by VETTED first, then most recent.
    results.sort(
        key=lambda r: (
            r.score,
            1 if r.review_status == "VETTED" else 0,
            r.entry_id,
        ),
        reverse=True,
    )
    return results[:limit]


def _score_entry(
    obj: ObjectEnvelope,
    jurisdiction: str,
    entry: ContextExplanationEntry,
) -> float:
    """Compute a 0.0-1.0 metadata match score.

    Weights:
      - subject overlap: 0.4
      - jurisdiction match: 0.2
      - pillar match: 0.2
      - review_status vetted: 0.2
    """
    score = 0.0
    if entry.subject in {tag for tag in obj.subject_tags}:
        score += 0.4
    if entry.jurisdiction == jurisdiction:
        score += 0.2
    if entry.pillar == obj.pillar:
        score += 0.2
    if entry.review_status == "VETTED":
        score += 0.2
    return score


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
