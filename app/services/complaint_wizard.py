"""
Semptify 5.0 - Complaint Filing Wizard Service
Guides users through filing complaints with regulatory agencies.
Supports evidence attachment and tracks filing status.
Now with DATABASE PERSISTENCE for drafts.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgencyType(str, Enum):
    """Types of complaint agencies."""
    ATTORNEY_GENERAL = "attorney_general"
    HUD = "hud"
    BBB = "bbb"
    REAL_ESTATE_COMMISSION = "real_estate_commission"
    LOCAL_HOUSING = "local_housing"
    LEGAL_AID = "legal_aid"


class ComplaintStatus(str, Enum):
    """Complaint filing status."""
    DRAFT = "draft"
    READY = "ready"
    FILED = "filed"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Agency(BaseModel):
    """Regulatory agency information."""
    id: str
    name: str
    type: AgencyType
    description: str
    jurisdiction: str
    website: str
    filing_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    filing_fee: Optional[float] = None
    typical_response_days: int = 30
    complaint_types: list[str] = []
    required_documents: list[str] = []
    tips: list[str] = []


class ComplaintDraft(BaseModel):
    """User's complaint draft."""
    id: str
    user_id: str
    agency_id: str
    status: ComplaintStatus = ComplaintStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    
    # Complaint details
    subject: str = ""
    description: str = ""
    incident_dates: list[str] = []
    damages_claimed: Optional[float] = None
    relief_sought: str = ""
    
    # Evidence
    attached_document_ids: list[str] = []
    timeline_included: bool = False
    
    # Respondent info
    respondent_name: str = ""
    respondent_company: str = ""
    respondent_address: str = ""
    respondent_phone: str = ""
    
    # Filing info
    filed_date: Optional[datetime] = None
    confirmation_number: Optional[str] = None
    notes: str = ""


# =============================================================================
# Agency Database - Minnesota Focus
# =============================================================================

AGENCIES: dict[str, Agency] = {
    "mn_ag_consumer": Agency(
        id="mn_ag_consumer",
        name="Minnesota Attorney General - Consumer Protection",
        type=AgencyType.ATTORNEY_GENERAL,
        description="Investigates unfair, deceptive, and fraudulent business practices",
        jurisdiction="Minnesota",
        website="https://www.ag.state.mn.us/consumer/",
        filing_url="https://www.ag.state.mn.us/Office/Complaint.asp",
        phone="(651) 296-3353",
        email="consumer.ag@ag.state.mn.us",
        address="Office of Minnesota Attorney General, 445 Minnesota Street, Suite 1400, St. Paul, MN 55101",
        filing_fee=None,
        typical_response_days=30,
        complaint_types=[
            "Unfair business practices",
            "Deceptive practices",
            "Fraud",
            "Landlord violations",
            "Security deposit disputes",
            "Consumer protection violations"
        ],
        required_documents=[
            "Lease agreement",
            "All communications with landlord",
            "Receipts/payment records",
            "Photos of property conditions",
            "Written notices received"
        ],
        tips=[
            "Include a clear timeline of events",
            "Attach all written communications",
            "Be specific about what laws you believe were violated",
            "State clearly what resolution you seek",
            "MN AG has strong tenant protection enforcement"
        ]
    ),

    "hud_fair_housing": Agency(
        id="hud_fair_housing",
        name="HUD - Fair Housing Complaint",
        type=AgencyType.HUD,
        description="Investigates housing discrimination under the Fair Housing Act",
        jurisdiction="Federal",
        website="https://www.hud.gov/program_offices/fair_housing_equal_opp/online-complaint",
        filing_url="https://portalapps.hud.gov/FHEO903/Form903/Form903Start.action",
        phone="1-800-669-9777",
        email="fheo_fhip@hud.gov",
        address="U.S. Department of Housing and Urban Development, 451 Seventh Street S.W., Washington, DC 20410",
        filing_fee=None,
        typical_response_days=100,
        complaint_types=[
            "Discrimination based on race, color, religion",
            "Discrimination based on national origin",
            "Discrimination based on sex/gender",
            "Discrimination based on familial status (families with children)",
            "Discrimination based on disability",
            "Retaliation for exercising fair housing rights",
            "Sexual harassment by landlord/property manager",
            "Refusal to make reasonable accommodations for disability",
            "Discriminatory advertising"
        ],
        required_documents=[
            "Description of discriminatory act",
            "Dates of discrimination",
            "Names of people involved",
            "Witness information",
            "Any written evidence",
            "Copies of rental applications, leases",
            "Screenshots of discriminatory ads"
        ],
        tips=[
            "File within 1 year of the discriminatory act",
            "Be specific about how you were treated differently than others",
            "Include any witnesses who can corroborate your experience",
            "HUD can award damages and require policy changes",
            "Free to file - no cost to you",
            "HUD investigates and can refer to DOJ for prosecution"
        ]
    ),

    "hud_region_5": Agency(
        id="hud_region_5",
        name="HUD Region V - Minneapolis Field Office",
        type=AgencyType.HUD,
        description="Regional HUD office serving Minnesota, Wisconsin, Michigan, Ohio, Indiana, Illinois",
        jurisdiction="Minnesota (Regional)",
        website="https://www.hud.gov/states/minnesota",
        filing_url="https://portalapps.hud.gov/FHEO903/Form903/Form903Start.action",
        phone="(612) 370-3000",
        email="mn_webmanager@hud.gov",
        address="HUD Minneapolis Field Office, 920 Second Avenue South, Suite 1300, Minneapolis, MN 55402",
        filing_fee=None,
        typical_response_days=60,
        complaint_types=[
            "Fair housing discrimination",
            "Section 8 voucher issues",
            "HUD-assisted housing complaints",
            "Public housing authority issues",
            "FHA loan problems",
            "Housing counseling agency issues"
        ],
        required_documents=[
            "Description of complaint",
            "Dates and timeline",
            "Names of people/agencies involved",
            "Housing voucher or assistance documents",
            "Written correspondence"
        ],
        tips=[
            "Regional office may respond faster than national",
            "Handles Section 8 and subsidized housing issues",
            "Can assist with HUD-insured mortgage problems",
            "Good for complaints about local housing authorities",
            "Walk-in hours available at Minneapolis office"
        ]
    ),

    "mn_commerce_real_estate": Agency(
        id="mn_commerce_real_estate",
        name="Minnesota Department of Commerce - Real Estate",
        type=AgencyType.REAL_ESTATE_COMMISSION,
        description="Regulates licensed real estate professionals and property managers",
        jurisdiction="Minnesota",
        website="https://mn.gov/commerce/licensees/real-estate/",
        filing_url="https://mn.gov/commerce/consumers/file-a-complaint/",
        phone="(651) 539-1600",
        email="commerce.real.estate@state.mn.us",
        address="Minnesota Department of Commerce, 85 7th Place East, Suite 280, St. Paul, MN 55101",
        filing_fee=None,
        typical_response_days=60,
        complaint_types=[
            "Unlicensed property management",
            "License law violations",
            "Misrepresentation",
            "Failure to account for funds",
            "Fraud by licensee",
            "Property manager misconduct"
        ],
        required_documents=[
            "Property manager's name and company",
            "Lease or management agreement",
            "Evidence of violation",
            "Communications showing misconduct"
        ],
        tips=[
            "Verify the person is actually licensed first at mn.gov/commerce",
            "Focus on violations of licensing laws",
            "Commission can revoke or suspend licenses",
            "This is separate from civil remedies - you can do both"
        ]
    ),

    "bbb_mn": Agency(
        id="bbb_mn",
        name="Better Business Bureau - Minnesota",
        type=AgencyType.BBB,
        description="Mediates disputes and maintains business reputation records",
        jurisdiction="Minnesota",
        website="https://www.bbb.org/us/mn",
        filing_url="https://www.bbb.org/file-a-complaint",
        phone="(651) 699-1111",
        filing_fee=None,
        typical_response_days=30,
        complaint_types=[
            "Business disputes",
            "Service complaints",
            "Billing issues",
            "Contract disputes",
            "Property management complaints"
        ],
        required_documents=[
            "Business name and address",
            "Description of transaction",
            "Copies of contracts/agreements",
            "Communication records"
        ],
        tips=[
            "BBB complaints become public record",
            "Businesses often respond to protect their rating",
            "Good for getting attention from management",
            "Not a regulatory body but applies social pressure"
        ]
    ),

    "legal_aid_mn": Agency(
        id="legal_aid_mn",
        name="Legal Aid - Minnesota",
        type=AgencyType.LEGAL_AID,
        description="Free legal help for low-income residents",
        jurisdiction="Minnesota",
        website="https://www.lawhelpmn.org/",
        phone="1-888-287-2266",
        address="Multiple locations across Minnesota",
        filing_fee=None,
        typical_response_days=14,
        complaint_types=[
            "Eviction defense",
            "Landlord-tenant disputes",
            "Housing conditions",
            "Security deposit recovery",
            "Fair housing",
            "Unlawful detainer defense"
        ],
        required_documents=[
            "Income verification",
            "All case documents",
            "Court papers if any",
            "Lease agreement"
        ],
        tips=[
            "Income limits apply for free services",
            "They can represent you in court",
            "Call early - before court dates",
            "They prioritize urgent housing matters",
            "Mid-Minnesota Legal Aid serves the metro area"
        ]
    ),

    "mn_housing_court": Agency(
        id="mn_housing_court",
        name="Minnesota Housing Court",
        type=AgencyType.LOCAL_HOUSING,
        description="Handles eviction cases and housing disputes",
        jurisdiction="Minnesota",
        website="https://www.mncourts.gov/Find-Courts.aspx",
        phone="(612) 348-2040",
        filing_fee=None,
        typical_response_days=7,
        complaint_types=[
            "Eviction proceedings",
            "Lease violations",
            "Rent disputes",
            "Security deposit claims"
        ],
        required_documents=[
            "Court summons",
            "Lease agreement",
            "Payment records",
            "Written notices"
        ],
        tips=[
            "Appear at all hearings - missing one can result in default judgment",
            "Bring all documentation",
            "Request a continuance if you need more time",
            "Ask about the Eviction Expungement program"
        ]
    ),

    "homeline_mn": Agency(
        id="homeline_mn",
        name="HOME Line - Minnesota Tenant Hotline",
        type=AgencyType.LEGAL_AID,
        description="Free tenant advice hotline and advocacy",
        jurisdiction="Minnesota",
        website="https://homelinemn.org/",
        phone="(612) 728-5767",
        email="info@homelinemn.org",
        address="3455 Bloomington Ave, Minneapolis, MN 55407",
        filing_fee=None,
        typical_response_days=1,
        complaint_types=[
            "Tenant rights questions",
            "Eviction prevention",
            "Security deposit disputes",
            "Repair issues",
            "Landlord harassment",
            "Lease questions"
        ],
        required_documents=[
            "Lease agreement",
            "Relevant correspondence",
            "Court papers if applicable"
        ],
        tips=[
            "Call the hotline for immediate advice",
            "They can help you understand your rights",
            "Great first step before filing formal complaints",
            "They offer tenant education workshops"
        ]
    ),

    "dakota_county_housing": Agency(
        id="dakota_county_housing",
        name="Dakota County Housing Authority",
        type=AgencyType.LOCAL_HOUSING,
        description="Local housing assistance and Section 8 programs",
        jurisdiction="Dakota County, Minnesota",
        website="https://www.dakotacda.org/",
        phone="(651) 675-4400",
        address="1228 Town Centre Drive, Eagan, MN 55123",
        filing_fee=None,
        typical_response_days=14,
        complaint_types=[
            "Section 8 issues",
            "Housing assistance",
            "Landlord violations in subsidized housing",
            "Fair housing in Dakota County"
        ],
        required_documents=[
            "Housing voucher documents",
            "Lease agreement",
            "Violation evidence"
        ],
        tips=[
            "Contact them if you have Section 8 voucher issues",
            "They can intervene with landlords in their program",
            "Report violations of housing quality standards"
        ]
    )
}


class ComplaintWizardService:
    """Service for guiding complaint filings with DATABASE PERSISTENCE."""

    def __init__(self):
        self.agencies = AGENCIES
        # In-memory cache for fast access (also persisted to DB)
        self._cache: dict[str, ComplaintDraft] = {}

    def get_all_agencies(self, state_code: str = "MN") -> list[Agency]:
        """Get all available agencies for a state."""
        # Filter by jurisdiction
        state_agencies = []
        for agency in self.agencies.values():
            jurisdiction = agency.jurisdiction.lower()
            if (state_code.lower() in jurisdiction or
                "minnesota" in jurisdiction or
                jurisdiction == "federal"):
                state_agencies.append(agency)
        return state_agencies if state_agencies else list(self.agencies.values())

    def get_agencies_for_user(self, user_id: str) -> list[Agency]:
        """Get agencies based on user's location from location service."""
        try:
            from app.services.location_service import location_service
            location = location_service.get_user_location(user_id)
            return self.get_all_agencies(location.state_code)
        except (ImportError, AttributeError, KeyError):
            # Default to all MN agencies
            return self.get_all_agencies("MN")

    def get_agency(self, agency_id: str) -> Optional[Agency]:
        """Get agency by ID."""
        return self.agencies.get(agency_id)

    def get_agencies_by_type(self, agency_type: AgencyType) -> list[Agency]:
        """Get agencies of a specific type."""
        return [a for a in self.agencies.values() if a.type == agency_type]

    def get_recommended_agencies(self, complaint_keywords: list[str]) -> list[Agency]:
        """Recommend agencies based on complaint keywords."""
        recommendations = []
        keywords_lower = [k.lower() for k in complaint_keywords]

        for agency in self.agencies.values():
            score = 0
            for ctype in agency.complaint_types:
                for keyword in keywords_lower:
                    if keyword in ctype.lower():
                        score += 1
            if score > 0:
                recommendations.append((score, agency))

        # Sort by score descending
        recommendations.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in recommendations]

    # =========================================================================
    # DATABASE METHODS (Async)
    # =========================================================================

    async def create_draft_db(
        self,
        db: AsyncSession,
        user_id: str,
        agency_id: str,
        subject: str = "",
        complaint_type: str = "general"
    ) -> ComplaintDraft:
        """Create a new complaint draft and persist to database."""
        from app.models.models import Complaint as ComplaintModel

        draft_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Create database record
        db_complaint = ComplaintModel(
            id=draft_id,
            user_id=user_id,
            agency_id=agency_id,
            complaint_type=complaint_type,
            status=ComplaintStatus.DRAFT.value,
            subject=subject,
            summary="",
            detailed_description="",
            target_type="landlord",
            created_at=now,
            updated_at=now
        )
        db.add(db_complaint)
        await db.commit()
        await db.refresh(db_complaint)

        # Create pydantic model for response
        draft = ComplaintDraft(
            id=draft_id,
            user_id=user_id,
            agency_id=agency_id,
            subject=subject,
            created_at=now,
            updated_at=now
        )
        self._cache[draft_id] = draft
        logger.info("📝 Created complaint draft %s... for user %s...", draft_id[:8], user_id[:8])
        return draft

    async def get_draft_db(self, db: AsyncSession, draft_id: str) -> Optional[ComplaintDraft]:
        """Get a draft from database by ID."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel).where(ComplaintModel.id == draft_id)
        )
        db_complaint = result.scalar_one_or_none()
        if not db_complaint:
            return None

        return self._db_to_draft(db_complaint)

    async def get_user_drafts_db(self, db: AsyncSession, user_id: str) -> list[ComplaintDraft]:
        """Get all drafts for a user from database."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel)
            .where(ComplaintModel.user_id == user_id)
            .order_by(ComplaintModel.updated_at.desc())
        )
        db_complaints = result.scalars().all()
        return [self._db_to_draft(c) for c in db_complaints]

    async def update_draft_db(
        self,
        db: AsyncSession,
        draft_id: str,
        **updates
    ) -> Optional[ComplaintDraft]:
        """Update a draft in database."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel).where(ComplaintModel.id == draft_id)
        )
        db_complaint = result.scalar_one_or_none()
        if not db_complaint:
            return None

        # Map pydantic field names to DB column names
        field_mapping = {
            "description": "detailed_description",
            "respondent_name": "target_name",
            "respondent_company": "target_company",
            "respondent_address": "target_address",
            "respondent_phone": "target_phone",
        }

        for key, value in updates.items():
            db_key = field_mapping.get(key, key)

            # Handle JSON array fields
            if key == "incident_dates" and isinstance(value, list):
                value = json.dumps(value)
            elif key == "attached_document_ids" and isinstance(value, list):
                value = json.dumps(value)

            if hasattr(db_complaint, db_key):
                setattr(db_complaint, db_key, value)

        db_complaint.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_complaint)

        return self._db_to_draft(db_complaint)

    async def attach_documents_db(
        self,
        db: AsyncSession,
        draft_id: str,
        document_ids: list[str]
    ) -> Optional[ComplaintDraft]:
        """Attach documents to a draft in database."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel).where(ComplaintModel.id == draft_id)
        )
        db_complaint = result.scalar_one_or_none()
        if not db_complaint:
            return None

        # Get existing document IDs
        existing = []
        if db_complaint.attached_document_ids:
            try:
                existing = json.loads(db_complaint.attached_document_ids)
            except json.JSONDecodeError:
                existing = []

        # Add new document IDs
        existing.extend(document_ids)
        db_complaint.attached_document_ids = json.dumps(existing)
        db_complaint.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_complaint)

        logger.info("📎 Attached %s documents to complaint %s...", len(document_ids), draft_id[:8])
        return self._db_to_draft(db_complaint)

    async def mark_as_filed_db(
        self,
        db: AsyncSession,
        draft_id: str,
        confirmation_number: Optional[str] = None
    ) -> Optional[ComplaintDraft]:
        """Mark a complaint as filed in database."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel).where(ComplaintModel.id == draft_id)
        )
        db_complaint = result.scalar_one_or_none()
        if not db_complaint:
            return None

        agency = self.get_agency(db_complaint.agency_id)

        db_complaint.status = ComplaintStatus.FILED.value
        db_complaint.filing_date = datetime.utcnow()
        db_complaint.confirmation_number = confirmation_number
        db_complaint.filed_with = agency.name if agency else db_complaint.agency_id
        db_complaint.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_complaint)

        logger.info("✅ Complaint %s... marked as FILED with %s", draft_id[:8], agency.name if agency else 'agency')
        return self._db_to_draft(db_complaint)

    async def delete_draft_db(self, db: AsyncSession, draft_id: str) -> bool:
        """Delete a draft from database."""
        from app.models.models import Complaint as ComplaintModel

        result = await db.execute(
            select(ComplaintModel).where(ComplaintModel.id == draft_id)
        )
        db_complaint = result.scalar_one_or_none()
        if not db_complaint:
            return False

        await db.delete(db_complaint)
        await db.commit()
        logger.info("🗑️ Deleted complaint draft %s...", draft_id[:8])
        return True

    def _db_to_draft(self, db_complaint) -> ComplaintDraft:
        """Convert database model to Pydantic ComplaintDraft."""
        # Parse JSON array fields
        incident_dates = []
        if db_complaint.incident_dates:
            try:
                incident_dates = json.loads(db_complaint.incident_dates)
            except json.JSONDecodeError:
                incident_dates = []

        attached_docs = []
        if db_complaint.attached_document_ids:
            try:
                attached_docs = json.loads(db_complaint.attached_document_ids)
            except json.JSONDecodeError:
                attached_docs = []

        return ComplaintDraft(
            id=db_complaint.id,
            user_id=db_complaint.user_id,
            agency_id=db_complaint.agency_id,
            status=ComplaintStatus(db_complaint.status),
            created_at=db_complaint.created_at,
            updated_at=db_complaint.updated_at,
            subject=db_complaint.subject or "",
            description=db_complaint.detailed_description or "",
            incident_dates=incident_dates,
            damages_claimed=db_complaint.damages_claimed,
            relief_sought=db_complaint.relief_sought or "",
            attached_document_ids=attached_docs,
            timeline_included=db_complaint.timeline_included or False,
            respondent_name=db_complaint.target_name or "",
            respondent_company=db_complaint.target_company or "",
            respondent_address=db_complaint.target_address or "",
            respondent_phone=db_complaint.target_phone or "",
            filed_date=db_complaint.filing_date,
            confirmation_number=db_complaint.confirmation_number or "",
            notes=db_complaint.notes or ""
        )

    # =========================================================================
    # LEGACY SYNC METHODS (In-Memory - for backward compatibility)
    # =========================================================================

    def create_draft(
        self,
        user_id: str,
        agency_id: str,
        subject: str = ""
    ) -> ComplaintDraft:
        """Create a new complaint draft (in-memory, use create_draft_db for persistence)."""
        draft_id = str(uuid.uuid4())
        now = datetime.utcnow()

        draft = ComplaintDraft(
            id=draft_id,
            user_id=user_id,
            agency_id=agency_id,
            subject=subject,
            created_at=now,
            updated_at=now
        )
        self._cache[draft_id] = draft
        return draft

    def get_draft(self, draft_id: str) -> Optional[ComplaintDraft]:
        """Get a draft by ID (from cache)."""
        return self._cache.get(draft_id)

    def get_user_drafts(self, user_id: str) -> list[ComplaintDraft]:
        """Get all drafts for a user (from cache)."""
        return [d for d in self._cache.values() if d.user_id == user_id]

    def update_draft(
        self,
        draft_id: str,
        **updates
    ) -> Optional[ComplaintDraft]:
        """Update a draft (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None

        for key, value in updates.items():
            if hasattr(draft, key):
                setattr(draft, key, value)

        draft.updated_at = datetime.utcnow()
        return draft

    def attach_documents(
        self,
        draft_id: str,
        document_ids: list[str]
    ) -> Optional[ComplaintDraft]:
        """Attach documents to a draft (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None

        draft.attached_document_ids.extend(document_ids)
        draft.updated_at = datetime.utcnow()
        return draft

    def generate_complaint_text(self, draft: ComplaintDraft) -> str:
        """Generate formatted complaint text from draft."""
        agency = self.get_agency(draft.agency_id)
        agency_name = agency.name if agency else "Agency"
        
        lines = [
            f"FORMAL COMPLAINT TO {agency_name.upper()}",
            f"Date: {datetime.utcnow().strftime('%B %d, %Y')}",
            "",
            "=" * 60,
            "COMPLAINANT INFORMATION",
            "=" * 60,
            "[Your name and contact information]",
            "",
            "=" * 60,
            "RESPONDENT INFORMATION",
            "=" * 60,
            f"Name: {draft.respondent_name}",
            f"Company: {draft.respondent_company}",
            f"Address: {draft.respondent_address}",
            f"Phone: {draft.respondent_phone}",
            "",
            "=" * 60,
            "SUBJECT OF COMPLAINT",
            "=" * 60,
            draft.subject,
            "",
            "=" * 60,
            "STATEMENT OF FACTS",
            "=" * 60,
            draft.description,
            "",
            "=" * 60,
            "RELEVANT DATES",
            "=" * 60,
        ]
        
        for date in draft.incident_dates:
            lines.append(f"• {date}")
        
        lines.extend([
            "",
            "=" * 60,
            "DAMAGES / HARM SUFFERED",
            "=" * 60,
        ])
        
        if draft.damages_claimed:
            lines.append(f"Financial damages claimed: ${draft.damages_claimed:,.2f}")
        
        lines.extend([
            "",
            "=" * 60,
            "RELIEF SOUGHT",
            "=" * 60,
            draft.relief_sought,
            "",
            "=" * 60,
            "ATTACHED EVIDENCE",
            "=" * 60,
            f"• {len(draft.attached_document_ids)} documents attached",
            f"• Timeline included: {'Yes' if draft.timeline_included else 'No'}",
            "",
            "I declare under penalty of perjury that the foregoing is true and correct.",
            "",
            "____________________________",
            "Signature",
            "",
            "____________________________",
            "Date"
        ])
        
        return "\n".join(lines)
    
    def mark_as_filed(
        self,
        draft_id: str,
        confirmation_number: Optional[str] = None
    ) -> Optional[ComplaintDraft]:
        """Mark a complaint as filed (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None
        
        draft.status = ComplaintStatus.FILED
        draft.filed_date = datetime.utcnow()
        draft.confirmation_number = confirmation_number
        draft.updated_at = datetime.utcnow()
        return draft
    
    def get_filing_checklist(self, agency_id: str) -> dict:
        """Get filing checklist for an agency."""
        agency = self.get_agency(agency_id)
        if not agency:
            return {"error": "Agency not found"}
        
        return {
            "agency": agency.name,
            "required_documents": agency.required_documents,
            "tips": agency.tips,
            "filing_url": agency.filing_url,
            "phone": agency.phone,
            "typical_response_days": agency.typical_response_days,
            "checklist": [
                "☐ Gather all required documents",
                "☐ Write clear description of events",
                "☐ Include specific dates and times",
                "☐ Name all parties involved",
                "☐ State what resolution you seek",
                "☐ Make copies of everything",
                "☐ Keep confirmation/tracking number",
                "☐ Note the date you filed",
                "☐ Set calendar reminder for follow-up"
            ]
        }


# Global service instance
complaint_wizard = ComplaintWizardService()
