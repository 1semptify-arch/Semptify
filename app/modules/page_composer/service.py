"""Page Composer service — assembles unified page view from multiple sources.

Pulls from:
- Context Engine cache (verified facts)
- Context Engine stories (published tenant stories)
- Case Builder (user's own case data, if any)

All sections are optional — the composer returns what exists. No hallucination:
every fact includes a source URL from the Context Engine.
"""

import logging
from typing import Any, Dict, List, Optional

from app.modules.context_engine import cache as ctx_cache
from app.modules.context_engine import stories as ctx_stories
from app.modules.context_engine.taxonomy import ALL_SUBJECTS, SUBJECT_LABELS

logger = logging.getLogger(__name__)


async def compose_page(
    subject: str,
    jurisdiction: str = "MN",
    user_id: Optional[str] = None,
    fact_limit: int = 10,
    story_limit: int = 5,
) -> Dict[str, Any]:
    """Compose a unified page view for a subject + jurisdiction.

    Returns a dict with:
        - subject: the subject key
        - label: human-readable label
        - jurisdiction: jurisdiction code
        - facts: list of verified facts (each with source_url)
        - stories: list of published tenant stories
        - case: user's case data for this subject (if any)
        - sections: ordered list of section keys present in the response
    """
    if subject not in ALL_SUBJECTS:
        raise ValueError(f"Unknown subject: {subject}. Valid: {', '.join(ALL_SUBJECTS)}")

    # Pull facts + stories in parallel
    facts, stories = await _gather_context(subject, jurisdiction, fact_limit, story_limit)

    # Pull user's case data (optional, best-effort)
    case = await _gather_user_case(subject, user_id) if user_id else None

    sections: List[str] = []
    if facts:
        sections.append("facts")
    if stories:
        sections.append("stories")
    if case:
        sections.append("case")

    return {
        "subject": subject,
        "label": SUBJECT_LABELS.get(subject, subject),
        "jurisdiction": jurisdiction,
        "facts": _serialize_facts(facts),
        "stories": _serialize_stories(stories),
        "case": case,
        "sections": sections,
    }


async def _gather_context(
    subject: str,
    jurisdiction: str,
    fact_limit: int,
    story_limit: int,
):
    """Fetch facts and stories in parallel."""
    import asyncio

    facts_task = ctx_cache.get_facts(subject, jurisdiction, limit=fact_limit)
    stories_task = ctx_stories.get_published_stories(
        subject=subject, jurisdiction=jurisdiction, limit=story_limit
    )
    return await asyncio.gather(facts_task, stories_task)


async def _gather_user_case(subject: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Pull the user's case data for this subject, if any.

    Best-effort: returns None if case_builder is unavailable or no case exists.
    """
    try:
        from app.modules.case_builder import case_builder as cb_module
        if hasattr(cb_module, "get_cases_for_user"):
            cases = await cb_module.get_cases_for_user(user_id, subject=subject)
            if cases:
                return {
                    "count": len(cases),
                    "items": [
                        {
                            "id": getattr(c, "id", None),
                            "title": getattr(c, "title", None),
                            "status": getattr(c, "status", None),
                            "updated_at": getattr(c, "updated_at", None),
                        }
                        for c in cases
                    ],
                }
    except Exception as e:
        logger.debug("Case builder not available for page composer: %s", e)
    return None


def _serialize_facts(facts) -> List[Dict[str, Any]]:
    return [
        {
            "id": f.id,
            "claim": f.claim,
            "source_url": f.source_url,
            "source_name": f.source_name,
            "citation": f.citation,
            "is_verified": f.is_verified,
            "verified_at": f.verified_at.isoformat() if f.verified_at else None,
        }
        for f in facts
    ]


def _serialize_stories(stories) -> List[Dict[str, Any]]:
    return [
        {
            "id": s.id,
            "title": s.title,
            "body": s.body,
            "outcome": s.outcome,
            "jurisdiction": s.jurisdiction,
            "subject": s.subject,
            "moderated_at": s.moderated_at.isoformat() if s.moderated_at else None,
        }
        for s in stories
    ]
