"""
Free API Module — Public data lookups for tenant rights research.

Public API:
    from app.modules.free_api import MANIFEST, router
    register_module(app, MANIFEST)

Endpoints (all under /freeapi):
    /property/parcel      — Parcel lookup
    /property/address     — Address lookup
    /landlord/business    — MN business records
    /landlord/owner       — Property owner lookup
    /courts/evictions     — Court eviction search
    /courts/federal       — Federal court cases
    /violations/city      — City inspection violations
    /violations/environment — EPA/MPCA violations
    /inspections/hud      — HUD REAC scores
    /inspections/local    — Local inspection records
    /statutes             — MN statute lookup
"""

from .manifest import MANIFEST
from .router import router

__all__ = ["MANIFEST", "router"]
