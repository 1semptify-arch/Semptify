"""Unit tests for app.services.eviction.case_builder.

These tests exercise the public data classes, constants, and service methods
without requiring a real database. All SQLAlchemy session access is mocked with
``unittest.mock`` and ``pytest.monkeypatch``.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.eviction import case_builder
from app.services.eviction.case_builder import (
    DAKOTA_COUNTY_FORM_FIELDS,
    MINNESOTA_DEFENSES,
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
    """Return a fresh EvictionCaseBuilder."""
    return EvictionCaseBuilder()


@pytest.fixture
def fixed_now():
    """Return a deterministic UTC timestamp for tests."""
    return datetime(2025, 12, 1, tzinfo=UTC)


# =============================================================================
# Minnesota Court Rules
# =============================================================================


def test_mn_court_rules_constants():
    """MNCourtRules exposes the expected Dakota County constants."""
    assert MNCourtRules.ANSWER_DEADLINE_DAYS == 7
    assert MNCourtRules.SERVICE_METHODS == ["personal", "substitute", "mail", "posting"]
    assert MNCourtRules.REQUIRED_SERVICE_PROOF is True
    assert MNCourtRules.MAX_COUNTERCLAIM_AMOUNT == 15000
    assert MNCourtRules.COUNTERCLAIM_FILING_FEE == 75
    assert MNCourtRules.REQUIRED_COPIES == 3
    assert MNCourtRules.ALLOWED_FORMATS == ["pdf", "jpg", "png", "doc", "docx"]
    assert MNCourtRules.MAX_FILE_SIZE_MB == 25
    assert MNCourtRules.ZOOM_APPEARANCE_ALLOWED is True
    assert MNCourtRules.IN_PERSON_REQUIRED_FOR == ["jury_trial", "contempt"]
    assert MNCourtRules.IFP_INCOME_THRESHOLD_PERCENT == 125
    assert MNCourtRules.DAKOTA_COUNTY_CODE == "19"
    assert MNCourtRules.COURT_ADDRESS == "1560 Highway 55, Hastings, MN 55033"
    assert MNCourtRules.EFILING_URL.startswith("https://")
    assert MNCourtRules.GUIDE_AND_FILE_URL.startswith("https://")


# =============================================================================
# ComplianceStatus, ComplianceCheck, ComplianceReport
# =============================================================================


def test_compliance_status_enum():
    """ComplianceStatus covers the four expected states."""
    values = {s.value for s in ComplianceStatus}
    assert values == {"compliant", "warning", "error", "missing"}
    assert ComplianceStatus("compliant") is ComplianceStatus.COMPLIANT


def test_compliance_check_dataclass():
    """ComplianceCheck stores rule, status, message, and optional fields."""
    check = ComplianceCheck(
        rule="tenant_name_required",
        status=ComplianceStatus.ERROR,
        message="Tenant name is required for court forms",
    )
    assert check.rule == "tenant_name_required"
    assert check.status == ComplianceStatus.ERROR
    assert check.message == "Tenant name is required for court forms"
    assert check.fix_action is None
    assert check.deadline is None


def test_compliance_report_to_dict():
    """ComplianceReport.to_dict serializes all fields, including deadlines."""
    deadline = datetime(2025, 12, 15, 9, 0, tzinfo=UTC)
    check = ComplianceCheck(
        rule="court_date_required",
        status=ComplianceStatus.WARNING,
        message="Court date is in 2 days - file immediately!",
        fix_action="Add court date to your calendar",
        deadline=deadline,
    )
    report = ComplianceReport(
        overall_status=ComplianceStatus.WARNING,
        checks=[check],
        blocking_issues=0,
        warnings=1,
        ready_to_file=False,
    )
    data = report.to_dict()

    assert data["overall_status"] == "warning"
    assert data["blocking_issues"] == 0
    assert data["warnings"] == 1
    assert data["ready_to_file"] is False
    assert data["checks"] == [
        {
            "rule": "court_date_required",
            "status": "warning",
            "message": "Court date is in 2 days - file immediately!",
            "fix_action": "Add court date to your calendar",
            "deadline": deadline.isoformat(),
        },
    ]


def test_compliance_report_to_dict_no_deadline():
    """ComplianceReport.to_dict handles checks with no deadline."""
    check = ComplianceCheck(rule="evidence_recommended", status=ComplianceStatus.COMPLIANT, message="ok")
    report = ComplianceReport(overall_status=ComplianceStatus.COMPLIANT, checks=[check])
    data = report.to_dict()

    assert data["checks"][0]["deadline"] is None


# =============================================================================
# Case Data Structures
# =============================================================================


def test_extracted_tenant_info():
    """ExtractedTenantInfo captures tenant profile and lease data."""
    tenant = ExtractedTenantInfo(
        full_name="Jane Doe",
        address="123 Main Street",
        city="Burnsville",
        state="MN",
        zip_code="55337",
        phone="555-1234",
        monthly_rent=120000,
    )
    assert tenant.full_name == "Jane Doe"
    assert tenant.monthly_rent == 120000
    assert tenant.security_deposit is None


def test_extracted_landlord_info():
    """ExtractedLandlordInfo captures landlord and agent details."""
    landlord = ExtractedLandlordInfo(
        name="ABC Properties LLC",
        address="456 Corporate Blvd",
        agent_name="Property Manager",
    )
    assert landlord.name == "ABC Properties LLC"
    assert landlord.email is None


def test_eviction_notice_info():
    """EvictionNoticeInfo stores notice and court details."""
    notice = EvictionNoticeInfo(
        notice_type="nonpayment",
        date_served=datetime(2025, 11, 20, tzinfo=UTC),
        amount_claimed=150000,
        court_date=datetime(2025, 12, 15, tzinfo=UTC),
        case_number="27-CV-25-12345",
    )
    assert notice.notice_type == "nonpayment"
    assert notice.amount_claimed == 150000


def test_evidence_item():
    """EvidenceItem holds exhibit metadata."""
    item = EvidenceItem(
        document_id="d1",
        filename="lease.pdf",
        document_type="lease",
        description="Signed lease",
    )
    assert item.exhibit_label is None
    assert item.relevance == ""


def test_timeline_entry():
    """TimelineEntry records a chronological event."""
    entry = TimelineEntry(
        date=datetime(2025, 11, 20, tzinfo=UTC),
        event_type="notice",
        title="14-Day Notice",
        description="Received notice",
    )
    assert entry.has_evidence is False
    assert entry.evidence_ids == []


def test_defense():
    """Defense tracks a legal defense and its strength."""
    defense = Defense(code="rent_paid", name="Rent Was Paid", description="All rent paid", applicable=True)
    assert defense.strength == "unknown"
    assert defense.applicable is True


def test_eviction_case_to_dict_full():
    """EvictionCase.to_dict serializes a fully populated case."""
    fixed = datetime(2025, 12, 1, tzinfo=UTC)
    tenant = ExtractedTenantInfo(
        full_name="Jane Doe",
        address="123 Main Street",
        city="Burnsville",
        state="MN",
        zip_code="55337",
        monthly_rent=120000,
    )
    landlord = ExtractedLandlordInfo(name="ABC Properties LLC", address="456 Corporate Blvd")
    notice = EvictionNoticeInfo(
        notice_type="nonpayment",
        date_served=datetime(2025, 11, 20, tzinfo=UTC),
        amount_claimed=150000,
        court_date=datetime(2025, 12, 15, tzinfo=UTC),
        case_number="27-CV-25-12345",
    )
    evidence = [EvidenceItem(document_id="d1", filename="lease.pdf", document_type="lease", description="Lease")]
    timeline = [TimelineEntry(date=datetime(2025, 11, 20, tzinfo=UTC), event_type="notice", title="N", description="")]
    defense = Defense(code="rent_paid", name="Rent Was Paid", description="paid", applicable=True, strength="strong")
    compliance = ComplianceReport(overall_status=ComplianceStatus.COMPLIANT, checks=[], ready_to_file=True)

    case = EvictionCase(
        user_id="GUtest1234",
        case_number="27-CV-25-12345",
        tenant=tenant,
        landlord=landlord,
        notice=notice,
        evidence=evidence,
        timeline=timeline,
        defenses=[defense],
        total_paid=120000,
        total_owed=0,
        compliance=compliance,
        created_at=fixed,
        updated_at=fixed,
    )
    data = case.to_dict()

    assert data["user_id"] == "GUtest1234"
    assert data["case_number"] == "27-CV-25-12345"
    assert data["tenant"]["full_name"] == "Jane Doe"
    assert data["tenant"]["monthly_rent"] == 120000
    assert data["landlord"]["name"] == "ABC Properties LLC"
    assert data["notice"]["type"] == "nonpayment"
    assert data["notice"]["court_date"] == notice.court_date.isoformat()
    assert data["evidence_count"] == 1
    assert data["timeline_count"] == 1
    assert data["defenses"] == [
        {"code": "rent_paid", "name": "Rent Was Paid", "applicable": True, "strength": "strong"}
    ]
    assert data["rent_history_summary"] == {"total_paid": 120000, "total_owed": 0, "payments_count": 0}
    assert data["compliance"]["overall_status"] == "compliant"
    assert data["language"] == "en"
    assert data["created_at"] == fixed.isoformat()


def test_eviction_case_to_dict_empty():
    """EvictionCase.to_dict handles an empty case gracefully."""
    fixed = datetime(2025, 12, 1, tzinfo=UTC)
    case = EvictionCase(user_id="GUtest1234", created_at=fixed, updated_at=fixed)
    data = case.to_dict()

    assert data["user_id"] == "GUtest1234"
    assert data["tenant"] is None
    assert data["landlord"] is None
    assert data["notice"] is None
    assert data["evidence_count"] == 0
    assert data["timeline_count"] == 0
    assert data["defenses"] == []
    assert data["compliance"] is None


# =============================================================================
# Module-Level Constants
# =============================================================================


def test_minnesota_defenses_list():
    """MINNESOTA_DEFENSES is a non-empty list of Defense objects."""
    assert len(MINNESOTA_DEFENSES) > 0
    assert all(isinstance(d, Defense) for d in MINNESOTA_DEFENSES)
    codes = {d.code for d in MINNESOTA_DEFENSES}
    assert "rent_paid" in codes
    assert "habitability" in codes


def test_dakota_county_form_fields():
    """DAKOTA_COUNTY_FORM_FIELDS maps Semptify fields to PDF form names."""
    assert "case_number" in DAKOTA_COUNTY_FORM_FIELDS
    assert DAKOTA_COUNTY_FORM_FIELDS["tenant_name"] == "DefendantName"
    assert DAKOTA_COUNTY_FORM_FIELDS["landlord_name"] == "PlaintiffName"
    assert "defense_habitability" in DAKOTA_COUNTY_FORM_FIELDS


# =============================================================================
# Case Builder Construction
# =============================================================================


def test_eviction_case_builder_init(builder):
    """EvictionCaseBuilder loads the Minnesota defenses at construction."""
    assert len(builder.defenses) == len(MINNESOTA_DEFENSES)
    assert all(isinstance(d, Defense) for d in builder.defenses)


@pytest.mark.anyio
async def test_get_case_builder():
    """get_case_builder returns a fresh EvictionCaseBuilder."""
    builder = await get_case_builder()
    assert isinstance(builder, EvictionCaseBuilder)


# =============================================================================
# Evidence and Timeline Helpers
# =============================================================================


def test_build_evidence_list_and_exhibit_labels(builder):
    """_build_evidence_list assigns exhibit labels and determines relevance."""
    docs = [
        SimpleNamespace(
            id="d1",
            original_filename="lease.pdf",
            document_type="lease",
            description="",
            uploaded_at=datetime(2025, 11, 1, tzinfo=UTC),
        ),
        SimpleNamespace(
            id="d2",
            original_filename="receipt.pdf",
            document_type="rent_receipt",
            description="",
            uploaded_at=datetime(2025, 11, 2, tzinfo=UTC),
        ),
    ]
    evidence = builder._build_evidence_list(docs)

    assert len(evidence) == 2
    assert evidence[0].exhibit_label == "Exhibit A"
    assert evidence[0].relevance == "Establishes terms of tenancy agreement"
    assert evidence[1].exhibit_label == "Exhibit B"
    assert evidence[1].relevance == "Proof of rent payment"


def test_determine_relevance_unknown_type(builder):
    """_determine_relevance returns a generic label for unknown document types."""
    doc = SimpleNamespace(document_type="other")
    assert builder._determine_relevance(doc) == "Supporting evidence"


def test_build_timeline(builder):
    """_build_timeline creates TimelineEntry objects with evidence links."""
    events = [
        SimpleNamespace(
            event_date=datetime(2025, 11, 20, tzinfo=UTC),
            event_type="notice",
            title="14-Day Notice",
            description="Received notice",
            document_id="d1",
        ),
        SimpleNamespace(
            event_date=datetime(2025, 11, 22, tzinfo=UTC),
            event_type="maintenance",
            title="Repair request",
            description="Heating broken",
            document_id=None,
        ),
    ]
    timeline = builder._build_timeline(events, [])

    assert len(timeline) == 2
    assert timeline[0].has_evidence is True
    assert timeline[0].evidence_ids == ["d1"]
    assert timeline[1].has_evidence is False
    assert timeline[1].evidence_ids == []


def test_update_from_calendar_sets_court_date(builder):
    """_update_from_calendar sets notice.court_date from a hearing event."""
    notice = EvictionNoticeInfo(notice_type="nonpayment")
    case = EvictionCase(user_id="u1", notice=notice)
    hearing = SimpleNamespace(event_type="hearing", start_datetime=datetime(2025, 12, 15, 9, 0, tzinfo=UTC))

    builder._update_from_calendar(case, [hearing])

    assert case.notice.court_date == hearing.start_datetime


def test_update_from_calendar_creates_notice_when_missing(builder):
    """_update_from_calendar creates a notice if the case has none."""
    case = EvictionCase(user_id="u1")
    hearing = SimpleNamespace(event_type="hearing", start_datetime=datetime(2025, 12, 15, 9, 0, tzinfo=UTC))

    builder._update_from_calendar(case, [hearing])

    assert case.notice is not None
    assert case.notice.notice_type == "unknown"
    assert case.notice.court_date == hearing.start_datetime


def test_build_rent_history(builder):
    """_build_rent_history converts RentPayment objects to dicts."""
    payments = [
        SimpleNamespace(
            payment_date=datetime(2025, 11, 1, tzinfo=UTC),
            amount=100000,
            status="paid",
            payment_method="check",
            confirmation_number="C1",
        ),
    ]
    history = builder._build_rent_history(payments)

    assert history == [
        {
            "date": payments[0].payment_date.isoformat(),
            "amount": 100000,
            "status": "paid",
            "method": "check",
            "confirmation": "C1",
        },
    ]


# =============================================================================
# Document Extraction Helpers
# =============================================================================


def test_extract_landlord_info(builder):
    """_extract_landlord_info parses landlord name and address from text."""
    text = "Landlord: ABC Properties LLC\n123 Main Street, Burnsville, MN 55337\nPhone: 555-0000"
    doc = SimpleNamespace(
        id="d1",
        document_type="lease",
        extracted_text=text,
        original_filename="lease.pdf",
    )
    landlord = builder._extract_landlord_info([doc])

    assert landlord.name == "Abc Properties Llc"
    assert "123 Main Street" in landlord.address


def test_extract_landlord_info_no_match(builder):
    """_extract_landlord_info returns an empty name when no landlord is found."""
    doc = SimpleNamespace(
        id="d1",
        document_type="rent_receipt",
        extracted_text="Receipt for rent",
        original_filename="receipt.pdf",
    )
    landlord = builder._extract_landlord_info([doc])

    assert landlord.name == ""


def test_extract_notice_info_nonpayment(builder):
    """_extract_notice_info parses a nonpayment notice."""
    text = "non-payment of rent. $1,500.00 in unpaid rent. Served: December 1, 2025."
    doc = SimpleNamespace(
        id="d1",
        document_type="eviction_notice",
        extracted_text=text,
        original_filename="notice.pdf",
        uploaded_at=datetime(2025, 11, 1, tzinfo=UTC),
    )
    notice = builder._extract_notice_info([doc])

    assert notice is not None
    assert notice.notice_type == "nonpayment"
    assert notice.amount_claimed == 150000
    assert notice.date_served == datetime(2025, 12, 1, tzinfo=UTC)


def test_extract_notice_info_lease_violation(builder):
    """_extract_notice_info identifies a lease violation notice."""
    text = "Notice of lease violation for unauthorized pet."
    doc = SimpleNamespace(
        id="d1",
        document_type="notice_to_quit",
        extracted_text=text,
        original_filename="violation.pdf",
        uploaded_at=datetime(2025, 11, 1, tzinfo=UTC),
    )
    notice = builder._extract_notice_info([doc])

    assert notice is not None
    assert notice.notice_type == "lease_violation"


def test_extract_notice_info_no_match(builder):
    """_extract_notice_info returns None when no notice document is present."""
    doc = SimpleNamespace(
        id="d1",
        document_type="photo",
        extracted_text="",
        original_filename="photo.png",
        uploaded_at=datetime(2025, 11, 1, tzinfo=UTC),
    )
    assert builder._extract_notice_info([doc]) is None


@pytest.mark.anyio
async def test_extract_tenant_info_from_lease(builder):
    """_extract_tenant_info parses tenant details from a lease document."""
    user = SimpleNamespace(id="GUtest1234", email="tenant@example.com")
    text = "Tenant: Jane Doe\nProperty Address: 123 Main Street, Burnsville, MN 55337\nMonthly Rent: $1,200"
    doc = SimpleNamespace(
        id="d1",
        user_id="GUtest1234",
        document_type="lease",
        extracted_text=text,
        original_filename="lease.pdf",
        uploaded_at=datetime(2025, 11, 1, tzinfo=UTC),
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [doc]
    session = AsyncMock()
    session.execute.return_value = result

    tenant = await builder._extract_tenant_info(session, user)

    assert tenant.full_name == "Jane Doe"
    assert "123 Main Street" in tenant.address
    assert tenant.city == "Burnsville"
    assert tenant.state == "MN"
    assert tenant.zip_code == "55337"


# =============================================================================
# Defense and Compliance Analysis
# =============================================================================


def test_analyze_defenses_rent_paid(builder):
    """_analyze_defenses flags the rent_paid defense when payments exist."""
    case = EvictionCase(user_id="u1", total_paid=120000, total_owed=0, timeline=[], evidence=[])
    defenses = builder._analyze_defenses(case)

    rent_paid = next(d for d in defenses if d.code == "rent_paid")
    assert rent_paid.applicable is True
    assert rent_paid.strength == "moderate"
    assert "$1200.00" in rent_paid.notes


def test_analyze_defenses_habitability(builder):
    """_analyze_defenses flags the habitability defense with maintenance/photos."""
    timeline = [
        TimelineEntry(date=datetime(2025, 11, 20, tzinfo=UTC), event_type="maintenance", title="r", description="")
    ]
    evidence = [EvidenceItem(document_id="d1", filename="photo.png", document_type="photo", description="")]
    case = EvictionCase(user_id="u1", total_paid=0, total_owed=0, timeline=timeline, evidence=evidence)
    defenses = builder._analyze_defenses(case)

    habitability = next(d for d in defenses if d.code == "habitability")
    assert habitability.applicable is True
    assert habitability.strength == "moderate"


def test_check_compliance_empty_case(builder, monkeypatch, fixed_now):
    """_check_compliance reports errors for an empty case."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)
    case = EvictionCase(user_id="u1")
    report = builder._check_compliance(case)

    assert report.overall_status == ComplianceStatus.ERROR
    assert report.blocking_issues > 0
    assert not report.ready_to_file
    rules = {c.rule: c.status for c in report.checks}
    assert rules["tenant_name_required"] == ComplianceStatus.ERROR
    assert rules["address_required"] == ComplianceStatus.ERROR
    assert rules["landlord_name_required"] == ComplianceStatus.ERROR


def test_check_compliance_compliant(builder, monkeypatch, fixed_now):
    """_check_compliance returns COMPLIANT when all required fields are present."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)
    tenant = ExtractedTenantInfo("Jane Doe", "123 Main Street", "Burnsville", "MN", "55337")
    landlord = ExtractedLandlordInfo("ABC Properties LLC")
    notice = EvictionNoticeInfo("nonpayment", court_date=datetime(2025, 12, 15, tzinfo=UTC))
    evidence = [EvidenceItem("d1", "lease.pdf", "lease", "")]
    case = EvictionCase(
        user_id="u1",
        tenant=tenant,
        landlord=landlord,
        notice=notice,
        evidence=evidence,
        case_number="27-CV-25-12345",
    )
    report = builder._check_compliance(case)

    assert report.overall_status == ComplianceStatus.COMPLIANT
    assert report.blocking_issues == 0
    assert report.warnings == 0
    assert report.ready_to_file is True


def test_check_compliance_past_court_date(builder, monkeypatch, fixed_now):
    """_check_compliance errors when the court date has passed."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)
    tenant = ExtractedTenantInfo("Jane Doe", "123 Main Street", "Burnsville", "MN", "55337")
    landlord = ExtractedLandlordInfo("ABC Properties LLC")
    notice = EvictionNoticeInfo("nonpayment", court_date=datetime(2025, 11, 25, tzinfo=UTC))
    case = EvictionCase(user_id="u1", tenant=tenant, landlord=landlord, notice=notice)
    report = builder._check_compliance(case)

    assert report.overall_status == ComplianceStatus.ERROR
    court_check = next(c for c in report.checks if c.rule == "court_date_required")
    assert court_check.status == ComplianceStatus.ERROR
    assert "passed" in court_check.message


def test_check_compliance_approaching_court_date(builder, monkeypatch, fixed_now):
    """_check_compliance warns when the court date is within 3 days."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)
    tenant = ExtractedTenantInfo("Jane Doe", "123 Main Street", "Burnsville", "MN", "55337")
    landlord = ExtractedLandlordInfo("ABC Properties LLC")
    notice = EvictionNoticeInfo("nonpayment", court_date=datetime(2025, 12, 3, tzinfo=UTC))
    case = EvictionCase(user_id="u1", tenant=tenant, landlord=landlord, notice=notice)
    report = builder._check_compliance(case)

    assert report.overall_status == ComplianceStatus.WARNING
    court_check = next(c for c in report.checks if c.rule == "court_date_required")
    assert court_check.status == ComplianceStatus.WARNING
    assert "in 2 days" in court_check.message


def test_check_compliance_missing_case_number(builder, monkeypatch, fixed_now):
    """_check_compliance warns when a court date is known but the case number is missing."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)
    tenant = ExtractedTenantInfo("Jane Doe", "123 Main Street", "Burnsville", "MN", "55337")
    landlord = ExtractedLandlordInfo("ABC Properties LLC")
    notice = EvictionNoticeInfo("nonpayment", court_date=datetime(2025, 12, 15, tzinfo=UTC))
    evidence = [EvidenceItem("d1", "lease.pdf", "lease", "")]
    case = EvictionCase(user_id="u1", tenant=tenant, landlord=landlord, notice=notice, evidence=evidence)
    report = builder._check_compliance(case)

    assert report.overall_status == ComplianceStatus.WARNING
    assert report.blocking_issues == 0
    assert report.ready_to_file is True
    case_number_check = next(c for c in report.checks if c.rule == "case_number_required")
    assert case_number_check.status == ComplianceStatus.WARNING


# =============================================================================
# Database-Backed Helpers (session mocked)
# =============================================================================


@pytest.mark.anyio
async def test_get_user(builder):
    """_get_user returns the single user from the mocked session."""
    user = SimpleNamespace(id="GUtest1234", email="tenant@example.com")
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session = AsyncMock()
    session.execute.return_value = result

    found = await builder._get_user(session, "GUtest1234")
    assert found is user


@pytest.mark.anyio
async def test_get_documents(builder):
    """_get_documents returns all documents for a user."""
    docs = [SimpleNamespace(id="d1"), SimpleNamespace(id="d2")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = docs
    session = AsyncMock()
    session.execute.return_value = result

    found = await builder._get_documents(session, "GUtest1234")
    assert found == docs


@pytest.mark.anyio
async def test_get_timeline_events(builder):
    """_get_timeline_events returns ordered timeline events."""
    events = [SimpleNamespace(id="t1"), SimpleNamespace(id="t2")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = events
    session = AsyncMock()
    session.execute.return_value = result

    found = await builder._get_timeline_events(session, "GUtest1234")
    assert found == events


@pytest.mark.anyio
async def test_get_calendar_events(builder):
    """_get_calendar_events returns ordered calendar events."""
    events = [SimpleNamespace(id="c1"), SimpleNamespace(id="c2")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = events
    session = AsyncMock()
    session.execute.return_value = result

    found = await builder._get_calendar_events(session, "GUtest1234")
    assert found == events


@pytest.mark.anyio
async def test_get_rent_payments(builder):
    """_get_rent_payments returns ordered payment records."""
    payments = [SimpleNamespace(id="p1"), SimpleNamespace(id="p2")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = payments
    session = AsyncMock()
    session.execute.return_value = result

    found = await builder._get_rent_payments(session, "GUtest1234")
    assert found == payments


# =============================================================================
# build_case Integration (get_db_session monkeypatched)
# =============================================================================


@pytest.mark.anyio
async def test_build_case_integration(monkeypatch, fixed_now):
    """build_case assembles a case from mocked data sources."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)

    user = SimpleNamespace(id="GUtest1234", email="tenant@example.com")
    lease_text = (
        "Tenant: Jane Doe\nProperty Address: 123 Main Street, Burnsville, MN 55337\nLandlord: ABC Properties LLC"
    )
    notice_text = (
        "non-payment of rent. $1,500.00 in unpaid rent. "
        "Served: December 1, 2025. "
        "Landlord: ABC Properties LLC\n"
        "123 Main Street, Burnsville, MN 55337"
    )

    lease_doc = SimpleNamespace(
        id="d1",
        user_id="GUtest1234",
        document_type="lease",
        original_filename="lease.pdf",
        description="",
        uploaded_at=fixed_now,
        extracted_text=lease_text,
    )
    notice_doc = SimpleNamespace(
        id="d2",
        user_id="GUtest1234",
        document_type="eviction_notice",
        original_filename="notice.pdf",
        description="",
        uploaded_at=fixed_now,
        extracted_text=notice_text,
    )
    receipt_doc = SimpleNamespace(
        id="d3",
        user_id="GUtest1234",
        document_type="rent_receipt",
        original_filename="receipt.pdf",
        description="",
        uploaded_at=fixed_now,
        extracted_text="",
    )
    photo_doc = SimpleNamespace(
        id="d4",
        user_id="GUtest1234",
        document_type="photo",
        original_filename="mold.png",
        description="",
        uploaded_at=fixed_now,
        extracted_text="",
    )

    timeline_event = SimpleNamespace(
        id="t1",
        user_id="GUtest1234",
        event_type="maintenance",
        title="Heating broken",
        description="Landlord has not fixed",
        event_date=fixed_now,
        document_id="d4",
    )
    hearing_event = SimpleNamespace(
        id="c1",
        user_id="GUtest1234",
        event_type="hearing",
        title="Court Hearing",
        start_datetime=datetime(2025, 12, 15, 9, 0, tzinfo=UTC),
    )
    paid_payment = SimpleNamespace(
        id="p1",
        user_id="GUtest1234",
        payment_date=fixed_now,
        amount=100000,
        status="paid",
        payment_method="check",
        confirmation_number="C1",
    )
    missed_payment = SimpleNamespace(
        id="p2",
        user_id="GUtest1234",
        payment_date=fixed_now,
        amount=50000,
        status="missed",
        payment_method=None,
        confirmation_number=None,
    )

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    user_result.scalars.return_value.all.return_value = []

    tenant_docs_result = MagicMock()
    tenant_docs_result.scalars.return_value.all.return_value = [lease_doc]

    all_docs_result = MagicMock()
    all_docs_result.scalars.return_value.all.return_value = [notice_doc, receipt_doc, photo_doc]

    timeline_result = MagicMock()
    timeline_result.scalars.return_value.all.return_value = [timeline_event]

    calendar_result = MagicMock()
    calendar_result.scalars.return_value.all.return_value = [hearing_event]

    payments_result = MagicMock()
    payments_result.scalars.return_value.all.return_value = [paid_payment, missed_payment]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            user_result,
            tenant_docs_result,
            all_docs_result,
            timeline_result,
            calendar_result,
            payments_result,
        ]
    )

    @asynccontextmanager
    async def mock_get_db_session():
        yield mock_session

    monkeypatch.setattr(case_builder, "get_db_session", mock_get_db_session)

    builder = EvictionCaseBuilder()
    case = await builder.build_case("GUtest1234", language="en")

    assert case.user_id == "GUtest1234"
    assert case.tenant is not None
    assert case.tenant.full_name == "Jane Doe"
    assert case.tenant.city == "Burnsville"
    assert case.landlord is not None
    assert case.landlord.name == "Abc Properties Llc"
    assert case.notice is not None
    assert case.notice.notice_type == "nonpayment"
    assert case.notice.amount_claimed == 150000
    assert case.notice.court_date == datetime(2025, 12, 15, 9, 0, tzinfo=UTC)
    assert len(case.evidence) == 3
    assert case.evidence[0].exhibit_label == "Exhibit A"
    assert len(case.timeline) == 1
    assert case.timeline[0].has_evidence is True
    assert case.total_paid == 100000
    assert case.total_owed == 50000
    assert any(d.applicable for d in case.defenses)
    assert case.compliance is not None
    assert case.compliance.blocking_issues == 0
    assert case.compliance.ready_to_file is True


@pytest.mark.anyio
async def test_build_case_user_not_found(monkeypatch, fixed_now):
    """build_case handles a missing user without crashing."""
    monkeypatch.setattr(case_builder, "utc_now", lambda: fixed_now)

    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    empty_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=empty_result)

    @asynccontextmanager
    async def mock_get_db_session():
        yield mock_session

    monkeypatch.setattr(case_builder, "get_db_session", mock_get_db_session)

    builder = EvictionCaseBuilder()
    case = await builder.build_case("missing-user", language="en")

    assert case.user_id == "missing-user"
    assert case.tenant is None
    assert case.evidence == []
    assert case.compliance is not None
    assert case.compliance.overall_status == ComplianceStatus.ERROR
    assert not case.compliance.ready_to_file
