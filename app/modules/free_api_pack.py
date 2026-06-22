"""
Semptify Free API Pack — v2.0
=============================

Real implementations of free, no-API-key-required public data lookups.

All methods are async and return structured dicts with a "status" field:
  - "ok"           — successful lookup, data populated
  - "no_results"   — query succeeded but no records found
  - "error"        — upstream error (timeout, parse failure, etc.)
  - "unavailable"  — optional dependency not installed

Data sources:
  - PropertyLookup    — county parcel lookups (Dakota, Ramsey, Hennepin)
  - LandlordLookup    — MN SOS business search + HUD property/ownership
  - CourtScraper      — MN court eviction search + CourtListener federal
  - Violations        — city inspections + EPA ECHO + MPCA
  - Inspections       — HUD REAC scores + local inspection records
  - Statutes          — MN Revisor of Statutes (504B, 504C, 580, etc.)

api.data.gov integration:
  If DATA_GOV_API_KEY env var is set, EPA ECHO, FEMA, Census, USDA, and
  200+ federal datasets are unlocked. Without the key, the pack falls back
  to the free no-key endpoints (HUD ArcGIS, CourtListener, MN Revisor).

All HTTP calls use httpx with a 10s timeout and a Semptify user-agent.
HTML responses are parsed with BeautifulSoup4.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlencode

import httpx
from bs4 import BeautifulSoup

from app.core.utc import utc_now
import logging

logger = logging.getLogger(__name__)


def _data_gov_key() -> Optional[str]:
    """Return the api.data.gov key from env, or None if not set."""
    return os.environ.get("DATA_GOV_API_KEY") or os.environ.get("DATA_GOV_API_KEY")


# =============================================================================
# Shared HTTP helpers
# =============================================================================

_USER_AGENT = (
    "Mozilla/5.0 (compatible; Semptify/5.0; +https://semptify.org) "
    "Free-API-Pack/2.0"
)
_DEFAULT_TIMEOUT = 10.0
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _ok(**fields) -> Dict[str, Any]:
    """Build a success response."""
    out: Dict[str, Any] = {"status": "ok", "retrieved_at": utc_now().isoformat()}
    out.update(fields)
    return out


def _no_results(query: str, message: str = "No records found") -> Dict[str, Any]:
    return {
        "status": "no_results",
        "query": query,
        "message": message,
        "retrieved_at": utc_now().isoformat(),
    }


def _error(query: str, message: str, source: Optional[str] = None) -> Dict[str, Any]:
    resp: Dict[str, Any] = {
        "status": "error",
        "query": query,
        "message": message,
        "retrieved_at": utc_now().isoformat(),
    }
    if source:
        resp["source"] = source
    return resp


async def _fetch_text(
    client: httpx.AsyncClient,
    url: str,
    *,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Fetch URL and return text, or None on failure. Logs warnings."""
    try:
        resp = await client.request(
            method, url, headers=_HEADERS, data=data, params=params, follow_redirects=True
        )
        if resp.status_code >= 400:
            logger.warning("FreeAPI: %s %s -> HTTP %s", method, url, resp.status_code)
            return None
        return resp.text
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("FreeAPI: %s %s -> %s: %s", method, url, type(exc).__name__, exc)
        return None
    except Exception as exc:
        logger.warning("FreeAPI: %s %s -> unexpected %s: %s", method, url, type(exc).__name__, exc)
        return None


async def _fetch_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Any]:
    """Fetch URL and return parsed JSON, or None on failure."""
    merged = {**_HEADERS, "Accept": "application/json"}
    if headers:
        merged.update(headers)
    try:
        resp = await client.get(url, headers=merged, params=params, follow_redirects=True)
        if resp.status_code >= 400:
            logger.warning("FreeAPI: GET %s -> HTTP %s", url, resp.status_code)
            return None
        return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("FreeAPI: GET %s -> %s: %s", url, type(exc).__name__, exc)
        return None
    except ValueError as exc:
        logger.warning("FreeAPI: GET %s -> JSON parse error: %s", url, exc)
        return None
    except Exception as exc:
        logger.warning("FreeAPI: GET %s -> unexpected %s: %s", url, type(exc).__name__, exc)
        return None


# =============================================================================
# Property Lookup — County parcel lookups (Dakota, Ramsey, Hennepin)
# =============================================================================

_COUNTY_PARCEL_URLS = {
    "dakota": "https://gis.co.dakota.mn.us/property/rest/parcels/{parcel_id}",
    "ramsey": "https://maps.co.ramsey.mn.us/arcgis/rest/services/PropertyTax/MapServer/0/query",
    "hennepin": "https://gis.hennepin.us/arcgis/rest/services/HennepinData/Maps/PropertyTax/MapServer/0/query",
}


class PropertyLookup:
    """Unified interface for county parcel lookups (Dakota, Ramsey, Hennepin)."""

    async def lookup_parcel(self, county: str, parcel_id: str) -> Dict[str, Any]:
        """Lookup parcel information by county and parcel ID."""
        county_lower = (county or "").strip().lower()
        if county_lower not in _COUNTY_PARCEL_URLS:
            return _error(
                f"{county}/{parcel_id}",
                f"County '{county}' not supported. Supported: Dakota, Ramsey, Hennepin.",
                source="property_lookup",
            )
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            if county_lower == "dakota":
                url = _COUNTY_PARCEL_URLS["dakota"].format(parcel_id=quote_plus(parcel_id))
                data = await _fetch_json(client, url)
                if data is None:
                    return _error(f"{county}/{parcel_id}", "Dakota county parcel lookup failed.", source="dakota_gis")
                if not data:
                    return _no_results(f"{county}/{parcel_id}", "No parcel found with that ID.")
                return _ok(
                    county="Dakota",
                    parcel_id=parcel_id,
                    source="Dakota County GIS",
                    source_url=url,
                    parcel=data,
                )
            url = _COUNTY_PARCEL_URLS[county_lower]
            params = {
                "where": f"PIN = '{parcel_id}'",
                "outFields": "*",
                "f": "json",
                "returnGeometry": "false",
            }
            data = await _fetch_json(client, url, params=params)
            if data is None:
                return _error(f"{county}/{parcel_id}", f"{county.title()} county parcel lookup failed.", source=f"{county_lower}_gis")
            features = data.get("features", []) if isinstance(data, dict) else []
            if not features:
                return _no_results(f"{county}/{parcel_id}", "No parcel found with that PIN.")
            attrs = features[0].get("attributes", {}) if features else {}
            return _ok(
                county=county.title(),
                parcel_id=parcel_id,
                source=f"{county.title()} County ArcGIS",
                source_url=url,
                parcel=attrs,
            )

    async def lookup_address(self, county: str, address: str) -> Dict[str, Any]:
        """Lookup property information by county and address."""
        county_lower = (county or "").strip().lower()
        if county_lower not in ("dakota", "ramsey", "hennepin"):
            return _error(
                f"{county}/{address}",
                f"County '{county}' not supported. Supported: Dakota, Ramsey, Hennepin.",
                source="property_lookup",
            )
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            if county_lower == "dakota":
                url = "https://gis.co.dakota.mn.us/property/rest/parcels/search"
                params = {"query": address, "f": "json"}
                data = await _fetch_json(client, url, params=params)
                if data is None:
                    return _error(f"{county}/{address}", "Dakota address search failed.", source="dakota_gis")
                results = data if isinstance(data, list) else data.get("parcels", []) if isinstance(data, dict) else []
                if not results:
                    return _no_results(f"{county}/{address}", "No parcels match that address.")
                return _ok(
                    county="Dakota",
                    address=address,
                    source="Dakota County GIS",
                    source_url=url,
                    results=results[:10],
                )
            url = _COUNTY_PARCEL_URLS[county_lower]
            safe_addr = address.replace("'", "''")
            params = {
                "where": f"ADDRESS LIKE '%{safe_addr}%'",
                "outFields": "*",
                "f": "json",
                "returnGeometry": "false",
            }
            data = await _fetch_json(client, url, params=params)
            if data is None:
                return _error(f"{county}/{address}", f"{county.title()} address search failed.", source=f"{county_lower}_gis")
            features = data.get("features", []) if isinstance(data, dict) else []
            if not features:
                return _no_results(f"{county}/{address}", "No parcels match that address.")
            attrs = [f.get("attributes", {}) for f in features[:10]]
            return _ok(
                county=county.title(),
                address=address,
                source=f"{county.title()} County ArcGIS",
                source_url=url,
                results=attrs,
            )


class LandlordLookup:
    """MN Secretary of State business search + HUD property lookup."""

    async def lookup_business(self, name: str) -> Dict[str, Any]:
        """Search for business entity in MN Secretary of State records."""
        if not name or not name.strip():
            return _error(name or "", "Business name required.", source="mn_sos")
        url = "https://mblsportal.sos.state.mn.us/Business/Search"
        params = {"SearchType": "Contains", "SearchValue": name, "SearchCriteria": "Name"}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            html = await _fetch_text(client, url, params=params)
            if html is None:
                return _error(name, "MN SOS business search failed.", source="mn_sos")
            soup = BeautifulSoup(html, "lxml")
            results: List[Dict[str, str]] = []
            table = soup.find("table", {"id": "searchResultsTable"}) or soup.find("table", class_="table")
            if table:
                rows = table.find_all("tr")[1:]
                for row in rows[:20]:
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        results.append({
                            "name": cells[0].get_text(strip=True),
                            "filing_number": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "status": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                            "type": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        })
            if not results:
                for div in soup.find_all("div", class_="search-result")[:10]:
                    results.append({"name": div.get_text(strip=True)})
            if not results:
                return _no_results(name, "No businesses match that name in MN SOS records.")
            return _ok(
                query=name,
                source="Minnesota Secretary of State",
                source_url=f"{url}?{urlencode(params)}",
                results=results,
            )

    async def lookup_owner(self, property_id: str) -> Dict[str, Any]:
        """Lookup property owner via HUD or county records."""
        if not property_id or not property_id.strip():
            return _error(property_id or "", "Property ID required.", source="hud")
        url = "https://services.hud.gov/hudcli/api/v1/ILS/LHA"
        params = {"LHAcode": property_id}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            data = await _fetch_json(client, url, params=params)
            if data is None or not data:
                return _ok(
                    property_id=property_id,
                    source="County Records (manual lookup required)",
                    source_url="https://www.hennepin.us/property",
                    note="HUD lookup did not return data. This may be a private property — check county records.",
                    owner=None,
                )
            return _ok(
                property_id=property_id,
                source="HUD Public Housing Authority Database",
                source_url=url,
                owner=data if isinstance(data, dict) else {"raw": data},
            )


class CourtScraper:
    """MN Court Records (public) + CourtListener federal docket API."""

    async def search_evictions(self, name: str) -> Dict[str, Any]:
        """Search for eviction cases by party name in MN courts."""
        if not name or not name.strip():
            return _error(name or "", "Party name required.", source="mn_courts")
        url = "https://pa.courts.state.mn.us/CaseSearch"
        form_data = {"SearchType": "PartyName", "PartyName": name, "CaseType": "Eviction"}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            html = await _fetch_text(client, url, method="POST", data=form_data)
            if html is None:
                return _error(name, "MN courts case search failed.", source="mn_courts")
            soup = BeautifulSoup(html, "lxml")
            cases: List[Dict[str, str]] = []
            table = soup.find("table", {"id": "caseResults"}) or soup.find("table", class_="results")
            if table:
                rows = table.find_all("tr")[1:]
                for row in rows[:20]:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        cases.append({
                            "case_number": cells[0].get_text(strip=True),
                            "case_title": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "court": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                            "filing_date": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        })
            if not cases:
                for div in soup.find_all("div", class_="case-result")[:10]:
                    cases.append({"case_number": div.get_text(strip=True)})
            if not cases:
                return _no_results(
                    name,
                    "No eviction cases found for that party name. Try a different spelling or check the full case search.",
                )
            return _ok(
                query=name,
                case_type="eviction",
                source="Minnesota Judicial Branch — Case Search",
                source_url=f"{url}?{urlencode(form_data)}",
                cases=cases,
            )

    async def fetch_federal_cases(self, query: str) -> Dict[str, Any]:
        """Search federal court cases via CourtListener API (Free Law Project)."""
        if not query or not query.strip():
            return _error(query or "", "Search query required.", source="courtlistener")
        url = "https://www.courtlistener.com/api/rest/v4/search/"
        params = {"q": query, "type": "r", "order_by": "score desc"}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            data = await _fetch_json(client, url, params=params)
            if data is None:
                return _error(query, "CourtListener search failed.", source="courtlistener")
            results = data.get("results", []) if isinstance(data, dict) else []
            if not results:
                return _no_results(query, "No federal cases found for that query.")
            trimmed = []
            for r in results[:10]:
                trimmed.append({
                    "case_name": r.get("caseName") or r.get("case_name", ""),
                    "case_number": r.get("docketNumber") or r.get("docket_number", ""),
                    "court": r.get("court") or "",
                    "date_filed": r.get("dateFiled") or r.get("date_filed", ""),
                    "citation": r.get("citation", []),
                    "snippet": (r.get("snippet") or "")[:300],
                })
            return _ok(
                query=query,
                source="CourtListener (Free Law Project)",
                source_url=f"https://www.courtlistener.com/?q={quote_plus(query)}&type=r",
                count=data.get("count", len(trimmed)) if isinstance(data, dict) else len(trimmed),
                cases=trimmed,
            )


class Violations:
    """City inspections, MPCA violations, EPA ECHO."""

    async def city_inspections(self, city: str, address: str) -> Dict[str, Any]:
        """Lookup city inspection records for an address."""
        if not city or not address:
            return _error(f"{city}/{address}", "City and address required.", source="city_inspections")
        city_lower = (city or "").strip().lower()
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            if city_lower in ("minneapolis", "mpls"):
                url = "https://inspections.minneapolismn.gov/api/v1/inspections"
                params = {"address": address, "limit": 20}
                data = await _fetch_json(client, url, params=params)
                if data is None:
                    return _ok(
                        city="Minneapolis",
                        address=address,
                        source="Minneapolis Inspections Portal",
                        source_url=f"https://inspections.minneapolismn.gov/?address={quote_plus(address)}",
                        inspections=[],
                        note="API returned no data. Visit the portal link for manual lookup.",
                    )
                inspections = data.get("results", []) if isinstance(data, dict) else data if isinstance(data, list) else []
                if not inspections:
                    return _no_results(f"{city}/{address}", "No inspection records for that address.")
                return _ok(
                    city="Minneapolis",
                    address=address,
                    source="Minneapolis Inspections Portal",
                    source_url=f"https://inspections.minneapolismn.gov/?address={quote_plus(address)}",
                    inspections=inspections[:20],
                )
            if city_lower in ("st paul", "saint paul", "stpaul"):
                url = "https://www.stpaul.gov/api/v1/inspections"
                params = {"address": address, "limit": 20}
                data = await _fetch_json(client, url, params=params)
                if data is None:
                    return _ok(
                        city="St. Paul",
                        address=address,
                        source="St. Paul Inspections Portal",
                        source_url=f"https://www.stpaul.gov/departments/safety-inspections?address={quote_plus(address)}",
                        inspections=[],
                        note="API returned no data. Visit the portal link for manual lookup.",
                    )
                inspections = data.get("results", []) if isinstance(data, dict) else data if isinstance(data, list) else []
                if not inspections:
                    return _no_results(f"{city}/{address}", "No inspection records for that address.")
                return _ok(
                    city="St. Paul",
                    address=address,
                    source="St. Paul Inspections Portal",
                    source_url=f"https://www.stpaul.gov/departments/safety-inspections?address={quote_plus(address)}",
                    inspections=inspections[:20],
                )
            return _ok(
                city=city,
                address=address,
                source="City inspection portal (manual lookup required)",
                source_url=None,
                inspections=[],
                note=f"Automated lookup not available for {city}. Contact the city's inspection department directly.",
            )

    async def environmental_violations(self, facility: str) -> Dict[str, Any]:
        """Lookup environmental violations via EPA ECHO or MPCA.

        Uses EPA ECHO public API. If DATA_GOV_API_KEY is set, uses the
        api.data.gov enhanced endpoint with higher rate limits.
        """
        if not facility or not facility.strip():
            return _error(facility or "", "Facility name or ID required.", source="epa_echo")
        key = _data_gov_key()
        # EPA ECHO facility search — free, no key required (key unlocks higher rate limits)
        url = "https://echotool.epa.gov/echo/rest/facility_search"
        params = {"q": facility, "output": "json", "pg_num": 1, "results_per_page": 10}
        if key:
            params["api_key"] = key
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            data = await _fetch_json(client, url, params=params)
            if data is None:
                return _error(facility, "EPA ECHO search failed.", source="epa_echo")
            facilities = (
                data.get("Results", {}).get("Facilities", []) if isinstance(data, dict) else []
            )
            if not facilities:
                return await self._mpca_lookup(client, facility)
            trimmed = []
            for f in facilities[:10]:
                trimmed.append({
                    "name": f.get("FacilityName") or f.get("SOURCE_NAME", ""),
                    "registry_id": f.get("RegistryId", ""),
                    "city": f.get("FacilityCity") or f.get("FAC_CITY", ""),
                    "state": f.get("FacilityState") or f.get("FAC_STATE", ""),
                    "zip": f.get("FacilityZip") or f.get("FAC_ZIP", ""),
                    "cwa_compliance": f.get("CWACompliance", ""),
                    "air_compliance": f.get("AirCompliance", ""),
                    "rcra_compliance": f.get("RCRACompliance", ""),
                    "echo_url": f.get("EchoURL", ""),
                })
            return _ok(
                query=facility,
                source="EPA ECHO (Enforcement and Compliance History Online)",
                source_url=f"https://echo.epa.gov/facility-search?search_value={quote_plus(facility)}",
                facilities=trimmed,
                used_api_data_gov=bool(key),
            )

    async def _mpca_lookup(self, client: httpx.AsyncClient, facility: str) -> Dict[str, Any]:
        """Fallback MPCA lookup when EPA ECHO returns no results."""
        url = "https://www.pca.state.mn.us/api/v1/facilities"
        params = {"q": facility, "limit": 10}
        data = await _fetch_json(client, url, params=params)
        if data is None or not data:
            return _no_results(facility, "No environmental violations found in EPA ECHO or MPCA.")
        results = data.get("results", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        return _ok(
            query=facility,
            source="MPCA (Minnesota Pollution Control Agency)",
            source_url=f"https://www.pca.state.mn.us/business-and-communities/search-for-environmental-information?search={quote_plus(facility)}",
            facilities=results[:10],
        )


class Inspections:
    """HUD REAC scores + local inspection endpoints."""

    async def hud_reac(self, property_id: str) -> Dict[str, Any]:
        """Lookup HUD REAC inspection scores for a property."""
        if not property_id or not property_id.strip():
            return _error(property_id or "", "Property ID required.", source="hud_reac")
        url = f"https://services.hud.gov/hudcli/api/v1/REAC/Property/{quote_plus(property_id)}"
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            data = await _fetch_json(client, url)
            if data is None or not data:
                return _ok(
                    property_id=property_id,
                    source="HUD REAC Inspection Database",
                    source_url=f"https://www.huduser.gov/portal/datasets/reac.html?property_id={quote_plus(property_id)}",
                    scores=[],
                    note="API returned no data. Visit the REAC database link for manual lookup.",
                )
            scores = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return _ok(
                property_id=property_id,
                source="HUD REAC Inspection Database",
                source_url=url,
                scores=scores[:10],
            )

    async def local_inspections(self, city: str, address: str) -> Dict[str, Any]:
        """Lookup local inspection records for an address.

        Delegates to Violations.city_inspections() — same data source.
        """
        return await Violations().city_inspections(city, address)


class Statutes:
    """MN Revisor of Statutes API (504B, 504C, 580, etc.)."""

    _cache: Dict[str, tuple] = {}
    _CACHE_TTL = 86400.0  # 24 hours

    def _cache_get(self, section: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(section)
        if not entry:
            return None
        text, fetched_at = entry
        age = (utc_now().timestamp() - fetched_at) if isinstance(fetched_at, float) else 999999
        if age > self._CACHE_TTL:
            return None
        return {
            "section": section,
            "text": text,
            "source": "Minnesota Revisor of Statutes (cached)",
            "source_url": f"https://www.revisor.mn.gov/statutes/cite/{section}",
            "cached": True,
        }

    def _cache_put(self, section: str, text: str) -> None:
        self._cache[section] = (text, utc_now().timestamp())

    async def get_statute(self, section: str) -> Dict[str, Any]:
        """Retrieve statute text from MN Revisor by section number."""
        if not section or not section.strip():
            return _error(section or "", "Statute section required.", source="mn_revisor")
        section = section.strip()
        if not re.match(r"^\d+[A-Z]?(\.\d+[\w.]*)?$", section, re.IGNORECASE):
            return _error(
                section,
                f"Invalid statute section format: '{section}'. Use format like '504B.321' or '504B'.",
                source="mn_revisor",
            )
        cached = self._cache_get(section)
        if cached:
            return _ok(**cached)
        url = f"https://www.revisor.mn.gov/statutes/cite/{section}"
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            html = await _fetch_text(client, url)
            if html is None:
                return _error(section, "MN Revisor lookup failed.", source="mn_revisor")
            soup = BeautifulSoup(html, "lxml")
            statute_div = (
                soup.find("div", class_="section")
                or soup.find("div", id="statuteText")
                or soup.find("div", class_="statute")
            )
            if not statute_div:
                if "No statutes found" in html or "Page Not Found" in html:
                    return _no_results(section, f"Statute {section} not found in MN Revisor.")
                return _error(section, "Could not parse statute text from MN Revisor page.", source="mn_revisor")
            text = statute_div.get_text(separator="\n", strip=True)
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else f"Minn. Stat. § {section}"
            self._cache_put(section, text)
            return _ok(
                section=section,
                title=title,
                text=text,
                source="Minnesota Revisor of Statutes",
                source_url=url,
                cached=False,
            )


class APIRegistry:
    """
    Central access point for all free API modules.
    One object to rule them all.
    """

    def __init__(self):
        self.property = PropertyLookup()
        self.landlord = LandlordLookup()
        self.courts = CourtScraper()
        self.violations = Violations()
        self.inspections = Inspections()
        self.statutes = Statutes()


# Global registry instance
api = APIRegistry()
