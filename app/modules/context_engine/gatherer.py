"""Context Engine gatherer — fetches fresh facts from external sources.

Repurposes free_api_pack.py fetchers. Writes results into the context_facts cache.
Every fact must have a source URL — no hallucination.
"""

import logging
import re

from app.modules.context_engine.cache import upsert_fact
from app.modules.context_engine.models import ContextFact
from app.modules.context_engine.taxonomy import SUBJECT_TO_FREE_API, Subject

logger = logging.getLogger(__name__)


DEFAULT_SUBJECT_STATUTES = {
    Subject.EVICTION.value: "504B",
    Subject.REPAIR.value: "504B.425",
    Subject.HABITABILITY.value: "504B.221",
    Subject.SAFETY.value: "504B.185",
    Subject.LEASE.value: "504B.117",
    Subject.RENT.value: "504B.441",
    Subject.DEPOSIT.value: "504B.178",
    Subject.RETALIATION.value: "504B.441",
    Subject.DISCRIMINATION.value: "363.03",
    Subject.SMALL_CLAIMS.value: "491A",
    Subject.COURT_PREP.value: "504B.285",
}


def _resolve_statute_section(subject: str, query: str | None) -> str | None:
    """Return a MN statute section usable by Statutes.get_statute."""
    if query and re.match(r"^\d+[A-Z]?(\.\d+[\w.]*)?$", query.strip(), re.IGNORECASE):
        return query.strip()
    return DEFAULT_SUBJECT_STATUTES.get(subject)


async def gather_for_subject(
    subject: str,
    jurisdiction: str = "MN",
    query: str | None = None,
) -> list[ContextFact]:
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
    facts: list[ContextFact] = []

    try:
        if api_name == "mn_statute_search":
            section = _resolve_statute_section(subject, query)
            if not section:
                logger.info("No statute section for subject=%s", subject)
                return facts
            resp = await registry.statutes.get_statute(section)
            if resp.get("status") == "ok":
                source_url = resp.get("source_url", "")
                if not source_url:
                    return facts
                facts.append(
                    await upsert_fact(
                        subject=subject,
                        jurisdiction=jurisdiction,
                        claim=resp.get("title") or f"Minn. Stat. § {section}",
                        source_url=source_url,
                        source_name="MN Revisor of Statutes",
                        citation=f"Minn. Stat. § {section}",
                    )
                )

        elif api_name == "epa_echo_lookup":
            resp = await registry.violations.environmental_violations(query or "")
            source_url = resp.get("source_url", "")
            if resp.get("status") == "ok" and source_url:
                for f in resp.get("facilities", [])[:3]:
                    name = f.get("name") or f.get("FacilityName") or "Unknown facility"
                    facts.append(
                        await upsert_fact(
                            subject=subject,
                            jurisdiction=jurisdiction,
                            claim=f"Environmental record: {name}",
                            source_url=source_url,
                            source_name="EPA ECHO",
                            citation=f.get("registry_id") or f.get("RegistryId"),
                        )
                    )

        elif api_name == "court_listener_search":
            resp = await registry.courts.fetch_federal_cases(query or subject)
            source_url = resp.get("source_url", "")
            if resp.get("status") == "ok" and source_url:
                for c in resp.get("cases", [])[:3]:
                    case_name = c.get("case_name") or "Unknown case"
                    snippet = c.get("snippet") or ""
                    claim = f"Federal case: {case_name}"
                    if snippet:
                        claim = f"{claim} — {snippet[:200]}"
                    facts.append(
                        await upsert_fact(
                            subject=subject,
                            jurisdiction=jurisdiction,
                            claim=claim,
                            source_url=source_url,
                            source_name="CourtListener",
                            citation=c.get("case_number") or c.get("docket_number"),
                        )
                    )

        elif api_name == "hud_fair_housing":
            resp = await registry.courts.fetch_federal_cases(query or "fair housing")
            source_url = resp.get("source_url", "")
            if resp.get("status") == "ok" and source_url:
                for c in resp.get("cases", [])[:3]:
                    case_name = c.get("case_name") or "Unknown case"
                    snippet = c.get("snippet") or ""
                    claim = f"Fair housing case: {case_name}"
                    if snippet:
                        claim = f"{claim} — {snippet[:200]}"
                    facts.append(
                        await upsert_fact(
                            subject=subject,
                            jurisdiction=jurisdiction,
                            claim=claim,
                            source_url=source_url,
                            source_name="CourtListener / Fair Housing",
                            citation=c.get("case_number") or c.get("docket_number"),
                        )
                    )

        elif api_name == "mncourts_search":
            resp = await registry.courts.search_evictions(query or "eviction")
            source_url = resp.get("source_url", "")
            if resp.get("status") == "ok" and source_url:
                for c in resp.get("cases", [])[:3]:
                    case_name = c.get("case_name") or "Unknown case"
                    facts.append(
                        await upsert_fact(
                            subject=subject,
                            jurisdiction=jurisdiction,
                            claim=f"Court record: {case_name}",
                            source_url=source_url,
                            source_name="MN Courts",
                            citation=c.get("docket_number") or c.get("case_number"),
                        )
                    )

    except Exception as e:
        logger.warning("Gatherer for %s failed: %s", subject, e)

    return facts
