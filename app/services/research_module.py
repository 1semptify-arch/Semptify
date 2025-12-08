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
import uuid
import logging
import asyncio
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIG (env-driven for portability)
# =============================================================================
CFG = {
    # County/Recorder/Assessor
    "ASSESSOR_BASE": os.getenv("ASSESSOR_BASE", "https://gis.hennepin.us/property"),
    "RECORDER_BASE": os.getenv("RECORDER_BASE", "https://www.hennepin.us/recorder"),
    "RECORDER_UCC_BASE": os.getenv("RECORDER_UCC_BASE", "https://mblsportal.sos.state.mn.us"),
    # Public safety/dispatch
    "DISPATCH_BASE": os.getenv("DISPATCH_BASE", "https://www.minneapolismn.gov/opendata"),
    # News aggregator
    "NEWS_BASE": os.getenv("NEWS_BASE", "https://newsapi.org/v2"),
    "NEWS_API_KEY": os.getenv("NEWS_API_KEY", ""),
    # Corporate registry (Secretary of State)
    "SOS_BASE": os.getenv("SOS_BASE", "https://mblsportal.sos.state.mn.us"),
    # Bankruptcy/Dockets
    "BANKRUPTCY_BASE": os.getenv("BANKRUPTCY_BASE", "https://www.mnb.uscourts.gov"),
    # Insurance sources
    "INSURANCE_BASE": os.getenv("INSURANCE_BASE", "https://mn.gov/commerce"),
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
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
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
        logger.info("🔍 Research Service initialized")
    
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
    # DATA SOURCE FETCHERS
    # =========================================================================
    async def fetch_assessor(self, property_id: str) -> Dict[str, Any]:
        """Taxes, assessed value, current owner, parcel geometry, legal description"""
        url = f"{CFG['ASSESSOR_BASE']}/parcel/{property_id}"
        data = await self._get_json(url)
        return {
            "source": "assessor",
            "owner_name": _safe(data, "owner") or _safe(data, "owner_name"),
            "mailing_address": _safe(data, "mailing_address"),
            "site_address": _safe(data, "site_address"),
            "parcel_id": property_id,
            "taxes": _safe(data, "taxes", {}),
            "assessed": _safe(data, "assessed", {}),
            "legal_description": _safe(data, "legal_description"),
            "raw": data,
        }
    
    async def fetch_recorder_deeds(self, property_id: str) -> Dict[str, Any]:
        """Deeds/transfers history, lien holders recorded against parcel"""
        url = f"{CFG['RECORDER_BASE']}/deeds"
        data = await self._get_json(url, params={"parcel_id": property_id})
        return {
            "source": "recorder",
            "deeds": _safe(data, "deeds", []),
            "liens": _safe(data, "liens", []),
            "raw": data,
        }
    
    async def fetch_ucc(self, entity_name: str) -> Dict[str, Any]:
        """UCC filings against landlord entity (secured interests)"""
        if not entity_name:
            return {"source": "ucc", "filings": []}
        url = f"{CFG['RECORDER_UCC_BASE']}/search"
        data = await self._get_json(url, params={"q": entity_name})
        return {"source": "ucc", "filings": _safe(data, "filings", []), "raw": data}
    
    async def fetch_dispatch(self, property_id: str, site_address: Optional[str]) -> Dict[str, Any]:
        """Public safety/emergency calls near address or parcel centroid"""
        q = site_address or property_id
        url = f"{CFG['DISPATCH_BASE']}/calls"
        data = await self._get_json(url, params={"q": q, "radius_m": 150})
        return {
            "source": "dispatch",
            "calls": _safe(data, "calls", []),
            "raw": data,
        }
    
    async def fetch_news(self, entity_name: str, site_address: Optional[str]) -> Dict[str, Any]:
        """Local/regional news mentions of landlord or property"""
        headers = {"Authorization": f"Bearer {CFG['NEWS_API_KEY']}"} if CFG["NEWS_API_KEY"] else None
        url = f"{CFG['NEWS_BASE']}/search"
        terms = [entity_name, site_address]
        q = " OR ".join([t for t in terms if t])
        data = await self._get_json(url, params={"q": q, "lang": "en", "limit": 25}, headers=headers)
        return {
            "source": "news",
            "mentions": _safe(data, "articles", []),
            "raw": data,
        }
    
    async def fetch_sos(self, entity_name: str) -> Dict[str, Any]:
        """Business registry: filings, registered agents, status, formation date"""
        if not entity_name:
            return {"source": "sos", "entity": {}}
        url = f"{CFG['SOS_BASE']}/entities"
        data = await self._get_json(url, params={"name": entity_name})
        return {
            "source": "sos",
            "entity": _safe(data, "entity", {}),
            "raw": data,
        }
    
    async def fetch_bankruptcy(self, entity_name: str) -> Dict[str, Any]:
        """Bankruptcy filings/dockets involving entity principals or company"""
        if not entity_name:
            return {"source": "bankruptcy", "cases": []}
        url = f"{CFG['BANKRUPTCY_BASE']}/cases"
        data = await self._get_json(url, params={"name": entity_name})
        return {"source": "bankruptcy", "cases": _safe(data, "cases", []), "raw": data}
    
    async def fetch_insurance(self, entity_name: str) -> Dict[str, Any]:
        """Insurance broker/carrier info (directory/municipal filings)"""
        if not entity_name:
            return {"source": "insurance", "brokers": [], "policies": []}
        url = f"{CFG['INSURANCE_BASE']}/brokers"
        data = await self._get_json(url, params={"q": entity_name})
        return {
            "source": "insurance",
            "brokers": _safe(data, "brokers", []),
            "policies": _safe(data, "policies", []),
            "raw": data,
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
            id=f"checkpoint_{uuid.uuid4().hex[:12]}",
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
        zip_token = f"zip_{uuid.uuid4().hex[:10]}"
        
        # Cache
        self._profiles[property_id] = profile
        self._checkpoints[checkpoint.id] = checkpoint
        self._zip_cache[property_id] = zip_bytes
        
        logger.info(f"🔍 Research complete for property {property_id}: {len(fraud_flags)} fraud flags")
        
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
