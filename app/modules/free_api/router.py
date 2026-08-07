"""
Semptify Free API Pack — v1.0
FastAPI Router

Migrated from app/routers/free_api.py into the free_api SDK module.
All endpoints mounted at /freeapi/*
"""

import logging

from fastapi import APIRouter

from app.modules.free_api_pack import api

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/freeapi", tags=["Free API Pack"])


# ---------------- PROPERTY LOOKUP ----------------


@router.get("/property/parcel")
async def property_parcel(county: str, parcel_id: str):
    """Lookup parcel by county and parcel ID."""
    return await api.property.lookup_parcel(county, parcel_id)


@router.get("/property/address")
async def property_address(county: str, address: str):
    """Lookup property by county and address."""
    return await api.property.lookup_address(county, address)


# ---------------- LANDLORD LOOKUP ----------------


@router.get("/landlord/business")
async def landlord_business(name: str):
    """Search MN Secretary of State business records."""
    return await api.landlord.lookup_business(name)


@router.get("/landlord/owner")
async def landlord_owner(property_id: str):
    """Lookup property owner via HUD/county records."""
    return await api.landlord.lookup_owner(property_id)


# ---------------- COURT SCRAPER ----------------


@router.get("/courts/evictions")
async def court_evictions(name: str):
    """Search MN court eviction records by party name."""
    return await api.courts.search_evictions(name)


@router.get("/courts/federal")
async def court_federal(query: str):
    """Search federal court cases via CourtListener."""
    return await api.courts.fetch_federal_cases(query)


# ---------------- VIOLATIONS ----------------


@router.get("/violations/city")
async def city_violations(city: str, address: str):
    """Lookup city inspection violations for an address."""
    return await api.violations.city_inspections(city, address)


@router.get("/violations/environment")
async def env_violations(facility: str):
    """Lookup EPA/MPCA environmental violations."""
    return await api.violations.environmental_violations(facility)


# ---------------- INSPECTIONS ----------------


@router.get("/inspections/hud")
async def hud_inspection(property_id: str):
    """Lookup HUD REAC inspection scores."""
    return await api.inspections.hud_reac(property_id)


@router.get("/inspections/local")
async def local_inspection(city: str, address: str):
    """Lookup local inspection records."""
    return await api.inspections.local_inspections(city, address)


# ---------------- STATUTES ----------------


@router.get("/statutes")
async def statute(section: str):
    """Retrieve MN statute text by section number."""
    return await api.statutes.get_statute(section)
