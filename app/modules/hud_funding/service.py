"""
HUD Funding & Tax Credit Guide Service
=======================================

Comprehensive database of:
- HUD funding programs
- Tax credit programs (LIHTC, Historic, etc.)
- Landlord eligibility requirements
- Compliance obligations
- Tax breaks for rental property owners

This module helps tenants understand what programs their landlord
may be participating in and what obligations that creates.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ProgramType(str, Enum):
    """Types of housing programs"""
    TAX_CREDIT = "tax_credit"
    GRANT = "grant"
    LOAN = "loan"
    VOUCHER = "voucher"
    SUBSIDY = "subsidy"
    TAX_DEDUCTION = "tax_deduction"
    TAX_EXEMPTION = "tax_exemption"


class EligibilityCategory(str, Enum):
    """Who the program serves"""
    LOW_INCOME = "low_income"           # ≤80% AMI
    VERY_LOW_INCOME = "very_low_income" # ≤50% AMI
    EXTREMELY_LOW_INCOME = "extremely_low_income"  # ≤30% AMI
    ELDERLY = "elderly"                 # 62+
    DISABLED = "disabled"
    VETERANS = "veterans"
    FAMILIES = "families"
    HOMELESS = "homeless"
    MARKET_RATE = "market_rate"         # No income restrictions


class ComplianceLevel(str, Enum):
    """Level of compliance monitoring"""
    HIGH = "high"       # Annual inspections, strict reporting
    MEDIUM = "medium"   # Periodic reviews
    LOW = "low"         # Self-certification
    NONE = "none"       # No ongoing compliance


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LandlordRequirement:
    """Specific requirement a landlord must meet"""
    requirement: str
    description: str
    penalty_for_violation: str
    tenant_recourse: str  # What tenant can do if violated


@dataclass
class IncomeLimit:
    """Income limits for program eligibility"""
    category: EligibilityCategory
    percent_of_ami: int  # Area Median Income percentage
    description: str
    

@dataclass
class FundingProgram:
    """Complete funding/tax program information"""
    id: str
    name: str
    program_type: ProgramType
    administering_agency: str
    description: str
    
    # Landlord eligibility
    landlord_eligibility: List[str]
    property_requirements: List[str]
    
    # Tenant eligibility (income limits, etc.)
    tenant_eligibility: List[IncomeLimit]
    
    # What landlord must do
    landlord_obligations: List[LandlordRequirement]
    
    # Compliance
    compliance_level: ComplianceLevel
    inspection_frequency: str
    reporting_requirements: List[str]
    
    # Financial details
    benefit_to_landlord: str
    typical_amount: str
    duration_years: int
    
    # Affordability requirements
    rent_restrictions: str
    affordability_period_years: int
    
    # Resources
    website: str
    application_url: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # Minnesota specific
    mn_administrator: Optional[str] = None
    mn_contact: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "program_type": self.program_type.value,
            "administering_agency": self.administering_agency,
            "description": self.description,
            "landlord_eligibility": self.landlord_eligibility,
            "property_requirements": self.property_requirements,
            "tenant_eligibility": [
                {"category": ie.category.value, "percent_ami": ie.percent_of_ami, "description": ie.description}
                for ie in self.tenant_eligibility
            ],
            "landlord_obligations": [
                {
                    "requirement": lo.requirement,
                    "description": lo.description,
                    "penalty": lo.penalty_for_violation,
                    "tenant_recourse": lo.tenant_recourse,
                }
                for lo in self.landlord_obligations
            ],
            "compliance_level": self.compliance_level.value,
            "inspection_frequency": self.inspection_frequency,
            "reporting_requirements": self.reporting_requirements,
            "benefit_to_landlord": self.benefit_to_landlord,
            "typical_amount": self.typical_amount,
            "duration_years": self.duration_years,
            "rent_restrictions": self.rent_restrictions,
            "affordability_period_years": self.affordability_period_years,
            "website": self.website,
            "application_url": self.application_url,
            "mn_administrator": self.mn_administrator,
        }


# =============================================================================
# FUNDING PROGRAMS DATABASE
# =============================================================================

FUNDING_PROGRAMS: Dict[str, FundingProgram] = {
    
    # =========================================================================
    # LOW-INCOME HOUSING TAX CREDIT (LIHTC)
    # =========================================================================
    "lihtc_9_percent": FundingProgram(
        id="lihtc_9_percent",
        name="Low-Income Housing Tax Credit (9% Competitive)",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="IRS / State Housing Finance Agency",
        description="Primary federal program for financing affordable rental housing. "
                    "9% credits are competitive and provide approximately 70% of project costs in equity.",
        
        landlord_eligibility=[
            "Must be a qualified low-income housing project",
            "Building must be residential rental property",
            "Cannot be used for transient housing (hotels)",
            "Owner must make irrevocable election to participate",
            "Must have allocation from state housing finance agency",
            "Must demonstrate financial need for credits",
            "Developer must have track record or partner with experienced developer",
        ],
        
        property_requirements=[
            "Minimum 10-year credit period",
            "15-year compliance period minimum",
            "Extended use period (typically 30 years total)",
            "Must meet Housing Quality Standards",
            "Building must be suitable for occupancy within specific timeframe",
            "Rehabilitation must meet minimum expenditure requirements ($6,000+/unit)",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.LOW_INCOME, 60, 
                       "At least 40% of units for households ≤60% AMI (40/60 test)"),
            IncomeLimit(EligibilityCategory.VERY_LOW_INCOME, 50,
                       "OR at least 20% of units for households ≤50% AMI (20/50 test)"),
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Income averaging option: average across units ≤60% AMI"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Rent Limits",
                "Gross rent (including utilities) cannot exceed 30% of imputed income limit",
                "Recapture of credits, disqualification from program",
                "Report to state HFA; file complaint with IRS if rent exceeds limits"
            ),
            LandlordRequirement(
                "Income Certification",
                "Must verify tenant income at move-in and annually",
                "Noncompliance penalties, potential credit recapture",
                "Request copy of your income certification; report if not done"
            ),
            LandlordRequirement(
                "Unit Availability",
                "Must accept all qualified applicants regardless of source of income",
                "Fair housing violations, program noncompliance",
                "File fair housing complaint if rejected due to voucher status"
            ),
            LandlordRequirement(
                "Physical Standards",
                "Units must meet Housing Quality Standards throughout compliance period",
                "Failed inspections can trigger noncompliance",
                "Report housing code violations to state HFA and local inspectors"
            ),
            LandlordRequirement(
                "Nondiscrimination",
                "Cannot discriminate against Section 8 voucher holders (in many states)",
                "Fair housing violations",
                "File HUD complaint; contact state HFA"
            ),
            LandlordRequirement(
                "Record Keeping",
                "Must maintain records for 6 years after compliance period",
                "Audit failures, potential penalties",
                "Request your tenant file records"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="Annual physical inspections by state HFA; IRS audits possible",
        reporting_requirements=[
            "Annual tenant income certifications",
            "Annual owner certification (Form 8609)",
            "Quarterly occupancy reports to state HFA",
            "Report any noncompliance within 30 days",
        ],
        
        benefit_to_landlord="Dollar-for-dollar reduction in federal tax liability; "
                           "typically provides 70% of eligible development costs as equity",
        typical_amount="$8,000-$15,000 per unit annually for 10 years",
        duration_years=10,
        
        rent_restrictions="Maximum rent = 30% of income limit for unit size "
                         "(e.g., 60% AMI for 2BR = 30% of 60% AMI for 3-person household)",
        affordability_period_years=30,
        
        website="https://www.irs.gov/credits-deductions/businesses/low-income-housing-tax-credit",
        application_url="https://www.mnhousing.gov/sites/multifamily/lihtc",
        contact_phone="1-800-829-4933",
        
        mn_administrator="Minnesota Housing Finance Agency",
        mn_contact="(651) 296-7608",
    ),
    
    "lihtc_4_percent": FundingProgram(
        id="lihtc_4_percent",
        name="Low-Income Housing Tax Credit (4% As-of-Right)",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="IRS / State Housing Finance Agency",
        description="Non-competitive LIHTC paired with tax-exempt bonds. "
                    "Provides approximately 30% of project costs. Easier to obtain than 9%.",
        
        landlord_eligibility=[
            "Must use tax-exempt bond financing for 50%+ of aggregate basis",
            "Same qualified low-income housing project requirements as 9%",
            "Must apply for bond allocation from state/local issuer",
            "Financial feasibility review required",
        ],
        
        property_requirements=[
            "Same as 9% LIHTC",
            "Must pair with tax-exempt bond financing",
            "Bonds must finance at least 50% of project costs",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.LOW_INCOME, 60, 
                       "Same 20/50 or 40/60 test as 9% LIHTC"),
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Income averaging option available"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Same as 9% LIHTC",
                "All rent limits, income certification, and compliance requirements apply",
                "Credit recapture, bond default",
                "Same tenant recourse as 9% LIHTC"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="Annual inspections",
        reporting_requirements=["Same as 9% LIHTC plus bond compliance reporting"],
        
        benefit_to_landlord="30% of eligible costs as equity; easier to obtain than 9%",
        typical_amount="$3,500-$7,000 per unit annually for 10 years",
        duration_years=10,
        
        rent_restrictions="Same as 9% LIHTC",
        affordability_period_years=30,
        
        website="https://www.irs.gov/credits-deductions/businesses/low-income-housing-tax-credit",
        mn_administrator="Minnesota Housing Finance Agency",
        mn_contact="(651) 296-7608",
    ),

    # =========================================================================
    # SECTION 8 PROGRAMS
    # =========================================================================
    "section_8_pbv": FundingProgram(
        id="section_8_pbv",
        name="Section 8 Project-Based Vouchers (PBV)",
        program_type=ProgramType.VOUCHER,
        administering_agency="HUD / Local Public Housing Authority",
        description="Rental assistance attached to specific units. "
                    "PHA pays difference between 30% of tenant income and contract rent.",
        
        landlord_eligibility=[
            "Property must pass Housing Quality Standards inspection",
            "Owner must enter into Housing Assistance Payments (HAP) contract",
            "Cannot be owner-occupied or in certain ineligible property types",
            "Must agree to 15-year initial contract term (or 20 years for new construction)",
            "Must not have been debarred from federal programs",
            "Must have no outstanding violations or HUD debts",
        ],
        
        property_requirements=[
            "Must pass HQS inspection before HAP contract execution",
            "Annual HQS inspections required",
            "Unit must meet local housing codes",
            "Reasonable rent as determined by PHA",
            "Cannot exceed 25% of units in building (with exceptions)",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.VERY_LOW_INCOME, 50,
                       "At least 75% of new admissions must be ≤30% AMI"),
            IncomeLimit(EligibilityCategory.EXTREMELY_LOW_INCOME, 30,
                       "Priority for extremely low income households"),
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Up to 25% can be ≤80% AMI"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Accept HAP Payment",
                "Must accept PHA payment as full rent for assisted portion",
                "HAP contract termination",
                "Contact PHA if landlord demands additional payment beyond tenant share"
            ),
            LandlordRequirement(
                "Maintain HQS",
                "Must maintain unit in Housing Quality Standards compliance",
                "HAP abatement (payments stop) until repairs made",
                "Report HQS violations to PHA; request inspection"
            ),
            LandlordRequirement(
                "Lease Requirements",
                "Must use HUD-approved lease addendum; cannot include prohibited provisions",
                "Lease violations, potential HAP termination",
                "Review your lease against HUD model lease requirements"
            ),
            LandlordRequirement(
                "No Discrimination",
                "Cannot refuse to lease to voucher holders (federal + MN law)",
                "Fair housing violations; PHA contract termination",
                "File HUD complaint and contact PHA"
            ),
            LandlordRequirement(
                "Rent Reasonableness",
                "Rent must be reasonable compared to unassisted units",
                "Rent reduction required; potential fraud charges if excessive",
                "Request rent reasonableness determination from PHA"
            ),
            LandlordRequirement(
                "Proper Eviction Process",
                "Must follow state eviction law AND provide copy of notice to PHA",
                "HAP termination for improper evictions",
                "Notify PHA of any eviction action; PHA may intervene"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="Annual HQS inspections; special inspections on complaint",
        reporting_requirements=[
            "Annual rent increase requests (60 days advance notice)",
            "Report any lease violations to PHA",
            "Report tenant income changes if known",
            "Provide move-out information",
        ],
        
        benefit_to_landlord="Guaranteed rent payment from PHA; reduced vacancy risk; "
                           "long-term stable income stream",
        typical_amount="Contract rent minus 30% of tenant income (paid monthly by PHA)",
        duration_years=15,
        
        rent_restrictions="Must be 'rent reasonable' - comparable to unassisted market units",
        affordability_period_years=15,
        
        website="https://www.hud.gov/program_offices/public_indian_housing/programs/hcv/project",
        mn_administrator="Local Public Housing Authorities",
        mn_contact="Metro HRA: (651) 602-1000; Minneapolis PHA: (612) 342-1400",
    ),
    
    "section_8_hcv": FundingProgram(
        id="section_8_hcv",
        name="Section 8 Housing Choice Vouchers (Tenant-Based)",
        program_type=ProgramType.VOUCHER,
        administering_agency="HUD / Local Public Housing Authority",
        description="Tenant-based rental assistance that moves with the tenant. "
                    "Landlord participation is voluntary but must meet requirements.",
        
        landlord_eligibility=[
            "Voluntary participation",
            "Property must pass HQS inspection",
            "Must sign HAP contract with PHA",
            "Rent must be reasonable for the area",
            "Cannot have been debarred from federal programs",
            "Cannot be related to the tenant",
        ],
        
        property_requirements=[
            "Pass HQS inspection before lease-up",
            "Meet rent reasonableness standard",
            "Annual reinspections required",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.VERY_LOW_INCOME, 50,
                       "75% of new vouchers to ≤30% AMI"),
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Remaining vouchers to ≤80% AMI"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "HQS Compliance",
                "Unit must meet and maintain Housing Quality Standards",
                "HAP abatement until repairs completed",
                "Report violations to PHA; request emergency inspection"
            ),
            LandlordRequirement(
                "Rent Limits",
                "Cannot charge more than approved rent; no side payments",
                "Fraud charges; termination from program",
                "Report any requests for additional payments to PHA and HUD OIG"
            ),
            LandlordRequirement(
                "Source of Income (MN)",
                "Minnesota law prohibits discrimination against voucher holders",
                "Fair housing violation; damages; attorney fees",
                "File complaint with MN Dept of Human Rights"
            ),
        ],
        
        compliance_level=ComplianceLevel.MEDIUM,
        inspection_frequency="Initial inspection; biennial reinspection (or annual)",
        reporting_requirements=[
            "Annual rent increase requests",
            "Report needed repairs",
            "Provide move-out notice to PHA",
        ],
        
        benefit_to_landlord="Reliable monthly payment from PHA; market-rate rent",
        typical_amount="Fair Market Rent minus tenant portion (typically 30% of income)",
        duration_years=1,
        
        rent_restrictions="Payment standard based on Fair Market Rent; tenant pays difference if rent exceeds standard",
        affordability_period_years=1,
        
        website="https://www.hud.gov/topics/housing_choice_voucher_program_section_8",
        mn_administrator="Local PHAs",
        mn_contact="HUD Minneapolis: (612) 370-3000",
    ),

    # =========================================================================
    # HUD MULTIFAMILY PROGRAMS
    # =========================================================================
    "section_202": FundingProgram(
        id="section_202",
        name="Section 202 Supportive Housing for the Elderly",
        program_type=ProgramType.GRANT,
        administering_agency="HUD Office of Multifamily Housing",
        description="Capital advances (no repayment required) and rental assistance "
                    "for housing for very low-income elderly (62+).",
        
        landlord_eligibility=[
            "Must be private nonprofit organization",
            "Must have IRS 501(c)(3) or 501(c)(4) status",
            "Cannot be controlled by or under direction of for-profit entities",
            "Must demonstrate housing management capacity",
            "Must show evidence of community support",
        ],
        
        property_requirements=[
            "New construction or substantial rehabilitation",
            "Designed for elderly occupancy",
            "Must include supportive services or service coordinator",
            "Accessibility requirements (Section 504)",
            "40-year affordability period",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.VERY_LOW_INCOME, 50,
                       "Household income ≤50% AMI"),
            IncomeLimit(EligibilityCategory.ELDERLY, 62,
                       "At least one household member must be 62+"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Supportive Services",
                "Must provide or coordinate supportive services for residents",
                "Program noncompliance; potential recapture",
                "Request services; report if not provided"
            ),
            LandlordRequirement(
                "Income Targeting",
                "All units must serve very low-income elderly",
                "Funding recapture",
                "Report if non-eligible tenants housed"
            ),
            LandlordRequirement(
                "Affordability",
                "Maintain affordability for 40 years",
                "Capital advance becomes due and payable",
                "Long-term affordability protects current and future tenants"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="HUD REAC inspections; annual financial audits",
        reporting_requirements=[
            "Annual financial statements",
            "Tenant income certifications",
            "Service coordinator reports",
        ],
        
        benefit_to_landlord="Capital advance requires no repayment if compliance maintained; "
                           "Project Rental Assistance Contract (PRAC) covers operating costs",
        typical_amount="Capital: $10,000-$20,000/unit; PRAC: covers operating shortfall",
        duration_years=40,
        
        rent_restrictions="Tenant pays 30% of adjusted income; PRAC covers remainder",
        affordability_period_years=40,
        
        website="https://www.hud.gov/program_offices/housing/mfh/progdesc/eld202",
        contact_phone="(202) 708-2866",
        mn_administrator="HUD Minneapolis Multifamily Hub",
        mn_contact="(612) 370-3000",
    ),
    
    "section_811": FundingProgram(
        id="section_811",
        name="Section 811 Supportive Housing for Persons with Disabilities",
        program_type=ProgramType.GRANT,
        administering_agency="HUD Office of Multifamily Housing",
        description="Capital advances and rental assistance for housing "
                    "for very low-income persons with disabilities.",
        
        landlord_eligibility=[
            "Must be private nonprofit organization",
            "501(c)(3) tax-exempt status required",
            "Cannot be controlled by for-profit entities",
            "Must partner with state/local disability service agencies",
        ],
        
        property_requirements=[
            "Group homes, independent living facilities, or multifamily units",
            "Must be integrated into community (not institutional)",
            "Accessibility requirements (beyond minimum code)",
            "Must facilitate access to support services",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.EXTREMELY_LOW_INCOME, 30,
                       "Household income ≤30% AMI (or 50% with PRA)"),
            IncomeLimit(EligibilityCategory.DISABLED, 0,
                       "Adult with disability as defined by Section 811"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Service Coordination",
                "Must coordinate with service providers for residents",
                "Program noncompliance",
                "Report if services not coordinated"
            ),
            LandlordRequirement(
                "Integration",
                "Housing must be integrated into community, not segregated",
                "Civil rights violations; program termination",
                "Report institutional or segregated settings"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="REAC inspections; state agency monitoring",
        reporting_requirements=["Annual reports", "Service coordination documentation"],
        
        benefit_to_landlord="No-repayment capital advance; Project Rental Assistance",
        typical_amount="Varies by project size and type",
        duration_years=40,
        
        rent_restrictions="30% of adjusted income",
        affordability_period_years=40,
        
        website="https://www.hud.gov/program_offices/housing/mfh/progdesc/disab811",
        mn_administrator="Minnesota Housing + HUD",
        mn_contact="(651) 296-7608",
    ),

    # =========================================================================
    # HISTORIC TAX CREDITS
    # =========================================================================
    "historic_tax_credit": FundingProgram(
        id="historic_tax_credit",
        name="Federal Historic Rehabilitation Tax Credit",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="IRS / National Park Service",
        description="20% tax credit for certified rehabilitation of historic buildings. "
                    "Often combined with LIHTC for affordable housing in historic structures.",
        
        landlord_eligibility=[
            "Building must be listed on National Register of Historic Places "
            "or contribute to a registered historic district",
            "Must be income-producing property after rehabilitation",
            "Substantial rehabilitation required (exceeds adjusted basis)",
            "Rehabilitation must be certified by National Park Service",
            "Must follow Secretary of Interior's Standards for Rehabilitation",
        ],
        
        property_requirements=[
            "Certified historic structure",
            "Rehabilitation work must meet NPS standards",
            "Cannot destroy historic character",
            "5-year recapture period after placed in service",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0,
                       "No income restrictions (unless combined with LIHTC)"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Historic Preservation",
                "Must maintain historic character of building",
                "Credit recapture if character altered",
                "Report alterations that damage historic features"
            ),
            LandlordRequirement(
                "5-Year Hold",
                "Must retain ownership for 5 years or credit is recaptured",
                "Pro-rata recapture of credits",
                "Building sale doesn't affect tenant directly"
            ),
        ],
        
        compliance_level=ComplianceLevel.MEDIUM,
        inspection_frequency="NPS certification review; state historic preservation office monitoring",
        reporting_requirements=["Part 3 certification application", "Maintain documentation"],
        
        benefit_to_landlord="20% credit on qualified rehabilitation expenditures; "
                           "can be combined with LIHTC and state historic credits",
        typical_amount="20% of qualified rehabilitation costs",
        duration_years=5,
        
        rent_restrictions="None (unless combined with other programs)",
        affordability_period_years=0,
        
        website="https://www.nps.gov/subjects/taxincentives/index.htm",
        application_url="https://www.nps.gov/subjects/taxincentives/how-to-apply.htm",
        mn_administrator="Minnesota State Historic Preservation Office",
        mn_contact="(651) 201-3287",
    ),
    
    "mn_historic_credit": FundingProgram(
        id="mn_historic_credit",
        name="Minnesota Historic Structure Rehabilitation Tax Credit",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="Minnesota SHPO / Dept of Revenue",
        description="State credit that can be stacked with federal historic credit. "
                    "20% for income-producing, 20% for owner-occupied residences.",
        
        landlord_eligibility=[
            "Property on National Register or contributing to historic district",
            "Must meet state certification requirements",
            "Can be stacked with federal historic credit",
        ],
        
        property_requirements=[
            "Certified historic structure in Minnesota",
            "Qualified rehabilitation expenditures",
            "Must follow Secretary of Interior's Standards",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0, "No income restrictions"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Historic Preservation",
                "Same as federal historic credit",
                "State credit recapture",
                "Same recourse as federal"
            ),
        ],
        
        compliance_level=ComplianceLevel.MEDIUM,
        inspection_frequency="SHPO review",
        reporting_requirements=["State certification", "Cost documentation"],
        
        benefit_to_landlord="Additional 20% state credit on top of federal 20%",
        typical_amount="20% of qualified costs (state)",
        duration_years=5,
        
        rent_restrictions="None",
        affordability_period_years=0,
        
        website="https://mn.gov/admin/shpo/incentives/tax-credit/",
        mn_administrator="MN State Historic Preservation Office",
        mn_contact="(651) 201-3287",
    ),

    # =========================================================================
    # OPPORTUNITY ZONES
    # =========================================================================
    "opportunity_zone": FundingProgram(
        id="opportunity_zone",
        name="Qualified Opportunity Zone Investment",
        program_type=ProgramType.TAX_DEDUCTION,
        administering_agency="IRS / Treasury",
        description="Tax incentives for investing capital gains in designated low-income areas. "
                    "Deferral, reduction, and potential elimination of capital gains taxes.",
        
        landlord_eligibility=[
            "Must invest through a Qualified Opportunity Fund (QOF)",
            "Investment must be capital gains within 180 days of realization",
            "90% of QOF assets must be in Qualified Opportunity Zone Property",
            "Property must be in designated census tract",
            "Substantial improvement required for existing buildings",
        ],
        
        property_requirements=[
            "Located in designated Opportunity Zone census tract",
            "Original use must begin with QOF, OR substantial improvement made",
            "Substantial improvement = double adjusted basis within 30 months",
            "Must be trade or business property",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0, 
                       "No income restrictions required (location-based, not tenant-based)"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Substantial Improvement",
                "Must substantially improve property if not original use",
                "Loss of OZ tax benefits",
                "OZ doesn't create tenant protections directly"
            ),
            LandlordRequirement(
                "90% Asset Test",
                "QOF must maintain 90% qualified property",
                "Penalty tax on non-qualifying assets",
                "No direct tenant recourse"
            ),
        ],
        
        compliance_level=ComplianceLevel.LOW,
        inspection_frequency="IRS audit; annual certification",
        reporting_requirements=["Form 8996 annual certification", "QOF investor reporting"],
        
        benefit_to_landlord="Capital gains deferral until 2026; 10% basis step-up if held 5 years; "
                           "exclusion of gains on OZ investment if held 10+ years",
        typical_amount="Tax savings on capital gains; varies by investment size",
        duration_years=10,
        
        rent_restrictions="NONE - This is the key difference. No affordability requirements.",
        affordability_period_years=0,
        
        website="https://www.irs.gov/credits-deductions/businesses/opportunity-zones",
        mn_administrator="N/A - Federal program",
    ),

    # =========================================================================
    # NEW MARKETS TAX CREDIT
    # =========================================================================
    "nmtc": FundingProgram(
        id="nmtc",
        name="New Markets Tax Credit (NMTC)",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="CDFI Fund / Treasury",
        description="39% tax credit over 7 years for investments in low-income communities. "
                    "Can be used for mixed-use with housing component.",
        
        landlord_eligibility=[
            "Investment through certified Community Development Entity (CDE)",
            "Project must be in qualifying low-income census tract",
            "Must demonstrate community impact",
            "Cannot be primarily residential (mixed-use OK)",
            "CDE must make Qualified Low-Income Community Investment",
        ],
        
        property_requirements=[
            "Located in qualifying census tract (poverty rate, income criteria)",
            "Must be active business or mixed-use",
            "Residential component limited (generally <80%)",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0,
                       "Location-based; residential component may have requirements"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Community Benefit",
                "Project must provide demonstrated community benefit",
                "Credit recapture",
                "Report if community benefits not delivered"
            ),
            LandlordRequirement(
                "7-Year Compliance",
                "Investment must remain in place for 7 years",
                "Credit recapture on early disposition",
                "No direct tenant impact"
            ),
        ],
        
        compliance_level=ComplianceLevel.MEDIUM,
        inspection_frequency="CDE monitoring; CDFI Fund audits",
        reporting_requirements=["Annual CDE reporting", "Community impact metrics"],
        
        benefit_to_landlord="39% credit over 7 years; below-market financing; gap financing",
        typical_amount="39% of Qualified Equity Investment over 7 years",
        duration_years=7,
        
        rent_restrictions="Varies by CDE requirements; not inherently required",
        affordability_period_years=0,
        
        website="https://www.cdfifund.gov/programs-training/programs/new-markets-tax-credit",
        mn_administrator="CDEs operating in Minnesota",
    ),

    # =========================================================================
    # ENERGY TAX INCENTIVES
    # =========================================================================
    "section_179d": FundingProgram(
        id="section_179d",
        name="Section 179D Energy Efficient Commercial Building Deduction",
        program_type=ProgramType.TAX_DEDUCTION,
        administering_agency="IRS",
        description="Tax deduction for energy-efficient improvements to commercial buildings, "
                    "including multifamily rental (4+ units).",
        
        landlord_eligibility=[
            "Building must be commercial or multifamily (4+ units)",
            "Must install qualifying energy-efficient systems",
            "Energy savings must be certified by qualified professional",
            "Enhanced deductions for meeting prevailing wage/apprenticeship requirements",
        ],
        
        property_requirements=[
            "Building envelope, HVAC, or lighting improvements",
            "Must achieve energy reduction targets",
            "Certification by qualified engineer/contractor",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0, "No income restrictions"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Energy Performance",
                "Building must achieve certified energy savings",
                "Deduction denied or recaptured",
                "Tenants may benefit from lower utility costs"
            ),
        ],
        
        compliance_level=ComplianceLevel.LOW,
        inspection_frequency="Third-party certification required",
        reporting_requirements=["Energy certification", "Tax form documentation"],
        
        benefit_to_landlord="Up to $5.00/sq ft deduction (enhanced) for qualifying improvements",
        typical_amount="$0.50-$5.00 per square foot",
        duration_years=1,
        
        rent_restrictions="None",
        affordability_period_years=0,
        
        website="https://www.irs.gov/credits-deductions/businesses/"
                "energy-efficient-commercial-buildings-deduction",
    ),
    
    "itc_solar": FundingProgram(
        id="itc_solar",
        name="Investment Tax Credit (ITC) - Solar/Renewable Energy",
        program_type=ProgramType.TAX_CREDIT,
        administering_agency="IRS",
        description="30% tax credit for solar and renewable energy installations. "
                    "Can apply to multifamily rental properties.",
        
        landlord_eligibility=[
            "Must own the solar/renewable energy system",
            "Property must be placed in service",
            "Cannot be for tax-exempt entities (but can lease/PPA)",
            "Enhanced credit for meeting labor requirements",
        ],
        
        property_requirements=[
            "Solar PV, solar water heating, geothermal, or other qualifying systems",
            "Must be new equipment (not used)",
            "5-year recapture period",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.MARKET_RATE, 0, "No restrictions"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "System Ownership",
                "Must maintain ownership for 5 years or partial recapture",
                "Pro-rata credit recapture",
                "Tenants may benefit from community solar or lower utility costs"
            ),
        ],
        
        compliance_level=ComplianceLevel.LOW,
        inspection_frequency="None routine; IRS audit possible",
        reporting_requirements=["Form 3468", "Cost documentation"],
        
        benefit_to_landlord="30% credit on system costs; bonus credits for domestic content, "
                           "energy communities, and low-income projects",
        typical_amount="30% of installed cost (base); up to 70% with bonuses",
        duration_years=5,
        
        rent_restrictions="None (10-20% bonus for low-income housing projects)",
        affordability_period_years=0,
        
        website="https://www.irs.gov/credits-deductions/businesses/"
                "investment-tax-credit-for-energy-property",
    ),

    # =========================================================================
    # HOME AND CDBG
    # =========================================================================
    "home_program": FundingProgram(
        id="home_program",
        name="HOME Investment Partnerships Program",
        program_type=ProgramType.GRANT,
        administering_agency="HUD",
        description="Federal block grant for affordable housing development, "
                    "rehabilitation, and tenant-based rental assistance.",
        
        landlord_eligibility=[
            "Apply through Participating Jurisdiction (city/county/state)",
            "Must commit to affordability period",
            "Financial capacity to complete project",
            "Property must meet property standards",
        ],
        
        property_requirements=[
            "Must meet HOME property standards within 6 months",
            "Lead-based paint requirements",
            "Minimum affordability period (5-20 years depending on investment)",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Rental: ≤80% AMI; 90% of units to ≤60% AMI"),
            IncomeLimit(EligibilityCategory.VERY_LOW_INCOME, 50,
                       "20% of units must serve ≤50% AMI in projects of 5+ units"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Rent Limits",
                "HOME units must charge High or Low HOME rents",
                "Repayment of HOME funds",
                "Report excessive rents to Participating Jurisdiction"
            ),
            LandlordRequirement(
                "Affordability Period",
                "5-20 year affordability period based on investment amount",
                "Repayment of HOME funds if affordability violated",
                "Long-term affordability protects tenants"
            ),
            LandlordRequirement(
                "Tenant Selection",
                "Must use written tenant selection policies",
                "Fair housing violations",
                "Request copy of tenant selection plan"
            ),
        ],
        
        compliance_level=ComplianceLevel.HIGH,
        inspection_frequency="PJ inspections; HUD monitoring",
        reporting_requirements=["Annual income certifications", "Rent compliance", "Physical inspections"],
        
        benefit_to_landlord="Gap financing; low-interest loans; grants for development",
        typical_amount="Varies; up to $40,000-$75,000 per unit",
        duration_years=20,
        
        rent_restrictions="High HOME Rent: 30% of 65% AMI; Low HOME Rent: 30% of 50% AMI",
        affordability_period_years=20,
        
        website="https://www.hud.gov/program_offices/comm_planning/home",
        mn_administrator="Minnesota Housing; Metro HRA; Cities",
        mn_contact="(651) 296-7608",
    ),
    
    "cdbg": FundingProgram(
        id="cdbg",
        name="Community Development Block Grant (CDBG)",
        program_type=ProgramType.GRANT,
        administering_agency="HUD",
        description="Flexible federal grant for community development including housing. "
                    "Primarily benefits low/moderate income persons.",
        
        landlord_eligibility=[
            "Must benefit low/moderate income persons (51%+ of beneficiaries)",
            "Apply through grantee (city/county/state)",
            "Project must meet national objective",
            "Environmental review required",
        ],
        
        property_requirements=[
            "Housing rehabilitation, infrastructure, economic development",
            "Must meet local codes and standards",
            "Environmental clearance required",
        ],
        
        tenant_eligibility=[
            IncomeLimit(EligibilityCategory.LOW_INCOME, 80,
                       "Must benefit low/moderate income households (≤80% AMI)"),
        ],
        
        landlord_obligations=[
            LandlordRequirement(
                "Low/Mod Benefit",
                "Must primarily benefit low/moderate income persons",
                "Fund repayment",
                "Report if benefits not reaching low-income tenants"
            ),
            LandlordRequirement(
                "Affordability",
                "May require affordability period for housing investments",
                "Recapture provisions",
                "Varies by grantee requirements"
            ),
        ],
        
        compliance_level=ComplianceLevel.MEDIUM,
        inspection_frequency="Grantee monitoring",
        reporting_requirements=["Quarterly/annual performance reports"],
        
        benefit_to_landlord="Grant funds for rehabilitation; infrastructure improvements",
        typical_amount="Varies widely by project",
        duration_years=5,
        
        rent_restrictions="Varies by grantee requirements",
        affordability_period_years=5,
        
        website="https://www.hud.gov/program_offices/comm_planning/cdbg",
        mn_administrator="Minnesota DEED; Cities; Counties",
        mn_contact="Varies by jurisdiction",
    ),
}


# =============================================================================
# TAX BREAKS AND DEDUCTIONS (General Rental Property)
# =============================================================================

GENERAL_TAX_BREAKS: List[Dict[str, Any]] = [
    {
        "id": "depreciation",
        "name": "Depreciation Deduction",
        "type": "deduction",
        "description": "Annual deduction for wear and tear on rental property",
        "details": "Residential rental property depreciated over 27.5 years straight-line. "
                   "Reduces taxable income but may be recaptured on sale.",
        "landlord_requirement": "Own rental property placed in service",
        "annual_benefit": "Building cost / 27.5 years annually",
        "irs_form": "Form 4562",
    },
    {
        "id": "mortgage_interest",
        "name": "Mortgage Interest Deduction",
        "type": "deduction",
        "description": "Deduct interest paid on rental property mortgages",
        "details": "100% of mortgage interest is deductible against rental income. "
                   "No limit on number of properties.",
        "landlord_requirement": "Have mortgage on rental property",
        "annual_benefit": "Full interest paid",
        "irs_form": "Schedule E",
    },
    {
        "id": "operating_expenses",
        "name": "Operating Expense Deduction",
        "type": "deduction",
        "description": "Deduct ordinary and necessary rental expenses",
        "details": "Includes repairs, maintenance, insurance, property management fees, "
                   "utilities (if paid by landlord), advertising, legal fees, etc.",
        "landlord_requirement": "Incur expenses for rental activity",
        "annual_benefit": "Full amount of qualifying expenses",
        "irs_form": "Schedule E",
    },
    {
        "id": "property_taxes",
        "name": "Property Tax Deduction",
        "type": "deduction",
        "description": "Deduct property taxes paid on rental property",
        "details": "State and local property taxes fully deductible against rental income. "
                   "No SALT cap for rental properties.",
        "landlord_requirement": "Pay property taxes on rental property",
        "annual_benefit": "Full property tax amount",
        "irs_form": "Schedule E",
    },
    {
        "id": "qbi_deduction",
        "name": "Qualified Business Income (QBI) Deduction",
        "type": "deduction",
        "description": "20% deduction on qualified rental income",
        "details": "Section 199A allows 20% deduction on qualified business income from rentals. "
                   "Must meet safe harbor (250+ hours) or be considered a trade or business.",
        "landlord_requirement": "Rental activity qualifies as trade/business or meets safe harbor",
        "annual_benefit": "20% of net rental income (subject to limitations)",
        "irs_form": "Form 8995",
    },
    {
        "id": "1031_exchange",
        "name": "1031 Like-Kind Exchange",
        "type": "deferral",
        "description": "Defer capital gains by exchanging into similar property",
        "details": "Swap rental property for another rental property and defer all capital gains. "
                   "Must identify replacement within 45 days, close within 180 days.",
        "landlord_requirement": "Exchange investment property for like-kind property",
        "annual_benefit": "100% capital gains deferral",
        "irs_form": "Form 8824",
    },
    {
        "id": "cost_segregation",
        "name": "Cost Segregation Study",
        "type": "acceleration",
        "description": "Accelerate depreciation by segregating building components",
        "details": "Engineering study reclassifies components to 5, 7, or 15-year property "
                   "instead of 27.5 years. Creates large upfront deductions.",
        "landlord_requirement": "Commission cost segregation study",
        "annual_benefit": "20-40% of building cost accelerated to year 1",
        "irs_form": "Form 4562",
    },
    {
        "id": "bonus_depreciation",
        "name": "Bonus Depreciation",
        "type": "deduction",
        "description": "100% first-year depreciation on qualifying property",
        "details": "Short-lived property and improvements can be 100% expensed in year 1. "
                   "Phasing down: 80% in 2023, 60% in 2024, 40% in 2025, 20% in 2026.",
        "landlord_requirement": "Acquire and place in service qualifying property",
        "annual_benefit": "100% of qualifying property cost (phasing down)",
        "irs_form": "Form 4562",
    },
    {
        "id": "passive_loss",
        "name": "Passive Activity Loss Rules",
        "type": "limitation",
        "description": "Rental losses limited unless real estate professional status",
        "details": "Rental losses generally passive; can offset passive income. "
                   "$25,000 allowance for active participation (phases out at $100k-$150k AGI). "
                   "Real estate professionals can deduct against all income.",
        "landlord_requirement": "Meet material participation tests for RE professional status",
        "annual_benefit": "Unlimited loss deduction if RE professional",
        "irs_form": "Form 8582",
    },
]


# =============================================================================
# SERVICE CLASS
# =============================================================================

class HUDFundingGuideService:
    """Service for accessing HUD funding and tax credit information."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.programs = FUNDING_PROGRAMS
        self.tax_breaks = GENERAL_TAX_BREAKS
        logger.info("📊 HUD Funding Guide Service initialized")
    
    # =========================================================================
    # PROGRAM QUERIES
    # =========================================================================
    
    def get_all_programs(self) -> List[FundingProgram]:
        """Get all funding programs."""
        return list(self.programs.values())
    
    def get_program(self, program_id: str) -> Optional[FundingProgram]:
        """Get a specific program by ID."""
        return self.programs.get(program_id)
    
    def get_programs_by_type(self, program_type: ProgramType) -> List[FundingProgram]:
        """Get programs of a specific type."""
        return [p for p in self.programs.values() if p.program_type == program_type]
    
    def get_tax_credit_programs(self) -> List[FundingProgram]:
        """Get all tax credit programs."""
        return self.get_programs_by_type(ProgramType.TAX_CREDIT)
    
    def get_voucher_programs(self) -> List[FundingProgram]:
        """Get all voucher/subsidy programs."""
        return [p for p in self.programs.values() 
                if p.program_type in [ProgramType.VOUCHER, ProgramType.SUBSIDY]]
    
    def get_grant_programs(self) -> List[FundingProgram]:
        """Get all grant programs."""
        return self.get_programs_by_type(ProgramType.GRANT)
    
    def search_programs(self, query: str) -> List[FundingProgram]:
        """Search programs by keyword."""
        query_lower = query.lower()
        results = []
        for program in self.programs.values():
            if (query_lower in program.name.lower() or
                query_lower in program.description.lower() or
                any(query_lower in req.lower() for req in program.landlord_eligibility)):
                results.append(program)
        return results
    
    # =========================================================================
    # LANDLORD REQUIREMENTS
    # =========================================================================
    
    def get_landlord_requirements(self, program_id: str) -> List[LandlordRequirement]:
        """Get landlord requirements for a program."""
        program = self.get_program(program_id)
        if program:
            return program.landlord_obligations
        return []
    
    def get_all_landlord_obligations(self) -> Dict[str, List[Dict]]:
        """Get all landlord obligations across all programs."""
        obligations = {}
        for program in self.programs.values():
            obligations[program.id] = [
                {
                    "program": program.name,
                    "requirement": lo.requirement,
                    "description": lo.description,
                    "penalty": lo.penalty_for_violation,
                    "tenant_recourse": lo.tenant_recourse,
                }
                for lo in program.landlord_obligations
            ]
        return obligations
    
    # =========================================================================
    # TENANT RECOURSE
    # =========================================================================
    
    def get_tenant_recourse_options(self, program_id: str) -> List[Dict]:
        """Get what a tenant can do if landlord violates program requirements."""
        program = self.get_program(program_id)
        if not program:
            return []
        
        recourse = []
        for obligation in program.landlord_obligations:
            recourse.append({
                "violation_type": obligation.requirement,
                "description": obligation.description,
                "what_tenant_can_do": obligation.tenant_recourse,
                "landlord_penalty": obligation.penalty_for_violation,
            })
        return recourse
    
    # =========================================================================
    # TAX BREAKS
    # =========================================================================
    
    def get_all_tax_breaks(self) -> List[Dict]:
        """Get all general tax breaks for rental properties."""
        return self.tax_breaks
    
    def get_tax_break(self, tax_break_id: str) -> Optional[Dict]:
        """Get specific tax break by ID."""
        for tb in self.tax_breaks:
            if tb["id"] == tax_break_id:
                return tb
        return None
    
    # =========================================================================
    # ELIGIBILITY CHECKING
    # =========================================================================
    
    def check_tenant_eligibility(
        self,
        income: float,
        ami: float,
        household_size: int = 1,
    ) -> List[Dict]:
        """Check which programs a tenant might be eligible for."""
        percent_ami = (income / ami) * 100
        
        eligible_programs = []
        for program in self.programs.values():
            for limit in program.tenant_eligibility:
                if limit.percent_of_ami == 0:
                    continue  # Skip market-rate only
                if percent_ami <= limit.percent_of_ami:
                    eligible_programs.append({
                        "program_id": program.id,
                        "program_name": program.name,
                        "income_category": limit.category.value,
                        "max_income_percent_ami": limit.percent_of_ami,
                        "your_income_percent_ami": round(percent_ami, 1),
                    })
                    break  # Only add once per program
        
        return eligible_programs
    
    def check_property_programs(self, address: str) -> Dict:
        """
        Check what programs a property might be participating in.
        NOTE: This would need integration with HUD databases for real data.
        """
        return {
            "note": "To determine actual programs, search:",
            "lihtc_database": "https://lihtc.huduser.gov/",
            "hud_multifamily": "https://www.hud.gov/program_offices/housing/mfh/exp/mfhdiscl",
            "section_8_search": "https://www.hud.gov/apps/section8/",
            "opportunity_zones": "https://opportunityzones.hud.gov/",
            "suggestion": "Ask your landlord directly what programs the property participates in",
        }
    
    # =========================================================================
    # SUMMARY REPORTS
    # =========================================================================
    
    def get_program_summary(self, program_id: str) -> Optional[Dict]:
        """Get a concise summary of a program."""
        program = self.get_program(program_id)
        if not program:
            return None
        
        return {
            "name": program.name,
            "type": program.program_type.value,
            "what_it_is": program.description,
            "who_administers": program.administering_agency,
            "landlord_benefit": program.benefit_to_landlord,
            "tenant_income_limits": [
                f"{ie.category.value}: ≤{ie.percent_of_ami}% AMI"
                for ie in program.tenant_eligibility
                if ie.percent_of_ami > 0
            ],
            "rent_restrictions": program.rent_restrictions,
            "affordability_period": f"{program.affordability_period_years} years",
            "key_landlord_obligations": [
                lo.requirement for lo in program.landlord_obligations
            ],
            "compliance_level": program.compliance_level.value,
            "website": program.website,
            "mn_contact": program.mn_contact,
        }
    
    def get_comparison_table(self, program_ids: List[str]) -> List[Dict]:
        """Compare multiple programs side by side."""
        comparisons = []
        for pid in program_ids:
            summary = self.get_program_summary(pid)
            if summary:
                comparisons.append(summary)
        return comparisons


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

hud_funding_guide = HUDFundingGuideService()


def get_hud_funding_guide() -> HUDFundingGuideService:
    """Dependency injection for FastAPI."""
    return hud_funding_guide
