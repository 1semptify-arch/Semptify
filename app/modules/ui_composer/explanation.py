"""Shared helper for retrieving contextual explanations on single-function guide pages.

This collapses the repeated ObjectEnvelope / retrieve_explanations / select_tapered_variant
pattern in `app/main.py` into one async call. Each guide page still owns its narration
and next-step CTA; this helper only fetches the right-sized explanation for the current
exposure count and sets the experience-token cookie if needed.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_envelope import (
    ObjectEnvelope,
    ObjectType,
    Pillar,
    Provenance,
    TemporalValidity,
    Who,
)
from app.modules.context_engine.retrieval import retrieve_explanations, select_tapered_variant
from app.modules.ui_composer.tapering import get_tapering_context, set_experience_token_cookie


async def get_explanation_for_guide(
    request: Request,
    contract,
    pillar: Pillar,
    why: str,
    subject_tags: list[str],
    jurisdiction: str = "MN",
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """Return the contextual explanation and tapering context for a guide page.

    Args:
        request: the FastAPI request.
        contract: a FunctionGroupContract (has `module` and `group_name`).
        pillar: the pillar this guide belongs to.
        why: one-sentence description of what the guide does.
        subject_tags: tags used for Layer 2 explanation retrieval.
        jurisdiction: defaults to "MN".
        db: optional async DB session.

    Returns:
        {
            "explanation": str | None,
            "tapering_ctx": {
                "intensity_level": str,
                "exposure_count": int,
                "experience_token": ExperienceToken,
                "experience_token_saved_to_cloud": bool,
            },
        }
    """
    object_type = f"{contract.module}:{contract.group_name}"
    tapering_ctx = await get_tapering_context(request, object_type, db)

    explanation_obj = ObjectEnvelope(
        object_id=f"guide:{object_type}",
        object_type=ObjectType.PAGE_ZONE,
        pillar=pillar,
        who=Who.TENANT,
        why=why,
        provenance=Provenance.SYSTEM_COMPUTED,
        temporal_validity=TemporalValidity.STATIC,
        subject_tags=subject_tags,
    )
    explanation_results = await retrieve_explanations(
        explanation_obj, jurisdiction=jurisdiction, limit=1
    )

    explanation = None
    if explanation_results:
        explanation = select_tapered_variant(
            explanation_results[0], tapering_ctx["exposure_count"]
        )

    return {
        "explanation": explanation,
        "tapering_ctx": tapering_ctx,
    }


__all__ = [
    "get_explanation_for_guide",
    "get_tapering_context",
    "set_experience_token_cookie",
]
