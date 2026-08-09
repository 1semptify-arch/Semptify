"""Tests for app.services.eviction.case_builder."""

from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.utc import utc_now
from app.services.eviction.case_builder import (
    ComplianceCheck,
    ComplianceReport,
    ComplianceStatus,
    Defense,
    EvictionCase,
    EvictionCaseBuilder,
    EvictionNoticeInfo,
    EvidenceItem,
    ExtractedLandlordInfo,
    ExtractedTenantInfo,
    MNCourtRules,
    TimelineEntry,
    get_case_builder,
)


@pytest.fixture
def builder():
    """A fresh case builder."""
    return EvictionCaseBuilder()


def make_document(**kwargs):
    """Build a lightweight fake Document."""
    defaults = {
        "id": "doc_1",
        "original_filename": "notice.pdf",
        "document_type": "eviction_notice",
        "description": "A document",
        "uploaded_at": utc_now(),
        "extracted_text": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_timeline_event(**kwargs):
    """Build a lightweight fake TimelineEvent."""
    defaults = {
        "id": "tl_1",
        "user_id": "user_1",
        "event_date": utc_now(),
        "event_type": "communication",
        "title": "Event title",
        "description": "Details",
        "document_id": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_calendar_event(**kwargs):
    """Build a lightweight fake CalendarEvent."""
    defaults = {
        "id": "cal_1",
        "user_id": "user_1",
        "event_type": "hearing",
        "title": "Hearing",
        "start_datetime": utc_now() + timedelta(days=7),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_rent_payment(**kwargs):
    """Build a lightweight fake RentPayment."""
    defaults = {
        "id": "pay_1",
        "user_id": "user_1",
        "payment_date": utc_now(),
        "amount": 120000,
        "status": "paid",
        "payment_method": "check",
        "confirmation_number": "CONF-1",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_user(**kwargs):
    """Build a lightweight fake User."""
    defaults = {"id": "user_1", "email": "tenant@example.com"}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestDataStructuresAndEnums:
    """Smoke tests for constants, dataclasses and enums."""

    def test_mn_court_rules_constants(self):
        assert MNCourtRules.ANSWER_DEADLINE_DAYS == 7
        assert "personal" in MNCourtRules.SERVICE_METHODS
        assert MNCourtRules.DAKOTA_COUNTY_CODE == "19"

    def test_compliance_status_values(self):
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.WARNING.value == "warning"
        assert ComplianceStatus.ERROR.value == "error"
        assert ComplianceStatus.MISSING.value == "missing"

    def test_defense_defaults(self):
        d = Defense(code="test", name="Test Defense", description="desc")
        assert d.applicable is False
        assert d.strength == "unknown"
        assert d.evidence_ids == []

    def test_compliance_report_to_dict(self):
        now = utc_now()
        report = ComplianceReport(
            overall_status=ComplianceStatus.WARNING,
            checks=[
                ComplianceCheck(
                    rule="rule_1",
                    status=ComplianceStatus.COMPLIANT,
                    message="ok",
                    deadline=now,
                ),
                ComplianceCheck(
                    rule="rule_2",
                    status=ComplianceStatus.MISSING,
                    message="missing",
                ),
            ],
            blocking_issues=0,
            warnings=1,
            ready_to_file=False,
        )
        data = report.to_dict()
        assert data["overall_status"] == "warning"
        assert data["blocking_issues"] == 0
        assert data["warnings"] == 1
        assert data["ready_to_file"] is False
        assert data["checks"][0]["deadline"] == now.isoformat()
        assert data["checks"][1]["deadline"] is None

    def test_eviction_case_to_dict(self):
        tenant = ExtractedTenantInfo(
            full_name="Jane Doe",
            address="123 Main St",
            city="Hastings",
            state="MN",
            zip_code="55033",
            phone="555-1234",
            email="jane@example.com",
            monthly_rent=120000,
        )
        landlord = ExtractedLandlordInfo(name="Landlord LLC", address="456 Oak Ave")
        notice = EvictionNoticeInfo(
            notice_type="nonpayment",
            amount_claimed=240000,
            court_date=utc_now() + timedelta(days=7),
        )
        case = EvictionCase(
            user_id="user_1",
            case_number="ABC-123",
            tenant=tenant,
            landlord=landlord,
            notice=notice,
            evidence=[
                EvidenceItem(
                    document_id="doc_1",
                    filename="notice.pdf",
                    document_type="eviction_notice",
                    description="",
                    exhibit_label="Exhibit A",
                    relevance="The notice being challenged",
                )
            ],
            timeline=[
                TimelineEntry(
                    date=utc_now(),
                    event_type="notice",
                    title="Notice served",
                    description="",
                    has_evidence=True,
                    evidence_ids=["doc_1"],
                )
            ],
            defenses=[
                Defense(
                    code="improper_notice", name="Improper Notice", description="", applicable=True, strength="strong"
                )
            ],
            total_paid=120000,
            total_owed=240000,
            compliance=ComplianceReport(
                overall_status=ComplianceStatus.COMPLIANT,
                blocking_issues=0,
                warnings=0,
                ready_to_file=True,
            ),
        )
        data = case.to_dict()
        assert data["user_id"] == "user_1"
        assert data["case_number"] == "ABC-123"
        assert data["tenant"]["full_name"] == "Jane Doe"
        assert data["landlord"]["name"] == "Landlord LLC"
        assert data["notice"]["type"] == "nonpayment"
        assert data["evidence_count"] == 1
        assert data["timeline_count"] == 1
        assert data["defenses"]
        assert data["compliance"]["overall_status"] == "compliant"

    def test_eviction_case_to_dict_missing_optional(self):
        case = EvictionCase(user_id="user_1")
        data = case.to_dict()
        assert data["tenant"] is None
        assert data["landlord"] is None
        assert data["notice"] is None
        assert data["compliance"] is None


class TestEvidenceAndExtraction:
    """Tests for evidence building and document extraction."""

    def test_build_evidence_list_assigns_exhibit_labels(self, builder):
        docs = [
            make_document(id="d1", document_type="lease"),
            make_document(id="d2", document_type="photo"),
            make_document(id="d3", document_type="rent_receipt"),
        ]
        evidence = builder._build_evidence_list(docs)
        assert len(evidence) == 3
        assert evidence[0].exhibit_label == "Exhibit A"
        assert evidence[1].exhibit_label == "Exhibit B"
        assert evidence[2].exhibit_label == "Exhibit C"

    def test_build_evidence_list_wraps_past_26(self, builder):
        docs = [make_document(id=f"d{i}") for i in range(27)]
        evidence = builder._build_evidence_list(docs)
        assert evidence[25].exhibit_label == "Exhibit Z"
        assert evidence[26].exhibit_label == "Exhibit AA1"

    def test_build_evidence_list_relevance(self, builder):
        doc = make_document(document_type="lease")
        evidence = builder._build_evidence_list([doc])
        assert evidence[0].relevance == "Establishes terms of tenancy agreement"

    def test_determine_relevance_default(self, builder):
        doc = make_document(document_type="unknown")
        assert builder._determine_relevance(doc) == "Supporting evidence"

    def test_extract_landlord_info_from_text(self, builder):
        text = "Landlord: Acme Properties\n123 Main Street, Hastings, MN 55033\nPhone: 555-0000"
        doc = make_document(document_type="lease", extracted_text=text)
        info = builder._extract_landlord_info([doc])
        assert info is not None
        assert "Acme Properties" in info.name
        assert "Main Street" in (info.address or "")

    def test_extract_landlord_info_returns_empty_when_no_match(self, builder):
        doc = make_document(document_type="photo", extracted_text="nothing")
        info = builder._extract_landlord_info([doc])
        assert info.name == ""

    def test_extract_notice_info_nonpayment(self, builder):
        text = "14-day notice to quit for non-payment. You owe $1,200.00 in rent. Served on January 15, 2024."
        doc = make_document(document_type="eviction_notice", extracted_text=text)
        notice = builder._extract_notice_info([doc])
        assert notice is not None
        assert notice.notice_type == "nonpayment"
        assert notice.amount_claimed == 120000
        assert notice.date_served is not None

    def test_extract_notice_info_lease_violation(self, builder):
        text = "Notice of lease violation: unauthorized pet."
        doc = make_document(document_type="notice_to_quit", extracted_text=text)
        notice = builder._extract_notice_info([doc])
        assert notice is not None
        assert notice.notice_type == "lease_violation"

    def test_extract_notice_info_holdover(self, builder):
        text = "30-day notice to end tenancy. Holdover."
        doc = make_document(document_type="eviction_notice", extracted_text=text)
        notice = builder._extract_notice_info([doc])
        assert notice is not None
        assert notice.notice_type == "holdover"

    def test_extract_notice_info_no_match(self, builder):
        doc = make_document(document_type="photo", original_filename="photo.jpg", extracted_text="nothing")
        assert builder._extract_notice_info([doc]) is None


class TestTimelineAndCalendar:
    """Tests for timeline and calendar helpers."""

    def test_build_timeline(self, builder):
        events = [
            make_timeline_event(document_id="doc_1"),
            make_timeline_event(document_id=None),
        ]
        timeline = builder._build_timeline(events, [])
        assert len(timeline) == 2
        assert timeline[0].has_evidence is True
        assert timeline[0].evidence_ids == ["doc_1"]
        assert timeline[1].has_evidence is False
        assert timeline[1].evidence_ids == []

    def test_update_from_calendar_sets_court_date(self, builder):
        hearing_date = utc_now() + timedelta(days=7)
        case = EvictionCase(user_id="user_1", notice=EvictionNoticeInfo(notice_type="nonpayment"))
        builder._update_from_calendar(
            case,
            [make_calendar_event(start_datetime=hearing_date)],
        )
        assert case.notice.court_date == hearing_date

    def test_update_from_calendar_creates_notice(self, builder):
        hearing_date = utc_now() + timedelta(days=7)
        case = EvictionCase(user_id="user_1")
        builder._update_from_calendar(
            case,
            [make_calendar_event(start_datetime=hearing_date)],
        )
        assert case.notice is not None
        assert case.notice.notice_type == "unknown"
        assert case.notice.court_date == hearing_date

    def test_build_rent_history(self, builder):
        payments = [
            make_rent_payment(status="paid", amount=120000),
            make_rent_payment(status="missed", amount=120000),
        ]
        history = builder._build_rent_history(payments)
        assert len(history) == 2
        assert history[0]["status"] == "paid"
        assert history[1]["status"] == "missed"


class TestDefenseAnalysis:
    """Tests for defense applicability analysis."""

    def test_analyze_defenses_rent_paid(self, builder):
        case = EvictionCase(user_id="user_1", total_paid=120000)
        defenses = builder._analyze_defenses(case)
        rent_paid = next(d for d in defenses if d.code == "rent_paid")
        assert rent_paid.applicable is True
        assert rent_paid.strength == "moderate"
        assert "$1200.00" in rent_paid.notes

    def test_analyze_defenses_habitability_with_photos(self, builder):
        case = EvictionCase(
            user_id="user_1",
            evidence=[EvidenceItem(document_id="d1", filename="mold.jpg", document_type="photo", description="")],
        )
        defenses = builder._analyze_defenses(case)
        habitability = next(d for d in defenses if d.code == "habitability")
        assert habitability.applicable is True
        assert habitability.strength == "moderate"

    def test_analyze_defenses_habitability_with_maintenance_event(self, builder):
        case = EvictionCase(
            user_id="user_1",
            timeline=[TimelineEntry(date=utc_now(), event_type="maintenance", title="", description="")],
        )
        defenses = builder._analyze_defenses(case)
        habitability = next(d for d in defenses if d.code == "habitability")
        assert habitability.applicable is True
        assert habitability.strength == "weak"


class TestCompliance:
    """Tests for compliance checking."""

    def test_compliance_compliant_case(self, builder):
        case = EvictionCase(
            user_id="user_1",
            case_number="ABC-123",
            tenant=ExtractedTenantInfo(
                full_name="Jane Doe", address="123 Main", city="Hastings", state="MN", zip_code="55033"
            ),
            landlord=ExtractedLandlordInfo(name="Landlord LLC"),
            notice=EvictionNoticeInfo(notice_type="nonpayment", court_date=utc_now() + timedelta(days=14)),
            evidence=[make_document()],
        )
        report = builder._check_compliance(case)
        assert report.overall_status == ComplianceStatus.COMPLIANT
        assert report.ready_to_file is True

    def test_compliance_missing_tenant_and_address(self, builder):
        case = EvictionCase(user_id="user_1")
        report = builder._check_compliance(case)
        assert report.overall_status == ComplianceStatus.ERROR
        assert report.blocking_issues >= 2
        assert report.ready_to_file is False

    def test_compliance_court_date_past(self, builder):
        case = EvictionCase(
            user_id="user_1",
            tenant=ExtractedTenantInfo(
                full_name="Jane", address="123 Main", city="Hastings", state="MN", zip_code="55033"
            ),
            landlord=ExtractedLandlordInfo(name="LLC"),
            notice=EvictionNoticeInfo(notice_type="nonpayment", court_date=utc_now() - timedelta(days=1)),
        )
        report = builder._check_compliance(case)
        court_check = next(c for c in report.checks if c.rule == "court_date_required")
        assert court_check.status == ComplianceStatus.ERROR

    def test_compliance_court_date_soon(self, builder):
        case = EvictionCase(
            user_id="user_1",
            tenant=ExtractedTenantInfo(
                full_name="Jane", address="123 Main", city="Hastings", state="MN", zip_code="55033"
            ),
            landlord=ExtractedLandlordInfo(name="LLC"),
            notice=EvictionNoticeInfo(notice_type="nonpayment", court_date=utc_now() + timedelta(days=2)),
        )
        report = builder._check_compliance(case)
        court_check = next(c for c in report.checks if c.rule == "court_date_required")
        assert court_check.status == ComplianceStatus.WARNING

    def test_compliance_missing_evidence(self, builder):
        case = EvictionCase(
            user_id="user_1",
            tenant=ExtractedTenantInfo(
                full_name="Jane", address="123 Main", city="Hastings", state="MN", zip_code="55033"
            ),
            landlord=ExtractedLandlordInfo(name="LLC"),
        )
        report = builder._check_compliance(case)
        evidence_check = next(c for c in report.checks if c.rule == "evidence_recommended")
        assert evidence_check.status == ComplianceStatus.WARNING

    def test_compliance_missing_case_number(self, builder):
        case = EvictionCase(
            user_id="user_1",
            tenant=ExtractedTenantInfo(
                full_name="Jane", address="123 Main", city="Hastings", state="MN", zip_code="55033"
            ),
            landlord=ExtractedLandlordInfo(name="LLC"),
            notice=EvictionNoticeInfo(notice_type="nonpayment", court_date=utc_now() + timedelta(days=14)),
        )
        report = builder._check_compliance(case)
        case_check = next((c for c in report.checks if c.rule == "case_number_required"), None)
        assert case_check is not None
        assert case_check.status == ComplianceStatus.WARNING


class TestBuildCase:
    """Integration-style tests for build_case with mocked database."""

    @pytest.mark.asyncio
    async def test_build_case_no_data(self, builder, monkeypatch):
        @asynccontextmanager
        async def fake_session():
            yield MagicMock()

        monkeypatch.setattr("app.services.eviction.case_builder.get_db_session", fake_session)
        builder._get_user = AsyncMock(return_value=None)
        builder._extract_tenant_info = AsyncMock(return_value=None)
        builder._get_documents = AsyncMock(return_value=[])
        builder._get_timeline_events = AsyncMock(return_value=[])
        builder._get_calendar_events = AsyncMock(return_value=[])
        builder._get_rent_payments = AsyncMock(return_value=[])

        case = await builder.build_case("user_1")
        assert case.user_id == "user_1"
        assert case.tenant is None
        assert case.evidence == []
        assert case.compliance is not None

    @pytest.mark.asyncio
    async def test_build_case_with_data(self, builder, monkeypatch):
        @asynccontextmanager
        async def fake_session():
            yield MagicMock()

        monkeypatch.setattr("app.services.eviction.case_builder.get_db_session", fake_session)
        user = make_user()
        tenant = ExtractedTenantInfo(
            full_name="Jane Doe", address="123 Main", city="Hastings", state="MN", zip_code="55033"
        )
        documents = [
            make_document(id="doc_1", document_type="eviction_notice", original_filename="notice.pdf"),
            make_document(id="doc_2", document_type="photo", original_filename="mold.jpg"),
        ]

        builder._get_user = AsyncMock(return_value=user)
        builder._extract_tenant_info = AsyncMock(return_value=tenant)
        builder._get_documents = AsyncMock(return_value=documents)
        builder._get_timeline_events = AsyncMock(return_value=[make_timeline_event(event_type="maintenance")])
        builder._get_calendar_events = AsyncMock(return_value=[make_calendar_event()])
        builder._get_rent_payments = AsyncMock(return_value=[make_rent_payment(status="paid")])

        case = await builder.build_case("user_1")
        assert case.tenant == tenant
        assert len(case.evidence) == 2
        assert case.evidence[0].exhibit_label == "Exhibit A"
        assert case.total_paid == 120000
        assert case.compliance is not None


@pytest.mark.asyncio
async def test_get_case_builder():
    """get_case_builder returns a builder."""
    builder = await get_case_builder()
    assert isinstance(builder, EvictionCaseBuilder)
