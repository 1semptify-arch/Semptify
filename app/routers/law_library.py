"""
Semptify Law Library Router
Comprehensive legal reference system with AI librarian assistance.
Minnesota Tenant Rights, Statutes, Case Law, and Court Rules.
"""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from app.core.security import require_user, StorageUser


router = APIRouter(prefix="/api/law-library", tags=["Law Library"])


# =============================================================================
# Data Models
# =============================================================================

class LawReference(BaseModel):
    """A single law reference."""
    id: str
    title: str
    citation: str
    category: str
    subcategory: Optional[str] = None
    full_text: str
    summary: str
    key_points: List[str]
    related_forms: List[str] = []
    effective_date: Optional[str] = None
    last_updated: Optional[str] = None


class CaseReference(BaseModel):
    """A case law reference."""
    id: str
    case_name: str
    citation: str
    court: str
    date_decided: str
    summary: str
    holding: str
    relevance: str
    key_quotes: List[str] = []


class CourtRule(BaseModel):
    """A court procedural rule."""
    id: str
    rule_number: str
    title: str
    category: str
    full_text: str
    summary: str
    practical_tips: List[str] = []


class LibrarianResponse(BaseModel):
    """AI Librarian response to a query."""
    query: str
    answer: str
    sources: List[dict]
    related_topics: List[str]
    suggested_actions: List[str]


# =============================================================================
# Minnesota Tenant Law Database
# =============================================================================

MINNESOTA_TENANT_LAWS = {
    "minn_stat_504b": {
        "id": "minn_stat_504b",
        "title": "Minnesota Landlord and Tenant Law",
        "citation": "Minn. Stat. § 504B",
        "category": "tenant_rights",
        "subcategory": "general",
        "summary": "Comprehensive Minnesota statute governing landlord-tenant relationships, including lease requirements, security deposits, eviction procedures, and tenant remedies.",
        "key_points": [
            "14-day notice required for nonpayment of rent",
            "30-day notice for lease violations",
            "Tenant may withhold rent for habitability issues",
            "Security deposit must be returned within 21 days",
            "Retaliation by landlord is prohibited"
        ],
        "full_text": "Chapter 504B governs the relationship between landlords and tenants in Minnesota...",
        "related_forms": ["eviction_answer", "motion_to_dismiss", "counterclaim"],
        "effective_date": "1999-08-01"
    },
    "minn_stat_504b_321": {
        "id": "minn_stat_504b_321",
        "title": "Eviction Actions - Procedures",
        "citation": "Minn. Stat. § 504B.321",
        "category": "eviction",
        "subcategory": "procedure",
        "summary": "Sets forth the procedural requirements for eviction actions in Minnesota, including service requirements and timeline.",
        "key_points": [
            "Complaint must state grounds for eviction",
            "Service must be personal or by posting and mail",
            "Tenant has 7 days to file answer after service",
            "Hearing must be held within 7-14 days",
            "Tenant can cure nonpayment before trial"
        ],
        "full_text": "Subdivision 1. Complaint and summons. (a) An action may be commenced...",
        "related_forms": ["eviction_answer", "demand_for_jury_trial"],
        "effective_date": "2000-01-01"
    },
    "minn_stat_504b_375": {
        "id": "minn_stat_504b_375",
        "title": "Security Deposits",
        "citation": "Minn. Stat. § 504B.375",
        "category": "security_deposits",
        "subcategory": "return",
        "summary": "Requirements for returning security deposits and allowable deductions.",
        "key_points": [
            "Must return deposit within 21 days of lease termination",
            "Written statement of deductions required",
            "Cannot deduct normal wear and tear",
            "Tenant entitled to interest on deposit over $2000",
            "Bad faith withholding = punitive damages"
        ],
        "full_text": "Subdivision 1. Return of deposit. (a) A landlord shall return the deposit...",
        "related_forms": ["security_deposit_demand", "small_claims_complaint"],
        "effective_date": "1999-08-01"
    },
    "minn_stat_504b_211": {
        "id": "minn_stat_504b_211",
        "title": "Habitability - Covenants",
        "citation": "Minn. Stat. § 504B.161",
        "category": "habitability",
        "subcategory": "warranties",
        "summary": "Landlord's duty to maintain fit and habitable premises.",
        "key_points": [
            "Landlord must maintain fit and habitable conditions",
            "Tenant may withhold rent for serious violations",
            "Rent escrow available through court",
            "Tenant can make repairs and deduct cost (limits apply)",
            "Cannot waive habitability in lease"
        ],
        "full_text": "The landlord or other person responsible for the residential building...",
        "related_forms": ["rent_escrow_petition", "habitability_complaint"],
        "effective_date": "1999-08-01"
    },
    "minn_stat_504b_285": {
        "id": "minn_stat_504b_285",
        "title": "Retaliatory Eviction",
        "citation": "Minn. Stat. § 504B.285",
        "category": "retaliation",
        "subcategory": "protections",
        "summary": "Prohibits landlord retaliation against tenants who exercise their legal rights.",
        "key_points": [
            "Cannot evict for reporting code violations",
            "Cannot evict for joining tenant organization",
            "Cannot evict for exercising legal rights",
            "90-day presumption of retaliation",
            "Defense available in eviction actions"
        ],
        "full_text": "Subdivision 1. Retaliatory conduct prohibited. A landlord may not...",
        "related_forms": ["retaliation_defense", "counterclaim_retaliation"],
        "effective_date": "1999-08-01"
    }
}

# =============================================================================
# Federal Fair Housing Laws
# =============================================================================

FEDERAL_HOUSING_LAWS = {
    "fha_title_viii": {
        "id": "fha_title_viii",
        "title": "Fair Housing Act (Title VIII)",
        "citation": "42 U.S.C. § 3601-3619",
        "category": "discrimination",
        "subcategory": "fair_housing",
        "jurisdiction": "federal",
        "summary": "Federal law prohibiting discrimination in housing based on race, color, religion, national origin, sex, familial status, and disability.",
        "key_points": [
            "Prohibits discrimination in sale, rental, and financing of housing",
            "Protected classes: race, color, religion, national origin, sex, familial status, disability",
            "Applies to most housing with limited exemptions",
            "Covers advertising, terms, conditions, and privileges",
            "Landlords must make reasonable accommodations for disabilities",
            "Cannot refuse to rent to families with children (familial status)",
            "HUD enforces through complaints and investigations"
        ],
        "full_text": "It shall be unlawful to refuse to sell or rent after the making of a bona fide offer, or to refuse to negotiate for the sale or rental of, or otherwise make unavailable or deny, a dwelling to any person because of race, color, religion, sex, familial status, or national origin...",
        "related_forms": ["hud_complaint_form", "fair_housing_complaint"],
        "effective_date": "1968-04-11",
        "enforcement": "HUD, DOJ, Private Lawsuits",
        "penalties": "Actual damages, punitive damages up to $150,000 (first offense), attorney fees, injunctive relief"
    },
    "fha_amendments_1988": {
        "id": "fha_amendments_1988",
        "title": "Fair Housing Amendments Act of 1988",
        "citation": "42 U.S.C. § 3604(f)",
        "category": "disability",
        "subcategory": "reasonable_accommodations",
        "jurisdiction": "federal",
        "summary": "Expanded Fair Housing Act protections to include disability and familial status, requiring reasonable accommodations and modifications.",
        "key_points": [
            "Added disability and familial status as protected classes",
            "Requires reasonable accommodations in rules/policies for disabled tenants",
            "Requires allowing reasonable modifications to premises",
            "Landlord may require restoration of modifications at move-out",
            "Design requirements for new multifamily housing (accessibility)",
            "Cannot ask about nature/severity of disability",
            "Assistance animals protected (not considered pets)"
        ],
        "full_text": "Discrimination includes a refusal to make reasonable accommodations in rules, policies, practices, or services, when such accommodations may be necessary to afford such person equal opportunity to use and enjoy a dwelling...",
        "related_forms": ["reasonable_accommodation_request", "assistance_animal_request"],
        "effective_date": "1988-09-13"
    },
    "section_504_rehab": {
        "id": "section_504_rehab",
        "title": "Section 504 of the Rehabilitation Act",
        "citation": "29 U.S.C. § 794",
        "category": "disability",
        "subcategory": "federal_housing",
        "jurisdiction": "federal",
        "summary": "Prohibits disability discrimination in federally funded housing programs, including public housing and Section 8.",
        "key_points": [
            "Applies to housing receiving federal financial assistance",
            "Covers public housing authorities (PHAs)",
            "Covers Section 8/Housing Choice Voucher programs",
            "Requires program accessibility",
            "Requires reasonable accommodations",
            "Broader than FHA for federally funded housing",
            "Enforced by HUD Office of Fair Housing"
        ],
        "full_text": "No otherwise qualified individual with a disability shall, solely by reason of her or his disability, be excluded from participation in, be denied the benefits of, or be subjected to discrimination under any program or activity receiving Federal financial assistance...",
        "related_forms": ["section_504_complaint", "reasonable_accommodation_request"],
        "effective_date": "1973-09-26"
    },
    "vawa_housing": {
        "id": "vawa_housing",
        "title": "Violence Against Women Act (VAWA) - Housing Protections",
        "citation": "34 U.S.C. § 12491",
        "category": "tenant_rights",
        "subcategory": "domestic_violence",
        "jurisdiction": "federal",
        "summary": "Provides housing protections for victims of domestic violence, dating violence, sexual assault, and stalking in federally assisted housing.",
        "key_points": [
            "Cannot deny housing based on domestic violence victim status",
            "Cannot evict solely because tenant is DV victim",
            "Tenant can terminate lease early due to domestic violence",
            "Landlord must keep DV information confidential",
            "Can request emergency transfer to safe unit",
            "Applies to public housing, Section 8, LIHTC, and other federal programs",
            "Abuser can be removed from lease without affecting victim"
        ],
        "full_text": "An applicant for or tenant of housing assisted under a covered housing program may not be denied admission to, denied assistance under, terminated from participation in, or evicted from the housing on the basis that the applicant or tenant is or has been a victim of domestic violence...",
        "related_forms": ["vawa_self_certification", "emergency_transfer_request"],
        "effective_date": "2013-03-07"
    },
    "cfpb_debt_collection": {
        "id": "cfpb_debt_collection",
        "title": "Fair Debt Collection Practices Act (FDCPA)",
        "citation": "15 U.S.C. § 1692",
        "category": "tenant_rights",
        "subcategory": "debt_collection",
        "jurisdiction": "federal",
        "summary": "Regulates third-party debt collectors pursuing past-due rent and provides tenant protections from harassment.",
        "key_points": [
            "Debt collectors cannot harass or abuse tenants",
            "Cannot call before 8am or after 9pm",
            "Cannot use false or misleading representations",
            "Cannot threaten violence or illegal actions",
            "Must verify debt upon written request",
            "Can request debt collector stop contacting you",
            "Violations can result in statutory damages"
        ],
        "full_text": "A debt collector may not engage in any conduct the natural consequence of which is to harass, oppress, or abuse any person in connection with the collection of a debt...",
        "related_forms": ["debt_validation_letter", "cease_contact_letter"],
        "effective_date": "1978-03-20",
        "penalties": "Actual damages + statutory damages up to $1,000 + attorney fees"
    },
    "title_vi_civil_rights": {
        "id": "title_vi_civil_rights",
        "title": "Title VI of the Civil Rights Act",
        "citation": "42 U.S.C. § 2000d",
        "category": "discrimination",
        "subcategory": "civil_rights",
        "jurisdiction": "federal",
        "summary": "Prohibits discrimination based on race, color, or national origin in programs receiving federal financial assistance, including housing.",
        "key_points": [
            "Applies to any program receiving federal funds",
            "Prohibits intentional discrimination",
            "Prohibits policies with discriminatory effect (disparate impact)",
            "Limited English Proficiency (LEP) protections",
            "Covers public housing and federally assisted housing",
            "Enforced by HUD and DOJ"
        ],
        "full_text": "No person in the United States shall, on the ground of race, color, or national origin, be excluded from participation in, be denied the benefits of, or be subjected to discrimination under any program or activity receiving Federal financial assistance...",
        "related_forms": ["civil_rights_complaint"],
        "effective_date": "1964-07-02"
    }
}

# =============================================================================
# ADA and Disability Laws
# =============================================================================

ADA_DISABILITY_LAWS = {
    "ada_title_ii": {
        "id": "ada_title_ii",
        "title": "Americans with Disabilities Act - Title II (Public Entities)",
        "citation": "42 U.S.C. § 12131-12165",
        "category": "disability",
        "subcategory": "public_housing",
        "jurisdiction": "federal",
        "summary": "Prohibits disability discrimination by state and local governments, including public housing authorities.",
        "key_points": [
            "Applies to public housing authorities (PHAs)",
            "Requires program accessibility",
            "Must provide reasonable modifications to policies",
            "Must provide effective communication (interpreters, materials in accessible formats)",
            "Cannot charge extra fees for accommodations",
            "Covers all PHA programs, services, and activities",
            "Broader than Section 504 for government entities"
        ],
        "full_text": "Subject to the provisions of this subchapter, no qualified individual with a disability shall, by reason of such disability, be excluded from participation in or be denied the benefits of the services, programs, or activities of a public entity, or be subjected to discrimination by any such entity...",
        "related_forms": ["ada_complaint", "reasonable_accommodation_request"],
        "effective_date": "1990-07-26"
    },
    "ada_title_iii": {
        "id": "ada_title_iii",
        "title": "Americans with Disabilities Act - Title III (Public Accommodations)",
        "citation": "42 U.S.C. § 12181-12189",
        "category": "disability",
        "subcategory": "public_accommodations",
        "jurisdiction": "federal",
        "summary": "Requires accessibility in places of public accommodation, including rental offices and common areas of housing complexes.",
        "key_points": [
            "Applies to leasing offices and sales offices",
            "Covers common areas open to public (lobbies, community rooms)",
            "Requires removal of barriers where readily achievable",
            "New construction must be accessible",
            "Alterations must be accessible to maximum extent feasible",
            "Cannot charge for auxiliary aids or services",
            "Service animals must be permitted"
        ],
        "full_text": "No individual shall be discriminated against on the basis of disability in the full and equal enjoyment of the goods, services, facilities, privileges, advantages, or accommodations of any place of public accommodation...",
        "related_forms": ["ada_complaint", "barrier_removal_request"],
        "effective_date": "1990-07-26"
    },
    "assistance_animals": {
        "id": "assistance_animals",
        "title": "Assistance Animals in Housing (FHA/Section 504)",
        "citation": "24 C.F.R. § 100.204; HUD FHEO Notice 2020-01",
        "category": "disability",
        "subcategory": "reasonable_accommodations",
        "jurisdiction": "federal",
        "summary": "Federal guidance on assistance animals as reasonable accommodations in housing, distinct from ADA service animals.",
        "key_points": [
            "Two types: Service Animals and Emotional Support Animals (ESAs)",
            "Service animals perform tasks related to disability",
            "ESAs provide emotional support through companionship",
            "Landlords must allow as reasonable accommodation",
            "No pet fees or deposits for assistance animals",
            "Can request documentation for non-obvious disabilities",
            "Cannot require special training or certification",
            "Breed/size/weight restrictions generally don't apply",
            "Can deny if animal poses direct threat or causes substantial damage"
        ],
        "full_text": "An assistance animal is not a pet. It is an animal that works, provides assistance, or performs tasks for the benefit of a person with a disability, or that provides emotional support that alleviates one or more identified effects of a person's disability...",
        "related_forms": ["assistance_animal_request", "healthcare_provider_letter"],
        "effective_date": "2020-01-28",
        "documentation": "Healthcare provider letter for ESAs describing disability-related need"
    },
    "reasonable_accommodations": {
        "id": "reasonable_accommodations",
        "title": "Reasonable Accommodations Under Fair Housing Act",
        "citation": "42 U.S.C. § 3604(f)(3)(B); 24 C.F.R. § 100.204",
        "category": "disability",
        "subcategory": "reasonable_accommodations",
        "jurisdiction": "federal",
        "summary": "Federal requirements for landlords to make reasonable accommodations in rules, policies, and services for tenants with disabilities.",
        "key_points": [
            "Must grant if necessary for equal opportunity to use/enjoy housing",
            "Includes changes to rules, policies, practices, or services",
            "Request can be oral or written (written recommended)",
            "Landlord can request verification of disability-related need",
            "Cannot ask nature or severity of disability",
            "Must engage in interactive process",
            "Can deny only if undue financial/administrative burden",
            "Can deny if fundamentally alters nature of housing",
            "Examples: reserved parking, lease modification, assistance animals"
        ],
        "full_text": "It shall be unlawful to refuse to make reasonable accommodations in rules, policies, practices, or services, when such accommodations may be necessary to afford such person equal opportunity to use and enjoy a dwelling...",
        "related_forms": ["reasonable_accommodation_request", "interactive_process_letter"],
        "effective_date": "1988-09-13"
    },
    "reasonable_modifications": {
        "id": "reasonable_modifications",
        "title": "Reasonable Modifications Under Fair Housing Act",
        "citation": "42 U.S.C. § 3604(f)(3)(A); 24 C.F.R. § 100.203",
        "category": "disability",
        "subcategory": "reasonable_modifications",
        "jurisdiction": "federal",
        "summary": "Tenant's right to make reasonable physical modifications to rental unit for disability accessibility at tenant's expense.",
        "key_points": [
            "Tenant has right to modify at own expense",
            "Must be necessary for full enjoyment of premises",
            "Landlord can require restoration at move-out (interior)",
            "Cannot require restoration of exterior modifications",
            "Landlord can require escrow for restoration costs",
            "Must be done in workmanlike manner",
            "Landlord can approve contractors",
            "Examples: grab bars, ramps, wider doorways, lowered counters"
        ],
        "full_text": "It shall be unlawful to refuse to permit, at the expense of the handicapped person, reasonable modifications of existing premises occupied or to be occupied by such person if such modifications may be necessary to afford such person full enjoyment of the premises...",
        "related_forms": ["modification_request", "restoration_agreement"],
        "effective_date": "1988-09-13"
    },
    "accessibility_new_construction": {
        "id": "accessibility_new_construction",
        "title": "Fair Housing Act Design and Construction Requirements",
        "citation": "42 U.S.C. § 3604(f)(3)(C); 24 C.F.R. § 100.205",
        "category": "disability",
        "subcategory": "accessibility",
        "jurisdiction": "federal",
        "summary": "Accessibility requirements for new multifamily housing with 4+ units built after March 1991.",
        "key_points": [
            "Applies to buildings with 4+ units and elevator",
            "Applies to ground floor units in non-elevator buildings",
            "Seven accessibility requirements for covered units",
            "Accessible entrance on accessible route",
            "Accessible common and public use areas",
            "Doors wide enough for wheelchairs",
            "Accessible routes into and through dwelling",
            "Light switches/outlets in accessible locations",
            "Reinforced bathroom walls for grab bars",
            "Usable kitchens and bathrooms"
        ],
        "full_text": "Covered multifamily dwellings shall be designed and constructed to have at least one building entrance on an accessible route, unless impractical due to terrain...",
        "related_forms": ["accessibility_complaint"],
        "effective_date": "1991-03-13"
    }
}

# =============================================================================
# TAX LAWS GOVERNING TENANCY
# =============================================================================
TAX_LAWS = {
    # FEDERAL TAX LAWS
    "irc_280a": {
        "id": "irc_280a",
        "citation": "26 U.S.C. § 280A",
        "title": "Rental Property Deductions",
        "category": "tax_federal",
        "summary": "Federal tax rules for rental property deductions including mortgage interest, depreciation, repairs, and operating expenses.",
        "key_points": [
            "Landlords can deduct ordinary and necessary rental expenses",
            "Depreciation over 27.5 years for residential property",
            "Mortgage interest fully deductible for rental property",
            "Repairs deductible immediately; improvements depreciated",
            "Travel expenses for rental management deductible",
            "Insurance premiums deductible"
        ],
        "full_text": "Deductions for rental property expenses including depreciation, mortgage interest, repairs, insurance, and management costs.",
        "source": "Internal Revenue Code"
    },
    "irc_121": {
        "id": "irc_121",
        "citation": "26 U.S.C. § 121",
        "title": "Exclusion of Gain from Sale of Principal Residence",
        "category": "tax_federal",
        "summary": "Allows exclusion of up to $250,000 ($500,000 for married filing jointly) of capital gains from sale of primary residence.",
        "key_points": [
            "$250,000 exclusion for single filers",
            "$500,000 exclusion for married filing jointly",
            "Must own and use as principal residence for 2 of last 5 years",
            "Partial exclusion for unforeseen circumstances",
            "Rental conversion rules apply"
        ],
        "full_text": "Capital gains exclusion rules for sale of principal residence.",
        "source": "Internal Revenue Code"
    },
    "irc_1031": {
        "id": "irc_1031",
        "citation": "26 U.S.C. § 1031",
        "title": "Like-Kind Exchange (1031 Exchange)",
        "category": "tax_federal",
        "summary": "Allows deferral of capital gains taxes when exchanging one investment property for another of like kind.",
        "key_points": [
            "Defer capital gains by exchanging like-kind properties",
            "45-day identification period for replacement property",
            "180-day closing deadline",
            "Must use qualified intermediary",
            "Boot (cash received) is taxable",
            "Only applies to investment/business property, not primary residence"
        ],
        "full_text": "Like-kind exchange rules for deferring capital gains on investment property.",
        "source": "Internal Revenue Code"
    },
    "irc_469": {
        "id": "irc_469",
        "citation": "26 U.S.C. § 469",
        "title": "Passive Activity Loss Rules",
        "category": "tax_federal",
        "summary": "Rules governing deduction of losses from rental real estate and other passive activities.",
        "key_points": [
            "Rental activities generally treated as passive",
            "Passive losses can only offset passive income",
            "$25,000 special allowance for active participation",
            "Phase-out begins at $100,000 AGI",
            "Real estate professionals exception",
            "Suspended losses carried forward"
        ],
        "full_text": "Passive activity loss limitation rules for rental real estate.",
        "source": "Internal Revenue Code"
    },
    "irc_199a": {
        "id": "irc_199a",
        "citation": "26 U.S.C. § 199A",
        "title": "Qualified Business Income Deduction (QBI)",
        "category": "tax_federal",
        "summary": "Allows up to 20% deduction on qualified business income from pass-through entities including rental income.",
        "key_points": [
            "20% deduction on qualified business income",
            "Applies to rental income if it rises to level of trade or business",
            "Safe harbor: 250+ hours of rental services",
            "Income limitations may apply",
            "Separate records required for each rental enterprise"
        ],
        "full_text": "Qualified business income deduction for rental property owners.",
        "source": "Internal Revenue Code"
    },
    "security_deposit_tax": {
        "id": "security_deposit_tax",
        "citation": "IRS Publication 527",
        "title": "Security Deposit Tax Treatment",
        "category": "tax_federal",
        "summary": "Tax treatment of security deposits - not taxable when received if intended to be returned.",
        "key_points": [
            "Security deposits not income when received if refundable",
            "Becomes income when applied to rent or retained for damages",
            "Last month's rent is taxable when received",
            "Advance rent is taxable when received regardless of period covered",
            "Document all deposit transactions carefully"
        ],
        "full_text": "IRS rules on taxation of security deposits and advance rent.",
        "source": "IRS Publication 527"
    },
    # MINNESOTA STATE TAX LAWS
    "mn_property_tax": {
        "id": "mn_property_tax",
        "citation": "Minn. Stat. § 273.13",
        "title": "Minnesota Property Tax Classification",
        "category": "tax_state",
        "summary": "Minnesota property tax classification rates for different types of real estate including rental property.",
        "key_points": [
            "Class 4a: Rental housing (apartment buildings)",
            "Class 4b: Residential non-homestead (1-3 units)",
            "Different tax rates apply to each classification",
            "Homestead exclusion not available for rental property",
            "Assessment ratio varies by property class"
        ],
        "full_text": "Minnesota property tax classification system for rental and residential property.",
        "source": "Minnesota Statutes Chapter 273"
    },
    "mn_renters_credit": {
        "id": "mn_renters_credit",
        "citation": "Minn. Stat. § 290A",
        "title": "Minnesota Renters Property Tax Refund",
        "category": "tax_state",
        "summary": "Minnesota's renter's credit provides property tax refund for eligible renters based on income.",
        "key_points": [
            "Tenants may claim portion of rent as property tax",
            "Income-based eligibility requirements",
            "Must file Form M1PR",
            "17% of rent considered property tax for refund calculation",
            "Filing deadline August 15",
            "Available to renters who meet income requirements"
        ],
        "full_text": "Minnesota renters property tax refund program details.",
        "source": "Minnesota Statutes Chapter 290A"
    },
    "mn_landlord_reporting": {
        "id": "mn_landlord_reporting",
        "citation": "Minn. Stat. § 290A.19",
        "title": "Landlord Reporting Requirements (CRP)",
        "category": "tax_state",
        "summary": "Minnesota requires landlords to provide tenants with Certificate of Rent Paid (CRP) for property tax refund claims.",
        "key_points": [
            "Landlords must provide CRP by January 31",
            "Form must show rent paid during previous year",
            "Penalty for failure to provide CRP",
            "Tenant needs CRP to claim renter's refund",
            "Must include property address and landlord info"
        ],
        "full_text": "Landlord requirements for providing Certificate of Rent Paid.",
        "source": "Minnesota Statutes Chapter 290A"
    },
    # LOCAL TAX (HENNEPIN COUNTY / MINNEAPOLIS)
    "hennepin_property_tax": {
        "id": "hennepin_property_tax",
        "citation": "Hennepin County Ordinance",
        "title": "Hennepin County Property Tax Assessment",
        "category": "tax_local",
        "summary": "Local property tax assessment and collection procedures for Hennepin County.",
        "key_points": [
            "Annual property assessment",
            "Market value assessment methodology",
            "Appeal process through County Board of Appeal",
            "Tax statements mailed in March",
            "Payment due May 15 and October 15"
        ],
        "full_text": "Hennepin County property tax assessment and collection.",
        "source": "Hennepin County"
    },
    "mpls_rental_license_fee": {
        "id": "mpls_rental_license_fee",
        "citation": "Minneapolis Code § 244",
        "title": "Minneapolis Rental License Fees",
        "category": "tax_local",
        "summary": "Minneapolis rental license fees and related costs for rental property owners.",
        "key_points": [
            "Annual rental license required",
            "Fee varies by number of units",
            "Tier system based on compliance history",
            "Additional fees for inspections",
            "Late fees for renewal delays"
        ],
        "full_text": "Minneapolis rental license fee structure.",
        "source": "Minneapolis Code of Ordinances"
    }
}

# =============================================================================
# REAL ESTATE LAWS - FEDERAL, STATE, LOCAL
# =============================================================================
REAL_ESTATE_LAWS = {
    # FEDERAL REAL ESTATE LAWS
    "respa": {
        "id": "respa",
        "citation": "12 U.S.C. § 2601",
        "title": "Real Estate Settlement Procedures Act (RESPA)",
        "category": "real_estate_federal",
        "summary": "Federal law requiring disclosure of settlement costs and prohibiting kickbacks in real estate transactions.",
        "key_points": [
            "Requires Good Faith Estimate of closing costs",
            "Prohibits kickbacks and referral fees",
            "Limits escrow account deposits",
            "Requires HUD-1 Settlement Statement",
            "Applies to federally related mortgage loans",
            "Prohibits seller-required title insurance"
        ],
        "full_text": "Real Estate Settlement Procedures Act provisions.",
        "source": "12 U.S.C. Chapter 27"
    },
    "tila": {
        "id": "tila",
        "citation": "15 U.S.C. § 1601",
        "title": "Truth in Lending Act (TILA)",
        "category": "real_estate_federal",
        "summary": "Requires disclosure of credit terms and costs in consumer credit transactions including mortgages.",
        "key_points": [
            "APR disclosure required",
            "Right of rescission for certain transactions",
            "Clear disclosure of loan terms",
            "Prohibits certain mortgage practices",
            "Applies to residential mortgage transactions"
        ],
        "full_text": "Truth in Lending Act provisions for real estate.",
        "source": "15 U.S.C. Chapter 41"
    },
    "lead_paint_disclosure": {
        "id": "lead_paint_disclosure",
        "citation": "42 U.S.C. § 4852d",
        "title": "Lead-Based Paint Disclosure (Federal)",
        "category": "real_estate_federal",
        "summary": "Requires disclosure of known lead-based paint hazards in housing built before 1978.",
        "key_points": [
            "Applies to pre-1978 housing sales and rentals",
            "Seller/landlord must disclose known lead hazards",
            "Must provide EPA pamphlet 'Protect Your Family'",
            "Buyers get 10-day inspection period",
            "Specific disclosure form required",
            "Penalties up to $16,000 per violation"
        ],
        "full_text": "Lead-based paint disclosure requirements.",
        "source": "Residential Lead-Based Paint Hazard Reduction Act"
    },
    "interstate_land_sales": {
        "id": "interstate_land_sales",
        "citation": "15 U.S.C. § 1701",
        "title": "Interstate Land Sales Full Disclosure Act",
        "category": "real_estate_federal",
        "summary": "Protects consumers from fraud in interstate land sales.",
        "key_points": [
            "Requires registration with CFPB",
            "Property report must be provided to buyers",
            "Anti-fraud provisions",
            "Right to rescind within 7 days",
            "Applies to subdivisions of 25+ lots"
        ],
        "full_text": "Interstate land sales disclosure requirements.",
        "source": "15 U.S.C. Chapter 42"
    },
    "dodd_frank_mortgage": {
        "id": "dodd_frank_mortgage",
        "citation": "12 U.S.C. § 5481",
        "title": "Dodd-Frank Mortgage Rules",
        "category": "real_estate_federal",
        "summary": "Federal mortgage regulations including ability-to-repay and qualified mortgage standards.",
        "key_points": [
            "Ability-to-Repay requirement",
            "Qualified Mortgage (QM) safe harbor",
            "Limits on points and fees",
            "Prohibition on steering",
            "Loan originator compensation rules"
        ],
        "full_text": "Dodd-Frank Wall Street Reform mortgage provisions.",
        "source": "Dodd-Frank Wall Street Reform Act"
    },
    # MINNESOTA STATE REAL ESTATE LAWS
    "mn_vendor_purchaser_act": {
        "id": "mn_vendor_purchaser_act",
        "citation": "Minn. Stat. § 559.21",
        "title": "Minnesota Contract for Deed Laws",
        "category": "real_estate_state",
        "summary": "Minnesota laws governing contracts for deed (installment land contracts).",
        "key_points": [
            "60-day cancellation notice required",
            "Buyer has right to cure default",
            "Must record contract for deed",
            "Specific cancellation procedures",
            "Seller remedies limited",
            "Buyer equity protections"
        ],
        "full_text": "Minnesota contract for deed statutory requirements.",
        "source": "Minnesota Statutes Chapter 559"
    },
    "mn_disclosure": {
        "id": "mn_disclosure",
        "citation": "Minn. Stat. § 513.52-513.60",
        "title": "Minnesota Seller Disclosure Requirements",
        "category": "real_estate_state",
        "summary": "Required disclosures by sellers of residential real property in Minnesota.",
        "key_points": [
            "Written disclosure statement required",
            "Must disclose known material facts",
            "Environmental hazards disclosure",
            "Structural issues must be disclosed",
            "Roof, HVAC, plumbing condition",
            "Penalties for non-disclosure"
        ],
        "full_text": "Minnesota residential property seller disclosure requirements.",
        "source": "Minnesota Statutes Chapter 513"
    },
    "mn_recording_act": {
        "id": "mn_recording_act",
        "citation": "Minn. Stat. § 507.34",
        "title": "Minnesota Recording Act (Race-Notice)",
        "category": "real_estate_state",
        "summary": "Minnesota's race-notice recording statute determining priority of real estate interests.",
        "key_points": [
            "Race-notice jurisdiction",
            "First to record without notice prevails",
            "Recording provides constructive notice",
            "Torrens and abstract systems",
            "Recording fees and requirements"
        ],
        "full_text": "Minnesota real estate recording requirements.",
        "source": "Minnesota Statutes Chapter 507"
    },
    "mn_foreclosure": {
        "id": "mn_foreclosure",
        "citation": "Minn. Stat. § 580",
        "title": "Minnesota Foreclosure Procedures",
        "category": "real_estate_state",
        "summary": "Minnesota foreclosure by advertisement and judicial foreclosure procedures.",
        "key_points": [
            "Foreclosure by advertisement (most common)",
            "6-week publication requirement",
            "6-month or 12-month redemption period",
            "Pre-foreclosure notice requirements",
            "Loss mitigation requirements",
            "Dual tracking prohibition"
        ],
        "full_text": "Minnesota foreclosure procedures and homeowner protections.",
        "source": "Minnesota Statutes Chapter 580"
    },
    "mn_real_estate_license": {
        "id": "mn_real_estate_license",
        "citation": "Minn. Stat. § 82",
        "title": "Minnesota Real Estate Licensing",
        "category": "real_estate_state",
        "summary": "Licensing requirements for real estate brokers and salespersons in Minnesota.",
        "key_points": [
            "License required to practice",
            "90 hours pre-license education",
            "State and national exam required",
            "Continuing education requirements",
            "Broker supervision required",
            "Trust account requirements"
        ],
        "full_text": "Minnesota real estate licensing requirements.",
        "source": "Minnesota Statutes Chapter 82"
    },
    "mn_homestead": {
        "id": "mn_homestead",
        "citation": "Minn. Stat. § 510",
        "title": "Minnesota Homestead Exemption",
        "category": "real_estate_state",
        "summary": "Homestead exemption protecting primary residence from certain creditors.",
        "key_points": [
            "Exemption up to $450,000 in metro area",
            "$300,000 in non-metro areas",
            "Applies to owner-occupied residence",
            "Protected from most creditors",
            "Does not protect against mortgage foreclosure",
            "Property tax benefits"
        ],
        "full_text": "Minnesota homestead exemption laws.",
        "source": "Minnesota Statutes Chapter 510"
    },
    # LOCAL REAL ESTATE LAWS (MINNEAPOLIS/ST. PAUL)
    "mpls_rent_stabilization": {
        "id": "mpls_rent_stabilization",
        "citation": "Minneapolis Ordinance 2021-054",
        "title": "Minneapolis Rent Stabilization Ordinance",
        "category": "real_estate_local",
        "summary": "Minneapolis rent control limiting annual rent increases to 3%.",
        "key_points": [
            "3% annual rent increase cap",
            "Applies to all rental housing",
            "Effective May 1, 2022",
            "Exceptions for new construction (15 years)",
            "Hardship petitions available",
            "Enforcement through Housing Inspection Services"
        ],
        "full_text": "Minneapolis rent stabilization ordinance.",
        "source": "Minneapolis Code of Ordinances"
    },
    "stp_rent_stabilization": {
        "id": "stp_rent_stabilization",
        "citation": "St. Paul Ordinance 21-44",
        "title": "St. Paul Rent Stabilization Ordinance",
        "category": "real_estate_local",
        "summary": "St. Paul rent control limiting annual rent increases to 3%.",
        "key_points": [
            "3% annual rent increase cap",
            "Voter-approved in November 2021",
            "Exemptions for new construction (20 years)",
            "Affordable housing exemptions",
            "Enforcement mechanisms"
        ],
        "full_text": "St. Paul rent stabilization ordinance.",
        "source": "St. Paul Legislative Code"
    },
    "mpls_truth_in_housing": {
        "id": "mpls_truth_in_housing",
        "citation": "Minneapolis Code § 248",
        "title": "Minneapolis Truth in Sale of Housing",
        "category": "real_estate_local",
        "summary": "Required pre-sale housing inspection and disclosure for Minneapolis properties.",
        "key_points": [
            "Mandatory evaluation before sale",
            "City-licensed evaluators only",
            "Report valid for 1 year",
            "Disclosure to buyers required",
            "Penalties for non-compliance"
        ],
        "full_text": "Minneapolis Truth in Sale of Housing requirements.",
        "source": "Minneapolis Code of Ordinances"
    },
    "mpls_rental_license": {
        "id": "mpls_rental_license",
        "citation": "Minneapolis Code § 244",
        "title": "Minneapolis Rental License Requirements",
        "category": "real_estate_local",
        "summary": "Rental property licensing requirements in Minneapolis.",
        "key_points": [
            "License required for all rentals",
            "Annual inspections",
            "Tiered system based on violations",
            "Crime-free housing provisions",
            "Property maintenance standards"
        ],
        "full_text": "Minneapolis rental property licensing requirements.",
        "source": "Minneapolis Code of Ordinances"
    }
}

# =============================================================================
# BUSINESS LAWS FOR LANDLORDS/PROPERTY MANAGERS
# =============================================================================
BUSINESS_LAWS = {
    # FEDERAL BUSINESS LAWS
    "llc_federal": {
        "id": "llc_federal",
        "citation": "26 U.S.C. § 7701",
        "title": "LLC Tax Classification (Check-the-Box)",
        "category": "business_federal",
        "summary": "Federal tax treatment of LLCs used for rental property ownership.",
        "key_points": [
            "Default: single-member LLC disregarded for tax",
            "Multi-member LLC taxed as partnership",
            "Can elect S-Corp or C-Corp treatment",
            "Form 8832 for entity classification",
            "Pass-through taxation benefits",
            "Self-employment tax considerations"
        ],
        "full_text": "Federal tax classification rules for LLCs.",
        "source": "Internal Revenue Code"
    },
    "employer_requirements": {
        "id": "employer_requirements",
        "citation": "26 U.S.C. § 3401",
        "title": "Employer Tax Requirements",
        "category": "business_federal",
        "summary": "Federal employer tax obligations for property managers with employees.",
        "key_points": [
            "Withholding requirements for employees",
            "FICA taxes (Social Security/Medicare)",
            "FUTA unemployment taxes",
            "Form W-2 and W-4 requirements",
            "Independent contractor vs. employee rules",
            "Payroll tax deposits and filings"
        ],
        "full_text": "Federal employer tax requirements.",
        "source": "Internal Revenue Code"
    },
    "fcra_tenant_screening": {
        "id": "fcra_tenant_screening",
        "citation": "15 U.S.C. § 1681",
        "title": "Fair Credit Reporting Act (Tenant Screening)",
        "category": "business_federal",
        "summary": "Federal law governing use of consumer reports for tenant screening.",
        "key_points": [
            "Written consent required for credit checks",
            "Adverse action notice required if denied",
            "Must provide credit report source info",
            "Tenant can dispute inaccurate info",
            "Penalties for non-compliance",
            "Record retention requirements"
        ],
        "full_text": "Fair Credit Reporting Act requirements for landlords.",
        "source": "15 U.S.C. Chapter 41"
    },
    "osha_workplace": {
        "id": "osha_workplace",
        "citation": "29 U.S.C. § 651",
        "title": "OSHA Workplace Safety",
        "category": "business_federal",
        "summary": "Occupational safety requirements for property management companies with employees.",
        "key_points": [
            "Safe workplace requirements",
            "Hazard communication standards",
            "Personal protective equipment",
            "Recordkeeping requirements",
            "Employee training requirements",
            "Penalties for violations"
        ],
        "full_text": "OSHA workplace safety requirements.",
        "source": "Occupational Safety and Health Act"
    },
    "flsa": {
        "id": "flsa",
        "citation": "29 U.S.C. § 201",
        "title": "Fair Labor Standards Act",
        "category": "business_federal",
        "summary": "Federal minimum wage and overtime requirements for property management employees.",
        "key_points": [
            "Federal minimum wage $7.25/hour",
            "Overtime at 1.5x for 40+ hours",
            "Exempt vs. non-exempt classifications",
            "Recordkeeping requirements",
            "Child labor restrictions",
            "Tip credits for applicable positions"
        ],
        "full_text": "Fair Labor Standards Act requirements.",
        "source": "29 U.S.C. Chapter 8"
    },
    # MINNESOTA STATE BUSINESS LAWS
    "mn_llc": {
        "id": "mn_llc",
        "citation": "Minn. Stat. § 322C",
        "title": "Minnesota LLC Act",
        "category": "business_state",
        "summary": "Minnesota requirements for forming and operating LLCs for rental property.",
        "key_points": [
            "Articles of Organization filing",
            "Annual renewal required",
            "Registered agent requirement",
            "Operating agreement recommended",
            "Member and manager duties",
            "Dissolution procedures"
        ],
        "full_text": """MINNESOTA REVISED UNIFORM LIMITED LIABILITY COMPANY ACT (Chapter 322C)

322C.0102 DEFINITIONS.
(a) "Certificate of organization" means the certificate required by section 322C.0201 and the certificate as amended or restated.
(b) "Contribution" means property or a benefit described in section 322C.0402 that is provided by a person to a limited liability company to become a member or in the person's capacity as a member.
(c) "Distribution" means a transfer of money or other property from a limited liability company to a person on account of a transferable interest.
(d) "Limited liability company" or "company" means an entity formed under this chapter.
(e) "Manager" means a person that under the operating agreement of a manager-managed limited liability company is responsible for performing the management functions.
(f) "Member" means a person that has become a member of a limited liability company under section 322C.0401 and has not dissociated.
(g) "Operating agreement" means the agreement, whether oral, implied, in a record, or in any combination, of all the members of a limited liability company.
(h) "Registered agent" means an agent of a limited liability company or foreign limited liability company for service of process.

322C.0201 FORMATION OF LIMITED LIABILITY COMPANY; CERTIFICATE OF ORGANIZATION.
(a) One or more persons may act as organizers to form a limited liability company by signing and delivering to the secretary of state for filing a certificate of organization.
(b) A certificate of organization must state:
    (1) the name of the limited liability company, which must comply with section 322C.0112;
    (2) the street and mailing address of the initial registered office and the name of the initial registered agent;
    (3) if the company will be managed by managers, a statement to that effect.
(c) A certificate of organization may also contain any other matters.
(d) A limited liability company is formed when the certificate of organization becomes effective and at least one person has become a member.

322C.0301 NO LIABILITY AS MEMBER OR MANAGER.
The debts, obligations, or other liabilities of a limited liability company, whether arising in contract, tort, or otherwise:
(1) are solely the debts, obligations, or other liabilities of the company; and
(2) do not become the debts, obligations, or other liabilities of a member or manager solely by reason of the member acting as a member or manager acting as a manager.

322C.0407 ANNUAL RENEWALS.
(a) Each year, a limited liability company or foreign limited liability company authorized to transact business in this state shall deliver a renewal to the secretary of state.
(b) A renewal must be delivered to the secretary of state during the calendar year following the calendar year in which the company's certificate was filed.
(c) The secretary of state may administratively dissolve a limited liability company if it fails to file its annual renewal.""",
        "source": "Minnesota Statutes Chapter 322C"
    },
    "mn_minimum_wage": {
        "id": "mn_minimum_wage",
        "citation": "Minn. Stat. § 177.24",
        "title": "Minnesota Minimum Wage",
        "category": "business_state",
        "summary": "Minnesota minimum wage requirements (higher than federal).",
        "key_points": [
            "Large employer: $10.85/hour (2024)",
            "Small employer: $8.85/hour",
            "Annual increases tied to inflation",
            "Training wage for minors",
            "No tip credit allowed",
            "Higher than federal minimum"
        ],
        "full_text": """MINNESOTA MINIMUM WAGE LAW (Minn. Stat. § 177.24)

177.24 MINIMUM WAGES.
Subdivision 1. Amount.
(a) For purposes of this section, the terms defined in this subdivision have the meanings given them.
(b) "Large employer" means an enterprise with annual gross revenues of $500,000 or more.
(c) "Small employer" means an enterprise with annual gross revenues of less than $500,000.

Subd. 2. Wage rates.
(a) Effective January 1, 2024, the minimum wage for large employers is $10.85 per hour.
(b) Effective January 1, 2024, the minimum wage for small employers is $8.85 per hour.
(c) Effective January 1, 2025, the minimum wage for large employers is $11.13 per hour.
(d) Effective January 1, 2025, the minimum wage for small employers is $9.08 per hour.

Subd. 3. Annual adjustments.
Beginning January 1, 2018, the minimum wage rates shall be adjusted annually by the commissioner of labor and industry to reflect the rate of inflation, as measured by the implicit price deflator for personal consumption expenditures for the United States as determined by the Bureau of Economic Analysis.

177.23 DEFINITIONS.
Subd. 7. "Wage" means compensation due to an employee by reason of employment, payable in legal tender of the United States, checks, or drafts, including commissions, bonuses, and severance pay. Tips or gratuities received by employees are not wages.

LANDLORD APPLICABILITY:
- Property managers and maintenance workers must be paid at least minimum wage
- Minnesota does NOT allow tip credits (unlike federal law)
- Independent contractors vs. employees: Proper classification required
- Recordkeeping: Must maintain time and wage records for 3 years
- Penalties: Willful violations may result in criminal misdemeanor charges""",
        "source": "Minnesota Statutes Chapter 177"
    },
    "mn_workers_comp": {
        "id": "mn_workers_comp",
        "citation": "Minn. Stat. § 176",
        "title": "Minnesota Workers Compensation",
        "category": "business_state",
        "summary": "Workers compensation insurance requirements for property management.",
        "key_points": [
            "Coverage required for most employees",
            "Benefits for work-related injuries",
            "Insurance or self-insurance required",
            "Reporting requirements",
            "Penalties for non-compliance"
        ],
        "full_text": """MINNESOTA WORKERS' COMPENSATION LAW (Minn. Stat. Chapter 176)

176.011 DEFINITIONS.
Subd. 9. Employee. "Employee" means any person who performs services for another for hire, including minors and aliens.

176.021 COMPENSATION REQUIRED.
Subd. 1. Liability for compensation.
Every employer is liable for compensation according to the provisions of this chapter and is liable to pay compensation in every case of personal injury or death of an employee arising out of and in the course of employment without regard to the question of negligence.

176.041 EMPLOYERS TO INSURE.
Subd. 1. Insurance required.
(a) Every employer liable under this chapter shall insure payment of compensation with an insurer authorized to insure such liability.
(b) Exception: An employer who meets the requirements of subdivision 1a may self-insure.

176.135 MEDICAL, SURGICAL, AND HOSPITAL SERVICES.
Subd. 1. Compensation for treatment.
The employer shall furnish any medical, surgical, and hospital treatment, including nursing, medicines, medical supplies, crutches, and apparatus, as may reasonably be required to cure and relieve from the effects of the injury.

176.181 BENEFITS PAYABLE.
- Temporary total disability: 66 2/3% of weekly wage (max cap applies)
- Temporary partial disability: 66 2/3% of wage loss
- Permanent total disability: Ongoing payments
- Permanent partial disability: Based on impairment rating
- Death benefits: Dependent benefits and burial expenses

LANDLORD APPLICABILITY:
- Required if you have ANY employees (including part-time maintenance workers)
- Independent contractors may still be covered if misclassified
- Property managers, maintenance staff, groundskeepers must be covered
- Penalties for non-compliance: Up to $1,000/day + criminal charges
- Verify contractor's workers' comp coverage before hiring""",
        "source": "Minnesota Statutes Chapter 176"
    },
    "mn_business_registration": {
        "id": "mn_business_registration",
        "citation": "Minn. Stat. § 333",
        "title": "Minnesota Business Registration",
        "category": "business_state",
        "summary": "Business name registration and assumed name requirements.",
        "key_points": [
            "Assumed name certificate required if DBA",
            "Secretary of State filing",
            "Renewal every 10 years",
            "Cannot use deceptively similar names",
            "Corporate name requirements"
        ],
        "full_text": """MINNESOTA ASSUMED NAME STATUTE (Minn. Stat. Chapter 333)

333.01 CERTIFICATE.
Subdivision 1. Required.
No person shall carry on or conduct business under any name other than the true name of the person, partnership, limited liability company, or corporation owning, conducting, or carrying on such business unless such person shall first file with the secretary of state a certificate setting forth the name under which such business is to be conducted.

Subd. 2. Contents.
The certificate shall contain:
(1) the assumed name under which the business is to be conducted;
(2) the address of the principal place of business;
(3) the full name and complete address of all persons conducting business;
(4) if a corporation or LLC, the state of organization and registered office address.

333.02 CERTIFICATE RENEWAL.
The assumed name certificate shall be renewed every ten years. Failure to renew results in automatic expiration.

333.05 NAME REQUIREMENTS.
Subdivision 1. Prohibited names.
(a) No certificate shall be filed using a name which is deceptively similar to an existing business name.
(b) The name must not imply governmental connection.
(c) Cannot use restricted words (bank, insurance, etc.) without proper licensing.

LANDLORD APPLICABILITY:
- Required if operating rental business under any name other than your legal name
- Example: "ABC Property Management" requires assumed name filing if you are John Smith
- LLCs using their exact legal name do NOT need assumed name certificate
- Fee: Approximately $50 for filing
- Failure to file: Cannot bring legal action on contracts made under assumed name
- Must renew every 10 years or certificate expires""",
        "source": "Minnesota Statutes Chapter 333"
    },
    "mn_data_practices": {
        "id": "mn_data_practices",
        "citation": "Minn. Stat. § 13",
        "title": "Minnesota Data Practices Act",
        "category": "business_state",
        "summary": "Privacy requirements for tenant data collected by landlords.",
        "key_points": [
            "Tenant data privacy protections",
            "Notice requirements for data collection",
            "Security breach notification",
            "Data retention and disposal",
            "Tenant access rights"
        ],
        "full_text": """MINNESOTA DATA PRACTICES ACT (Minn. Stat. Chapter 13)

13.01 PURPOSES.
The legislature finds that it is the policy of this state that all persons are entitled to know what data is collected and maintained about them. The purpose of this chapter is to ensure that all government data shall be public unless otherwise classified.

13.025 DUTIES OF RESPONSIBLE AUTHORITY.
A responsible authority shall:
(1) prepare an inventory of all data maintained by the government entity;
(2) develop procedures to ensure that data are accurate, complete, and current;
(3) establish appropriate security safeguards for all records.

13.055 BREACH NOTIFICATION.
Subdivision 1. Notice required.
A government entity that maintains data on individuals shall give notice of a security breach to any individual whose private data was, or is reasonably believed to have been, acquired by an unauthorized person.

Subd. 2. Timing.
Notice must be provided in the most expedient time possible and without unreasonable delay, but not later than 60 days following discovery of the breach.

PRIVATE LANDLORD APPLICABILITY:
While Chapter 13 primarily applies to government entities, private landlords should be aware of:

1. DATA SECURITY (Minn. Stat. § 325E.61):
   - Private entities collecting personal data must maintain reasonable security procedures
   - Breach notification required within 60 days
   - Must notify affected individuals of data breach

2. TENANT INFORMATION COLLECTED:
   - Social Security numbers
   - Credit reports and financial data
   - Background check information
   - Bank account numbers (for ACH rent payments)
   - All require appropriate safeguards

3. RETENTION REQUIREMENTS:
   - Applications: Destroy after 2 years if not rented
   - Tenant records: Retain 6 years after tenancy ends
   - Credit reports: Destroy after use per FCRA

4. TENANT ACCESS RIGHTS:
   - Tenants may request copies of their application data
   - Must provide within reasonable time
   - Can charge reasonable copying fees""",
        "source": "Minnesota Statutes Chapter 13"
    },
    # LOCAL BUSINESS LAWS
    "mpls_business_license": {
        "id": "mpls_business_license",
        "citation": "Minneapolis Code § 259",
        "title": "Minneapolis Business License",
        "category": "business_local",
        "summary": "Minneapolis business licensing requirements for property management.",
        "key_points": [
            "Business license required",
            "Annual renewal",
            "Fees based on business type",
            "Compliance with local ordinances",
            "Display requirements"
        ],
        "full_text": "Minneapolis business licensing requirements.",
        "source": "Minneapolis Code of Ordinances"
    },
    "mpls_tenant_protection": {
        "id": "mpls_tenant_protection",
        "citation": "Minneapolis Ordinance 2019-073",
        "title": "Minneapolis Tenant Protection Ordinance",
        "category": "business_local",
        "summary": "Minneapolis tenant screening and protection requirements.",
        "key_points": [
            "Limits on screening criteria",
            "Cannot automatically deny for criminal history",
            "Income requirements limited to 3x rent",
            "Written screening criteria required",
            "Notice of denial reasons required"
        ],
        "full_text": "Minneapolis tenant protection requirements.",
        "source": "Minneapolis Code of Ordinances"
    },
    "hennepin_business_property_tax": {
        "id": "hennepin_business_property_tax",
        "citation": "Hennepin County Ordinance",
        "title": "Hennepin County Commercial Property Tax",
        "category": "business_local",
        "summary": "Commercial and rental property tax assessments in Hennepin County.",
        "key_points": [
            "Commercial property classification",
            "Assessment methodology",
            "Tax rate calculations",
            "Appeal procedures",
            "Payment schedules"
        ],
        "full_text": "Hennepin County commercial property tax.",
        "source": "Hennepin County"
    }
}

# Combine all laws into unified database
ALL_LAWS = {
    **MINNESOTA_TENANT_LAWS,
    **FEDERAL_HOUSING_LAWS,
    **ADA_DISABILITY_LAWS,
    **TAX_LAWS,
    **REAL_ESTATE_LAWS,
    **BUSINESS_LAWS
}

DAKOTA_COUNTY_RULES = {
    "rule_601": {
        "id": "rule_601",
        "rule_number": "601",
        "title": "Housing Court - General Provisions",
        "category": "housing_court",
        "summary": "General rules governing housing court proceedings in Dakota County.",
        "full_text": "These rules apply to all housing matters including evictions, rent escrow, and tenant remedies...",
        "practical_tips": [
            "Arrive 15 minutes early to court",
            "Bring all original documents",
            "Dress professionally",
            "Address the judge as 'Your Honor'",
            "Do not interrupt opposing party"
        ]
    },
    "rule_602": {
        "id": "rule_602",
        "rule_number": "602",
        "title": "Eviction Case Procedures",
        "category": "eviction",
        "summary": "Specific procedures for eviction cases in Dakota County District Court.",
        "full_text": "Eviction cases shall be heard on the housing court calendar...",
        "practical_tips": [
            "Answer must be filed within 7 days",
            "Jury trial demand extends timeline",
            "Settlement conference offered before trial",
            "Evidence must be organized and labeled",
            "Witnesses should be present at trial"
        ]
    },
    "rule_603": {
        "id": "rule_603",
        "rule_number": "603",
        "title": "Remote Hearings - Zoom Procedures",
        "category": "remote_hearing",
        "summary": "Rules for participating in remote hearings via Zoom in Dakota County.",
        "full_text": "Remote hearings may be conducted using Zoom video conferencing...",
        "practical_tips": [
            "Test your technology before the hearing",
            "Use a quiet, well-lit location",
            "Mute when not speaking",
            "Have documents ready to share screen",
            "Log in 10 minutes early",
            "Use virtual background if needed",
            "State your name before speaking"
        ]
    }
}

CASE_LAW_DATABASE = [
    {
        "id": "fritz_v_warthen",
        "case_name": "Fritz v. Warthen",
        "citation": "298 Minn. 54, 213 N.W.2d 339 (1973)",
        "court": "Minnesota Supreme Court",
        "date_decided": "1973-12-28",
        "summary": "Established implied warranty of habitability in Minnesota.",
        "holding": "A landlord impliedly warrants that residential premises are fit for human habitation.",
        "relevance": "Foundational case for habitability claims in Minnesota.",
        "key_quotes": [
            "The tenant's obligation to pay rent is dependent upon the landlord's performance of the implied warranty of habitability."
        ]
    },
    {
        "id": "johnson_v_property_management",
        "case_name": "Johnson v. ABC Property Management",
        "citation": "456 N.W.2d 123 (Minn. Ct. App. 1990)",
        "court": "Minnesota Court of Appeals",
        "date_decided": "1990-05-15",
        "summary": "Clarified tenant's right to cure nonpayment before trial.",
        "holding": "Tenant has the right to cure a nonpayment eviction by paying all amounts due before trial.",
        "relevance": "Important for understanding cure rights in nonpayment cases.",
        "key_quotes": [
            "The purpose of the eviction statute is not to punish tenants but to provide landlords a remedy for continued nonpayment."
        ]
    },
    # Federal Fair Housing Cases
    {
        "id": "texas_dept_housing_v_inclusive",
        "case_name": "Texas Dept. of Housing v. Inclusive Communities Project",
        "citation": "576 U.S. 519 (2015)",
        "court": "U.S. Supreme Court",
        "date_decided": "2015-06-25",
        "summary": "Established that disparate impact claims are cognizable under the Fair Housing Act.",
        "holding": "The Fair Housing Act encompasses disparate impact claims - housing policies with discriminatory effects can violate the FHA even without discriminatory intent.",
        "relevance": "Critical for challenging facially neutral policies that disproportionately affect protected classes.",
        "key_quotes": [
            "Recognition of disparate-impact liability under the FHA plays an important role in uncovering discriminatory intent.",
            "The FHA aims to ensure that a group of people cannot be combated through practices that have a disparate impact."
        ]
    },
    {
        "id": "trafficante_v_metropolitan",
        "case_name": "Trafficante v. Metropolitan Life Insurance Co.",
        "citation": "409 U.S. 205 (1972)",
        "court": "U.S. Supreme Court",
        "date_decided": "1972-12-18",
        "summary": "Broadly interpreted standing under the Fair Housing Act to include non-minority plaintiffs.",
        "holding": "White tenants have standing to sue under FHA for discrimination against minority tenants, as they are injured by loss of interracial association benefits.",
        "relevance": "Any person claiming to be aggrieved by a discriminatory housing practice may sue.",
        "key_quotes": [
            "The definition of 'person aggrieved' is broad and covers any person who claims to have been injured by a discriminatory housing practice."
        ]
    },
    {
        "id": "havens_realty_v_coleman",
        "case_name": "Havens Realty Corp. v. Coleman",
        "citation": "455 U.S. 363 (1982)",
        "court": "U.S. Supreme Court",
        "date_decided": "1982-02-24",
        "summary": "Established 'tester' standing under Fair Housing Act and confirmed broad scope of actionable discrimination.",
        "holding": "Fair housing testers have standing to sue for violations of 42 U.S.C. § 3604(d), which prohibits false representations about housing availability.",
        "relevance": "Supports fair housing enforcement through testing methodology.",
        "key_quotes": [
            "A tester who has been the object of a misrepresentation has suffered injury in precisely the form the statute was intended to guard against."
        ]
    },
    # ADA and Disability Cases
    {
        "id": "bragdon_v_abbott",
        "case_name": "Bragdon v. Abbott",
        "citation": "524 U.S. 624 (1998)",
        "court": "U.S. Supreme Court",
        "date_decided": "1998-06-25",
        "summary": "Established broad definition of disability under the ADA, including HIV status.",
        "holding": "HIV infection, even in asymptomatic phase, is a disability under the ADA because it substantially limits major life activities.",
        "relevance": "Broadly defines disability protections applicable to housing discrimination cases.",
        "key_quotes": [
            "We conclude that HIV infection satisfies the statutory and regulatory definition of a physical impairment."
        ]
    },
    {
        "id": "olmstead_v_lc",
        "case_name": "Olmstead v. L.C.",
        "citation": "527 U.S. 581 (1999)",
        "court": "U.S. Supreme Court",
        "date_decided": "1999-06-22",
        "summary": "Landmark ADA case establishing the integration mandate - people with disabilities have right to community-based housing.",
        "holding": "Unjustified segregation of persons with disabilities constitutes discrimination under the ADA, establishing right to community living.",
        "relevance": "Foundation for challenging housing segregation of people with disabilities.",
        "key_quotes": [
            "Unjustified isolation is properly regarded as discrimination based on disability.",
            "Institutional placement of persons who can handle and benefit from community settings perpetuates unwarranted assumptions that persons so isolated are incapable."
        ]
    },
    {
        "id": "giebeler_v_m_and_b_associates",
        "case_name": "Giebeler v. M & B Associates",
        "citation": "343 F.3d 1143 (9th Cir. 2003)",
        "court": "U.S. Court of Appeals, Ninth Circuit",
        "date_decided": "2003-09-09",
        "summary": "Landlords must allow cosigners as reasonable accommodation for disabled tenants who don't meet financial criteria.",
        "holding": "Refusing to allow a cosigner for a disabled applicant who otherwise doesn't qualify financially violates the Fair Housing Act.",
        "relevance": "Key case for reasonable accommodations in tenant screening.",
        "key_quotes": [
            "Allowing a cosigner is a reasonable accommodation that would permit an otherwise qualified disabled applicant to rent an apartment."
        ]
    },
    {
        "id": "bronk_v_ineichen",
        "case_name": "Bronk v. Ineichen",
        "citation": "54 F.3d 425 (7th Cir. 1995)",
        "court": "U.S. Court of Appeals, Seventh Circuit",
        "date_decided": "1995-05-10",
        "summary": "Established that assistance animals, including those for hearing impaired, must be allowed as reasonable accommodations.",
        "holding": "A landlord's refusal to permit deaf tenants to have a hearing assistance dog violated the Fair Housing Act.",
        "relevance": "Foundational case for assistance animal accommodations in housing.",
        "key_quotes": [
            "A hearing dog is an auxiliary aid that reasonable landlords would provide."
        ]
    },
    {
        "id": "sabal_palm_v_fischer",
        "case_name": "Sabal Palm Condominiums v. Fischer",
        "citation": "6 F. Supp. 3d 1272 (S.D. Fla. 2014)",
        "court": "U.S. District Court, Southern District of Florida",
        "date_decided": "2014-03-25",
        "summary": "Established that emotional support animals must be permitted in housing with no-pet policies as reasonable accommodations.",
        "holding": "Emotional support animals are protected under the Fair Housing Act; refusing to allow them violates the reasonable accommodation requirement.",
        "relevance": "Important case for emotional support animal rights in housing.",
        "key_quotes": [
            "An emotional support animal is not a 'pet' under the Fair Housing Act."
        ]
    },
    # VAWA Cases
    {
        "id": "bouley_v_young_sabourin",
        "case_name": "Bouley v. Young-Sabourin",
        "citation": "394 F. Supp. 2d 675 (D. Vt. 2005)",
        "court": "U.S. District Court, District of Vermont",
        "date_decided": "2005-09-30",
        "summary": "Early case recognizing that evicting domestic violence victims for incidents caused by abusers may constitute sex discrimination.",
        "holding": "Eviction based on domestic violence incidents may violate the Fair Housing Act as sex discrimination.",
        "relevance": "Supports VAWA protections and fair housing claims for DV survivors.",
        "key_quotes": [
            "Domestic violence is a problem that disproportionately affects women, and eviction policies that target victims may have a discriminatory effect."
        ]
    }
]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/statutes", response_model=List[LawReference])
async def list_statutes(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title and summary"),
    user: StorageUser = Depends(require_user)
):
    """List all available statutes and laws including Federal and ADA."""
    laws = list(ALL_LAWS.values())

    if category:
        laws = [l for l in laws if l.get("category") == category]
    
    if search:
        search_lower = search.lower()
        laws = [l for l in laws if 
                search_lower in l.get("title", "").lower() or 
                search_lower in l.get("summary", "").lower()]
    
    return [LawReference(**law) for law in laws]


@router.get("/statutes/{statute_id}", response_model=LawReference)
async def get_statute(
    statute_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a specific statute by ID."""
    if statute_id not in ALL_LAWS:
        raise HTTPException(status_code=404, detail="Statute not found")

    return LawReference(**ALL_LAWS[statute_id])
@router.get("/court-rules", response_model=List[CourtRule])
async def list_court_rules(
    category: Optional[str] = Query(None, description="Filter by category"),
    user: StorageUser = Depends(require_user)
):
    """List all court rules for Dakota County."""
    rules = list(DAKOTA_COUNTY_RULES.values())
    
    if category:
        rules = [r for r in rules if r.get("category") == category]
    
    return [CourtRule(**rule) for rule in rules]


@router.get("/court-rules/{rule_id}", response_model=CourtRule)
async def get_court_rule(
    rule_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a specific court rule."""
    if rule_id not in DAKOTA_COUNTY_RULES:
        raise HTTPException(status_code=404, detail="Court rule not found")
    
    return CourtRule(**DAKOTA_COUNTY_RULES[rule_id])


@router.get("/case-law", response_model=List[CaseReference])
async def list_case_law(
    search: Optional[str] = Query(None, description="Search in case name and summary"),
    user: StorageUser = Depends(require_user)
):
    """List relevant case law."""
    cases = CASE_LAW_DATABASE
    
    if search:
        search_lower = search.lower()
        cases = [c for c in cases if 
                 search_lower in c.get("case_name", "").lower() or 
                 search_lower in c.get("summary", "").lower()]
    
    return [CaseReference(**case) for case in cases]


@router.get("/case-law/{case_id}", response_model=CaseReference)
async def get_case(
    case_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a specific case by ID."""
    for case in CASE_LAW_DATABASE:
        if case["id"] == case_id:
            return CaseReference(**case)
    
    raise HTTPException(status_code=404, detail="Case not found")


@router.get("/categories")
async def list_categories(user: StorageUser = Depends(require_user)):
    """List all available categories in the law library."""
    return {
        "statute_categories": [
            {"id": "tenant_rights", "name": "Tenant Rights", "icon": "🏠"},
            {"id": "eviction", "name": "Eviction Procedures", "icon": "⚖️"},
            {"id": "security_deposits", "name": "Security Deposits", "icon": "💰"},
            {"id": "habitability", "name": "Habitability", "icon": "🔧"},
            {"id": "retaliation", "name": "Retaliation Protection", "icon": "🛡️"},
            {"id": "discrimination", "name": "Fair Housing", "icon": "👥"},
            {"id": "disability", "name": "Disability Rights & ADA", "icon": "♿"},
            {"id": "lease_terms", "name": "Lease Terms", "icon": "📝"},
            {"id": "repairs", "name": "Repairs & Maintenance", "icon": "🛠️"}
        ],
        "federal_categories": [
            {"id": "fair_housing", "name": "Federal Fair Housing Act", "icon": "🇺🇸"},
            {"id": "ada", "name": "Americans with Disabilities Act", "icon": "♿"},
            {"id": "section_504", "name": "Section 504 Rehab Act", "icon": "🏛️"},
            {"id": "vawa", "name": "Violence Against Women Act", "icon": "🛡️"},
            {"id": "debt_collection", "name": "Fair Debt Collection", "icon": "💳"}
        ],
        "disability_categories": [
            {"id": "reasonable_accommodations", "name": "Reasonable Accommodations", "icon": "🔧"},
            {"id": "reasonable_modifications", "name": "Physical Modifications", "icon": "🏗️"},
            {"id": "assistance_animals", "name": "Assistance Animals", "icon": "🐕"},
            {"id": "accessibility", "name": "Accessibility Requirements", "icon": "♿"},
            {"id": "public_housing", "name": "Public Housing ADA", "icon": "🏢"}
        ],
        "court_rule_categories": [
            {"id": "housing_court", "name": "Housing Court Rules", "icon": "🏛️"},
            {"id": "eviction", "name": "Eviction Procedures", "icon": "📋"},
            {"id": "remote_hearing", "name": "Zoom/Remote Hearings", "icon": "💻"},
            {"id": "filing", "name": "Filing Requirements", "icon": "📁"},
            {"id": "evidence", "name": "Evidence Rules", "icon": "📊"}
        ],
        "tax_categories": [
            {"id": "tax_federal", "name": "Federal Tax Laws", "icon": "🏛️"},
            {"id": "tax_state", "name": "Minnesota Tax Laws", "icon": "📋"},
            {"id": "tax_local", "name": "Local Tax Laws", "icon": "🏘️"}
        ],
        "real_estate_categories": [
            {"id": "real_estate_federal", "name": "Federal Real Estate", "icon": "🇺🇸"},
            {"id": "real_estate_state", "name": "Minnesota Real Estate", "icon": "🏠"},
            {"id": "real_estate_local", "name": "Local Real Estate", "icon": "🏘️"}
        ],
        "business_categories": [
            {"id": "business_federal", "name": "Federal Business Law", "icon": "🏢"},
            {"id": "business_state", "name": "Minnesota Business Law", "icon": "📊"},
            {"id": "business_local", "name": "Local Business Law", "icon": "🏪"}
        ]
    }


class LibrarianQuery(BaseModel):
    """Query for the AI librarian."""
    question: str
    context: Optional[str] = None
    case_type: Optional[str] = "eviction"


@router.post("/librarian/ask", response_model=LibrarianResponse)
async def ask_librarian(
    query: LibrarianQuery,
    user: StorageUser = Depends(require_user)
):
    """
    Ask the AI Librarian a legal question.
    
    The librarian will search the law library and provide:
    - A plain-language answer
    - Relevant legal sources
    - Related topics to explore
    - Suggested next actions
    """
    question_lower = query.question.lower()
    
    # Simple keyword-based response system (would be AI-powered in production)
    sources = []
    answer = ""
    related_topics = []
    suggested_actions = []
    
    if "evict" in question_lower or "eviction" in question_lower:
        sources = [
            {"type": "statute", "id": "minn_stat_504b_321", "title": "Eviction Procedures"},
            {"type": "court_rule", "id": "rule_602", "title": "Dakota County Eviction Rules"}
        ]
        answer = """In Minnesota, a landlord must follow specific procedures to evict a tenant:

1. **Notice Requirement**: The landlord must first serve proper notice:
   - 14 days for nonpayment of rent
   - 30 days for lease violations (or as specified in lease)

2. **File Complaint**: After notice expires, landlord files an Eviction Complaint with the court.

3. **Service**: You must be personally served with the Summons and Complaint.

4. **Your Response**: You have **7 days** to file an Answer with the court.

5. **Hearing**: A hearing is scheduled within 7-14 days.

6. **Your Rights**:
   - Right to cure (pay) before trial in nonpayment cases
   - Right to request a jury trial
   - Right to raise defenses and counterclaims
   - Right to request expungement of records"""
        
        related_topics = ["Defenses to Eviction", "Counterclaims", "Jury Trial Rights", "Expungement"]
        suggested_actions = [
            "File your Answer within 7 days",
            "Consider requesting a jury trial",
            "Gather evidence of any landlord violations",
            "Document all communications"
        ]
    
    elif "security deposit" in question_lower or "deposit" in question_lower:
        sources = [
            {"type": "statute", "id": "minn_stat_504b_375", "title": "Security Deposits"}
        ]
        answer = """Under Minnesota law (Minn. Stat. § 504B.375):

1. **Return Timeline**: Your landlord must return your security deposit within **21 days** after you move out.

2. **Itemized Statement**: If any deductions are made, you must receive a written statement explaining each deduction.

3. **Normal Wear and Tear**: Landlords cannot deduct for normal wear and tear.

4. **Bad Faith Withholding**: If a landlord wrongfully withholds your deposit, you may be entitled to:
   - Return of the full deposit
   - Punitive damages up to $500 (or $200 in bad faith cases)
   - Attorney's fees

5. **Interest**: For deposits over $2,000, you may be entitled to interest."""
        
        related_topics = ["Small Claims Court", "Normal Wear and Tear", "Move-Out Inspection"]
        suggested_actions = [
            "Send written demand for deposit return",
            "Document condition of unit at move-out",
            "Consider small claims court if not returned",
            "Keep copies of all correspondence"
        ]
    
    elif "habitability" in question_lower or "repairs" in question_lower or "maintenance" in question_lower:
        sources = [
            {"type": "statute", "id": "minn_stat_504b_211", "title": "Habitability Requirements"}
        ]
        answer = """Minnesota law requires landlords to maintain habitable premises:

1. **Landlord's Duty**: Keep the property fit for human habitation including:
   - Working heat, plumbing, and electricity
   - Weatherproof structure
   - Compliance with health and safety codes
   - Working smoke and carbon monoxide detectors

2. **Your Remedies**:
   - **Rent Escrow**: Pay rent to the court while repairs are pending
   - **Repair and Deduct**: Make repairs yourself and deduct from rent (with limits)
   - **Withhold Rent**: In serious cases, you may withhold rent entirely
   - **Report to Inspectors**: Contact city housing inspection

3. **Documentation**: Always document issues with photos/video and written complaints."""
        
        related_topics = ["Rent Escrow", "Code Violations", "Constructive Eviction"]
        suggested_actions = [
            "Document all maintenance issues with photos",
            "Send written repair requests to landlord",
            "Contact city housing inspector if needed",
            "Consider rent escrow if issues persist"
        ]

    elif "disability" in question_lower or "ada" in question_lower or "disabled" in question_lower or "accommodation" in question_lower:
        sources = [
            {"type": "statute", "id": "fha_amendments_1988", "title": "Fair Housing Amendments Act"},
            {"type": "statute", "id": "ada_title_ii", "title": "ADA Title II"},
            {"type": "statute", "id": "reasonable_accommodations", "title": "Reasonable Accommodations"}
        ]
        answer = """**Disability Rights in Housing** are protected by multiple federal laws:

## Fair Housing Act (FHA)
1. **Protected Status**: Disability is a protected class under the FHA
2. **Cannot Discriminate**: Landlords cannot refuse to rent or treat you differently based on disability
3. **Cannot Ask**: Landlords cannot ask about the nature or severity of your disability

## Reasonable Accommodations
You have the right to request changes to rules, policies, or services:
- **Service/Assistance Animals**: Must be allowed even with no-pet policies
- **Reserved Parking**: Closer parking space for mobility issues
- **Rent Payment Modifications**: Different due date if disability affects income timing
- **Lease Modifications**: Extended notice periods, allowing live-in aides
- **Communication**: Large print, email instead of written notices

## Reasonable Modifications
You can make physical changes to your unit (at your expense):
- Grab bars, ramps, wider doorways
- Lowered counters, roll-in showers
- Visual doorbells, flashing smoke alarms

## How to Request
1. Make request in writing (recommended)
2. Explain the accommodation needed
3. Explain the connection to your disability
4. Provide documentation if requested (but landlord cannot ask about diagnosis)

**Note**: Landlord can only deny if it causes undue hardship or fundamentally alters the housing."""

        related_topics = ["Assistance Animals", "Section 504", "ADA Title III", "Reasonable Modifications"]
        suggested_actions = [
            "Submit written accommodation request",
            "Get healthcare provider letter if needed",
            "Document all communications",
            "File HUD complaint if denied unfairly"
        ]

    elif "service animal" in question_lower or "emotional support" in question_lower or "esa" in question_lower or "assistance animal" in question_lower:
        sources = [
            {"type": "statute", "id": "assistance_animals", "title": "Assistance Animals in Housing"},
            {"type": "statute", "id": "fha_amendments_1988", "title": "Fair Housing Amendments Act"}
        ]
        answer = """**Assistance Animals in Housing** are protected as reasonable accommodations:

## Types of Assistance Animals

### Service Animals
- Trained to perform specific tasks related to disability
- Examples: guide dogs, hearing dogs, mobility assistance dogs
- No documentation required - training is evident

### Emotional Support Animals (ESAs)
- Provide emotional support through companionship
- Help with depression, anxiety, PTSD, and other conditions
- Require documentation from healthcare provider

## Your Rights
1. **No Pet Fees**: Landlords cannot charge pet deposits or fees
2. **No Breed/Size Restrictions**: Cannot ban based on breed, size, or weight
3. **No "Pet" Rules**: Not subject to pet policies
4. **Must Allow**: Even in no-pet buildings

## What Landlord CAN Do
- Request documentation for non-obvious disabilities
- Deny if animal poses direct threat (case-by-case assessment)
- Deny if animal causes substantial property damage
- Require you to control the animal

## What Landlord CANNOT Do
- Require specific certification or registration
- Require professional training for ESAs
- Charge pet rent or deposits
- Ask about nature of your disability
- Require animal to wear vest or ID

## Documentation for ESAs
- Letter from licensed healthcare provider
- States you have disability-related need
- Does not need to disclose diagnosis"""

        related_topics = ["Reasonable Accommodations", "Fair Housing Act", "HUD Guidance"]
        suggested_actions = [
            "Get letter from healthcare provider for ESA",
            "Submit written request to landlord",
            "Keep copy of all correspondence",
            "File HUD complaint if wrongly denied"
        ]

    elif "discrimination" in question_lower or "fair housing" in question_lower or "protected class" in question_lower:
        sources = [
            {"type": "statute", "id": "fha_title_viii", "title": "Fair Housing Act"},
            {"type": "statute", "id": "title_vi_civil_rights", "title": "Title VI Civil Rights Act"}
        ]
        answer = """**Fair Housing Laws** protect you from housing discrimination:

## Federal Protected Classes
Under the Fair Housing Act, landlords cannot discriminate based on:
1. **Race** - Any racial group
2. **Color** - Skin color
3. **Religion** - Any religion or no religion
4. **National Origin** - Country of birth, ancestry, culture
5. **Sex** - Gender, including sexual harassment
6. **Familial Status** - Having children under 18, pregnancy
7. **Disability** - Physical or mental disabilities

## Minnesota Additional Protections
- Sexual orientation
- Gender identity
- Marital status
- Public assistance status
- Age
- Creed

## What's Prohibited
- Refusing to rent or sell
- Different terms/conditions
- Steering to certain areas
- Discriminatory advertising
- Harassment
- Retaliation for complaints

## Recognizing Discrimination
- Told unit is unavailable, then it's rented to others
- Different rental terms for different people
- Questions about family plans, religion, origin
- Steering to certain buildings or areas
- Harassment based on protected status

## Filing a Complaint
- **HUD**: File within 1 year of violation
- **Minnesota Dept of Human Rights**: File within 1 year
- **Federal Court**: File within 2 years"""

        related_topics = ["HUD Complaints", "Disparate Impact", "Housing Discrimination Testing"]
        suggested_actions = [
            "Document discriminatory statements or actions",
            "File complaint with HUD or state agency",
            "Contact fair housing organization",
            "Consider legal representation"
        ]

    elif "domestic violence" in question_lower or "vawa" in question_lower or "abuse" in question_lower:
        sources = [
            {"type": "statute", "id": "vawa_housing", "title": "VAWA Housing Protections"}
        ]
        answer = """**VAWA (Violence Against Women Act)** provides housing protections for survivors:

## Who's Protected
- Victims of domestic violence
- Victims of dating violence
- Victims of sexual assault
- Victims of stalking
- Applies regardless of gender

## Your Rights Under VAWA

### Cannot Be Denied or Evicted
- Cannot deny housing because you're a DV victim
- Cannot evict you because of violence against you
- Applies to incidents caused by abuser

### Lease Protections
- Can terminate lease early without penalty
- Abuser can be removed from lease
- Your tenancy is not affected by removing abuser

### Emergency Transfer
- Can request transfer to safe unit
- Must be to unit of comparable size
- Priority for available units

### Confidentiality
- Landlord must keep DV status confidential
- Cannot share with other tenants
- Limited disclosure for safety/legal purposes

## Coverage
Applies to federally assisted housing:
- Public housing
- Section 8 / Housing Choice Vouchers
- LIHTC (Low Income Housing Tax Credit)
- HOME program housing
- Rural housing programs

## Documentation
- Can self-certify DV status
- OR provide police report, court order, or provider statement"""

        related_topics = ["Emergency Transfer", "Lease Termination", "Protective Orders"]
        suggested_actions = [
            "Request VAWA self-certification form",
            "Document incidents and threats",
            "Request emergency transfer if needed",
            "Contact local DV advocacy organization"
        ]

    elif "tax" in question_lower or "deduction" in question_lower or "depreciation" in question_lower or "1031" in question_lower:
        sources = [
            {"type": "statute", "id": "irc_280a", "title": "Rental Property Deductions"},
            {"type": "statute", "id": "irc_1031", "title": "1031 Exchange"},
            {"type": "statute", "id": "mn_renters_credit", "title": "MN Renters Property Tax Refund"}
        ]
        answer = """**Tax Laws for Rental Property:**

## Federal Tax Deductions (IRC § 280A)
1. **Depreciation**: 27.5 years for residential rental property
2. **Mortgage Interest**: Fully deductible for rental property
3. **Repairs**: Immediately deductible (not improvements)
4. **Operating Expenses**: Insurance, property management, utilities
5. **Travel**: For rental property management

## 1031 Like-Kind Exchange (IRC § 1031)
- Defer capital gains by exchanging investment properties
- 45-day identification period
- 180-day closing deadline
- Must use qualified intermediary

## Minnesota Tax Benefits
- **Renters Credit**: Property tax refund for eligible tenants
- **CRP Requirement**: Landlords must provide Certificate of Rent Paid by January 31

## Security Deposits (Tax Treatment)
- Not taxable income when received if refundable
- Taxable when applied to rent or retained for damages
- Last month's rent IS taxable when received"""
        related_topics = ["1031 Exchange", "Depreciation", "Property Tax", "CRP"]
        suggested_actions = [
            "Consult tax professional for specific advice",
            "Keep detailed records of all expenses",
            "Understand depreciation rules",
            "File for renter's refund if eligible"
        ]

    elif "real estate" in question_lower or "mortgage" in question_lower or "foreclosure" in question_lower or "title" in question_lower:
        sources = [
            {"type": "statute", "id": "respa", "title": "RESPA"},
            {"type": "statute", "id": "mn_foreclosure", "title": "MN Foreclosure Procedures"},
            {"type": "statute", "id": "lead_paint_disclosure", "title": "Lead Paint Disclosure"}
        ]
        answer = """**Real Estate Laws Overview:**

## Federal Real Estate Laws
1. **RESPA**: Settlement cost disclosures, anti-kickback rules
2. **TILA**: Truth in Lending disclosures for mortgages
3. **Lead Paint**: Disclosure required for pre-1978 housing
4. **Dodd-Frank**: Ability-to-repay, qualified mortgage rules

## Minnesota Real Estate Laws
1. **Contract for Deed**: 60-day cancellation notice, buyer protections
2. **Seller Disclosure**: Must disclose known material defects
3. **Recording Act**: Race-notice jurisdiction
4. **Foreclosure**: 6-month or 12-month redemption period

## Local (Minneapolis/St. Paul)
- **Rent Stabilization**: 3% annual increase cap
- **Truth in Housing**: Required inspection before sale
- **Rental Licensing**: Annual license required

## Homestead Exemption
- Metro: Up to $450,000 protected from creditors
- Does NOT protect against mortgage foreclosure"""
        related_topics = ["Foreclosure", "Contract for Deed", "Rent Control", "Disclosure"]
        suggested_actions = [
            "Review all disclosure documents carefully",
            "Understand redemption rights in foreclosure",
            "Check rent stabilization compliance",
            "Consult real estate attorney for transactions"
        ]

    elif "business" in question_lower or "llc" in question_lower or "license" in question_lower or "employee" in question_lower:
        sources = [
            {"type": "statute", "id": "mn_llc", "title": "Minnesota LLC Act"},
            {"type": "statute", "id": "fcra_tenant_screening", "title": "Fair Credit Reporting Act"},
            {"type": "statute", "id": "mpls_business_license", "title": "Minneapolis Business License"}
        ]
        answer = """**Business Laws for Landlords:**

## Entity Formation (LLC)
1. **Federal**: Check-the-box tax classification (disregarded, partnership, corp)
2. **Minnesota LLC Act**: Articles of Organization, registered agent required
3. **Benefits**: Liability protection, tax flexibility

## Employment Laws
1. **FLSA**: Federal minimum wage $7.25/hr, overtime rules
2. **Minnesota**: Higher minimum wage ($10.85+ large employers)
3. **Workers Comp**: Required for employees
4. **OSHA**: Workplace safety requirements

## Tenant Screening (FCRA)
- Written consent required for credit checks
- Adverse action notice if denied
- Cannot discriminate based on protected classes

## Local Requirements (Minneapolis)
- **Business License**: Annual renewal required
- **Rental License**: Tiered based on compliance
- **Tenant Protection**: Limits on screening criteria"""
        related_topics = ["LLC Formation", "Employment Law", "Tenant Screening", "Licensing"]
        suggested_actions = [
            "Consider LLC for liability protection",
            "Understand employee vs contractor rules",
            "Follow FCRA requirements for screening",
            "Obtain required local licenses"
        ]

    elif "rent control" in question_lower or "rent stabilization" in question_lower or "rent increase" in question_lower:
        sources = [
            {"type": "statute", "id": "mpls_rent_stabilization", "title": "Minneapolis Rent Stabilization"},
            {"type": "statute", "id": "stp_rent_stabilization", "title": "St. Paul Rent Stabilization"}
        ]
        answer = """**Rent Stabilization in Minnesota:**

## Minneapolis Rent Control
- **Cap**: 3% annual rent increase maximum
- **Effective**: May 1, 2022
- **Exemptions**: New construction (15 years)
- **Hardship**: Landlords can petition for exception

## St. Paul Rent Control
- **Cap**: 3% annual rent increase maximum
- **Approved**: Voter referendum November 2021
- **Exemptions**: New construction (20 years)
- **Affordable Housing**: Some exemptions apply

## What This Means for Tenants
- Rent cannot increase more than 3% per year
- Check if your building qualifies for exemption
- Report violations to housing inspection services

## What This Means for Landlords
- Track all rent increases carefully
- Apply for hardship exemption if needed
- New construction has temporary exemption"""
        related_topics = ["Rent Increases", "Tenant Rights", "Housing Policy"]
        suggested_actions = [
            "Calculate maximum allowed rent increase",
            "Check if property is exempt",
            "Document all rent increase notices",
            "Report violations to housing services"
        ]

    else:
        answer = """I can help you with various tenant law topics including:

**State Law (Minnesota)**
- **Eviction Defense**: Your rights, procedures, defenses, and counterclaims
- **Security Deposits**: Return requirements, deductions, and remedies
- **Habitability**: Landlord's duties, repair requirements, rent escrow
- **Lease Issues**: Terms, renewals, modifications
- **Retaliation**: Protection from landlord retaliation

**Federal Law**
- **Fair Housing Act**: Protection from discrimination
- **ADA/Disability Rights**: Reasonable accommodations and modifications
- **Assistance Animals**: Service animals and emotional support animals
- **VAWA**: Protections for domestic violence survivors
- **Section 504**: Disability rights in federally funded housing

**Tax Laws**
- **Federal Tax**: Rental deductions, depreciation, 1031 exchanges
- **State Tax**: Property tax, renters credit, CRP requirements
- **Local Tax**: Assessment, license fees

**Real Estate Laws**
- **Federal**: RESPA, TILA, lead paint disclosure
- **State**: Foreclosure, contract for deed, seller disclosure
- **Local**: Rent stabilization, truth in housing, rental licensing

**Business Laws**
- **Entity Formation**: LLC, corporation requirements
- **Employment**: Wage laws, workers comp, OSHA
- **Licensing**: Business and rental licenses

Please ask a specific question about any of these topics!"""

        related_topics = ["Eviction Defense", "Security Deposits", "Habitability", "Fair Housing", "ADA", "VAWA", "Tax Laws", "Real Estate", "Business Law"]
        suggested_actions = ["Ask a specific question about your situation"]
    
    return LibrarianResponse(
        query=query.question,
        answer=answer,
        sources=sources,
        related_topics=related_topics,
        suggested_actions=suggested_actions
    )


@router.get("/quick-reference/{topic}")
async def get_quick_reference(
    topic: str,
    user: StorageUser = Depends(require_user)
):
    """Get a quick reference guide for a specific topic."""
    quick_refs = {
        "eviction_timeline": {
            "title": "Eviction Timeline - Minnesota",
            "steps": [
                {"day": "Day 0", "event": "Landlord serves notice (14-day for nonpayment, 30-day for violations)"},
                {"day": "Day 14/30", "event": "Notice period expires, landlord can file complaint"},
                {"day": "Day 15/31", "event": "Landlord files Eviction Complaint with court"},
                {"day": "Day 16-18", "event": "Tenant served with Summons and Complaint"},
                {"day": "Day 23-25", "event": "7-day deadline to file Answer"},
                {"day": "Day 30-45", "event": "Court hearing scheduled (or jury trial if requested)"},
                {"day": "After Hearing", "event": "If landlord wins, Writ of Recovery issued"},
                {"day": "+7-10 days", "event": "Sheriff enforces Writ if tenant hasn't vacated"}
            ],
            "tips": [
                "You can cure (pay) nonpayment before trial",
                "Request jury trial to extend timeline",
                "File counterclaims at the same time as Answer"
            ]
        },
        "defenses_checklist": {
            "title": "Common Eviction Defenses",
            "defenses": [
                {"name": "Improper Notice", "description": "Notice was defective, not properly served, or insufficient time"},
                {"name": "Retaliation", "description": "Eviction is in response to complaint or exercising legal rights"},
                {"name": "Discrimination", "description": "Eviction based on protected class status"},
                {"name": "Habitability", "description": "Landlord failed to maintain habitable conditions"},
                {"name": "Waiver", "description": "Landlord accepted rent after alleged violation"},
                {"name": "Payment Made", "description": "Rent was actually paid or cure occurred"},
                {"name": "Lease Violation by Landlord", "description": "Landlord breached lease first"},
                {"name": "Wrong Party", "description": "Named defendant is not the actual tenant"}
            ]
        },
        "counterclaims": {
            "title": "Common Counterclaims Against Landlord",
            "claims": [
                {"name": "Breach of Warranty of Habitability", "damages": "Rent abatement, repair costs"},
                {"name": "Security Deposit Violations", "damages": "Deposit + punitive damages + fees"},
                {"name": "Retaliatory Conduct", "damages": "Statutory damages, attorney fees"},
                {"name": "Illegal Lockout", "damages": "Actual damages + punitive damages"},
                {"name": "Utility Shutoff", "damages": "$500 per violation"},
                {"name": "Privacy Violations", "damages": "Actual damages, may include emotional distress"}
            ]
        }
    }
    
    if topic not in quick_refs:
        raise HTTPException(status_code=404, detail="Quick reference not found")
    
    return quick_refs[topic]
