"""
Semptify Free API Pack — v1.0
FastAPI Router

All endpoints mounted at /freeapi/*
"""

from fastapi import APIRouter

from app.modules.free_api_pack import api

router = APIRouter(prefix="/freeapi", tags=["Free API Pack"])


# ---------------- PROPERTY LOOKUP ----------------

@router.get("/property/parcel")
def property_parcel(county: str, parcel_id: str):
    """Lookup parcel by county and parcel ID."""
    return api.property.lookup_parcel(county, parcel_id)


@router.get("/property/address")
def property_address(county: str, address: str):
    """Lookup property by county and address."""
    return api.property.lookup_address(county, address)


# ---------------- LANDLORD LOOKUP ----------------

@router.get("/landlord/business")
def landlord_business(name: str):
    """Search MN Secretary of State business records."""
    return api.landlord.lookup_business(name)


@router.get("/landlord/owner")
def landlord_owner(property_id: str):
    """Lookup property owner via HUD/county records."""
    return api.landlord.lookup_owner(property_id)


# ---------------- COURT SCRAPER ----------------

@router.get("/courts/evictions")
def court_evictions(name: str):
    """Search MN court eviction records by party name."""
    return api.courts.search_evictions(name)


@router.get("/courts/federal")
def court_federal(query: str):
    """Search federal court cases via CourtListener."""
    return api.courts.fetch_federal_cases(query)


# ---------------- VIOLATIONS ----------------

@router.get("/violations/city")
def city_violations(city: str, address: str):
    """Lookup city inspection violations for an address."""
    return api.violations.city_inspections(city, address)


@router.get("/violations/environment")
def env_violations(facility: str):
    """Lookup EPA/MPCA environmental violations."""
    return api.violations.environmental_violations(facility)


# ---------------- INSPECTIONS ----------------

@router.get("/inspections/hud")
def hud_inspection(property_id: str):
    """Lookup HUD REAC inspection scores."""
    return api.inspections.hud_reac(property_id)


@router.get("/inspections/local")
def local_inspection(city: str, address: str):
    """Lookup local inspection records."""
    return api.inspections.local_inspections(city, address)


# ---------------- STATUTES ----------------

@router.get("/statutes")
def statute(section: str):
    """Retrieve MN statute text by section number."""
    return api.statutes.get_statute(section)
