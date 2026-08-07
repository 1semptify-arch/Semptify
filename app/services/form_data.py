"""
Semptify Form Data Module
Central data hub that connects all modules - document processing, defense, forms, timeline.
Gathers and distributes data across the entire system.
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select

from app.core.database import get_db_session
from app.core.event_bus import EventType, event_bus
from app.core.utc import utc_now
from app.models.models import Document, TimelineEvent

logger = logging.getLogger(__name__)


class CaseStage(str, Enum):
    NOTICE_RECEIVED = "notice_received"
    SUMMONS_SERVED = "summons_served"
    ANSWER_DUE = "answer_due"
    ANSWER_FILED = "answer_filed"
    HEARING_SCHEDULED = "hearing_scheduled"
    HEARING_COMPLETE = "hearing_complete"
    APPEAL = "appeal"


@dataclass
class PartyInfo:
    """Party information (tenant or landlord)"""

    name: str = ""
    address: str = ""
    city: str = ""
    state: str = "MN"
    zip_code: str = ""
    phone: str = ""
    email: str = ""
    attorney_name: str = ""
    attorney_bar_number: str = ""


@dataclass
class CaseInfo:
    """Core case information"""

    case_number: str = ""
    court_name: str = "Dakota County District Court"
    court_address: str = "1560 Highway 55, Hastings, MN 55033"
    court_phone: str = "651-438-4300"
    judicial_district: str = "First Judicial District"
    county: str = "Dakota"

    # Parties
    tenant: PartyInfo = field(default_factory=PartyInfo)
    landlord: PartyInfo = field(default_factory=PartyInfo)

    # Property
    property_address: str = ""
    property_city: str = ""
    property_state: str = "MN"
    property_zip: str = ""
    unit_number: str = ""

    # Lease
    lease_start_date: str = ""
    lease_end_date: str = ""
    monthly_rent: float = 0.0
    security_deposit: float = 0.0
    lease_type: str = "month-to-month"  # fixed-term, month-to-month

    # Case dates
    notice_date: str = ""
    notice_type: str = ""  # 14-day, 30-day, etc.
    summons_date: str = ""
    answer_deadline: str = ""
    hearing_date: str = ""
    hearing_time: str = ""

    # Case status
    stage: CaseStage = CaseStage.NOTICE_RECEIVED

    # Amounts claimed
    rent_claimed: float = 0.0
    late_fees_claimed: float = 0.0
    other_fees_claimed: float = 0.0
    total_claimed: float = 0.0

    # Defenses
    selected_defenses: list[str] = field(default_factory=list)
    counterclaims: list[str] = field(default_factory=list)

    # Notes
    notes: str = ""


@dataclass
class FormData:
    """Complete form data package for all court forms"""

    case: CaseInfo = field(default_factory=CaseInfo)

    # Document references
    documents: list[dict[str, Any]] = field(default_factory=list)
    timeline_events: list[dict[str, Any]] = field(default_factory=list)

    # Extracted data from documents
    extracted_dates: list[dict[str, str]] = field(default_factory=list)
    extracted_amounts: list[dict[str, float]] = field(default_factory=list)
    extracted_parties: list[dict[str, str]] = field(default_factory=list)

    # Form-specific data
    answer_form_data: dict[str, Any] = field(default_factory=dict)
    counterclaim_data: dict[str, Any] = field(default_factory=dict)
    motion_data: dict[str, Any] = field(default_factory=dict)

    # Processing status
    last_updated: str = ""
    processing_complete: bool = False
    confidence_score: float = 0.0


class FormDataService:
    """
    Central service for managing form data across all Semptify modules.
    Acts as the data hub connecting:
    - Document processing (input)
    - Timeline events (input/output)
    - Defense modules (input/output)
    - Form generation (output)
    - Calendar (output)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.form_data = FormData()
        self._storage_key = f"form_data_{user_id}"

    async def load(self) -> FormData:
        """Load form data from database and documents"""
        await self._load_from_documents()
        await self._load_from_timeline()
        await self._extract_case_info()
        self.form_data.last_updated = utc_now().isoformat()
        return self.form_data

    async def save(self) -> bool:
        """Save form data for persistence"""
        # Store in user's local storage via API response
        # In production, would store in database
        return True

    async def _load_from_documents(self):
        """Extract data from user's vault documents"""
        async with get_db_session() as session:
            query = select(Document).where(Document.user_id == self.user_id)
            result = await session.execute(query)
            documents = result.scalars().all()

            for doc in documents:
                doc_data = {
                    "id": doc.id,
                    "filename": doc.original_filename or doc.filename,
                    "type": doc.document_type,
                    "uploaded": doc.uploaded_at.isoformat() if doc.uploaded_at else "",
                    "description": doc.description or "",
                }
                self.form_data.documents.append(doc_data)

                # Extract data based on document type
                if doc.document_type == "notice":
                    await self._extract_notice_data(doc)
                elif doc.document_type == "lease":
                    await self._extract_lease_data(doc)
                elif doc.document_type == "legal":
                    await self._extract_legal_data(doc)

    async def _load_from_timeline(self):
        """Load timeline events"""
        async with get_db_session() as session:
            query = (
                select(TimelineEvent)
                .where(TimelineEvent.user_id == self.user_id)
                .order_by(TimelineEvent.event_date.desc())
            )
            result = await session.execute(query)
            events = result.scalars().all()

            for event in events:
                event_data = {
                    "id": event.id,
                    "type": event.event_type,
                    "title": event.title,
                    "date": event.event_date.isoformat() if event.event_date else "",
                    "description": event.description or "",
                    "is_evidence": event.is_evidence,
                }
                self.form_data.timeline_events.append(event_data)

    async def _extract_case_info(self):
        """Extract case information from documents and timeline"""
        # Look for case number patterns
        case_patterns = [
            r"(\d{2}[A-Z]{2}-CV-\d{2}-\d+)",  # 19AV-CV-25-0000
            r"(\d{2}-CV-[A-Z]{2}-\d{2}-\d+)",  # 27-CV-HC-24-5847
            r"Case\s*(?:No\.?|Number|#)?\s*:?\s*([A-Z0-9-]+)",
        ]

        for doc in self.form_data.documents:
            desc = doc.get("description", "") + " " + doc.get("filename", "")
            for pattern in case_patterns:
                match = re.search(pattern, desc, re.IGNORECASE)
                if match:
                    self.form_data.case.case_number = match.group(1)
                    break

        # Extract dates from timeline
        for event in self.form_data.timeline_events:
            event.get("type", "")
            event_date = event.get("date", "")
            title = event.get("title", "").lower()

            if not event_date:
                continue

            if "notice" in title and "served" in title:
                self.form_data.case.notice_date = event_date[:10]
            elif "hearing" in title or "court date" in title:
                self.form_data.case.hearing_date = event_date[:10]
                if "9:00" in title or "9am" in title.lower():
                    self.form_data.case.hearing_time = "9:00 AM"
            elif "summons" in title:
                self.form_data.case.summons_date = event_date[:10]
            elif "lease" in title and ("start" in title or "begin" in title):
                self.form_data.case.lease_start_date = event_date[:10]
            elif "lease" in title and "end" in title:
                self.form_data.case.lease_end_date = event_date[:10]

        # Calculate answer deadline if we have summons date
        if self.form_data.case.summons_date:
            try:
                summons = datetime.fromisoformat(self.form_data.case.summons_date)
                deadline = summons + timedelta(days=7)
                self.form_data.case.answer_deadline = deadline.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Determine case stage
        self._determine_case_stage()

    async def _extract_notice_data(self, doc: Document):
        """Extract data from notice documents"""
        self.form_data.extracted_dates.append(
            {
                "source": doc.original_filename,
                "type": "notice_date",
                "date": doc.uploaded_at.strftime("%Y-%m-%d") if doc.uploaded_at else "",
            }
        )

        # Try to determine notice type from filename
        filename = (doc.original_filename or doc.filename).lower()
        if "14" in filename or "fourteen" in filename:
            self.form_data.case.notice_type = "14-day"
        elif "30" in filename or "thirty" in filename:
            self.form_data.case.notice_type = "30-day"
        elif "pay" in filename and "quit" in filename:
            self.form_data.case.notice_type = "pay-or-quit"

    async def _extract_lease_data(self, doc: Document):
        """Extract data from lease documents"""
        (doc.original_filename or doc.filename or "").lower()
        text = (doc.extracted_text or "").lower()

        # Monthly rent — look for "$X/month", "rent: $X", "monthly rent of $X"
        rent_patterns = [
            r"monthly\s+rent\s+(?:of\s+)?\$?([\d,]+(?:\.\d{2})?)",
            r"rent\s*(?:amount\s*)?(?:is\s*)?\$?([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/\s*month|monthly)",
            r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/\s*month)",
        ]
        for pattern in rent_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    amount = float(m.group(1).replace(",", ""))
                    if 100 <= amount <= 20000:
                        self.form_data.case.monthly_rent = amount
                        break
                except ValueError:
                    pass

        # Security deposit
        deposit_patterns = [
            r"security\s+deposit\s+(?:of\s+)?\$?([\d,]+(?:\.\d{2})?)",
            r"deposit\s*(?:amount\s*)?(?:is\s*)?\$?([\d,]+(?:\.\d{2})?)",
        ]
        for pattern in deposit_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    amount = float(m.group(1).replace(",", ""))
                    if 0 < amount <= 50000:
                        self.form_data.case.security_deposit = amount
                        break
                except ValueError:
                    pass

        # Lease start date — "commencing", "beginning", "start date", "effective"
        start_patterns = [
            r"(?:commenc(?:ing|es?)|beginning|start(?:ing)?\s+date|effective\s+(?:date\s+)?(?:of\s+)?(?:this\s+)?(?:lease\s+)?(?:on\s+)?)"
            r"\s*(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})",
            r"lease\s+(?:term\s+)?(?:begins?|starts?)\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})",
        ]
        for pattern in start_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    parsed = datetime.strptime(m.group(1).strip().rstrip(","), "%B %d %Y")
                    self.form_data.case.lease_start_date = parsed.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    try:
                        parsed = datetime.strptime(m.group(1).strip().rstrip(","), "%B %d, %Y")
                        self.form_data.case.lease_start_date = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass

        # Lease end date — "terminating", "ending", "expir"
        end_patterns = [
            r"(?:terminat(?:ing|es?)|ending|expir(?:ing|es?|ation\s+date))\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})",
            r"lease\s+(?:term\s+)?(?:ends?|terminates?|expires?)\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})",
        ]
        for pattern in end_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    parsed = datetime.strptime(m.group(1).strip().rstrip(","), "%B %d %Y")
                    self.form_data.case.lease_end_date = parsed.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    try:
                        parsed = datetime.strptime(m.group(1).strip().rstrip(","), "%B %d, %Y")
                        self.form_data.case.lease_end_date = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass

        # Lease type — fixed-term vs month-to-month
        if "month-to-month" in text or "month to month" in text or "monthly tenancy" in text:
            self.form_data.case.lease_type = "month-to-month"
        elif re.search(r"(?:fixed[- ]term|one[- ]year|two[- ]year|\d+[- ]month\s+lease)", text):
            self.form_data.case.lease_type = "fixed-term"

        # Unit number — "unit #X", "apt X", "apartment X", "unit X"
        if not self.form_data.case.unit_number:
            unit_m = re.search(r"(?:unit|apt\.?|apartment)\s*#?\s*([A-Za-z0-9\-]+)", text)
            if unit_m:
                self.form_data.case.unit_number = unit_m.group(1).strip()

        # Property address from lease header (first address-like pattern in text)
        if not self.form_data.case.property_address:
            addr_m = re.search(
                r"(\d{2,5}\s+[A-Za-z][A-Za-z0-9\s\.,]+(?:street|st|avenue|ave|road|rd|blvd|drive|dr|lane|ln|court|ct|way|circle|cir)\.?)",
                text,
                re.IGNORECASE,
            )
            if addr_m:
                self.form_data.case.property_address = addr_m.group(1).strip().title()

    async def _extract_legal_data(self, doc: Document):
        """Extract data from legal documents (complaints, summons, etc.)"""
        filename = (doc.original_filename or doc.filename).lower()

        if "complaint" in filename or "summons" in filename:
            self.form_data.case.stage = CaseStage.SUMMONS_SERVED

    def _determine_case_stage(self):
        """Determine current case stage based on available data"""
        case = self.form_data.case

        if case.hearing_date:
            hearing = datetime.fromisoformat(case.hearing_date)
            if hearing < utc_now():
                case.stage = CaseStage.HEARING_COMPLETE
            else:
                case.stage = CaseStage.HEARING_SCHEDULED
        elif case.answer_deadline:
            deadline = datetime.fromisoformat(case.answer_deadline)
            if deadline < utc_now():
                case.stage = CaseStage.ANSWER_FILED  # Assume filed if past
            else:
                case.stage = CaseStage.ANSWER_DUE
        elif case.summons_date:
            case.stage = CaseStage.SUMMONS_SERVED
        elif case.notice_date:
            case.stage = CaseStage.NOTICE_RECEIVED

    def update_case_info(self, updates: dict[str, Any]) -> CaseInfo:
        """Update case information from user input"""
        case = self.form_data.case

        # Update tenant info
        if "tenant" in updates:
            for key, value in updates["tenant"].items():
                if hasattr(case.tenant, key):
                    setattr(case.tenant, key, value)

        # Update landlord info
        if "landlord" in updates:
            for key, value in updates["landlord"].items():
                if hasattr(case.landlord, key):
                    setattr(case.landlord, key, value)

        # Update case fields
        for key, value in updates.items():
            if key not in ["tenant", "landlord"] and hasattr(case, key):
                setattr(case, key, value)

        self.form_data.last_updated = utc_now().isoformat()

        # Publish event
        try:
            event_bus.publish_sync(
                EventType.CASE_INFO_UPDATED,
                {"updates": list(updates.keys()), "user_id": self.user_id},
                source="form_data",
                user_id=self.user_id,
            )
        except Exception:
            pass  # Don't fail on event publish errors

        return case

    def add_defense(self, defense_code: str) -> list[str]:
        """Add a defense to the case"""
        if defense_code not in self.form_data.case.selected_defenses:
            self.form_data.case.selected_defenses.append(defense_code)
        return self.form_data.case.selected_defenses

    def remove_defense(self, defense_code: str) -> list[str]:
        """Remove a defense from the case"""
        if defense_code in self.form_data.case.selected_defenses:
            self.form_data.case.selected_defenses.remove(defense_code)
        return self.form_data.case.selected_defenses

    def add_counterclaim(self, claim_code: str) -> list[str]:
        """Add a counterclaim"""
        if claim_code not in self.form_data.case.counterclaims:
            self.form_data.case.counterclaims.append(claim_code)
        return self.form_data.case.counterclaims

    def get_answer_form_data(self) -> dict[str, Any]:
        """Get pre-filled data for Answer to Eviction form"""
        case = self.form_data.case
        return {
            "court_name": case.court_name,
            "county": case.county,
            "case_number": case.case_number,
            "plaintiff_name": case.landlord.name,
            "plaintiff_address": f"{case.landlord.address}, {case.landlord.city}, {case.landlord.state} {case.landlord.zip_code}",
            "defendant_name": case.tenant.name,
            "defendant_address": f"{case.tenant.address}, {case.tenant.city}, {case.tenant.state} {case.tenant.zip_code}",
            "property_address": f"{case.property_address}, {case.property_city}, {case.property_state} {case.property_zip}",
            "rent_amount": case.monthly_rent,
            "defenses": case.selected_defenses,
            "counterclaims": case.counterclaims,
            "hearing_date": case.hearing_date,
            "hearing_time": case.hearing_time,
        }

    def get_motion_form_data(self, motion_type: str) -> dict[str, Any]:
        """Get pre-filled data for motion forms"""
        case = self.form_data.case
        base_data = {
            "court_name": case.court_name,
            "county": case.county,
            "judicial_district": case.judicial_district,
            "case_number": case.case_number,
            "plaintiff_name": case.landlord.name,
            "defendant_name": case.tenant.name,
            "property_address": case.property_address,
            "filing_date": utc_now().strftime("%Y-%m-%d"),
        }

        if motion_type == "continuance":
            base_data["current_hearing_date"] = case.hearing_date
            base_data["reason"] = ""
        elif motion_type == "dismiss":
            base_data["grounds"] = case.selected_defenses
        elif motion_type == "stay":
            base_data["hearing_date"] = case.hearing_date

        return base_data

    def get_counterclaim_form_data(self) -> dict[str, Any]:
        """Get pre-filled data for counterclaim form"""
        case = self.form_data.case
        return {
            "court_name": case.court_name,
            "county": case.county,
            "case_number": case.case_number,
            "counter_plaintiff": case.tenant.name,
            "counter_defendant": case.landlord.name,
            "property_address": case.property_address,
            "claims": case.counterclaims,
            "security_deposit": case.security_deposit,
            "monthly_rent": case.monthly_rent,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert form data to dictionary for API response"""
        return {
            "case": asdict(self.form_data.case),
            "documents": self.form_data.documents,
            "timeline_events": self.form_data.timeline_events,
            "extracted_dates": self.form_data.extracted_dates,
            "extracted_amounts": self.form_data.extracted_amounts,
            "answer_form_data": self.get_answer_form_data(),
            "last_updated": self.form_data.last_updated,
            "processing_complete": self.form_data.processing_complete,
        }

    def get_case_summary(self) -> dict[str, Any]:
        """Get a summary of the case for display"""
        case = self.form_data.case

        # Calculate days until hearing
        days_to_hearing = None
        if case.hearing_date:
            try:
                hearing = datetime.fromisoformat(case.hearing_date)
                days_to_hearing = (hearing - utc_now()).days
            except ValueError:
                pass

        return {
            "case_number": case.case_number or "Not yet assigned",
            "court": case.court_name,
            "stage": case.stage.value,
            "stage_display": case.stage.value.replace("_", " ").title(),
            "tenant_name": case.tenant.name or "Not entered",
            "landlord_name": case.landlord.name or "Not entered",
            "property_address": case.property_address or "Not entered",
            "hearing_date": case.hearing_date or "Not scheduled",
            "hearing_time": case.hearing_time or "",
            "days_to_hearing": days_to_hearing,
            "defenses_count": len(case.selected_defenses),
            "counterclaims_count": len(case.counterclaims),
            "documents_count": len(self.form_data.documents),
            "timeline_events_count": len(self.form_data.timeline_events),
            "rent_claimed": case.rent_claimed,
            "total_claimed": case.total_claimed,
        }


# Singleton instance cache
_form_data_services: dict[str, FormDataService] = {}


def get_form_data_service(user_id: str) -> FormDataService:
    """Get or create form data service for user"""
    if user_id not in _form_data_services:
        _form_data_services[user_id] = FormDataService(user_id)
    return _form_data_services[user_id]
