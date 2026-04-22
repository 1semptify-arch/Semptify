"""
Research Module (FastAPI + Semptify SDK)
========================================

Collects landlord/property data tied to a parcel/lot: emergency calls,
news, background on landlord/entity, taxes, sales, liens, financials,
and insurance broker info. Exposes REST endpoints via FastAPI and
integrates with the Semptify Positronic Mesh.

Multilingual-ready (labels), checkpointing, and ZIP bundling included.

Quick start (standalone mode):
    uvicorn app.modules.research_module:app --reload
    GET  /status
    POST /research/{parcel_id}?user_id=bradley
    GET  /download/{parcel_id}
"""

import os
import io
import json
import hmac
from app.core.id_gen import make_id
import hashlib
import logging
import asyncio
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, RedirectResponse

# Conditional import for integrated vs standalone mode
STANDALONE_MODE = False
try:
    from app.core.security import require_user, StorageUser
except ImportError:
    STANDALONE_MODE = True
    # Stub for standalone mode
    class StorageUser:  # type: ignore[no-redef]
        def __init__(self, user_id: str = "standalone"):
            self.user_id = user_id
    
    async def require_user() -> Any:  # type: ignore[no-redef]
        """Standalone mode: return a stub user."""
        return StorageUser()

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIG (env-driven for portability)
# =============================================================================
# Collaborators: set these in your .env or environment to use real county APIs
# without code changes. See docs/RESEARCH_MODULE.md for endpoint specs.
CFG = {
    # -------------------------------------------------------------------------
    # COUNTY ASSESSOR / PROPERTY TAX
    # Minnesota counties with public APIs:
    #   Hennepin: https://gis.hennepin.us/property/api/v1
    #   Ramsey: https://beacon.schneidercorp.com/api/ramsey
    #   Dakota: https://gis.co.dakota.mn.us/api/property
    # -------------------------------------------------------------------------
    "ASSESSOR_BASE": os.getenv("ASSESSOR_BASE", "https://gis.hennepin.us/property/api/v1"),
    "ASSESSOR_API_KEY": os.getenv("ASSESSOR_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # COUNTY RECORDER (Deeds, Liens, Mortgages)
    # Hennepin: https://www.hennepin.us/recorder/api
    # Ramsey: https://www.ramseycounty.us/recorder/api
    # Dakota: https://www.co.dakota.mn.us/recorder/api
    # -------------------------------------------------------------------------
    "RECORDER_BASE": os.getenv("RECORDER_BASE", "https://www.hennepin.us/recorder/api/v2"),
    "RECORDER_API_KEY": os.getenv("RECORDER_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # UCC FILINGS (Secretary of State - Business Services)
    # Minnesota SOS: https://mblsportal.sos.state.mn.us/api/ucc
    # Direct Connect: https://sos.state.mn.us/direct-connect/ucc
    # -------------------------------------------------------------------------
    "UCC_BASE": os.getenv("UCC_BASE", "https://mblsportal.sos.state.mn.us/api/ucc"),
    "UCC_API_KEY": os.getenv("UCC_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # PUBLIC SAFETY / 911 DISPATCH
    # Minneapolis Open Data: https://opendata.minneapolismn.gov/api/911
    # St. Paul: https://information.stpaul.gov/api/public-safety
    # Hennepin County Sheriff: https://hennepin.us/sheriff/api/cad
    # -------------------------------------------------------------------------
    "DISPATCH_BASE": os.getenv("DISPATCH_BASE", "https://opendata.minneapolismn.gov/api/v2/public_safety"),
    "DISPATCH_API_KEY": os.getenv("DISPATCH_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # NEWS AGGREGATION
    # NewsAPI.org: https://newsapi.org/v2 (requires API key)
    # Google News RSS: https://news.google.com/rss/search
    # Local: Star Tribune, Pioneer Press RSS feeds
    # -------------------------------------------------------------------------
    "NEWS_BASE": os.getenv("NEWS_BASE", "https://newsapi.org/v2"),
    "NEWS_API_KEY": os.getenv("NEWS_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # SECRETARY OF STATE (Business Registry)
    # Minnesota SOS Portal: https://mblsportal.sos.state.mn.us/api/business
    # Direct search: https://sos.state.mn.us/business-services
    # -------------------------------------------------------------------------
    "SOS_BASE": os.getenv("SOS_BASE", "https://mblsportal.sos.state.mn.us/api/business"),
    "SOS_API_KEY": os.getenv("SOS_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # BANKRUPTCY / FEDERAL COURTS
    # PACER: https://pacer.uscourts.gov/api (requires PACER account)
    # MN Bankruptcy Court: https://www.mnb.uscourts.gov/api
    # CourtListener: https://www.courtlistener.com/api/rest/v3
    # -------------------------------------------------------------------------
    "BANKRUPTCY_BASE": os.getenv("BANKRUPTCY_BASE", "https://www.courtlistener.com/api/rest/v3"),
    "BANKRUPTCY_API_KEY": os.getenv("BANKRUPTCY_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # INSURANCE (MN Dept of Commerce)
    # License lookup: https://mn.gov/commerce/insurance/api
    # NAIC database: https://content.naic.org/api
    # -------------------------------------------------------------------------
    "INSURANCE_BASE": os.getenv("INSURANCE_BASE", "https://mn.gov/commerce/insurance/api"),
    "INSURANCE_API_KEY": os.getenv("INSURANCE_API_KEY", ""),
    
    # -------------------------------------------------------------------------
    # HTTP CLIENT SETTINGS
    # -------------------------------------------------------------------------
    "HTTP_TIMEOUT": float(os.getenv("HTTP_TIMEOUT", "15.0")),
    "HTTP_RETRIES": int(os.getenv("HTTP_RETRIES", "3")),
    
    # -------------------------------------------------------------------------
    # STORAGE / OBJECT STORE (for production ZIP storage)
    # Options: S3, R2, MinIO, Azure Blob, GCS
    # Set STORAGE_MODE="cloud" to enable signed URL generation
    # -------------------------------------------------------------------------
    "STORAGE_MODE": os.getenv("STORAGE_MODE", "memory"),  # "memory" or "cloud"
    "STORAGE_BUCKET": os.getenv("STORAGE_BUCKET", "semptify-research-exports"),
    "STORAGE_ENDPOINT": os.getenv("STORAGE_ENDPOINT", ""),  # S3-compatible endpoint
    "STORAGE_ACCESS_KEY": os.getenv("STORAGE_ACCESS_KEY", ""),
    "STORAGE_SECRET_KEY": os.getenv("STORAGE_SECRET_KEY", ""),
    "STORAGE_REGION": os.getenv("STORAGE_REGION", "us-east-1"),
    "SIGNED_URL_EXPIRY": int(os.getenv("SIGNED_URL_EXPIRY", "3600")),  # 1 hour default
    
    # -------------------------------------------------------------------------
    # FEATURE FLAGS
    # -------------------------------------------------------------------------
    "USE_MOCK_DATA": os.getenv("USE_MOCK_DATA", "true").lower() == "true",
    "ENABLE_REAL_APIS": os.getenv("ENABLE_REAL_APIS", "false").lower() == "true",
}

# =============================================================================
# I18N LABELS (Quad-lingual: English, Spanish, Somali, Hmong)
# =============================================================================
I18N_LABELS = {
    "en": {
        "property_id": "Property ID",
        "owner_name": "Owner Name",
        "site_address": "Site Address",
        "mailing_address": "Mailing Address",
        "taxes": "Property Taxes",
        "assessed_value": "Assessed Value",
        "liens": "Liens",
        "deeds": "Deed History",
        "ucc_filings": "UCC Filings",
        "emergency_calls": "911 Calls",
        "news_mentions": "News Mentions",
        "bankruptcy": "Bankruptcy Records",
        "entity_info": "Business Entity Info",
        "insurance": "Insurance",
        "fraud_flags": "Fraud Flags",
        "risk_score": "Risk Score",
        "risk_low": "Low Risk",
        "risk_medium": "Medium Risk",
        "risk_high": "High Risk",
        "risk_critical": "Critical Risk",
        "download_evidence": "Download Evidence Package",
        "generated_at": "Generated At",
    },
    "es": {
        "property_id": "ID de Propiedad",
        "owner_name": "Nombre del Propietario",
        "site_address": "Dirección del Sitio",
        "mailing_address": "Dirección Postal",
        "taxes": "Impuestos de Propiedad",
        "assessed_value": "Valor Tasado",
        "liens": "Gravámenes",
        "deeds": "Historial de Escrituras",
        "ucc_filings": "Archivos UCC",
        "emergency_calls": "Llamadas al 911",
        "news_mentions": "Menciones en Noticias",
        "bankruptcy": "Registros de Bancarrota",
        "entity_info": "Info de Entidad Comercial",
        "insurance": "Seguro",
        "fraud_flags": "Indicadores de Fraude",
        "risk_score": "Puntuación de Riesgo",
        "risk_low": "Riesgo Bajo",
        "risk_medium": "Riesgo Medio",
        "risk_high": "Riesgo Alto",
        "risk_critical": "Riesgo Crítico",
        "download_evidence": "Descargar Paquete de Evidencia",
        "generated_at": "Generado En",
    },
    "so": {  # Somali
        "property_id": "Aqoonsiga Hantida",
        "owner_name": "Magaca Milkiilaha",
        "site_address": "Cinwaanka Goobta",
        "mailing_address": "Cinwaanka Boostada",
        "taxes": "Canshuuraha Hantida",
        "assessed_value": "Qiimaha La Qiimeeyey",
        "liens": "Deymaha",
        "deeds": "Taariikhda Hantida",
        "ucc_filings": "Faylalka UCC",
        "emergency_calls": "Wicitaannada 911",
        "news_mentions": "Wararka",
        "bankruptcy": "Diiwaanka Falastaynta",
        "entity_info": "Macluumaadka Shirkadda",
        "insurance": "Caymiska",
        "fraud_flags": "Calaamadaha Khiyaanada",
        "risk_score": "Dhibcaha Khatarta",
        "risk_low": "Khatar Yar",
        "risk_medium": "Khatar Dhexdhexaad",
        "risk_high": "Khatar Sare",
        "risk_critical": "Khatar Aad u Daran",
        "download_evidence": "Soo Deji Caddaynta",
        "generated_at": "Waqtiga La Sameeyey",
    },
    "hmn": {  # Hmong
        "property_id": "Tus Lej Vaj Tse",
        "owner_name": "Tus Tswv Npe",
        "site_address": "Qhov Chaw Nyob",
        "mailing_address": "Chaw Xa Ntawv",
        "taxes": "Se Vaj Tse",
        "assessed_value": "Tus Nqi Kwv Yees",
        "liens": "Cov Nqi Tshuav",
        "deeds": "Keeb Kwm Vaj Tse",
        "ucc_filings": "UCC Cov Ntaub Ntawv",
        "emergency_calls": "Hu 911",
        "news_mentions": "Xov Xwm",
        "bankruptcy": "Cov Ntaub Ntawv Poob Nyiaj",
        "entity_info": "Cov Ntaub Ntawv Lag Luam",
        "insurance": "Kev Tuav Pov Hwm",
        "fraud_flags": "Cov Cim Dag",
        "risk_score": "Qhab Nias Kev Pheej Hmoo",
        "risk_low": "Kev Pheej Hmoo Tsawg",
        "risk_medium": "Kev Pheej Hmoo Nruab Nrab",
        "risk_high": "Kev Pheej Hmoo Siab",
        "risk_critical": "Kev Pheej Hmoo Loj Heev",
        "download_evidence": "Rub Cov Pov Thawj",
        "generated_at": "Tsim Thaum",
    },
}


def get_labels(lang: str = "en") -> Dict[str, str]:
    """Get i18n labels for the specified language."""
    return I18N_LABELS.get(lang, I18N_LABELS["en"])


# =============================================================================
# ROUTER & STANDALONE APP
# =============================================================================
router = APIRouter(prefix="/api/research-module", tags=["Research Module SDK"])

# Standalone FastAPI app for direct execution
app = FastAPI(
    title="Research Module SDK",
    description="Landlord/Property Research & Dossier Engine",
    version="2.0.0",
)
app.include_router(router)

# In-memory cache for ZIP downloads and research profiles
_research_cache: Dict[str, Dict[str, Any]] = {}
_zip_cache: Dict[str, bytes] = {}

# Shared HTTP client
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=CFG["HTTP_TIMEOUT"],
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    return _client


# =============================================================================
# UTILITIES
# =============================================================================
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Fetch JSON with retry policy"""
    client = get_client()
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


def _clean_text(text: Optional[str]) -> str:
    return (text or "").strip()


# =============================================================================
# SIGNED URL GENERATOR (for production cloud storage)
# =============================================================================
def generate_signed_url(object_key: str, expires_in: Optional[int] = None) -> str:
    """
    Generate a signed URL for downloading from S3-compatible storage.
    
    In production, replace in-memory ZIP with cloud storage:
    1. Upload ZIP to object store during research
    2. Return signed URL from /download endpoint
    
    For real implementation, use boto3 or cloud SDK:
        import boto3
        s3 = boto3.client('s3', ...)
        return s3.generate_presigned_url('get_object', ...)
    """
    if CFG["STORAGE_MODE"] != "cloud":
        return ""  # In-memory mode, no signed URL
    
    expires_in = expires_in or CFG["SIGNED_URL_EXPIRY"]
    expiration = datetime.utcnow() + timedelta(seconds=expires_in)
    expiration_ts = int(expiration.timestamp())
    
    # Build canonical request for signing
    bucket = CFG["STORAGE_BUCKET"]
    region = CFG["STORAGE_REGION"]
    endpoint = CFG["STORAGE_ENDPOINT"] or f"https://{bucket}.s3.{region}.amazonaws.com"
    
    # Simple HMAC-based signature (production: use proper AWS Sig V4)
    string_to_sign = f"{bucket}/{object_key}:{expiration_ts}"
    secret = CFG["STORAGE_SECRET_KEY"].encode() or b"dev-secret"
    signature = hmac.new(secret, string_to_sign.encode(), hashlib.sha256).hexdigest()
    
    params = {
        "X-Amz-Expires": expires_in,
        "X-Amz-Signature": signature,
        "X-Amz-Date": expiration.strftime("%Y%m%dT%H%M%SZ"),
    }
    
    return f"{endpoint}/{object_key}?{urlencode(params)}"


async def upload_to_cloud_storage(object_key: str, data: bytes) -> bool:
    """
    Upload data to cloud storage (S3-compatible).
    
    Production implementation:
        import boto3
        s3 = boto3.client('s3', endpoint_url=CFG["STORAGE_ENDPOINT"], ...)
        s3.put_object(Bucket=CFG["STORAGE_BUCKET"], Key=object_key, Body=data)
    """
    if CFG["STORAGE_MODE"] != "cloud":
        return False
    
    # Placeholder for actual cloud upload
    # In production, use boto3, aioboto3, or httpx to upload
    logger.info(f"Would upload {len(data)} bytes to {CFG['STORAGE_BUCKET']}/{object_key}")
    return True


def _safe(data: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def _mk_checkpoint(user_id: str, property_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": make_id("chk"),
        "user_id": user_id,
        "property_id": property_id,
        "created_at": now_iso(),
        "payload": payload,
    }


def _mk_zip_bytes(files: Dict[str, str]) -> bytes:
    """Create ZIP in-memory from {path: text}"""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, text in files.items():
            zf.writestr(path, text)
    bio.seek(0)
    return bio.read()


# =============================================================================
# MOCK DATA (Minnesota-focused for demo)
# =============================================================================
MOCK_PROPERTIES = {
    "27-028-24-31-0001": {
        "owner_name": "Northstar Properties LLC",
        "mailing_address": "123 Corporate Way, Minneapolis, MN 55401",
        "site_address": "456 Tenant Ave, Minneapolis, MN 55401",
        "taxes": {"2024": {"amount": 12500, "status": "paid"}, "2023": {"amount": 11800, "status": "paid"}},
        "assessed": {"land": 150000, "building": 450000, "total": 600000},
        "legal_description": "Lot 1, Block 2, Northstar Addition"
    },
    "19-116-21-44-0025": {
        "owner_name": "Dakota Rentals Inc",
        "mailing_address": "789 Business Blvd, Eagan, MN 55121",
        "site_address": "321 Renter St, Eagan, MN 55122",
        "taxes": {"2024": {"amount": 8900, "status": "delinquent"}, "2023": {"amount": 8500, "status": "paid"}},
        "assessed": {"land": 85000, "building": 320000, "total": 405000},
        "legal_description": "Lot 15, Block 7, Dakota Heights"
    },
    "demo-property": {
        "owner_name": "Demo Landlord LLC",
        "mailing_address": "100 Demo Street, St. Paul, MN 55101",
        "site_address": "200 Sample Ave, St. Paul, MN 55102",
        "taxes": {"2024": {"amount": 6500, "status": "paid"}},
        "assessed": {"land": 75000, "building": 225000, "total": 300000},
        "legal_description": "Lot 5, Block 3, Demo Subdivision"
    }
}

MOCK_DEEDS = {
    "27-028-24-31-0001": [
        {"date": "2020-03-15", "type": "Warranty Deed", "grantor": "Previous Owner Inc", "grantee": "Northstar Properties LLC", "amount": 550000},
        {"date": "2015-08-22", "type": "Warranty Deed", "grantor": "Original Owner", "grantee": "Previous Owner Inc", "amount": 420000}
    ],
    "19-116-21-44-0025": [
        {"date": "2019-06-10", "type": "Quit Claim Deed", "grantor": "Family Trust", "grantee": "Dakota Rentals Inc", "amount": 380000}
    ]
}

MOCK_LIENS = {
    "27-028-24-31-0001": [],
    "19-116-21-44-0025": [
        {"type": "Mechanics Lien", "amount": 15000, "date": "2024-02-15", "creditor": "ABC Contractors"},
        {"type": "Tax Lien", "amount": 8900, "date": "2024-06-01", "creditor": "Dakota County"},
        {"type": "Judgment Lien", "amount": 25000, "date": "2023-11-20", "creditor": "Smith v. Dakota Rentals"}
    ]
}

MOCK_UCC = {
    "Northstar Properties LLC": [
        {"filing_number": "UCC-2023-123456", "date": "2023-05-10", "secured_party": "First Bank MN", "collateral": "All equipment and fixtures"}
    ],
    "Dakota Rentals Inc": [
        {"filing_number": "UCC-2022-789012", "date": "2022-08-15", "secured_party": "Commercial Lender Corp", "collateral": "Accounts receivable"},
        {"filing_number": "UCC-2024-345678", "date": "2024-01-20", "secured_party": "Equipment Finance LLC", "collateral": "HVAC systems"}
    ]
}

MOCK_DISPATCH = {
    "456 Tenant Ave": [
        {"date": "2024-11-15", "type": "Disturbance", "disposition": "Resolved"},
        {"date": "2024-08-22", "type": "Medical", "disposition": "Transport"},
        {"date": "2024-03-10", "type": "Property Damage", "disposition": "Report Filed"}
    ],
    "321 Renter St": [
        {"date": "2024-12-01", "type": "Welfare Check", "disposition": "No Action"},
        {"date": "2024-10-05", "type": "Noise Complaint", "disposition": "Warning Issued"},
        {"date": "2024-09-18", "type": "Domestic", "disposition": "Arrest"},
        {"date": "2024-07-30", "type": "Fire", "disposition": "Extinguished"},
        {"date": "2024-05-12", "type": "Burglary", "disposition": "Under Investigation"}
    ]
}

MOCK_NEWS = {
    "Northstar Properties LLC": [
        {"date": "2024-06-15", "title": "Local developer expands portfolio", "source": "Star Tribune", "url": "https://example.com/1"},
    ],
    "Dakota Rentals Inc": [
        {"date": "2024-11-20", "title": "Tenants file complaint against Eagan landlord", "source": "Pioneer Press", "url": "https://example.com/2"},
        {"date": "2024-09-05", "title": "Housing violations found at Dakota Rentals property", "source": "Eagan Patch", "url": "https://example.com/3"},
        {"date": "2024-04-18", "title": "Landlord faces multiple lawsuits", "source": "MN Daily", "url": "https://example.com/4"}
    ]
}

MOCK_SOS = {
    "Northstar Properties LLC": {
        "legal_name": "Northstar Properties LLC",
        "status": "Active",
        "formation_date": "2018-02-14",
        "registered_agent": "John Smith",
        "registered_address": "123 Corporate Way, Minneapolis, MN 55401",
        "principals": ["John Smith - Manager", "Jane Doe - Member"]
    },
    "Dakota Rentals Inc": {
        "legal_name": "Dakota Rentals Inc",
        "status": "Delinquent",
        "formation_date": "2015-07-22",
        "registered_agent": "Robert Johnson",
        "registered_address": "789 Business Blvd, Eagan, MN 55121",
        "principals": ["Robert Johnson - President", "Mary Johnson - Secretary"]
    }
}

MOCK_BANKRUPTCY = {
    "Dakota Rentals Inc": [
        {"case_number": "24-12345", "chapter": "11", "filed": "2024-03-01", "status": "Pending", "court": "US Bankruptcy Court - District of Minnesota"}
    ]
}

MOCK_INSURANCE = {
    "Northstar Properties LLC": {
        "brokers": [{"name": "ABC Insurance Agency", "license": "MN-INS-123456", "phone": "612-555-1234"}],
        "policies": [{"type": "Commercial Property", "carrier": "State Farm", "policy_number": "CP-2024-789"}]
    },
    "Dakota Rentals Inc": {
        "brokers": [{"name": "Budget Insurance Brokers", "license": "MN-INS-654321", "phone": "651-555-9876"}],
        "policies": []  # Lapsed coverage
    }
}


# =============================================================================
# DATA SOURCE FETCHERS (using mock data, ready for real API integration)
# =============================================================================
async def fetch_assessor(property_id: str) -> Dict[str, Any]:
    """Taxes, assessed value, current owner, parcel geometry, legal description."""
    # Use mock data if enabled or if property is in demo set
    if CFG["USE_MOCK_DATA"] and property_id in MOCK_PROPERTIES:
        data = MOCK_PROPERTIES[property_id]
        return {
            "source": "assessor",
            "owner_name": data.get("owner_name"),
            "mailing_address": data.get("mailing_address"),
            "site_address": data.get("site_address"),
            "parcel_id": property_id,
            "taxes": data.get("taxes", {}),
            "assessed": data.get("assessed", {}),
            "legal_description": data.get("legal_description"),
            "raw": data,
        }

    # Real API call to county assessor
    # Hennepin County example: GET /property/api/v1/parcel/{pid}
    # Dakota County example: GET /api/property/search?parcel_id={pid}
    url = f"{CFG['ASSESSOR_BASE']}/parcel/{property_id}"
    headers = {}
    if CFG["ASSESSOR_API_KEY"]:
        headers["X-API-Key"] = CFG["ASSESSOR_API_KEY"]
    
    data = await _get_json(url, headers=headers)
    return {
        "source": "assessor",
        "owner_name": _safe(data, "owner") or _safe(data, "owner_name") or _safe(data, "taxpayer_name"),
        "mailing_address": _safe(data, "mailing_address") or _safe(data, "taxpayer_address"),
        "site_address": _safe(data, "site_address") or _safe(data, "property_address"),
        "parcel_id": property_id,
        "taxes": _safe(data, "taxes", {}) or _safe(data, "tax_info", {}),
        "assessed": _safe(data, "assessed", {}) or _safe(data, "valuation", {}),
        "legal_description": _safe(data, "legal_description") or _safe(data, "legal"),
        "raw": data,
    }
async def fetch_recorder_deeds(property_id: str) -> Dict[str, Any]:
    """Deeds/transfers history, lien holders recorded against parcel."""
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and (property_id in MOCK_DEEDS or property_id in MOCK_LIENS):
        deeds = MOCK_DEEDS.get(property_id, [])
        liens = MOCK_LIENS.get(property_id, [])
        return {
            "source": "recorder",
            "deeds": deeds,
            "liens": liens,
            "raw": {"deeds": deeds, "liens": liens},
        }
    
    # Real API call to county recorder
    # Example: GET /recorder/api/v2/documents?parcel={pid}&type=deed,lien
    headers = {}
    if CFG["RECORDER_API_KEY"]:
        headers["X-API-Key"] = CFG["RECORDER_API_KEY"]
    
    url = f"{CFG['RECORDER_BASE']}/documents"
    params = {"parcel_id": property_id, "doc_types": "deed,lien,mortgage"}
    data = await _get_json(url, params=params, headers=headers)
    
    return {
        "source": "recorder",
        "deeds": _safe(data, "deeds", []) or _safe(data, "documents", []),
        "liens": _safe(data, "liens", []),
        "raw": data,
    }


async def fetch_ucc(entity_name: str) -> Dict[str, Any]:
    """UCC filings against landlord entity (secured interests)."""
    if not entity_name:
        return {"source": "ucc", "filings": [], "raw": {}}
    
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and entity_name in MOCK_UCC:
        filings = MOCK_UCC.get(entity_name, [])
        return {"source": "ucc", "filings": filings, "raw": {"filings": filings}}
    
    # Real API call to MN Secretary of State UCC portal
    # Example: GET /api/ucc/search?debtor_name={entity}
    headers = {}
    if CFG["UCC_API_KEY"]:
        headers["X-API-Key"] = CFG["UCC_API_KEY"]
    
    url = f"{CFG['UCC_BASE']}/search"
    params = {"debtor_name": entity_name, "state": "MN"}
    data = await _get_json(url, params=params, headers=headers)
    
    filings = _safe(data, "filings", []) or _safe(data, "results", [])
    return {"source": "ucc", "filings": filings, "raw": data}


async def fetch_dispatch(property_id: str, site_address: Optional[str]) -> Dict[str, Any]:
    """Public safety/emergency calls near address."""
    calls = []
    
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and site_address:
        # Match partial address
        for addr, addr_calls in MOCK_DISPATCH.items():
            if addr in site_address or site_address in addr:
                calls = addr_calls
                break
        if calls:
            return {"source": "dispatch", "calls": calls, "raw": {"calls": calls}}
    
    # Real API call to city/county dispatch records
    # Minneapolis example: GET /api/v2/public_safety/911_calls?address={addr}
    if not site_address:
        return {"source": "dispatch", "calls": [], "raw": {}}
    
    headers = {}
    if CFG["DISPATCH_API_KEY"]:
        headers["X-API-Key"] = CFG["DISPATCH_API_KEY"]
    
    url = f"{CFG['DISPATCH_BASE']}/911_calls"
    params = {"address": site_address, "days": 365}  # Last year of calls
    data = await _get_json(url, params=params, headers=headers)
    
    calls = _safe(data, "calls", []) or _safe(data, "incidents", []) or _safe(data, "results", [])
    return {"source": "dispatch", "calls": calls, "raw": data}


async def fetch_news(entity_name: str, site_address: Optional[str]) -> Dict[str, Any]:
    """Local/regional news mentions of landlord or property."""
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and entity_name in MOCK_NEWS:
        mentions = MOCK_NEWS.get(entity_name, [])
        return {"source": "news", "mentions": mentions, "raw": {"articles": mentions}}
    
    # Real API call to news aggregator
    # NewsAPI example: GET /v2/everything?q={entity}&sources=star-tribune,pioneer-press
    if not entity_name and not site_address:
        return {"source": "news", "mentions": [], "raw": {}}
    
    headers = {}
    if CFG["NEWS_API_KEY"]:
        headers["X-Api-Key"] = CFG["NEWS_API_KEY"]
    
    # Build search query
    query = entity_name or ""
    if site_address:
        # Extract city from address for local news
        query = f"{query} {site_address.split(',')[-2] if ',' in site_address else ''}"
    
    url = f"{CFG['NEWS_BASE']}/everything"
    params = {
        "q": query.strip(),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 10,
    }
    data = await _get_json(url, params=params, headers=headers)
    
    articles = _safe(data, "articles", [])
    mentions = [
        {
            "date": a.get("publishedAt", "")[:10],
            "title": a.get("title", ""),
            "source": a.get("source", {}).get("name", ""),
            "url": a.get("url", ""),
        }
        for a in articles
    ]
    return {"source": "news", "mentions": mentions, "raw": data}


async def fetch_sos(entity_name: str) -> Dict[str, Any]:
    """Business registry: filings, registered agents, status, formation date."""
    if not entity_name:
        return {"source": "sos", "entity": {}, "raw": {}}
    
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and entity_name in MOCK_SOS:
        entity = MOCK_SOS.get(entity_name, {})
        return {"source": "sos", "entity": entity, "raw": entity}
    
    # Real API call to MN Secretary of State business portal
    # Example: GET /api/business/search?name={entity}
    headers = {}
    if CFG["SOS_API_KEY"]:
        headers["X-API-Key"] = CFG["SOS_API_KEY"]
    
    url = f"{CFG['SOS_BASE']}/search"
    params = {"name": entity_name, "state": "MN", "exact_match": "false"}
    data = await _get_json(url, params=params, headers=headers)
    
    # Parse response - may be a list of matches
    entities = _safe(data, "businesses", []) or _safe(data, "results", [])
    if entities and isinstance(entities, list):
        # Take best match (first result)
        entity = entities[0] if entities else {}
    else:
        entity = data if "legal_name" in data or "name" in data else {}
    
    return {"source": "sos", "entity": entity, "raw": data}


async def fetch_bankruptcy(entity_name: str) -> Dict[str, Any]:
    """Bankruptcy filings/dockets involving entity."""
    if not entity_name:
        return {"source": "bankruptcy", "cases": [], "raw": {}}
    
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and entity_name in MOCK_BANKRUPTCY:
        cases = MOCK_BANKRUPTCY.get(entity_name, [])
        return {"source": "bankruptcy", "cases": cases, "raw": {"cases": cases}}
    
    # Real API call to PACER/CourtListener
    # CourtListener example: GET /api/rest/v3/dockets/?party_name={entity}&court=mnb
    headers = {}
    if CFG["BANKRUPTCY_API_KEY"]:
        headers["Authorization"] = f"Token {CFG['BANKRUPTCY_API_KEY']}"
    
    url = f"{CFG['BANKRUPTCY_BASE']}/dockets/"
    params = {
        "party_name": entity_name,
        "court": "mnb",  # Minnesota Bankruptcy Court
        "order_by": "-date_filed",
    }
    data = await _get_json(url, params=params, headers=headers)
    
    cases = _safe(data, "results", []) or _safe(data, "cases", [])
    return {"source": "bankruptcy", "cases": cases, "raw": data}


async def fetch_insurance(entity_name: str) -> Dict[str, Any]:
    """Insurance broker/carrier info."""
    if not entity_name:
        return {"source": "insurance", "brokers": [], "policies": [], "raw": {}}
    
    # Use mock data if enabled
    if CFG["USE_MOCK_DATA"] and entity_name in MOCK_INSURANCE:
        data = MOCK_INSURANCE.get(entity_name, {"brokers": [], "policies": []})
        return {
            "source": "insurance",
            "brokers": data.get("brokers", []),
            "policies": data.get("policies", []),
            "raw": data,
        }
    
    # Real API call to MN Dept of Commerce insurance lookup
    # Example: GET /api/license/search?name={entity}&type=insurance
    headers = {}
    if CFG["INSURANCE_API_KEY"]:
        headers["X-API-Key"] = CFG["INSURANCE_API_KEY"]
    
    url = f"{CFG['INSURANCE_BASE']}/license/search"
    params = {"name": entity_name, "license_type": "insurance"}
    data = await _get_json(url, params=params, headers=headers)
    
    return {
        "source": "insurance",
        "brokers": _safe(data, "brokers", []) or _safe(data, "agents", []),
        "policies": _safe(data, "policies", []),
        "raw": data,
    }


# =============================================================================
# FRAUD FLAGS
# =============================================================================
def compute_fraud_flags(assessor: Dict[str, Any], recorder: Dict[str, Any], sos: Dict[str, Any], bankruptcy: Dict[str, Any]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    # Owner mismatch between assessor and SOS
    assessor_owner = _safe(assessor, "owner_name", "")
    sos_entity = _safe(sos, "entity", {})
    sos_name = _safe(sos_entity, "legal_name", "")
    if assessor_owner and sos_name and assessor_owner.lower() != sos_name.lower():
        flags.append({
            "type": "owner_mismatch",
            "severity": "high",
            "detail": f"Assessor owner '{assessor_owner}' doesn't match SOS '{sos_name}'"
        })

    # Multiple liens
    liens = _safe(recorder, "liens", [])
    if isinstance(liens, list) and len(liens) >= 3:
        flags.append({
            "type": "multiple_liens",
            "severity": "high",
            "detail": f"{len(liens)} liens recorded against property"
        })
    elif isinstance(liens, list) and len(liens) >= 1:
        flags.append({
            "type": "liens_present",
            "severity": "medium",
            "detail": f"{len(liens)} lien(s) recorded against property"
        })

    # Entity inactive/delinquent
    status = _safe(sos_entity, "status", "").lower()
    if status in {"inactive", "dissolved", "delinquent"}:
        flags.append({
            "type": "entity_status",
            "severity": "critical",
            "detail": f"Entity status: {status.upper()} - business may not be properly registered"
        })

    # Active bankruptcy
    bankruptcy_cases = _safe(bankruptcy, "cases", [])
    if bankruptcy_cases:
        flags.append({
            "type": "bankruptcy",
            "severity": "critical",
            "detail": f"Active bankruptcy case(s): {len(bankruptcy_cases)}"
        })

    # Tax delinquency
    taxes = _safe(assessor, "raw", {}).get("taxes", {})
    for year, tax_info in taxes.items():
        if isinstance(tax_info, dict) and tax_info.get("status", "").lower() == "delinquent":
            flags.append({
                "type": "tax_delinquent",
                "severity": "high",
                "detail": f"Property taxes delinquent for {year}"
            })

    # Missing insurance
    # (checked at profile level)

    return flags


def normalize_profile(
    property_id: str,
    assessor: Dict[str, Any],
    recorder: Dict[str, Any],
    ucc: Dict[str, Any],
    sos: Dict[str, Any],
    news: Dict[str, Any],
    dispatch: Dict[str, Any],
    bankruptcy: Dict[str, Any],
    insurance: Dict[str, Any],
) -> Dict[str, Any]:
    owner_name = _safe(assessor, "owner_name") or _safe(sos, "entity", {}).get("legal_name")
    site_address = _safe(assessor, "site_address")
    
    # Compute fraud flags
    fraud_flags = compute_fraud_flags(assessor, recorder, sos, bankruptcy)
    
    # Check for missing insurance
    if not _safe(insurance, "policies", []):
        fraud_flags.append({
            "type": "no_insurance",
            "severity": "high",
            "detail": "No active insurance policies found on file"
        })
    
    profile = {
        "property_id": property_id,
        "owner_name": owner_name,
        "site_address": site_address,
        "mailing_address": _safe(assessor, "mailing_address"),
        "taxes": _safe(assessor, "taxes", {}),
        "assessed": _safe(assessor, "assessed", {}),
        "legal_description": _safe(assessor, "legal_description"),
        "deeds": _safe(recorder, "deeds", []),
        "liens": _safe(recorder, "liens", []),
        "ucc_filings": _safe(ucc, "filings", []),
        "news_mentions": _safe(news, "mentions", []),
        "emergency_calls": _safe(dispatch, "calls", []),
        "bankruptcy_cases": _safe(bankruptcy, "cases", []),
        "entity_info": _safe(sos, "entity", {}),
        "insurance": {
            "brokers": _safe(insurance, "brokers", []),
            "policies": _safe(insurance, "policies", []),
        },
        "fraud_flags": fraud_flags,
        "risk_score": calculate_risk_score(fraud_flags),
        "sources": {
            "assessor": assessor.get("raw"),
            "recorder": recorder.get("raw"),
            "ucc": ucc.get("raw"),
            "sos": sos.get("raw"),
            "news": news.get("raw"),
            "dispatch": dispatch.get("raw"),
            "bankruptcy": bankruptcy.get("raw"),
            "insurance": insurance.get("raw"),
        },
        "generated_at": now_iso(),
    }
    return profile


def calculate_risk_score(fraud_flags: List[Dict[str, Any]]) -> int:
    """Calculate risk score 0-100 based on fraud flags"""
    score = 0
    severity_weights = {"low": 5, "medium": 15, "high": 25, "critical": 35}
    for flag in fraud_flags:
        score += severity_weights.get(flag.get("severity", "medium"), 15)
    return min(100, score)


# =============================================================================
# MAIN RESEARCH FUNCTION
# =============================================================================
async def collect_landlord_data(user_id: str, property_id: str) -> Dict[str, Any]:
    """Collect and bundle all landlord/property data"""
    property_id = _clean_text(property_id)
    if not property_id:
        raise HTTPException(status_code=400, detail="property_id is required")

    # Fetch Assessor first to get owner + site address
    assessor = await fetch_assessor(property_id)
    owner_name = _safe(assessor, "owner_name", "")
    site_address = _safe(assessor, "site_address", "")

    # Parallel fetch all other sources
    recorder, ucc, sos, news, dispatch, bankruptcy, insurance = await asyncio.gather(
        fetch_recorder_deeds(property_id),
        fetch_ucc(owner_name),
        fetch_sos(owner_name),
        fetch_news(owner_name, site_address),
        fetch_dispatch(property_id, site_address),
        fetch_bankruptcy(owner_name),
        fetch_insurance(owner_name),
    )

    # Build normalized profile
    profile = normalize_profile(
        property_id, assessor, recorder, ucc, sos, news, dispatch, bankruptcy, insurance
    )
    checkpoint = _mk_checkpoint(user_id, property_id, profile)

    # Build evidence ZIP
    files = {
        f"{property_id}/profile.json": json.dumps(profile, indent=2),
        f"{property_id}/checkpoint.json": json.dumps(checkpoint, indent=2),
        f"{property_id}/summary.txt": (
            f"═══════════════════════════════════════════════════════\n"
            f"       LANDLORD/PROPERTY RESEARCH DOSSIER\n"
            f"═══════════════════════════════════════════════════════\n\n"
            f"Property ID: {property_id}\n"
            f"Owner: {profile.get('owner_name', 'Unknown')}\n"
            f"Site Address: {profile.get('site_address', 'Unknown')}\n"
            f"Mailing Address: {profile.get('mailing_address', 'Unknown')}\n\n"
            f"───────────────────────────────────────────────────────\n"
            f"                    RISK ASSESSMENT\n"
            f"───────────────────────────────────────────────────────\n"
            f"Risk Score: {profile.get('risk_score', 0)}/100\n"
            f"Fraud Flags: {len(profile.get('fraud_flags', []))}\n\n"
            f"───────────────────────────────────────────────────────\n"
            f"                    DATA SUMMARY\n"
            f"───────────────────────────────────────────────────────\n"
            f"Liens: {len(profile.get('liens', []))}\n"
            f"UCC Filings: {len(profile.get('ucc_filings', []))}\n"
            f"Deeds/Transfers: {len(profile.get('deeds', []))}\n"
            f"Emergency Calls: {len(profile.get('emergency_calls', []))}\n"
            f"News Mentions: {len(profile.get('news_mentions', []))}\n"
            f"Bankruptcy Cases: {len(profile.get('bankruptcy_cases', []))}\n\n"
            f"───────────────────────────────────────────────────────\n"
            f"                    ENTITY INFO\n"
            f"───────────────────────────────────────────────────────\n"
            f"Entity Status: {profile.get('entity_info', {}).get('status', 'Unknown')}\n"
            f"Formation Date: {profile.get('entity_info', {}).get('formation_date', 'Unknown')}\n"
            f"Registered Agent: {profile.get('entity_info', {}).get('registered_agent', 'Unknown')}\n\n"
            f"Generated: {profile.get('generated_at')}\n"
            f"═══════════════════════════════════════════════════════\n"
        ),
    }
    
    # Add fraud flags detail
    if profile.get("fraud_flags"):
        flags_text = "═══════════════════════════════════════════════════════\n"
        flags_text += "                    FRAUD FLAGS\n"
        flags_text += "═══════════════════════════════════════════════════════\n\n"
        for i, flag in enumerate(profile["fraud_flags"], 1):
            flags_text += f"{i}. [{flag.get('severity', 'medium').upper()}] {flag.get('type', 'unknown')}\n"
            flags_text += f"   {flag.get('detail', '')}\n\n"
        files[f"{property_id}/fraud_flags.txt"] = flags_text

    zip_bytes = _mk_zip_bytes(files)

    # Cache for download
    _research_cache[property_id] = profile
    _zip_cache[property_id] = zip_bytes

    return {
        "landlord_profile": profile,
        "checkpoint": checkpoint,
        "evidence_zip_token": f"zip_{property_id}",
    }


# =============================================================================
# API ROUTES
# =============================================================================
@router.get("/health")
@router.get("/status")  # Alias for standalone mode
async def health_check():
    """Health/status check endpoint - GET /status or GET /health"""
    return {
        "status": "healthy",
        "service": "research_module_sdk",
        "version": "2.0.0",
        "standalone_mode": STANDALONE_MODE,
        "config": {
            "use_mock_data": CFG["USE_MOCK_DATA"],
            "enable_real_apis": CFG["ENABLE_REAL_APIS"],
            "storage_mode": CFG["STORAGE_MODE"],
            "http_timeout": CFG["HTTP_TIMEOUT"],
        },
        "available_demo_properties": list(MOCK_PROPERTIES.keys()),
        "supported_languages": list(I18N_LABELS.keys()),
    }


@router.post("/research/{property_id}")
async def research_property(
    property_id: str,
    user_id: Optional[str] = Query(None, description="User ID (for standalone mode)"),
    lang: str = Query("en", description="Language for labels (en, es, so, hmn)"),
    user: StorageUser = Depends(require_user),
):
    """
    Run full research pipeline on a property.
    
    Standalone mode: POST /research/{parcel_id}?user_id=bradley
    Integrated mode: Uses authenticated user from session
    
    Returns comprehensive landlord/property profile with:
    - Tax and assessment records
    - Deeds and liens
    - UCC filings
    - Emergency call history
    - News mentions
    - Secretary of State records
    - Bankruptcy records
    - Insurance info
    - Fraud flags and risk score
    - i18n labels for UI rendering
    """
    try:
        # Use query param user_id for standalone mode, else use authenticated user
        effective_user_id = user_id or getattr(user, "user_id", "anonymous")
        result = await collect_landlord_data(effective_user_id, property_id)
        
        # Add i18n labels if requested
        if lang != "en":
            result["labels"] = get_labels(lang)
        
        return result
        return result
    except Exception as e:
        logger.error(f"Research failed for {property_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{property_id}")
async def get_cached_profile(
    property_id: str,
    user: StorageUser = Depends(require_user),
):
    """Get cached research profile for a property"""
    if property_id not in _research_cache:
        raise HTTPException(status_code=404, detail="Profile not found. Run /research first.")
    return {"landlord_profile": _research_cache[property_id]}


@router.get("/download/{property_id}")
async def download_evidence_zip(
    property_id: str,
    user: StorageUser = Depends(require_user),
):
    """
    Download the evidence ZIP for a researched property.
    
    In cloud storage mode (STORAGE_MODE=cloud), returns a redirect to a signed URL.
    In memory mode (default), streams the ZIP directly.
    """
    # Check if we have the ZIP
    if property_id not in _zip_cache:
        raise HTTPException(status_code=404, detail="No ZIP available. Run /research first.")
    
    # Production mode: redirect to signed URL from object store
    if CFG["STORAGE_MODE"] == "cloud":
        object_key = f"research/{property_id}/evidence.zip"
        signed_url = generate_signed_url(object_key)
        if signed_url:
            return RedirectResponse(url=signed_url, status_code=302)
    
    # Development mode: stream from memory
    filename = f"{property_id}_evidence.zip"
    return StreamingResponse(
        io.BytesIO(_zip_cache[property_id]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
@router.get("/fraud-flags/{property_id}")
async def get_fraud_flags(
    property_id: str,
    user: StorageUser = Depends(require_user),
):
    """Get fraud flags for a researched property"""
    if property_id not in _research_cache:
        raise HTTPException(status_code=404, detail="Profile not found. Run /research first.")
    
    profile = _research_cache[property_id]
    return {
        "property_id": property_id,
        "fraud_flags": profile.get("fraud_flags", []),
        "risk_score": profile.get("risk_score", 0),
    }


@router.get("/summary/{property_id}")
async def get_summary(
    property_id: str,
    user: StorageUser = Depends(require_user),
):
    """Get a summary of research findings"""
    if property_id not in _research_cache:
        raise HTTPException(status_code=404, detail="Profile not found. Run /research first.")
    
    profile = _research_cache[property_id]
    return {
        "property_id": property_id,
        "owner_name": profile.get("owner_name"),
        "site_address": profile.get("site_address"),
        "risk_score": profile.get("risk_score", 0),
        "counts": {
            "liens": len(profile.get("liens", [])),
            "ucc_filings": len(profile.get("ucc_filings", [])),
            "deeds": len(profile.get("deeds", [])),
            "emergency_calls": len(profile.get("emergency_calls", [])),
            "news_mentions": len(profile.get("news_mentions", [])),
            "bankruptcy_cases": len(profile.get("bankruptcy_cases", [])),
            "fraud_flags": len(profile.get("fraud_flags", [])),
        },
        "entity_status": profile.get("entity_info", {}).get("status", "Unknown"),
        "has_insurance": bool(profile.get("insurance", {}).get("policies")),
    }


@router.get("/demo-properties")
async def list_demo_properties():
    """List available demo properties for testing"""
    return {
        "demo_properties": [
            {
                "property_id": pid,
                "owner": data.get("owner_name"),
                "address": data.get("site_address"),
                "description": "High risk" if pid == "19-116-21-44-0025" else "Low risk" if pid == "27-028-24-31-0001" else "Demo"
            }
            for pid, data in MOCK_PROPERTIES.items()
        ]
    }


@router.get("/labels")
async def get_i18n_labels(
    lang: str = Query("en", description="Language code: en, es, so, hmn")
):
    """
    Get i18n labels for UI rendering.
    
    Supported languages:
    - en: English (default)
    - es: Spanish / Español
    - so: Somali / Soomaali
    - hmn: Hmong / Hmoob
    """
    return {
        "language": lang,
        "labels": get_labels(lang),
        "supported_languages": list(I18N_LABELS.keys()),
    }


@router.get("/config")
async def get_config():
    """
    Get current configuration (non-sensitive values only).
    
    Useful for debugging and verifying environment setup.
    """
    return {
        "use_mock_data": CFG["USE_MOCK_DATA"],
        "enable_real_apis": CFG["ENABLE_REAL_APIS"],
        "storage_mode": CFG["STORAGE_MODE"],
        "http_timeout": CFG["HTTP_TIMEOUT"],
        "http_retries": CFG["HTTP_RETRIES"],
        "endpoints": {
            "assessor": CFG["ASSESSOR_BASE"],
            "recorder": CFG["RECORDER_BASE"],
            "ucc": CFG["UCC_BASE"],
            "dispatch": CFG["DISPATCH_BASE"],
            "news": CFG["NEWS_BASE"],
            "sos": CFG["SOS_BASE"],
            "bankruptcy": CFG["BANKRUPTCY_BASE"],
            "insurance": CFG["INSURANCE_BASE"],
        },
        "api_keys_configured": {
            "assessor": bool(CFG["ASSESSOR_API_KEY"]),
            "recorder": bool(CFG["RECORDER_API_KEY"]),
            "ucc": bool(CFG["UCC_API_KEY"]),
            "dispatch": bool(CFG["DISPATCH_API_KEY"]),
            "news": bool(CFG["NEWS_API_KEY"]),
            "sos": bool(CFG["SOS_API_KEY"]),
            "bankruptcy": bool(CFG["BANKRUPTCY_API_KEY"]),
            "insurance": bool(CFG["INSURANCE_API_KEY"]),
        },
    }
# =============================================================================
# MODULE INITIALIZATION
# =============================================================================
def initialize():
    logger.info("✅ Research Module SDK initialized")


initialize()
