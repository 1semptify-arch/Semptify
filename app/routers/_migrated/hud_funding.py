"""
HUD Funding & Tax Credit Guide Router
=====================================

API endpoints for searching HUD funding programs, tax credits,
landlord eligibility requirements, and tenant recourse options.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from app.services.hud_funding_guide import (
    HUDFundingGuideService,
    get_hud_funding_guide,
    ProgramType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hud-funding", tags=["HUD Funding Guide"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class ProgramSummary(BaseModel):
    """Brief program summary."""
    id: str
    name: str
    program_type: str
    description: str
    benefit_to_landlord: str
    rent_restrictions: str
    affordability_years: int


class LandlordObligation(BaseModel):
    """Landlord requirement detail."""
    requirement: str
    description: str
    penalty: str
    tenant_recourse: str


class TenantRecourse(BaseModel):
    """What tenant can do if landlord violates."""
    violation_type: str
    description: str
    what_tenant_can_do: str
    landlord_penalty: str


class EligibilityCheck(BaseModel):
    """Tenant eligibility check request."""
    annual_income: float
    area_median_income: float
    household_size: int = 1


# =============================================================================
# PROGRAM ENDPOINTS
# =============================================================================

@router.get("/programs")
async def list_all_programs(
    program_type: Optional[str] = Query(None, description="Filter by type: tax_credit, grant, loan, voucher, subsidy"),
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[ProgramSummary]:
    """
    📋 List all HUD funding and tax credit programs.
    
    Optionally filter by program type.
    """
    if program_type:
        try:
            ptype = ProgramType(program_type)
            programs = service.get_programs_by_type(ptype)
        except ValueError:
            raise HTTPException(400, f"Invalid program type: {program_type}")
    else:
        programs = service.get_all_programs()
    
    return [
        ProgramSummary(
            id=p.id,
            name=p.name,
            program_type=p.program_type.value,
            description=p.description,
            benefit_to_landlord=p.benefit_to_landlord,
            rent_restrictions=p.rent_restrictions,
            affordability_years=p.affordability_period_years,
        )
        for p in programs
    ]


@router.get("/programs/{program_id}")
async def get_program_details(
    program_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    📊 Get full details for a specific program.
    
    Includes landlord eligibility, tenant requirements,
    landlord obligations, compliance info, and resources.
    """
    program = service.get_program(program_id)
    if not program:
        raise HTTPException(404, f"Program not found: {program_id}")
    
    return program.to_dict()


@router.get("/programs/{program_id}/summary")
async def get_program_summary(
    program_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    📝 Get a concise summary of a program.
    """
    summary = service.get_program_summary(program_id)
    if not summary:
        raise HTTPException(404, f"Program not found: {program_id}")
    return summary


@router.get("/search")
async def search_programs(
    q: str = Query(..., description="Search query"),
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[ProgramSummary]:
    """
    🔍 Search programs by keyword.
    
    Searches program names, descriptions, and eligibility requirements.
    """
    programs = service.search_programs(q)
    return [
        ProgramSummary(
            id=p.id,
            name=p.name,
            program_type=p.program_type.value,
            description=p.description,
            benefit_to_landlord=p.benefit_to_landlord,
            rent_restrictions=p.rent_restrictions,
            affordability_years=p.affordability_period_years,
        )
        for p in programs
    ]


# =============================================================================
# CATEGORY ENDPOINTS
# =============================================================================

@router.get("/tax-credits")
async def list_tax_credit_programs(
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[ProgramSummary]:
    """
    💰 List all tax credit programs.
    
    Includes LIHTC, Historic Tax Credit, etc.
    """
    programs = service.get_tax_credit_programs()
    return [
        ProgramSummary(
            id=p.id,
            name=p.name,
            program_type=p.program_type.value,
            description=p.description,
            benefit_to_landlord=p.benefit_to_landlord,
            rent_restrictions=p.rent_restrictions,
            affordability_years=p.affordability_period_years,
        )
        for p in programs
    ]


@router.get("/voucher-programs")
async def list_voucher_programs(
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[ProgramSummary]:
    """
    🏠 List Section 8 and other voucher programs.
    """
    programs = service.get_voucher_programs()
    return [
        ProgramSummary(
            id=p.id,
            name=p.name,
            program_type=p.program_type.value,
            description=p.description,
            benefit_to_landlord=p.benefit_to_landlord,
            rent_restrictions=p.rent_restrictions,
            affordability_years=p.affordability_period_years,
        )
        for p in programs
    ]


@router.get("/grants")
async def list_grant_programs(
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[ProgramSummary]:
    """
    💵 List grant programs (Section 202, 811, HOME, CDBG).
    """
    programs = service.get_grant_programs()
    return [
        ProgramSummary(
            id=p.id,
            name=p.name,
            program_type=p.program_type.value,
            description=p.description,
            benefit_to_landlord=p.benefit_to_landlord,
            rent_restrictions=p.rent_restrictions,
            affordability_years=p.affordability_period_years,
        )
        for p in programs
    ]


# =============================================================================
# LANDLORD REQUIREMENTS
# =============================================================================

@router.get("/programs/{program_id}/landlord-requirements")
async def get_landlord_requirements(
    program_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[LandlordObligation]:
    """
    📜 Get what a landlord MUST do to qualify for and maintain a program.
    
    Includes penalties for violations and what tenants can do.
    """
    program = service.get_program(program_id)
    if not program:
        raise HTTPException(404, f"Program not found: {program_id}")
    
    return [
        LandlordObligation(
            requirement=lo.requirement,
            description=lo.description,
            penalty=lo.penalty_for_violation,
            tenant_recourse=lo.tenant_recourse,
        )
        for lo in program.landlord_obligations
    ]


@router.get("/programs/{program_id}/landlord-eligibility")
async def get_landlord_eligibility(
    program_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    ✅ Get landlord eligibility requirements for a program.
    
    What the landlord must have/do to APPLY for the program.
    """
    program = service.get_program(program_id)
    if not program:
        raise HTTPException(404, f"Program not found: {program_id}")
    
    return {
        "program": program.name,
        "eligibility_requirements": program.landlord_eligibility,
        "property_requirements": program.property_requirements,
        "application_url": program.application_url,
        "administering_agency": program.administering_agency,
        "mn_administrator": program.mn_administrator,
        "mn_contact": program.mn_contact,
    }


@router.get("/all-landlord-obligations")
async def get_all_landlord_obligations(
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, List[Dict]]:
    """
    📋 Get ALL landlord obligations across ALL programs.
    
    Useful for understanding what your landlord should be doing
    if they're receiving any government funding.
    """
    return service.get_all_landlord_obligations()


# =============================================================================
# TENANT RECOURSE
# =============================================================================

@router.get("/programs/{program_id}/tenant-recourse")
async def get_tenant_recourse(
    program_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[TenantRecourse]:
    """
    ⚖️ Get what a tenant can do if landlord violates program requirements.
    
    This is your ammunition if your landlord is getting government
    money but not following the rules.
    """
    recourse = service.get_tenant_recourse_options(program_id)
    if not recourse:
        raise HTTPException(404, f"Program not found: {program_id}")
    
    return [
        TenantRecourse(
            violation_type=r["violation_type"],
            description=r["description"],
            what_tenant_can_do=r["what_tenant_can_do"],
            landlord_penalty=r["landlord_penalty"],
        )
        for r in recourse
    ]


# =============================================================================
# TAX BREAKS
# =============================================================================

@router.get("/tax-breaks")
async def list_tax_breaks(
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[Dict[str, Any]]:
    """
    💰 List general tax breaks available to rental property owners.
    
    These are standard deductions/credits available to ALL landlords,
    not program-specific benefits.
    """
    return service.get_all_tax_breaks()


@router.get("/tax-breaks/{tax_break_id}")
async def get_tax_break(
    tax_break_id: str,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    📊 Get details on a specific tax break.
    """
    tax_break = service.get_tax_break(tax_break_id)
    if not tax_break:
        raise HTTPException(404, f"Tax break not found: {tax_break_id}")
    return tax_break


# =============================================================================
# ELIGIBILITY CHECKING
# =============================================================================

@router.post("/check-eligibility")
async def check_tenant_eligibility(
    check: EligibilityCheck,
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    🔍 Check which programs a tenant might be eligible for.
    
    Provide annual income and Area Median Income (AMI) for your location.
    AMI can be found at: https://www.huduser.gov/portal/datasets/il.html
    """
    eligible = service.check_tenant_eligibility(
        income=check.annual_income,
        ami=check.area_median_income,
        household_size=check.household_size,
    )
    
    percent_ami = (check.annual_income / check.area_median_income) * 100
    
    return {
        "your_income": check.annual_income,
        "area_median_income": check.area_median_income,
        "your_percent_of_ami": round(percent_ami, 1),
        "income_category": (
            "Extremely Low Income (≤30% AMI)" if percent_ami <= 30 else
            "Very Low Income (≤50% AMI)" if percent_ami <= 50 else
            "Low Income (≤60% AMI)" if percent_ami <= 60 else
            "Low-Moderate Income (≤80% AMI)" if percent_ami <= 80 else
            "Above Low Income (>80% AMI)"
        ),
        "eligible_programs": eligible,
        "total_eligible": len(eligible),
    }


@router.get("/check-property")
async def check_property_programs(
    address: str = Query(..., description="Property address"),
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> Dict[str, Any]:
    """
    🏢 Get resources to check what programs a property participates in.
    
    NOTE: This provides links to official databases where you can search.
    Actual property lookup would require integration with HUD APIs.
    """
    return service.check_property_programs(address)


# =============================================================================
# COMPARISON
# =============================================================================

@router.get("/compare")
async def compare_programs(
    programs: str = Query(..., description="Comma-separated program IDs"),
    service: HUDFundingGuideService = Depends(get_hud_funding_guide),
) -> List[Dict[str, Any]]:
    """
    📊 Compare multiple programs side by side.
    
    Example: /compare?programs=lihtc_9_percent,section_8_pbv,home_program
    """
    program_ids = [p.strip() for p in programs.split(",")]
    return service.get_comparison_table(program_ids)


# =============================================================================
# QUICK REFERENCE
# =============================================================================

@router.get("/quick-reference")
async def quick_reference() -> Dict[str, Any]:
    """
    📚 Quick reference guide for understanding HUD programs.
    """
    return {
        "income_categories": {
            "extremely_low_income": "≤30% of Area Median Income (AMI)",
            "very_low_income": "≤50% of AMI",
            "low_income": "≤60% or ≤80% of AMI depending on program",
        },
        "common_programs": {
            "LIHTC": "Low-Income Housing Tax Credit - 9% or 4%, most common affordable housing program",
            "Section 8 PBV": "Project-Based Vouchers - attached to specific units",
            "Section 8 HCV": "Housing Choice Vouchers - tenant-based, moves with you",
            "Section 202": "Elderly housing (62+)",
            "Section 811": "Disabled housing",
            "HOME": "Block grant for affordable housing",
            "CDBG": "Community Development Block Grant",
        },
        "what_to_look_for": [
            "Ask landlord: 'Is this property LIHTC, Section 8, or receive any government funding?'",
            "Check lease for income certification requirements",
            "Look for HUD or state housing finance agency logos",
            "Search HUD LIHTC database for property",
            "Check if rent is below market rate (may indicate subsidized)",
        ],
        "tenant_rights_in_subsidized_housing": [
            "Rent limited to 30% of income (in most programs)",
            "Annual income recertification",
            "Housing Quality Standards must be maintained",
            "Cannot be evicted except for good cause",
            "Fair housing protections apply",
            "Report violations to program administrator",
        ],
        "resources": {
            "hud_lihtc_database": "https://lihtc.huduser.gov/",
            "ami_lookup": "https://www.huduser.gov/portal/datasets/il.html",
            "mn_housing": "https://www.mnhousing.gov/",
            "hud_minneapolis": "https://www.hud.gov/states/minnesota",
        },
    }
