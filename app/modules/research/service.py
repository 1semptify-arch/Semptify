"""
Research Module Service
=======================

Collects landlord/property data tied to a parcel/lot: emergency calls,
news, background on landlord/entity, taxes, sales, liens, financials,
and insurance broker info.

Multilingual-ready (labels), checkpointing, and ZIP bundling included.
"""

import os
import io
import json
import logging
import asyncio
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, quote

from app.core.id_gen import make_id
from app.core.utc import utc_now
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIG (env-driven for portability)
# =============================================================================
CFG = {
    # County Assessor — Hennepin County ArcGIS REST (free, no key)
    "ASSESSOR_BASE": os.getenv("ASSESSOR_BASE", "https://gis.hennepin.us/arcgis/rest/services/Property/PropertyData/MapServer/0"),
    # County Recorder — NO FREE API (web scraping or honest status)
    "RECORDER_BASE": os.getenv("RECORDER_BASE", "https://www.hennepin.us/recorder"),
    # UCC — MN SOS (no free API, web scraping)
    "RECORDER_UCC_BASE": os.getenv("RECORDER_UCC_BASE", "https://mblsportal.sos.state.mn.us"),
    # Public safety/dispatch — Minneapolis Open Data (free, no key)
    "DISPATCH_BASE": os.getenv("DISPATCH_BASE", "https://opendata.minneapolismn.us/api/views/6e3i-8xqa/rows.json"),
    # News aggregator — NewsAPI free tier + Google News RSS fallback
    "NEWS_BASE": os.getenv("NEWS_BASE", "https://newsapi.org/v2"),
    "NEWS_API_KEY": os.getenv("NEWS_API_KEY", ""),
    # Corporate registry (Secretary of State) — web scraping, no free API
    "SOS_BASE": os.getenv("SOS_BASE", "https://mblsportal.sos.state.mn.us/Business/Search"),
    # Bankruptcy — CourtListener (free with token)
    "BANKRUPTCY_BASE": os.getenv("BANKRUPTCY_BASE", "https://www.courtlistener.com/api/rest/v3"),
    # Insurance — NO FREE API (web-only lookup)
    "INSURANCE_BASE": os.getenv("INSURANCE_BASE", "https://mn.gov/commerce/insurance"),
    # Timeouts and retries
    "HTTP_TIMEOUT": float(os.getenv("HTTP_TIMEOUT", "12.0")),
    "HTTP_RETRIES": int(os.getenv("HTTP_RETRIES", "2")),
}


# =============================================================================
# DATA CLASSES
# =============================================================================
@dataclass
class FraudFlag:
    """A potential fraud indicator"""
    flag_type: str
    detail: str
    severity: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.flag_type,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass
class LandlordProfile:
    """Complete landlord/property research profile"""
    property_id: str
    owner_name: Optional[str]
    site_address: Optional[str]
    mailing_address: Optional[str]
    taxes: Dict[str, Any] = field(default_factory=dict)
    assessed: Dict[str, Any] = field(default_factory=dict)
    legal_description: Optional[str] = None
    deeds: List[Dict[str, Any]] = field(default_factory=list)
    liens: List[Dict[str, Any]] = field(default_factory=list)
    ucc_filings: List[Dict[str, Any]] = field(default_factory=list)
    news_mentions: List[Dict[str, Any]] = field(default_factory=list)
    emergency_calls: List[Dict[str, Any]] = field(default_factory=list)
    bankruptcy_cases: List[Dict[str, Any]] = field(default_factory=list)
    insurance_brokers: List[Dict[str, Any]] = field(default_factory=list)
    insurance_policies: List[Dict[str, Any]] = field(default_factory=list)
    entity_info: Dict[str, Any] = field(default_factory=dict)
    fraud_flags: List[FraudFlag] = field(default_factory=list)
    sources: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: utc_now())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "owner_name": self.owner_name,
            "site_address": self.site_address,
            "mailing_address": self.mailing_address,
            "taxes": self.taxes,
            "assessed": self.assessed,
            "legal_description": self.legal_description,
            "deeds": self.deeds,
            "liens": self.liens,
            "ucc_filings": self.ucc_filings,
            "news_mentions": self.news_mentions,
            "emergency_calls": self.emergency_calls,
            "bankruptcy_cases": self.bankruptcy_cases,
            "insurance": {
                "brokers": self.insurance_brokers,
                "policies": self.insurance_policies,
            },
            "entity_info": self.entity_info,
            "fraud_flags": [f.to_dict() for f in self.fraud_flags],
            "sources": self.sources,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ResearchCheckpoint:
    """Checkpoint for research progress"""
    id: str
    user_id: str
    property_id: str
    profile: LandlordProfile
    created_at: datetime = field(default_factory=lambda: utc_now())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "property_id": self.property_id,
            "profile": self.profile.to_dict(),
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# UTILITIES
# =============================================================================
def _clean_text(text: Optional[str]) -> str:
    return (text or "").strip()


def _safe(data: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def _mk_zip_bytes(files: Dict[str, str]) -> bytes:
    """Create zip in-memory from {path: text}"""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, text in files.items():
            zf.writestr(path, text)
    bio.seek(0)
    return bio.read()


# =============================================================================
# RESEARCH SERVICE
# =============================================================================
class ResearchService:
    """Service for landlord/property research"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._profiles: Dict[str, LandlordProfile] = {}
        self._checkpoints: Dict[str, ResearchCheckpoint] = {}
        self._zip_cache: Dict[str, bytes] = {}
        logger.info("▸ Research Service initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=CFG["HTTP_TIMEOUT"])
        return self._client
    
    async def _get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """HTTP GET with retry policy"""
        client = await self._get_client()
        for attempt in range(1, CFG["HTTP_RETRIES"] + 2):
            try:
                r = await client.get(url, params=params or {}, headers=headers or {})
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"GET {url} attempt {attempt} failed: {e}")
                if attempt >= CFG["HTTP_RETRIES"] + 1:
                    return {"_error": str(e), "_url": url, "_params": params or {}}
        return {}
    
    # =========================================================================
    # DATA SOURCE FETCHERS — ZERO-COST REAL APIs
    # =========================================================================

    async def fetch_assessor(self, property_id: str) -> Dict[str, Any]:
        """Hennepin County ArcGIS REST — free public parcel data (no API key)."""
        base = CFG["ASSESSOR_BASE"]
        # ArcGIS REST query for PIN/parcel ID
        # Escape single quotes in property_id to prevent WHERE clause breakage
        safe_property_id = property_id.replace("'", "''")
        url = f"{base}/query"
        params = {
            "where": f"PIN='{safe_property_id}'",
            "outFields": "*",
            "f": "json",
        }
        data = await self._get_json(url, params=params)

        features = _safe(data, "features", [])
        attrs = _safe(features[0], "attributes", {}) if features else {}

        return {
            "source": "assessor",
            "owner_name": _safe(attrs, "OWNER_NAME") or _safe(attrs, "PRIMARY_OWNER"),
            "mailing_address": _safe(attrs, "OWNER_MAILING_ADDRESS"),
            "site_address": _safe(attrs, "SITUS_ADDRESS") or _safe(attrs, "PROP_ADDRESS"),
            "parcel_id": property_id,
            "taxes": {
                "total": _safe(attrs, "TAX_CAPACITY"),
                "net_tax": _safe(attrs, "NET_TAX"),
                "market_value": _safe(attrs, "ESTIMATED_MARKET_VALUE"),
            },
            "assessed": {
                "total_value": _safe(attrs, "TOTAL_VALUE"),
                "land_value": _safe(attrs, "LAND_VALUE"),
                "building_value": _safe(attrs, "BUILDING_VALUE"),
            },
            "legal_description": _safe(attrs, "LEGAL_DESCRIPTION"),
            "raw": data,
        }

    async def fetch_recorder_deeds(self, property_id: str) -> Dict[str, Any]:
        """County recorder — NO FREE API. Returns honest status."""
        logger.info("Recorder deeds: no free API available. Returning honest status.")
        return {
            "source": "recorder",
            "deeds": [],
            "liens": [],
            "status": "no_free_api",
            "note": "County recorders do not offer free APIs. Paid subscription required.",
            "raw": {"_error": "No free API available", "_source": "recorder"},
        }

    async def fetch_ucc(self, entity_name: str) -> Dict[str, Any]:
        """UCC filings — NO FREE API. Returns honest status."""
        if not entity_name:
            return {"source": "ucc", "filings": []}
        logger.info("UCC: no free API available. Returning honest status.")
        return {
            "source": "ucc",
            "filings": [],
            "status": "no_free_api",
            "note": "MN SOS UCC search has no free API. Web scraping possible but fragile.",
            "raw": {"_error": "No free API available", "_source": "ucc"},
        }

    async def fetch_dispatch(self, property_id: str, site_address: Optional[str]) -> Dict[str, Any]:
        """Minneapolis Open Data — free 911 call data (no API key)."""
        q = site_address or property_id
        base = CFG["DISPATCH_BASE"]
        # Socrata API: search parameter filters results
        params = {"search": q, "max_rows": 50}
        data = await self._get_json(base, params=params)

        rows = _safe(data, "data", [])
        if rows is None:
            rows = []

        # Build column name -> index map from Socrata metadata for robust parsing
        columns = []
        meta = _safe(data, "meta", {})
        view = _safe(meta, "view", {})
        cols_meta = _safe(view, "columns", [])
        if isinstance(cols_meta, list):
            columns = [str(_safe(c, "fieldName", _safe(c, "name", ""))).lower() for c in cols_meta]

        col_map = {}
        if columns:
            for idx, col_name in enumerate(columns):
                col_map[col_name] = idx

        calls = []
        for row in rows:
            if not isinstance(row, list):
                continue
            # Map by known field names; fallback to position guesses if metadata unavailable
            def _val(*names):
                for name in names:
                    if name in col_map and col_map[name] < len(row):
                        return row[col_map[name]]
                return ""

            calls.append({
                "description": _val("description", "desc", "reason") or (row[0] if len(row) > 0 and not columns else ""),
                "date": _val("date", "datetime", "call_date") or (row[1] if len(row) > 1 and not columns else ""),
                "address": _val("address", "location", "incident_address") or (row[2] if len(row) > 2 and not columns else ""),
                "precinct": _val("precinct", "police_precinct", "precinct_number") or (row[3] if len(row) > 3 and not columns else ""),
            })

        return {
            "source": "dispatch",
            "calls": calls,
            "call_count": len(calls),
            "raw": data,
        }

    async def _fetch_news_rss(self, query: str) -> List[Dict[str, Any]]:
        """Google News RSS — completely free, no API key."""
        encoded_q = quote_plus(query)
        rss_url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded_q}"
            f"&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            client = await self._get_client()
            r = await client.get(rss_url, timeout=15.0)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            articles = []
            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                description = item.find("description")
                articles.append({
                    "title": title.text if title is not None else "",
                    "url": link.text if link is not None else "",
                    "publishedAt": pub_date.text if pub_date is not None else "",
                    "description": description.text if description is not None else "",
                    "source": {"name": "Google News RSS"},
                })
                if len(articles) >= 25:
                    break
            return articles
        except Exception as e:
            logger.warning(f"RSS news fetch failed: {e}")
            return []

    async def fetch_news(self, entity_name: str, site_address: Optional[str]) -> Dict[str, Any]:
        """NewsAPI free tier (100 req/day) + Google News RSS fallback."""
        terms = [t for t in [entity_name, site_address] if t]
        q = " OR ".join(terms) if terms else entity_name
        if not q:
            return {"source": "news", "mentions": []}

        # Try NewsAPI first if key is configured
        if CFG["NEWS_API_KEY"]:
            try:
                url = f"{CFG['NEWS_BASE']}/everything"
                params = {"q": q, "pageSize": 25, "sortBy": "relevancy"}
                headers = {"Authorization": f"Bearer {CFG['NEWS_API_KEY']}"}
                data = await self._get_json(url, params=params, headers=headers)
                articles = _safe(data, "articles", [])
                if articles:
                    return {"source": "news", "mentions": articles, "provider": "newsapi", "raw": data}
            except Exception as e:
                logger.warning(f"NewsAPI failed, falling back to RSS: {e}")

        # Fallback: Google News RSS (always free)
        rss_articles = await self._fetch_news_rss(q)
        return {
            "source": "news",
            "mentions": rss_articles,
            "provider": "google_news_rss",
            "raw": {"rss_count": len(rss_articles)},
        }

    async def fetch_sos(self, entity_name: str) -> Dict[str, Any]:
        """MN Secretary of State — no free API. Ethical crawler on public search."""
        if not entity_name:
            return {"source": "sos", "entity": {}}
        logger.info("MN SOS: no free API. Attempting ethical web crawl.")
        try:
            from app.services.crawler import get_crawler
            crawler = get_crawler()
            search_url = f"{CFG['SOS_BASE']}?BusinessName={quote_plus(entity_name)}"
            result = await crawler.crawl(search_url)
            if result.success and result.data:
                tables = result.data.get("tables", [])
                rows = tables[0] if tables else []
                entity = {
                    "legal_name": entity_name,
                    "status": "unknown",
                    "registered_agent": "",
                    "formation_date": "",
                }
                if rows and len(rows) > 1:
                    # Best-effort extraction from HTML table
                    for row in rows[1:]:
                        if len(row) >= 2 and "active" in str(row).lower():
                            entity["status"] = "active"
                            break
                        elif len(row) >= 2 and "inactive" in str(row).lower():
                            entity["status"] = "inactive"
                            break
                return {
                    "source": "sos",
                    "entity": entity,
                    "status": "web_scraped",
                    "note": "MN SOS has no free API. Data extracted from public search page.",
                    "raw": {"crawled": True, "url": result.url, "tables_found": len(tables)},
                }
        except Exception as e:
            logger.warning(f"SOS crawl failed: {e}")

        return {
            "source": "sos",
            "entity": {"legal_name": entity_name, "status": "unknown"},
            "status": "no_free_api",
            "note": "MN SOS has no free API. Web scraping attempt failed.",
            "raw": {"_error": "No free API available", "_source": "sos"},
        }

    async def fetch_bankruptcy(self, entity_name: str) -> Dict[str, Any]:
        """CourtListener — free federal court API (token required, no cost)."""
        if not entity_name:
            return {"source": "bankruptcy", "cases": []}
        try:
            base = CFG["BANKRUPTCY_BASE"]
            url = f"{base}/search/"
            params = {"type": "d", "q": entity_name}
            headers = {}
            token = os.getenv("BANKRUPTCY_API_KEY", "")
            if token:
                headers["Authorization"] = f"Token {token}"
            data = await self._get_json(url, params=params, headers=headers)
            results = _safe(data, "results", [])
            cases = []
            for r in results[:10]:
                cases.append({
                    "case_name": _safe(r, "caseName"),
                    "docket_number": _safe(r, "docketNumber"),
                    "court": _safe(r, "court"),
                    "date_filed": _safe(r, "dateFiled"),
                    "status": _safe(r, "status"),
                })
            return {
                "source": "bankruptcy",
                "cases": cases,
                "case_count": len(cases),
                "provider": "courtlistener",
                "raw": data,
            }
        except Exception as e:
            logger.warning(f"CourtListener fetch failed: {e}")
            return {
                "source": "bankruptcy",
                "cases": [],
                "status": "api_error",
                "note": "CourtListener requires free token. Sign up at courtlistener.com.",
                "raw": {"_error": str(e)},
            }

    async def fetch_insurance(self, entity_name: str) -> Dict[str, Any]:
        """Insurance — NO FREE API. Returns honest status."""
        if not entity_name:
            return {"source": "insurance", "brokers": [], "policies": []}
        logger.info("Insurance: no free API available. Returning honest status.")
        return {
            "source": "insurance",
            "brokers": [],
            "policies": [],
            "status": "no_free_api",
            "note": "MN Dept of Commerce insurance lookup has no free API.",
            "raw": {"_error": "No free API available", "_source": "insurance"},
        }
    
    # =========================================================================
    # FRAUD FLAG DETECTION
    # =========================================================================
    def detect_fraud_flags(
        self,
        assessor: Dict[str, Any],
        recorder: Dict[str, Any],
        sos: Dict[str, Any],
    ) -> List[FraudFlag]:
        """Detect potential fraud indicators"""
        flags: List[FraudFlag] = []
        
        # Owner mismatch between assessor and SOS
        assessor_owner = _safe(assessor, "owner_name", "")
        sos_entity = _safe(sos, "entity", {})
        sos_name = _safe(sos_entity, "legal_name", "")
        if assessor_owner and sos_name and assessor_owner.lower() != sos_name.lower():
            flags.append(FraudFlag(
                flag_type="owner_mismatch",
                detail=f"Assessor owner '{assessor_owner}' != SOS '{sos_name}'",
                severity="medium",
            ))
        
        # Suspicious liens (recent, high count)
        liens = _safe(recorder, "liens", [])
        if isinstance(liens, list):
            if len(liens) >= 5:
                flags.append(FraudFlag(
                    flag_type="multiple_liens",
                    detail=f"{len(liens)} liens recorded - high risk",
                    severity="high",
                ))
            elif len(liens) >= 3:
                flags.append(FraudFlag(
                    flag_type="multiple_liens",
                    detail=f"{len(liens)} liens recorded",
                    severity="medium",
                ))
        
        # Entity inactive/delinquent
        status = _safe(sos_entity, "status", "").lower()
        if status in {"inactive", "dissolved", "delinquent"}:
            flags.append(FraudFlag(
                flag_type="entity_status",
                detail=f"Entity status: {status}",
                severity="high",
            ))
        
        # Tax delinquency
        taxes = _safe(assessor, "taxes", {})
        if _safe(taxes, "delinquent") or _safe(taxes, "past_due"):
            flags.append(FraudFlag(
                flag_type="tax_delinquent",
                detail="Property taxes are delinquent",
                severity="medium",
            ))
        
        return flags
    
    # =========================================================================
    # MAIN RESEARCH FUNCTION
    # =========================================================================
    async def collect_landlord_data(
        self,
        user_id: str,
        property_id: str,
    ) -> Dict[str, Any]:
        """
        Collect and bundle landlord/property data.
        
        Returns profile, checkpoint, and ZIP token.
        """
        property_id = _clean_text(property_id)
        if not property_id:
            raise ValueError("property_id is required")
        
        # Fetch Assessor first to get owner + site address
        assessor = await self.fetch_assessor(property_id)
        owner_name = _safe(assessor, "owner_name", "")
        site_address = _safe(assessor, "site_address", "")
        
        # Parallel fetch remainder
        recorder, ucc, sos, news, dispatch, bankruptcy, insurance = await asyncio.gather(
            self.fetch_recorder_deeds(property_id),
            self.fetch_ucc(owner_name),
            self.fetch_sos(owner_name),
            self.fetch_news(owner_name, site_address),
            self.fetch_dispatch(property_id, site_address),
            self.fetch_bankruptcy(owner_name),
            self.fetch_insurance(owner_name),
        )
        
        # Detect fraud flags
        fraud_flags = self.detect_fraud_flags(assessor, recorder, sos)
        
        # Build profile
        profile = LandlordProfile(
            property_id=property_id,
            owner_name=owner_name or _safe(sos, "entity", {}).get("legal_name"),
            site_address=site_address,
            mailing_address=_safe(assessor, "mailing_address"),
            taxes=_safe(assessor, "taxes", {}),
            assessed=_safe(assessor, "assessed", {}),
            legal_description=_safe(assessor, "legal_description"),
            deeds=_safe(recorder, "deeds", []),
            liens=_safe(recorder, "liens", []),
            ucc_filings=_safe(ucc, "filings", []),
            news_mentions=_safe(news, "mentions", []),
            emergency_calls=_safe(dispatch, "calls", []),
            bankruptcy_cases=_safe(bankruptcy, "cases", []),
            insurance_brokers=_safe(insurance, "brokers", []),
            insurance_policies=_safe(insurance, "policies", []),
            entity_info=_safe(sos, "entity", {}),
            fraud_flags=fraud_flags,
            sources={
                "assessor": assessor.get("raw"),
                "recorder": recorder.get("raw"),
                "ucc": ucc.get("raw"),
                "sos": sos.get("raw"),
                "news": news.get("raw"),
                "dispatch": dispatch.get("raw"),
                "bankruptcy": bankruptcy.get("raw"),
                "insurance": insurance.get("raw"),
            },
        )
        
        # Create checkpoint
        checkpoint = ResearchCheckpoint(
            id=make_id("chk"),
            user_id=user_id,
            property_id=property_id,
            profile=profile,
        )
        
        # Build evidence ZIP
        profile_dict = profile.to_dict()
        files = {
            f"{property_id}/profile.json": json.dumps(profile_dict, indent=2),
            f"{property_id}/checkpoint.json": json.dumps(checkpoint.to_dict(), indent=2),
            f"{property_id}/summary.txt": self._generate_summary(profile),
        }
        zip_bytes = _mk_zip_bytes(files)
        zip_token = make_id("zip")
        
        # Cache
        self._profiles[property_id] = profile
        self._checkpoints[checkpoint.id] = checkpoint
        self._zip_cache[property_id] = zip_bytes
        
        logger.info(f"▸ Research complete for property {property_id}: {len(fraud_flags)} fraud flags")
        
        return {
            "landlord_profile": profile_dict,
            "checkpoint_id": checkpoint.id,
            "evidence_zip_token": zip_token,
            "fraud_flag_count": len(fraud_flags),
        }
    
    def _generate_summary(self, profile: LandlordProfile) -> str:
        """Generate human-readable summary"""
        lines = [
            f"LANDLORD/PROPERTY RESEARCH REPORT",
            f"=" * 40,
            f"",
            f"Property ID: {profile.property_id}",
            f"Owner: {profile.owner_name or 'Unknown'}",
            f"Site Address: {profile.site_address or 'Unknown'}",
            f"Mailing Address: {profile.mailing_address or 'Unknown'}",
            f"",
            f"FINDINGS:",
            f"---------",
            f"Liens: {len(profile.liens)}",
            f"UCC Filings: {len(profile.ucc_filings)}",
            f"Deeds/Transfers: {len(profile.deeds)}",
            f"Emergency Calls: {len(profile.emergency_calls)}",
            f"News Mentions: {len(profile.news_mentions)}",
            f"Bankruptcy Cases: {len(profile.bankruptcy_cases)}",
            f"",
            f"FRAUD FLAGS: {len(profile.fraud_flags)}",
            f"-----------",
        ]
        
        for flag in profile.fraud_flags:
            lines.append(f"  [{flag.severity.upper()}] {flag.flag_type}: {flag.detail}")
        
        lines.extend([
            f"",
            f"Generated: {profile.generated_at.isoformat()}",
            f"",
            f"This report was generated by Semptify Research Module.",
        ])
        
        return "\n".join(lines)
    
    def get_profile(self, property_id: str) -> Optional[LandlordProfile]:
        """Get a cached profile"""
        return self._profiles.get(property_id)
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[ResearchCheckpoint]:
        """Get a checkpoint by ID"""
        return self._checkpoints.get(checkpoint_id)
    
    def get_zip(self, property_id: str) -> Optional[bytes]:
        """Get cached ZIP bytes"""
        return self._zip_cache.get(property_id)
    
    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global instance
_research_service: Optional[ResearchService] = None


def get_research_service() -> ResearchService:
    """Get the research service singleton"""
    global _research_service
    if _research_service is None:
        _research_service = ResearchService()
    return _research_service
