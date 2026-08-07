# app/crawlers/courtlistener.py
from datetime import datetime

import httpx

COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v3/search/"
COURTLISTENER_BASE = "https://www.courtlistener.com"


async def fetch_federal_cases_for_attorney(name: str) -> list[dict]:
    """
    Fetch federal cases for an attorney from CourtListener API.

    CourtListener provides federal court cases, opinions, and RECAP docket entries.
    """
    params = {
        "q": name,
        "type": "opinion",  # Search opinions by default
        "page_size": 20,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(COURTLISTENER_API, params=params, follow_redirects=True)
        data = resp.json()

        results = data.get("results", [])
        normalized = []

        for result in results:
            try:
                normalized_case = normalize_courtlistener_case(result)
                if normalized_case:
                    normalized.append(normalized_case)
            except Exception:
                continue

        return normalized


def normalize_courtlistener_case(raw: dict) -> dict | None:
    """
    Normalize a CourtListener case result to internal schema.

    CourtListener API response structure:
    - id: CourtListener internal ID
    - case_name: Case title
    - court: Court object with id and name
    - date_filed: Filing date
    - date_terminated: Termination date
    - docket_number: Docket/case number
    - citation: Citation string
    - status: Case status
    """
    if not raw:
        return None

    # Extract court information
    court_info = raw.get("court", {})
    court_name = court_info.get("full_name", court_info.get("short_name", "")) if court_info else ""
    court_id = court_info.get("id") if court_info else None

    # Extract dates
    date_filed = raw.get("date_filed")
    date_terminated = raw.get("date_terminated")

    # Parse dates if present
    filing_date = None
    if date_filed:
        try:
            filing_date = datetime.fromisoformat(date_filed.replace("Z", "+00:00")).date()
        except Exception:
            pass

    # Extract docket/case number
    docket_number = raw.get("docket_number", "")
    docket_id = raw.get("docket")

    # Extract citation
    citation = raw.get("citation", "")
    federal_cite_one = raw.get("federal_cite_one", "")

    # Extract case name/title
    case_name = raw.get("case_name", "")
    case_name_full = raw.get("case_name_full", "")

    # Extract status
    status = raw.get("status", "")

    # Build normalized case
    normalized = {
        "courtlistener_id": raw.get("id"),
        "case_number": docket_number,
        "case_title": case_name_full or case_name,
        "court": court_name,
        "court_id": court_id,
        "courtlistener_court_id": court_id,
        "case_type": "federal",
        "filing_date": filing_date,
        "filing_date_str": date_filed,
        "termination_date": date_terminated,
        "status": status,
        "citation": citation or federal_cite_one,
        "docket_id": docket_id,
        "source": "courtlistener",
        "url": f"{COURTLISTENER_BASE}/docket/{docket_id}/" if docket_id else None,
    }

    # Extract opinion information if available
    opinion = raw.get("opinion", {})
    if opinion:
        normalized["opinion_id"] = opinion.get("id")
        normalized["opinion_text"] = opinion.get("text")
        normalized["opinion_type"] = opinion.get("type")

    # Extract panel information if available
    panel = raw.get("panel", [])
    if panel:
        normalized["panel"] = [p.get("name") for p in panel if p.get("name")]

    return normalized


async def fetch_courtlistener_docket(docket_id: int) -> dict | None:
    """
    Fetch detailed docket information from CourtListener.
    """
    docket_url = f"{COURTLISTENER_API}dockets/{docket_id}/"

    async with httpx.AsyncClient() as client:
        resp = await client.get(docket_url, follow_redirects=True)
        if resp.status_code != 200:
            return None

        data = resp.json()

        return {
            "courtlistener_id": data.get("id"),
            "docket_number": data.get("docket_number"),
            "court": data.get("court", {}).get("full_name", ""),
            "case_name": data.get("case_name"),
            "case_name_full": data.get("case_name_full"),
            "date_filed": data.get("date_filed"),
            "date_terminated": data.get("date_terminated"),
            "status": data.get("status"),
            "source": "courtlistener",
        }
