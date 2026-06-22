"""Context Engine gatherer — fetches fresh facts from external sources.

Repurposes free_api_pack.py fetchers. Writes results into the context_facts cache.
Every fact must have a source URL — no hallucination.
"""

import logging
from typing import List, Optional

from app.modules.context_engine.cache import upsert_fact
from app.modules.context_engine.models import ContextFact
from app.modules.context_engine.taxonomy import Subject, SUBJECT_TO_FREE_API

logger = logging.getLogger(__name__)


async def gather_for_subject(
    subject: str,
    jurisdiction: str = "MN",
    query: Optional[str] = None,
) -> List[ContextFact]:
    """Gather fresh facts for a subject from external sources.

    Returns list of newly cached facts. No hallucination — every fact has a source URL.
    """
    api_name = SUBJECT_TO_FREE_API.get(subject)
    if not api_name:
        logger.info("No external gatherer for subject=%s — guidance only", subject)
        return []

    try:
        from app.modules import free_api_pack
    except ImportError:
        logger.warning("free_api_pack not available — cannot gather for %s", subject)
        return []

    registry = free_api_pack.APIRegistry()
    facts: List[ContextFact] = []

    try:
        if api_name == "mn_statute_search":
            api = registry.statutes
            results = await api.search_statutes(query or subject, jurisdiction=jurisdiction)
            for r in (results or [])[:5]:
                if not r.get("url") or not r.get("citation"):
                    continue
                facts.append(upsert_fact(
                    subject=subject,
                    jurisdiction=jurisdiction,
                    claim=r.get("summary") or r.get("title") or f"Statute: {r.get('citation')}",
                    source_url=r["url"],
                    source_name="MN Revisor of Statutes",
                    citation=r.get("citation"),
                ))

        elif api_name == "epa_echo_lookup":
            api = registry.violations
            results = await api.search_violations(query or "", jurisdiction=jurisdiction)
            for r in (results or [])[:3]:
                if not r.get("url"):
                    continue
                facts.append(upsert_fact(
                    subject=subject,
                    jurisdiction=jurisdiction,
                    claim=r.get("summary") or f"Violation record: {r.get('facility', 'Unknown')}",
                    source_url=r["url"],
                    source_name="EPA ECHO",
                    citation=r.get("case_number"),
                ))

        elif api_name == "court_listener_search":
            api = registry.court
            results = await api.search_cases(query or subject)
            for r in (results or [])[:3]:
                if not r.get("url"):
                    continue
                facts.append(upsert_fact(
                    subject=subject,
                    jurisdiction=jurisdiction,
                    claim=r.get("summary") or f"Case: {r.get('case_name', 'Unknown')}",
                    source_url=r["url"],
                    source_name="CourtListener",
                    citation=r.get("docket_number"),
                ))

        elif api_name == "hud_fair_housing":
            api = registry.statutes  # closest analog; HUD fair housing content via statutes path
            results = await api.search_statutes("fair housing", jurisdiction=jurisdiction)
            for r in (results or [])[:3]:
                if not r.get("url"):
                    continue
                facts.append(upsert_fact(
                    subject=subject,
                    jurisdiction=jurisdiction,
                    claim=r.get("summary") or "Fair housing guidance",
                    source_url=r["url"],
                    source_name="HUD / Fair Housing",
                    citation=r.get("citation"),
                ))

        elif api_name == "mncourts_search":
            api = registry.court
            results = await api.search_cases(query or "eviction")
            for r in (results or [])[:3]:
                if not r.get("url"):
                    continue
                facts.append(upsert_fact(
                    subject=subject,
                    jurisdiction=jurisdiction,
                    claim=r.get("summary") or f"Court record: {r.get('case_name', 'Unknown')}",
                    source_url=r["url"],
                    source_name="MN Courts",
                    citation=r.get("docket_number"),
                ))

    except Exception as e:
        logger.warning("Gatherer for %s failed: %s", subject, e)

    return facts
