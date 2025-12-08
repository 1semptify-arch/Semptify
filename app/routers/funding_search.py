"""
Funding & Tax Credit Search Router
Search for LIHTC, NMTC, HUD funding, tax credits, and financing by company, address, or broker
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
import logging
import uuid

from app.core.security import require_user, StorageUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/funding", tags=["Funding & Tax Credit Search"])

# =============================================================================
# ENUMS AND MODELS
# =============================================================================

class FundingProgramType(str, Enum):
    LIHTC = "lihtc"  # Low-Income Housing Tax Credit
    NMTC = "nmtc"  # New Markets Tax Credit
    HISTORIC = "historic"  # Historic Rehabilitation Tax Credit
    OPPORTUNITY_ZONE = "opportunity_zone"
    SECTION_179D = "section_179d"  # Energy Deduction
    SECTION_48_ITC = "section_48_itc"  # Investment Tax Credit
    HUD_PBV = "hud_pbv"  # Project-Based Vouchers
    HUD_202 = "hud_202"  # Section 202 Supportive Housing for Elderly
    HUD_811 = "hud_811"  # Section 811 Supportive Housing for Disabled
    HOME = "home"  # HOME Investment Partnerships
    CDBG = "cdbg"  # Community Development Block Grant
    FANNIE_MAE = "fannie_mae"
    FREDDIE_MAC = "freddie_mac"
    STATE_LIHTC = "state_lihtc"
    STATE_HISTORIC = "state_historic"
    TAX_EXEMPT_BONDS = "tax_exempt_bonds"

class SearchType(str, Enum):
    ADDRESS = "address"
    COMPANY = "company"
    BROKER = "broker"
    PROGRAM = "program"
    ALL = "all"

class PropertySearchRequest(BaseModel):
    query: str
    search_type: SearchType = SearchType.ALL
    programs: Optional[List[FundingProgramType]] = None
    state: Optional[str] = "MN"
    city: Optional[str] = None
    include_expired: bool = False

class FundingRecord(BaseModel):
    id: str
    property_address: str
    property_name: Optional[str] = None
    city: str
    state: str
    zip_code: Optional[str] = None
    county: Optional[str] = None
    
    # Owner/Company info
    owner_company: str
    owner_type: Optional[str] = None  # LLC, Corporation, Trust, etc.
    
    # Broker/Agent info
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_license: Optional[str] = None
    
    # Program details
    program_type: FundingProgramType
    program_name: str
    application_date: Optional[str] = None
    approval_date: Optional[str] = None
    placed_in_service_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: str  # applied, approved, active, expired, revoked
    
    # Financial details
    credit_amount: Optional[float] = None
    loan_amount: Optional[float] = None
    subsidy_amount: Optional[float] = None
    total_project_cost: Optional[float] = None
    
    # Unit/Property details
    total_units: Optional[int] = None
    affordable_units: Optional[int] = None
    ami_targeting: Optional[str] = None  # e.g., "60% AMI"
    
    # Qualification details
    qualification_requirements: List[str] = []
    compliance_period: Optional[str] = None
    annual_reporting_required: bool = False
    
    # Source/Reference
    data_source: str
    source_url: Optional[str] = None
    last_updated: str

# =============================================================================
# SAMPLE DATA (In production, this would come from database/external APIs)
# =============================================================================

SAMPLE_FUNDING_RECORDS: List[Dict[str, Any]] = [
    {
        "id": "lihtc_mn_001",
        "property_address": "1234 Cedar Ave S",
        "property_name": "Cedar Commons Apartments",
        "city": "Minneapolis",
        "state": "MN",
        "zip_code": "55404",
        "county": "Hennepin",
        "owner_company": "Cedar Housing Partners LLC",
        "owner_type": "LLC",
        "broker_name": "John Anderson",
        "broker_company": "MN Housing Advisors",
        "broker_license": "MN-RE-123456",
        "program_type": "lihtc",
        "program_name": "Low-Income Housing Tax Credit (9%)",
        "application_date": "2022-03-15",
        "approval_date": "2022-08-01",
        "placed_in_service_date": "2024-06-15",
        "expiration_date": "2039-06-15",
        "status": "active",
        "credit_amount": 1250000.00,
        "total_project_cost": 15000000.00,
        "total_units": 100,
        "affordable_units": 100,
        "ami_targeting": "60% AMI",
        "qualification_requirements": [
            "All units restricted to households at or below 60% AMI",
            "15-year compliance period",
            "Extended use period of 30 years",
            "Annual income certifications required",
            "Physical inspections every 3 years"
        ],
        "compliance_period": "15 years (extended: 30 years)",
        "annual_reporting_required": True,
        "data_source": "Minnesota Housing Finance Agency",
        "source_url": "https://www.mnhousing.gov",
        "last_updated": "2024-12-01"
    },
    {
        "id": "lihtc_mn_002",
        "property_address": "5678 University Ave",
        "property_name": "University Village",
        "city": "St. Paul",
        "state": "MN",
        "zip_code": "55104",
        "county": "Ramsey",
        "owner_company": "Dominium Management",
        "owner_type": "Corporation",
        "broker_name": "Sarah Johnson",
        "broker_company": "Affordable Housing Partners",
        "broker_license": "MN-RE-789012",
        "program_type": "lihtc",
        "program_name": "Low-Income Housing Tax Credit (4%)",
        "application_date": "2021-06-01",
        "approval_date": "2021-11-15",
        "placed_in_service_date": "2023-09-01",
        "status": "active",
        "credit_amount": 850000.00,
        "loan_amount": 8000000.00,
        "total_project_cost": 12000000.00,
        "total_units": 80,
        "affordable_units": 64,
        "ami_targeting": "50% AMI (40 units), 60% AMI (24 units)",
        "qualification_requirements": [
            "80% of units affordable at 60% AMI or below",
            "Tax-exempt bond financing required",
            "15-year compliance period",
            "Income averaging allowed"
        ],
        "compliance_period": "15 years",
        "annual_reporting_required": True,
        "data_source": "Minnesota Housing Finance Agency",
        "source_url": "https://www.mnhousing.gov",
        "last_updated": "2024-11-15"
    },
    {
        "id": "hud_pbv_001",
        "property_address": "900 Portland Ave",
        "property_name": "Portland Place",
        "city": "Minneapolis",
        "state": "MN",
        "zip_code": "55404",
        "county": "Hennepin",
        "owner_company": "CommonBond Communities",
        "owner_type": "Non-Profit",
        "broker_name": None,
        "broker_company": None,
        "program_type": "hud_pbv",
        "program_name": "HUD Project-Based Vouchers",
        "application_date": "2020-01-15",
        "approval_date": "2020-06-01",
        "placed_in_service_date": "2020-09-01",
        "expiration_date": "2040-09-01",
        "status": "active",
        "subsidy_amount": 450000.00,
        "total_units": 50,
        "affordable_units": 50,
        "ami_targeting": "30% AMI",
        "qualification_requirements": [
            "All units for households at 30% AMI or below",
            "20-year HAP contract",
            "HUD physical inspections annually",
            "Tenant income recertification annually",
            "Fair Housing compliance required"
        ],
        "compliance_period": "20 years (renewable)",
        "annual_reporting_required": True,
        "data_source": "HUD Multifamily Database",
        "source_url": "https://www.hud.gov/program_offices/housing/mfh",
        "last_updated": "2024-12-01"
    },
    {
        "id": "nmtc_mn_001",
        "property_address": "2100 Lake Street E",
        "property_name": "Lake Street Commons",
        "city": "Minneapolis",
        "state": "MN",
        "zip_code": "55407",
        "county": "Hennepin",
        "owner_company": "Urban Development Partners",
        "owner_type": "LLC",
        "broker_name": "Michael Chen",
        "broker_company": "CDFI Capital Advisors",
        "broker_license": "MN-RE-345678",
        "program_type": "nmtc",
        "program_name": "New Markets Tax Credit",
        "application_date": "2022-09-01",
        "approval_date": "2023-02-15",
        "placed_in_service_date": "2024-03-01",
        "status": "active",
        "credit_amount": 2000000.00,
        "total_project_cost": 8000000.00,
        "total_units": 40,
        "affordable_units": 16,
        "ami_targeting": "80% AMI (affordable set-aside)",
        "qualification_requirements": [
            "Located in qualified low-income census tract",
            "7-year compliance period",
            "40% of units affordable at 80% AMI",
            "Community impact reporting required",
            "CDE allocation through Greater MN Housing Fund"
        ],
        "compliance_period": "7 years",
        "annual_reporting_required": True,
        "data_source": "CDFI Fund",
        "source_url": "https://www.cdfifund.gov/programs-training/programs/new-markets-tax-credit",
        "last_updated": "2024-10-15"
    },
    {
        "id": "historic_mn_001",
        "property_address": "350 Market Street",
        "property_name": "Historic Market Building",
        "city": "St. Paul",
        "state": "MN",
        "zip_code": "55102",
        "county": "Ramsey",
        "owner_company": "Historic Preservation LLC",
        "owner_type": "LLC",
        "broker_name": "Emily Williams",
        "broker_company": "Heritage Real Estate",
        "broker_license": "MN-RE-567890",
        "program_type": "historic",
        "program_name": "Federal Historic Rehabilitation Tax Credit (20%)",
        "application_date": "2021-04-01",
        "approval_date": "2021-12-15",
        "placed_in_service_date": "2023-06-01",
        "status": "active",
        "credit_amount": 1800000.00,
        "total_project_cost": 9000000.00,
        "total_units": 35,
        "qualification_requirements": [
            "Building listed on National Register of Historic Places",
            "Certified rehabilitation by NPS",
            "Substantial rehabilitation test (QRE > adjusted basis)",
            "5-year recapture period",
            "Secretary of Interior's Standards compliance"
        ],
        "compliance_period": "5 years (recapture period)",
        "annual_reporting_required": False,
        "data_source": "National Park Service",
        "source_url": "https://www.nps.gov/subjects/taxincentives",
        "last_updated": "2024-09-01"
    },
    {
        "id": "oz_mn_001",
        "property_address": "1500 Central Ave NE",
        "property_name": "Central Avenue Lofts",
        "city": "Minneapolis",
        "state": "MN",
        "zip_code": "55413",
        "county": "Hennepin",
        "owner_company": "Opportunity Fund I LLC",
        "owner_type": "Qualified Opportunity Fund",
        "broker_name": "David Martinez",
        "broker_company": "OZ Investment Group",
        "broker_license": "MN-RE-901234",
        "program_type": "opportunity_zone",
        "program_name": "Qualified Opportunity Zone Investment",
        "application_date": "2023-01-15",
        "approval_date": "2023-03-01",
        "placed_in_service_date": "2024-08-01",
        "status": "active",
        "total_project_cost": 6500000.00,
        "total_units": 30,
        "qualification_requirements": [
            "Located in designated Opportunity Zone census tract",
            "90% asset test (quarterly)",
            "Substantial improvement within 30 months",
            "Hold for 10+ years for maximum benefit",
            "QOF certification with IRS Form 8996"
        ],
        "compliance_period": "10 years (for full exclusion)",
        "annual_reporting_required": True,
        "data_source": "IRS / Treasury",
        "source_url": "https://www.irs.gov/credits-deductions/opportunity-zones",
        "last_updated": "2024-11-01"
    },
    {
        "id": "lihtc_dakota_001",
        "property_address": "4500 Pilot Knob Rd",
        "property_name": "Eagan Affordable Housing",
        "city": "Eagan",
        "state": "MN",
        "zip_code": "55122",
        "county": "Dakota",
        "owner_company": "Dakota County Housing Authority",
        "owner_type": "Housing Authority",
        "broker_name": "Jennifer Lee",
        "broker_company": "Twin Cities Housing Consultants",
        "broker_license": "MN-RE-112233",
        "program_type": "lihtc",
        "program_name": "Low-Income Housing Tax Credit (9%)",
        "application_date": "2023-02-01",
        "approval_date": "2023-07-15",
        "placed_in_service_date": "2025-01-15",
        "status": "approved",
        "credit_amount": 950000.00,
        "total_project_cost": 11000000.00,
        "total_units": 60,
        "affordable_units": 60,
        "ami_targeting": "50% AMI (30 units), 60% AMI (30 units)",
        "qualification_requirements": [
            "All units restricted to 60% AMI or below",
            "Income averaging election",
            "15-year compliance period",
            "Dakota County preference for local residents",
            "Accessibility requirements (5% mobility, 2% sensory)"
        ],
        "compliance_period": "15 years (extended: 30 years)",
        "annual_reporting_required": True,
        "data_source": "Minnesota Housing Finance Agency",
        "source_url": "https://www.mnhousing.gov",
        "last_updated": "2024-12-05"
    },
    {
        "id": "section_179d_001",
        "property_address": "7890 France Ave S",
        "property_name": "Green Tower Apartments",
        "city": "Edina",
        "state": "MN",
        "zip_code": "55435",
        "county": "Hennepin",
        "owner_company": "Sustainable Properties Inc",
        "owner_type": "Corporation",
        "broker_name": "Robert Thompson",
        "broker_company": "Green Building Advisors",
        "program_type": "section_179d",
        "program_name": "Section 179D Energy Efficient Commercial Building Deduction",
        "application_date": "2024-01-15",
        "approval_date": "2024-04-01",
        "status": "active",
        "credit_amount": 375000.00,
        "total_project_cost": 5000000.00,
        "total_units": 45,
        "qualification_requirements": [
            "25% energy savings vs ASHRAE 90.1-2007 baseline",
            "Certification by qualified professional",
            "Building treated as commercial for tax purposes",
            "IRA enhanced deduction up to $5/sq ft available",
            "Prevailing wage requirements for full deduction"
        ],
        "compliance_period": "N/A (one-time deduction)",
        "annual_reporting_required": False,
        "data_source": "IRS",
        "source_url": "https://www.irs.gov/credits-deductions/energy-efficient-commercial-buildings-deduction",
        "last_updated": "2024-06-01"
    }
]

# =============================================================================
# PROGRAM INFORMATION DATABASE
# =============================================================================

PROGRAM_INFO: Dict[str, Dict[str, Any]] = {
    "lihtc": {
        "name": "Low-Income Housing Tax Credit (LIHTC)",
        "description": "Primary federal tool to finance affordable rental construction and rehabilitation",
        "administering_agency": "IRS (allocated by state housing agencies)",
        "credit_type": "Tax Credit",
        "typical_amount": "9% credit (competitive) or 4% credit (as-of-right with bonds)",
        "compliance_period": "15 years (extended use: 30 years)",
        "income_limits": "Typically 60% AMI or below",
        "key_requirements": [
            "Rent restrictions for qualified units",
            "Annual tenant income certification",
            "Physical property standards",
            "Non-discrimination requirements",
            "Extended use agreement recorded"
        ],
        "mn_administrator": "Minnesota Housing Finance Agency",
        "application_deadlines": "Annual QAP cycle (typically February)",
        "resources": [
            {"name": "MHFA LIHTC Program", "url": "https://www.mnhousing.gov/sites/multifamily/lihtc"},
            {"name": "Novogradac LIHTC Map", "url": "https://www.novoco.com/resource-centers/affordable-housing-tax-credits/lihtc-property-database"}
        ]
    },
    "nmtc": {
        "name": "New Markets Tax Credit (NMTC)",
        "description": "Attracts private capital to projects in low-income communities",
        "administering_agency": "CDFI Fund (Treasury)",
        "credit_type": "Tax Credit",
        "typical_amount": "39% of investment over 7 years",
        "compliance_period": "7 years",
        "income_limits": "Located in qualified census tract",
        "key_requirements": [
            "Investment through Community Development Entity (CDE)",
            "Qualified Low-Income Community Investment (QLICI)",
            "7-year compliance period",
            "Community impact reporting"
        ],
        "mn_administrator": "Various CDEs (Greater MN Housing Fund, etc.)",
        "application_deadlines": "CDE allocation rounds (varies)",
        "resources": [
            {"name": "CDFI Fund NMTC", "url": "https://www.cdfifund.gov/programs-training/programs/new-markets-tax-credit"},
            {"name": "Novogradac NMTC Map", "url": "https://www.novoco.com/resource-centers/new-markets-tax-credits"}
        ]
    },
    "historic": {
        "name": "Federal Historic Rehabilitation Tax Credit",
        "description": "20% credit for certified rehabilitation of income-producing historic buildings",
        "administering_agency": "National Park Service / IRS",
        "credit_type": "Tax Credit",
        "typical_amount": "20% of qualified rehabilitation expenditures",
        "compliance_period": "5 years (recapture period)",
        "key_requirements": [
            "Building listed on National Register (or in historic district)",
            "Certified rehabilitation by NPS",
            "Substantial rehabilitation test",
            "Secretary of Interior's Standards compliance",
            "Income-producing use"
        ],
        "mn_administrator": "State Historic Preservation Office (SHPO)",
        "resources": [
            {"name": "NPS Tax Incentives", "url": "https://www.nps.gov/subjects/taxincentives"},
            {"name": "MN SHPO", "url": "https://mn.gov/admin/shpo/"}
        ]
    },
    "opportunity_zone": {
        "name": "Qualified Opportunity Zone Investment",
        "description": "Capital gains deferral and potential exclusion for investments in designated zones",
        "administering_agency": "IRS / Treasury",
        "credit_type": "Tax Deferral/Exclusion",
        "typical_amount": "Deferral of capital gains; 10-year exclusion of new gains",
        "compliance_period": "10 years for maximum benefit",
        "key_requirements": [
            "Investment through Qualified Opportunity Fund (QOF)",
            "90% asset test quarterly",
            "Substantial improvement within 30 months",
            "Located in designated OZ census tract"
        ],
        "resources": [
            {"name": "IRS Opportunity Zones", "url": "https://www.irs.gov/credits-deductions/opportunity-zones"},
            {"name": "HUD OZ Map", "url": "https://opportunityzones.hud.gov/"}
        ]
    },
    "hud_pbv": {
        "name": "HUD Project-Based Vouchers",
        "description": "Rental assistance attached to specific housing units",
        "administering_agency": "HUD",
        "credit_type": "Rental Subsidy",
        "compliance_period": "15-20 year HAP contracts (renewable)",
        "income_limits": "30% to 50% AMI typically",
        "key_requirements": [
            "Housing Authority administration",
            "HUD physical inspections",
            "Annual income recertification",
            "Fair Housing compliance",
            "Tenant selection preferences allowed"
        ],
        "mn_administrator": "Local Housing Authorities",
        "resources": [
            {"name": "HUD PBV Program", "url": "https://www.hud.gov/program_offices/public_indian_housing/programs/hcv/project"}
        ]
    },
    "section_179d": {
        "name": "Section 179D Energy Efficient Commercial Building Deduction",
        "description": "Deduction for energy-efficient improvements to commercial buildings",
        "administering_agency": "IRS",
        "credit_type": "Tax Deduction",
        "typical_amount": "Up to $5/sq ft (IRA enhanced)",
        "key_requirements": [
            "25%+ energy savings vs baseline",
            "Certification by qualified professional",
            "Building treated as commercial",
            "Prevailing wage for full deduction (IRA)"
        ],
        "resources": [
            {"name": "IRS 179D", "url": "https://www.irs.gov/credits-deductions/energy-efficient-commercial-buildings-deduction"}
        ]
    }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def search_records(
    query: str,
    search_type: SearchType,
    programs: Optional[List[str]] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    include_expired: bool = False
) -> List[Dict[str, Any]]:
    """Search funding records by various criteria"""
    results = []
    query_lower = query.lower()
    
    for record in SAMPLE_FUNDING_RECORDS:
        # Filter by status if not including expired
        if not include_expired and record.get("status") == "expired":
            continue
        
        # Filter by state
        if state and record.get("state", "").upper() != state.upper():
            continue
        
        # Filter by city
        if city and city.lower() not in record.get("city", "").lower():
            continue
        
        # Filter by programs
        if programs and record.get("program_type") not in programs:
            continue
        
        # Search by type
        match = False
        if search_type == SearchType.ALL or search_type == SearchType.ADDRESS:
            if query_lower in record.get("property_address", "").lower():
                match = True
            if query_lower in record.get("property_name", "").lower():
                match = True
            if query_lower in record.get("city", "").lower():
                match = True
            if query_lower in record.get("zip_code", ""):
                match = True
        
        if search_type == SearchType.ALL or search_type == SearchType.COMPANY:
            if query_lower in record.get("owner_company", "").lower():
                match = True
        
        if search_type == SearchType.ALL or search_type == SearchType.BROKER:
            broker_name = record.get("broker_name", "") or ""
            broker_company = record.get("broker_company", "") or ""
            if query_lower in broker_name.lower() or query_lower in broker_company.lower():
                match = True
        
        if search_type == SearchType.PROGRAM:
            if query_lower in record.get("program_type", "").lower():
                match = True
            if query_lower in record.get("program_name", "").lower():
                match = True
        
        if match:
            results.append(record)
    
    return results

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/programs")
async def list_funding_programs():
    """List all available funding programs with details"""
    return {
        "programs": PROGRAM_INFO,
        "total": len(PROGRAM_INFO)
    }

@router.get("/programs/{program_type}")
async def get_program_details(program_type: FundingProgramType):
    """Get detailed information about a specific funding program"""
    if program_type.value not in PROGRAM_INFO:
        raise HTTPException(status_code=404, detail="Program not found")
    return PROGRAM_INFO[program_type.value]

@router.post("/search")
async def search_funding_records(
    request: PropertySearchRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Search for funding records by address, company, broker, or program.
    Returns matching records with full qualification details.
    """
    programs = [p.value for p in request.programs] if request.programs else None
    
    results = search_records(
        query=request.query,
        search_type=request.search_type,
        programs=programs,
        state=request.state,
        city=request.city,
        include_expired=request.include_expired
    )
    
    return {
        "query": request.query,
        "search_type": request.search_type.value,
        "filters": {
            "state": request.state,
            "city": request.city,
            "programs": programs,
            "include_expired": request.include_expired
        },
        "results": results,
        "total": len(results)
    }

@router.get("/search/address")
async def search_by_address(
    address: str = Query(..., description="Address or partial address to search"),
    state: str = Query("MN", description="State filter"),
    user: StorageUser = Depends(require_user)
):
    """Search funding records by property address"""
    results = search_records(address, SearchType.ADDRESS, state=state)
    return {"query": address, "results": results, "total": len(results)}

@router.get("/search/company")
async def search_by_company(
    company: str = Query(..., description="Company or owner name to search"),
    state: str = Query("MN", description="State filter"),
    user: StorageUser = Depends(require_user)
):
    """Search funding records by company/owner name"""
    results = search_records(company, SearchType.COMPANY, state=state)
    return {"query": company, "results": results, "total": len(results)}

@router.get("/search/broker")
async def search_by_broker(
    broker: str = Query(..., description="Broker name or company to search"),
    state: str = Query("MN", description="State filter"),
    user: StorageUser = Depends(require_user)
):
    """Search funding records by broker/agent"""
    results = search_records(broker, SearchType.BROKER, state=state)
    return {"query": broker, "results": results, "total": len(results)}

@router.get("/record/{record_id}")
async def get_funding_record(
    record_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get detailed funding record by ID"""
    for record in SAMPLE_FUNDING_RECORDS:
        if record["id"] == record_id:
            # Add program info
            program_type = record.get("program_type")
            program_info = PROGRAM_INFO.get(program_type, {})
            return {
                "record": record,
                "program_info": program_info
            }
    raise HTTPException(status_code=404, detail="Record not found")

@router.get("/statistics")
async def get_funding_statistics(
    state: str = Query("MN", description="State filter"),
    user: StorageUser = Depends(require_user)
):
    """Get funding statistics by program type"""
    stats = {}
    total_credits = 0
    total_units = 0
    
    for record in SAMPLE_FUNDING_RECORDS:
        if record.get("state", "").upper() != state.upper():
            continue
        
        program = record.get("program_type", "unknown")
        if program not in stats:
            stats[program] = {
                "count": 0,
                "total_credit_amount": 0,
                "total_units": 0,
                "affordable_units": 0
            }
        
        stats[program]["count"] += 1
        stats[program]["total_credit_amount"] += record.get("credit_amount", 0) or 0
        stats[program]["total_units"] += record.get("total_units", 0) or 0
        stats[program]["affordable_units"] += record.get("affordable_units", 0) or 0
        
        total_credits += record.get("credit_amount", 0) or 0
        total_units += record.get("total_units", 0) or 0
    
    return {
        "state": state,
        "by_program": stats,
        "totals": {
            "total_records": len([r for r in SAMPLE_FUNDING_RECORDS if r.get("state", "").upper() == state.upper()]),
            "total_credit_amount": total_credits,
            "total_units": total_units
        }
    }

@router.get("/eligibility-check")
async def check_eligibility(
    address: str = Query(..., description="Property address"),
    city: str = Query(..., description="City"),
    state: str = Query("MN", description="State"),
    property_type: str = Query("multifamily", description="Property type"),
    total_units: int = Query(..., description="Total units"),
    target_ami: int = Query(60, description="Target AMI percentage"),
    user: StorageUser = Depends(require_user)
):
    """
    Check potential eligibility for various funding programs based on property characteristics.
    This is a preliminary screening - actual eligibility requires detailed application.
    """
    eligible_programs = []
    
    # LIHTC eligibility
    if total_units >= 4 and target_ami <= 80:
        eligible_programs.append({
            "program": "lihtc",
            "name": "Low-Income Housing Tax Credit",
            "eligibility": "Likely Eligible" if target_ami <= 60 else "Potentially Eligible",
            "notes": [
                f"Property has {total_units} units (minimum 4 required)",
                f"Target AMI of {target_ami}% meets income restrictions",
                "9% credits are competitive; 4% credits are as-of-right with bonds"
            ],
            "next_steps": [
                "Contact MHFA for QAP and application timeline",
                "Engage tax credit consultant/syndicator",
                "Prepare market study and development budget"
            ]
        })
    
    # NMTC eligibility (would need census tract check)
    eligible_programs.append({
        "program": "nmtc",
        "name": "New Markets Tax Credit",
        "eligibility": "Requires Census Tract Verification",
        "notes": [
            "Property must be in a qualified low-income census tract",
            "Often requires affordable housing set-aside",
            "Can layer with LIHTC"
        ],
        "next_steps": [
            "Verify census tract eligibility on CDFI Fund mapper",
            "Contact local CDE (Greater MN Housing Fund, etc.)"
        ]
    })
    
    # Opportunity Zone (would need tract check)
    eligible_programs.append({
        "program": "opportunity_zone",
        "name": "Opportunity Zone Investment",
        "eligibility": "Requires Census Tract Verification",
        "notes": [
            "Property must be in designated Opportunity Zone",
            "Investor must have capital gains to invest",
            "10-year hold for maximum tax benefit"
        ],
        "next_steps": [
            "Verify OZ designation on HUD mapper",
            "Structure investment through QOF"
        ]
    })
    
    # Energy incentives
    if property_type == "multifamily":
        eligible_programs.append({
            "program": "section_179d",
            "name": "Section 179D Energy Deduction",
            "eligibility": "Potentially Eligible",
            "notes": [
                "Multifamily properties may qualify if treated as commercial",
                "Requires 25%+ energy savings certification",
                "IRA enhanced deduction available with prevailing wage"
            ],
            "next_steps": [
                "Engage energy consultant for modeling",
                "Evaluate cost-benefit of efficiency upgrades"
            ]
        })
    
    return {
        "property": {
            "address": address,
            "city": city,
            "state": state,
            "total_units": total_units,
            "target_ami": target_ami
        },
        "eligible_programs": eligible_programs,
        "disclaimer": "This is a preliminary eligibility screening only. Actual eligibility requires formal application and review by program administrators."
    }

@router.get("/data-sources")
async def list_data_sources():
    """List authoritative data sources for funding research"""
    return {
        "federal_sources": [
            {
                "name": "HUD LIHTC Database",
                "description": "Official database of all LIHTC properties nationwide",
                "url": "https://lihtc.huduser.gov/",
                "search_capabilities": ["address", "city", "state", "year"]
            },
            {
                "name": "CDFI Fund NMTC Awards",
                "description": "New Markets Tax Credit allocations and projects",
                "url": "https://www.cdfifund.gov/awards",
                "search_capabilities": ["CDE", "state", "year"]
            },
            {
                "name": "National Park Service Tax Credit Projects",
                "description": "Historic rehabilitation tax credit certifications",
                "url": "https://www.nps.gov/subjects/taxincentives/index.htm",
                "search_capabilities": ["state", "project_name"]
            },
            {
                "name": "HUD Multifamily Properties",
                "description": "Properties with HUD multifamily assistance",
                "url": "https://www.hud.gov/program_offices/housing/mfh/exp/mfhdiscl",
                "search_capabilities": ["address", "city", "state", "program"]
            },
            {
                "name": "Opportunity Zone Mapping",
                "description": "Designated Qualified Opportunity Zones",
                "url": "https://opportunityzones.hud.gov/",
                "search_capabilities": ["address", "census_tract"]
            }
        ],
        "state_sources_mn": [
            {
                "name": "Minnesota Housing Finance Agency",
                "description": "State LIHTC allocations and multifamily programs",
                "url": "https://www.mnhousing.gov/sites/multifamily/lihtc",
                "search_capabilities": ["property", "developer", "year"]
            },
            {
                "name": "MN SHPO Historic Properties",
                "description": "State historic preservation listings",
                "url": "https://mn.gov/admin/shpo/",
                "search_capabilities": ["address", "city", "county"]
            }
        ],
        "county_sources_dakota": [
            {
                "name": "Dakota County Recorder",
                "description": "Property records, deeds, financing documents",
                "url": "https://www.co.dakota.mn.us/Government/RecorderSurveyor",
                "search_capabilities": ["address", "owner", "document_type"]
            },
            {
                "name": "Dakota County Assessor",
                "description": "Property tax and ownership records",
                "url": "https://www.co.dakota.mn.us/Government/PropertyTaxes",
                "search_capabilities": ["address", "PID", "owner"]
            }
        ],
        "commercial_tools": [
            {
                "name": "Novogradac LIHTC/NMTC Maps",
                "description": "Interactive mapping tools for tax credit properties",
                "url": "https://www.novoco.com/resource-centers"
            },
            {
                "name": "National Housing Conference Database",
                "description": "Affordable housing property search",
                "url": "https://www.nhc.org/"
            }
        ]
    }

@router.get("/health")
async def funding_search_health():
    """Health check for funding search service"""
    return {
        "status": "ok",
        "service": "funding_search",
        "records_loaded": len(SAMPLE_FUNDING_RECORDS),
        "programs_available": len(PROGRAM_INFO)
    }
