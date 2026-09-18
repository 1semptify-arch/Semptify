"""
Semptify 5.0 - Complaint Filing Wizard Service
Guides users through filing complaints with regulatory agencies.
Supports evidence attachment and tracks filing status.
Drafts persist as COMPLAINT overlays in the tenant's cloud vault
(vault-persistence Phase 1 — legacy `complaints` rows migrate on first read).
"""

import json
import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_RECORDS_FILE
from app.models.unified_overlay_models import CreateOverlayRequest

logger = logging.getLogger(__name__)


class AgencyType(StrEnum):
    """Types of complaint agencies."""

    ATTORNEY_GENERAL = "attorney_general"
    HUD = "hud"
    BBB = "bbb"
    REAL_ESTATE_COMMISSION = "real_estate_commission"
    LOCAL_HOUSING = "local_housing"
    LEGAL_AID = "legal_aid"


class ComplaintStatus(StrEnum):
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
    filing_url: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    filing_fee: float | None = None
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
    damages_claimed: float | None = None
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
    filed_date: datetime | None = None
    confirmation_number: str | None = None
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
            "Consumer protection violations",
        ],
        required_documents=[
            "Lease agreement",
            "All communications with landlord",
            "Receipts/payment records",
            "Photos of property conditions",
            "Written notices received",
        ],
        tips=[
            "Include a clear timeline of events",
            "Attach all written communications",
            "Be specific about what laws you believe were violated",
            "State clearly what resolution you seek",
            "MN AG has strong tenant protection enforcement",
        ],
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
            "Discriminatory advertising",
        ],
        required_documents=[
            "Description of discriminatory act",
            "Dates of discrimination",
            "Names of people involved",
            "Witness information",
            "Any written evidence",
            "Copies of rental applications, leases",
            "Screenshots of discriminatory ads",
        ],
        tips=[
            "File within 1 year of the discriminatory act",
            "Be specific about how you were treated differently than others",
            "Include any witnesses who can corroborate your experience",
            "HUD can award damages and require policy changes",
            "Free to file - no cost to you",
            "HUD investigates and can refer to DOJ for prosecution",
        ],
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
            "Housing counseling agency issues",
        ],
        required_documents=[
            "Description of complaint",
            "Dates and timeline",
            "Names of people/agencies involved",
            "Housing voucher or assistance documents",
            "Written correspondence",
        ],
        tips=[
            "Regional office may respond faster than national",
            "Handles Section 8 and subsidized housing issues",
            "Can assist with HUD-insured mortgage problems",
            "Good for complaints about local housing authorities",
            "Walk-in hours available at Minneapolis office",
        ],
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
            "Property manager misconduct",
        ],
        required_documents=[
            "Property manager's name and company",
            "Lease or management agreement",
            "Evidence of violation",
            "Communications showing misconduct",
        ],
        tips=[
            "Verify the person is actually licensed first at mn.gov/commerce",
            "Focus on violations of licensing laws",
            "Commission can revoke or suspend licenses",
            "This is separate from civil remedies - you can do both",
        ],
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
            "Property management complaints",
        ],
        required_documents=[
            "Business name and address",
            "Description of transaction",
            "Copies of contracts/agreements",
            "Communication records",
        ],
        tips=[
            "BBB complaints become public record",
            "Businesses often respond to protect their rating",
            "Good for getting attention from management",
            "Not a regulatory body but applies social pressure",
        ],
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
            "Unlawful detainer defense",
        ],
        required_documents=["Income verification", "All case documents", "Court papers if any", "Lease agreement"],
        tips=[
            "Income limits apply for free services",
            "They can represent you in court",
            "Call early - before court dates",
            "They prioritize urgent housing matters",
            "Mid-Minnesota Legal Aid serves the metro area",
        ],
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
        complaint_types=["Eviction proceedings", "Lease violations", "Rent disputes", "Security deposit claims"],
        required_documents=["Court summons", "Lease agreement", "Payment records", "Written notices"],
        tips=[
            "Appear at all hearings - missing one can result in default judgment",
            "Bring all documentation",
            "Request a continuance if you need more time",
            "Ask about the Eviction Expungement program",
        ],
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
            "Lease questions",
        ],
        required_documents=["Lease agreement", "Relevant correspondence", "Court papers if applicable"],
        tips=[
            "Call the hotline for immediate advice",
            "They can help you understand your rights",
            "Great first step before filing formal complaints",
            "They offer tenant education workshops",
        ],
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
            "Fair housing in Dakota County",
        ],
        required_documents=["Housing voucher documents", "Lease agreement", "Violation evidence"],
        tips=[
            "Contact them if you have Section 8 voucher issues",
            "They can intervene with landlords in their program",
            "Report violations of housing quality standards",
        ],
    ),
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
            if state_code.lower() in jurisdiction or "minnesota" in jurisdiction or jurisdiction == "federal":
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

    def get_agency(self, agency_id: str) -> Agency | None:
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
    # VAULT METHODS (Async — COMPLAINT overlays in the tenant's cloud vault)
    # =========================================================================

    @staticmethod
    def _draft_field_to_payload(key: str) -> str:
        """Map ComplaintDraft field names to the payload's model-column names."""
        return {
            "description": "detailed_description",
            "respondent_name": "target_name",
            "respondent_company": "target_company",
            "respondent_address": "target_address",
            "respondent_phone": "target_phone",
            "filed_date": "filing_date",
        }.get(key, key)

    @staticmethod
    def _records_anchor(user) -> str:
        """Per-user document_id anchor for complaint overlays."""
        return f"complaints:{user.get_effective_user_id()}"

    async def _get_manager(self, user):
        """Per-user overlay manager; effective id so impersonation writes
        records that belong to the tenant."""
        from app.services.storage import get_provider
        from app.services.unified_overlay_manager import get_unified_overlay_manager

        storage = get_provider(user.provider.value, access_token=user.access_token)
        return await get_unified_overlay_manager(storage, user.get_effective_user_id())

    async def _list_overlays(self, user) -> list:
        manager = await self._get_manager(user)
        response = await manager.get_overlays(
            document_id=self._records_anchor(user),
            overlay_type=OverlayType.COMPLAINT,
        )
        if not response.success:
            logger.warning("Complaint overlay list failed for user %s: %s", user.user_id[:8], response.message)
            return []
        return [o for o in response.overlays if self._owns(o, user)]

    @staticmethod
    def _owns(overlay, user) -> bool:
        return overlay.created_by == user.get_effective_user_id()

    async def _resolve_overlay(self, user, draft_id: str):
        """Resolve a draft by overlay_id or its stored payload id (cmp_* / legacy)."""
        overlays = await self._list_overlays(user)
        for o in overlays:
            if o.overlay_id == draft_id or o.payload.get("id") == draft_id:
                return o
        return None

    async def create_draft_vault(
        self, user, agency_id: str, subject: str = "", complaint_type: str = "general"
    ) -> ComplaintDraft:
        """Create a new complaint draft persisted to the user's cloud vault."""
        draft_id = make_id("cmp")
        now = utc_now()

        manager = await self._get_manager(user)
        response = await manager.create_overlay(
            CreateOverlayRequest(
                overlay_type=OverlayType.COMPLAINT,
                document_id=self._records_anchor(user),
                vault_path=VAULT_RECORDS_FILE,
                payload={
                    "id": draft_id,
                    "agency_id": agency_id,
                    "complaint_type": complaint_type,
                    "status": ComplaintStatus.DRAFT.value,
                    "subject": subject,
                    "summary": "",
                    "detailed_description": "",
                    "target_type": "landlord",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                metadata={"complaint_type": complaint_type, "scope": "complaints"},
            )
        )
        if not response.success:
            raise RuntimeError(f"Failed to persist complaint draft: {response.message}")

        draft = ComplaintDraft(
            id=draft_id, user_id=user.user_id, agency_id=agency_id, subject=subject, created_at=now, updated_at=now
        )
        self._cache[draft_id] = draft
        logger.info("📝 Created complaint draft %s... for user %s...", draft_id[:8], user.user_id[:8])
        return draft

    async def get_draft_vault(self, user, draft_id: str) -> ComplaintDraft | None:
        """Get a draft from the user's vault by overlay or draft ID."""
        overlay = await self._resolve_overlay(user, draft_id)
        if not overlay:
            return None
        return self._overlay_to_draft(overlay, user.user_id)

    async def get_user_drafts_vault(self, user) -> list[ComplaintDraft]:
        """Get all drafts for a user from their vault (legacy rows migrate first)."""
        await self.migrate_legacy_complaints(user)
        overlays = await self._list_overlays(user)
        overlays.sort(key=lambda o: o.payload.get("updated_at") or "", reverse=True)
        return [self._overlay_to_draft(o, user.user_id) for o in overlays]

    async def update_draft_vault(self, user, draft_id: str, **updates) -> ComplaintDraft | None:
        """Update a draft in the user's vault."""
        overlay = await self._resolve_overlay(user, draft_id)
        if not overlay:
            return None

        allowed = {
            "id", "agency_id", "complaint_type", "status", "subject", "summary",
            "detailed_description", "incident_dates", "damages_claimed",
            "relief_sought", "target_type", "target_name", "target_company",
            "target_address", "target_phone", "attached_document_ids",
            "timeline_included", "filed_with", "filing_date", "case_number",
            "confirmation_number", "notes",
        }

        for key, value in updates.items():
            payload_key = self._draft_field_to_payload(key)
            if payload_key in allowed:
                if isinstance(value, datetime):
                    value = value.isoformat()
                overlay.payload[payload_key] = value

        overlay.payload["updated_at"] = utc_now().isoformat()
        manager = await self._get_manager(user)
        await manager.update_overlay(overlay.overlay_id, overlay.payload)
        return self._overlay_to_draft(overlay, user.user_id)

    async def attach_documents_vault(self, user, draft_id: str, document_ids: list[str]) -> ComplaintDraft | None:
        """Attach documents to a draft in the user's vault."""
        overlay = await self._resolve_overlay(user, draft_id)
        if not overlay:
            return None

        existing = overlay.payload.get("attached_document_ids") or []
        existing.extend(document_ids)
        overlay.payload["attached_document_ids"] = existing
        overlay.payload["updated_at"] = utc_now().isoformat()

        manager = await self._get_manager(user)
        await manager.update_overlay(overlay.overlay_id, overlay.payload)

        logger.info("📎 Attached %s documents to complaint %s...", len(document_ids), draft_id[:8])
        return self._overlay_to_draft(overlay, user.user_id)

    async def mark_as_filed_vault(
        self, user, draft_id: str, confirmation_number: str | None = None
    ) -> ComplaintDraft | None:
        """Mark a complaint as filed in the user's vault."""
        overlay = await self._resolve_overlay(user, draft_id)
        if not overlay:
            return None

        agency = self.get_agency(overlay.payload.get("agency_id"))

        overlay.payload["status"] = ComplaintStatus.FILED.value
        overlay.payload["filing_date"] = utc_now().isoformat()
        overlay.payload["confirmation_number"] = confirmation_number
        overlay.payload["filed_with"] = agency.name if agency else overlay.payload.get("agency_id")
        overlay.payload["updated_at"] = utc_now().isoformat()

        manager = await self._get_manager(user)
        await manager.update_overlay(overlay.overlay_id, overlay.payload)

        logger.info("✅ Complaint %s... marked as FILED with %s", draft_id[:8], agency.name if agency else "agency")
        return self._overlay_to_draft(overlay, user.user_id)

    async def delete_draft_vault(self, user, draft_id: str) -> bool:
        """Delete a draft from the user's vault."""
        overlay = await self._resolve_overlay(user, draft_id)
        if not overlay:
            return False

        manager = await self._get_manager(user)
        await manager.delete_overlay(overlay.overlay_id)
        logger.info("🗑️ Deleted complaint draft %s...", draft_id[:8])
        return True

    async def migrate_legacy_complaints(self, user, limit: int = 25) -> int:
        """One-shot bounded import of legacy `complaints` rows into vault overlays.

        Non-destructive (rows stay until the table-drop phase) and idempotent
        via payload["legacy_id"]. Returns the number imported this call.
        """
        try:
            from sqlalchemy import select

            from app.core.database import get_db_session
            from app.models.models import Complaint as ComplaintModel
        except Exception:
            return 0

        overlays = await self._list_overlays(user)
        migrated = {o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id")}
        imported = 0

        try:
            async with get_db_session() as db:
                result = await db.execute(
                    select(ComplaintModel)
                    .where(ComplaintModel.user_id == user.user_id)
                    .order_by(ComplaintModel.created_at)
                    .limit(limit + len(migrated))
                )
                rows = result.scalars().all()
        except Exception:
            return 0

        manager = await self._get_manager(user)
        for row in rows:
            if imported >= limit:
                break
            if row.id in migrated:
                continue

            incident_dates = []
            if row.incident_dates:
                try:
                    incident_dates = json.loads(row.incident_dates)
                except (json.JSONDecodeError, TypeError):
                    incident_dates = []

            attached_docs = []
            if row.attached_document_ids:
                try:
                    attached_docs = json.loads(row.attached_document_ids)
                except (json.JSONDecodeError, TypeError):
                    attached_docs = []

            await manager.create_overlay(
                CreateOverlayRequest(
                    overlay_type=OverlayType.COMPLAINT,
                    document_id=self._records_anchor(user),
                    vault_path=VAULT_RECORDS_FILE,
                    payload={
                        "id": row.id,
                    "agency_id": row.agency_id,
                    "complaint_type": row.complaint_type,
                    "status": row.status,
                    "subject": row.subject or "",
                    "summary": row.summary or "",
                    "detailed_description": row.detailed_description or "",
                    "incident_dates": incident_dates,
                    "damages_claimed": row.damages_claimed,
                    "relief_sought": row.relief_sought or "",
                    "target_type": row.target_type or "landlord",
                    "target_name": row.target_name,
                    "target_company": row.target_company,
                    "target_address": row.target_address,
                    "target_phone": row.target_phone,
                    "attached_document_ids": attached_docs,
                    "timeline_included": bool(row.timeline_included),
                    "filed_with": row.filed_with,
                    "filing_date": row.filing_date.isoformat() if row.filing_date else None,
                    "case_number": row.case_number,
                    "confirmation_number": row.confirmation_number,
                    "notes": row.notes,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                        "legacy_id": row.id,
                        "migrated_from": "complaints",
                    },
                    metadata={"complaint_type": row.complaint_type, "scope": "complaints"},
                )
            )
            migrated.add(row.id)
            imported += 1

        return imported

    def _overlay_to_draft(self, overlay, user_id: str) -> ComplaintDraft:
        """Convert a COMPLAINT overlay to a Pydantic ComplaintDraft."""
        p = overlay.payload

        def _parse_dt(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(str(value))
            except ValueError:
                return None

        incident_dates = p.get("incident_dates") or []
        if isinstance(incident_dates, str):
            try:
                incident_dates = json.loads(incident_dates)
            except (json.JSONDecodeError, TypeError):
                incident_dates = []

        attached_docs = p.get("attached_document_ids") or []
        if isinstance(attached_docs, str):
            try:
                attached_docs = json.loads(attached_docs)
            except (json.JSONDecodeError, TypeError):
                attached_docs = []

        try:
            status = ComplaintStatus(p.get("status") or ComplaintStatus.DRAFT.value)
        except ValueError:
            status = ComplaintStatus.DRAFT

        return ComplaintDraft(
            id=p.get("id") or overlay.overlay_id,
            user_id=user_id,
            agency_id=p.get("agency_id") or "",
            status=status,
            created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
            updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
            subject=p.get("subject") or "",
            description=p.get("detailed_description") or "",
            incident_dates=incident_dates,
            damages_claimed=p.get("damages_claimed"),
            relief_sought=p.get("relief_sought") or "",
            attached_document_ids=attached_docs,
            timeline_included=bool(p.get("timeline_included")),
            respondent_name=p.get("target_name") or "",
            respondent_company=p.get("target_company") or "",
            respondent_address=p.get("target_address") or "",
            respondent_phone=p.get("target_phone") or "",
            filed_date=_parse_dt(p.get("filing_date")),
            confirmation_number=p.get("confirmation_number") or "",
            notes=p.get("notes") or "",
        )

    # =========================================================================
    # LEGACY SYNC METHODS (In-Memory - for backward compatibility)
    # =========================================================================

    def create_draft(self, user_id: str, agency_id: str, subject: str = "") -> ComplaintDraft:
        """Create a new complaint draft (in-memory, use create_draft_vault for persistence)."""
        draft_id = make_id("cmp")
        now = utc_now()

        draft = ComplaintDraft(
            id=draft_id, user_id=user_id, agency_id=agency_id, subject=subject, created_at=now, updated_at=now
        )
        self._cache[draft_id] = draft
        return draft

    def get_draft(self, draft_id: str) -> ComplaintDraft | None:
        """Get a draft by ID (from cache)."""
        return self._cache.get(draft_id)

    def get_user_drafts(self, user_id: str) -> list[ComplaintDraft]:
        """Get all drafts for a user (from cache)."""
        return [d for d in self._cache.values() if d.user_id == user_id]

    def update_draft(self, draft_id: str, **updates) -> ComplaintDraft | None:
        """Update a draft (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None

        for key, value in updates.items():
            if hasattr(draft, key):
                setattr(draft, key, value)

        draft.updated_at = utc_now()
        return draft

    def attach_documents(self, draft_id: str, document_ids: list[str]) -> ComplaintDraft | None:
        """Attach documents to a draft (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None

        draft.attached_document_ids.extend(document_ids)
        draft.updated_at = utc_now()
        return draft

    def generate_complaint_text(self, draft: ComplaintDraft) -> str:
        """Generate formatted complaint text from draft."""
        agency = self.get_agency(draft.agency_id)
        agency_name = agency.name if agency else "Agency"

        lines = [
            f"FORMAL COMPLAINT TO {agency_name.upper()}",
            f"Date: {utc_now().strftime('%B %d, %Y')}",
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

        lines.extend(
            [
                "",
                "=" * 60,
                "DAMAGES / HARM SUFFERED",
                "=" * 60,
            ]
        )

        if draft.damages_claimed:
            lines.append(f"Financial damages claimed: ${draft.damages_claimed:,.2f}")

        lines.extend(
            [
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
                "Date",
            ]
        )

        return "\n".join(lines)

    def mark_as_filed(self, draft_id: str, confirmation_number: str | None = None) -> ComplaintDraft | None:
        """Mark a complaint as filed (in cache)."""
        draft = self._cache.get(draft_id)
        if not draft:
            return None

        draft.status = ComplaintStatus.FILED
        draft.filed_date = utc_now()
        draft.confirmation_number = confirmation_number
        draft.updated_at = utc_now()
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
                "☐ Set calendar reminder for follow-up",
            ],
        }


# Global service instance
complaint_wizard = ComplaintWizardService()
