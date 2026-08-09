"""
Unit tests for app.services.eviction.court_learning.

These tests exercise the public Enums, dataclasses, and the CourtLearningEngine
without requiring a real database. External dependencies (make_id, utc_now, and
the seed_learning_engine used by the singleton factory) are monkeypatched.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.services.eviction.court_learning import (
    CaseOutcome,
    CaseOutcomeRecord,
    CourtLearningEngine,
    DefenseEffectiveness,
    DefenseOutcomeRecord,
    DefenseSuccessRate,
    JudgePattern,
    LandlordPattern,
    MotionOutcome,
    MotionOutcomeRecord,
    get_learning_engine,
)

FIXED_NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def patched_engine(monkeypatch):
    """Provide a CourtLearningEngine with patched helpers and clean shared state."""
    monkeypatch.setattr(
        "app.services.eviction.court_learning.make_id",
        lambda prefix, length=16: f"{prefix}_testid",
    )
    monkeypatch.setattr(
        "app.services.eviction.court_learning.utc_now",
        lambda: FIXED_NOW,
    )

    # The engine stores outcomes on class-level lists, so reset them for isolation.
    CourtLearningEngine._case_outcomes = []
    CourtLearningEngine._defense_outcomes = []
    CourtLearningEngine._motion_outcomes = []

    yield CourtLearningEngine()

    CourtLearningEngine._case_outcomes = []
    CourtLearningEngine._defense_outcomes = []
    CourtLearningEngine._motion_outcomes = []


# =============================================================================
# Enums
# =============================================================================


def test_case_outcome_enum_values():
    """CaseOutcome should expose the documented outcome values."""
    assert CaseOutcome.PENDING.value == "pending"
    assert CaseOutcome.WON.value == "won"
    assert CaseOutcome.LOST.value == "lost"
    assert CaseOutcome.SETTLED.value == "settled"
    assert CaseOutcome.DISMISSED.value == "dismissed"
    assert CaseOutcome.CONTINUED.value == "continued"
    assert CaseOutcome.DEFAULT.value == "default"
    assert CaseOutcome.UNKNOWN.value == "unknown"


def test_defense_effectiveness_enum_values():
    """DefenseEffectiveness should expose the documented values."""
    assert DefenseEffectiveness.HIGHLY_EFFECTIVE.value == "highly_effective"
    assert DefenseEffectiveness.EFFECTIVE.value == "effective"
    assert DefenseEffectiveness.NEUTRAL.value == "neutral"
    assert DefenseEffectiveness.INEFFECTIVE.value == "ineffective"
    assert DefenseEffectiveness.COUNTERPRODUCTIVE.value == "counterproductive"
    assert DefenseEffectiveness.NOT_USED.value == "not_used"


def test_motion_outcome_enum_values():
    """MotionOutcome should expose the documented values."""
    assert MotionOutcome.GRANTED.value == "granted"
    assert MotionOutcome.DENIED.value == "denied"
    assert MotionOutcome.PARTIALLY_GRANTED.value == "partially_granted"
    assert MotionOutcome.MOOT.value == "moot"
    assert MotionOutcome.PENDING.value == "pending"


# =============================================================================
# Dataclasses
# =============================================================================


def test_case_outcome_record_defaults(patched_engine):
    """CaseOutcomeRecord should use sensible defaults and patched helpers."""
    record = CaseOutcomeRecord()
    assert record.id == "cout_testid"
    assert record.user_id == ""
    assert record.case_number == ""
    assert record.county == "Dakota"
    assert record.outcome == CaseOutcome.PENDING
    assert record.created_at == FIXED_NOW
    assert record.defenses_used == []
    assert record.motions_filed == []


def test_dataclasses_accept_explicit_values():
    """All public dataclasses should accept and store explicit field values."""
    case = CaseOutcomeRecord(
        id="cout_explicit",
        user_id="U1",
        case_number="25-CV-1234",
        outcome=CaseOutcome.WON,
    )
    assert case.id == "cout_explicit"
    assert case.outcome == CaseOutcome.WON

    defense = DefenseOutcomeRecord(
        id="def_explicit",
        case_outcome_id="cout_explicit",
        defense_code="habitability",
        effectiveness=DefenseEffectiveness.HIGHLY_EFFECTIVE,
        judge_response="Accepted",
        notes="Strong defense",
    )
    assert defense.effectiveness == DefenseEffectiveness.HIGHLY_EFFECTIVE

    motion = MotionOutcomeRecord(
        id="mot_explicit",
        case_outcome_id="cout_explicit",
        motion_type="motion_to_dismiss",
        outcome=MotionOutcome.GRANTED,
        filed_date=FIXED_NOW,
        decided_date=FIXED_NOW,
        judge_name="Judge Test",
        reasoning="Defective notice",
    )
    assert motion.outcome == MotionOutcome.GRANTED

    rate = DefenseSuccessRate(
        defense_code="code",
        defense_name="Code Name",
        total_uses=10,
        wins=5,
        partial_wins=2,
        losses=3,
        win_rate=0.6,
        confidence="medium",
        avg_settlement_savings_cents=10000,
        notes="Test note",
    )
    assert rate.confidence == "medium"

    judge = JudgePattern(
        judge_name="Judge Test",
        total_cases=5,
        tenant_win_rate=0.4,
        favored_defenses=["improper_notice", "habitability"],
        motion_grant_rate=0.5,
        avg_days_to_decision=12,
        notes="Test judge",
    )
    assert judge.favored_defenses == ["improper_notice", "habitability"]

    landlord = LandlordPattern(
        landlord_name="Big Landlord LLC",
        total_cases=5,
        settlement_rate=0.2,
        avg_settlement_percent=0.5,
        common_violations=["notice"],
        typical_attorney="Lawyer X",
        notes="Test landlord",
    )
    assert landlord.typical_attorney == "Lawyer X"


# =============================================================================
# Recording outcomes
# =============================================================================


@pytest.mark.anyio
async def test_record_case_outcome(patched_engine):
    """record_case_outcome should create and store a CaseOutcomeRecord."""
    record = await patched_engine.record_case_outcome(
        user_id="U123",
        case_number="25-CV-1234",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice", "habitability"],
        primary_defense="improper_notice",
        served_date=datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC),
    )

    assert record.id == "cout_testid"
    assert record.user_id == "U123"
    assert record.case_number == "25-CV-1234"
    assert record.outcome == CaseOutcome.WON
    assert record.defenses_used == ["improper_notice", "habitability"]
    assert record.primary_defense == "improper_notice"
    assert record.outcome_date == FIXED_NOW
    assert record.county == "Dakota"
    assert record.days_to_resolution == 5
    assert record.created_at == FIXED_NOW
    assert len(CourtLearningEngine._case_outcomes) == 1


@pytest.mark.anyio
async def test_record_case_outcome_with_kwargs(patched_engine):
    """record_case_outcome should pass extra kwargs to CaseOutcomeRecord."""
    record = await patched_engine.record_case_outcome(
        user_id="U124",
        case_number="25-CV-9999",
        outcome=CaseOutcome.SETTLED,
        defenses_used=["payment"],
        primary_defense="payment",
        county="Hennepin",
        amount_claimed_cents=100000,
        settlement_amount_cents=60000,
        landlord_type="corporate",
        landlord_attorney="Law Offices X",
        judge_name="Judge Test",
        notice_type="14-day",
    )

    assert record.county == "Hennepin"
    assert record.amount_claimed_cents == 100000
    assert record.settlement_amount_cents == 60000
    assert record.landlord_attorney == "Law Offices X"
    assert record.judge_name == "Judge Test"
    assert record.notice_type == "14-day"
    assert record.days_to_resolution is None


@pytest.mark.anyio
async def test_record_defense_effectiveness(patched_engine):
    """record_defense_effectiveness should create a DefenseOutcomeRecord."""
    case = await patched_engine.record_case_outcome(
        user_id="U1",
        case_number="25-CV-0001",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice"],
    )

    defense_record = await patched_engine.record_defense_effectiveness(
        case_outcome_id=case.id,
        defense_code="improper_notice",
        effectiveness=DefenseEffectiveness.HIGHLY_EFFECTIVE,
        judge_response="Well received",
        notes="Key to victory",
    )

    assert defense_record.id == "def_testid"
    assert defense_record.case_outcome_id == case.id
    assert defense_record.defense_code == "improper_notice"
    assert defense_record.effectiveness == DefenseEffectiveness.HIGHLY_EFFECTIVE
    assert defense_record.judge_response == "Well received"
    assert len(CourtLearningEngine._defense_outcomes) == 1


@pytest.mark.anyio
async def test_record_motion_outcome(patched_engine):
    """record_motion_outcome should create a MotionOutcomeRecord."""
    case = await patched_engine.record_case_outcome(
        user_id="U1",
        case_number="25-CV-0002",
        outcome=CaseOutcome.WON,
        defenses_used=["procedural"],
    )

    motion_record = await patched_engine.record_motion_outcome(
        case_outcome_id=case.id,
        motion_type="motion_to_dismiss",
        outcome=MotionOutcome.GRANTED,
        judge_name="Judge Test",
        reasoning="Notice defect cured by motion",
    )

    assert motion_record.id == "mot_testid"
    assert motion_record.case_outcome_id == case.id
    assert motion_record.motion_type == "motion_to_dismiss"
    assert motion_record.outcome == MotionOutcome.GRANTED
    assert motion_record.decided_date == FIXED_NOW
    assert motion_record.judge_name == "Judge Test"
    assert len(CourtLearningEngine._motion_outcomes) == 1


# =============================================================================
# Defense success rates
# =============================================================================


@pytest.mark.anyio
async def test_get_defense_success_rates(patched_engine):
    """get_defense_success_rates should aggregate wins, losses, and partials."""
    for i in range(5):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"imp-win-{i}",
            outcome=CaseOutcome.WON,
            defenses_used=["improper_notice"],
            county="TestCounty",
        )

    await patched_engine.record_case_outcome(
        user_id="U",
        case_number="imp-dismiss",
        outcome=CaseOutcome.DISMISSED,
        defenses_used=["improper_notice"],
        county="TestCounty",
    )

    for i in range(3):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"imp-loss-{i}",
            outcome=CaseOutcome.LOST,
            defenses_used=["improper_notice"],
            county="TestCounty",
        )

    for i in range(2):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"hab-settle-{i}",
            outcome=CaseOutcome.SETTLED,
            defenses_used=["habitability"],
            amount_claimed_cents=100000,
            settlement_amount_cents=60000 if i == 0 else 70000,
            county="TestCounty",
        )

    # This case is in a different county and should be ignored.
    await patched_engine.record_case_outcome(
        user_id="U",
        case_number="other-county",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice"],
        county="OtherCounty",
    )

    rates = await patched_engine.get_defense_success_rates(county="TestCounty", min_cases=3)
    codes = [r.defense_code for r in rates]

    # improper_notice has 9 uses; habitability only has 2, so it is filtered out.
    assert "improper_notice" in codes
    assert "habitability" not in codes

    improper = next(r for r in rates if r.defense_code == "improper_notice")
    assert improper.defense_name == "Improper Notice"
    assert improper.total_uses == 9
    assert improper.wins == 6  # 5 won + 1 dismissed
    assert improper.partial_wins == 0
    assert improper.losses == 3
    assert improper.win_rate == round(6 / 9, 3)
    assert improper.confidence == "low"
    assert improper.avg_settlement_savings_cents is None


@pytest.mark.anyio
async def test_defense_success_rate_confidence_and_settlement_savings(patched_engine):
    """Confidence and average settlement savings should be calculated correctly."""
    for i in range(20):
        if i < 7:
            outcome = CaseOutcome.WON
            settlement = None
        elif i < 17:
            outcome = CaseOutcome.SETTLED
            settlement = 50000 if i < 12 else 30000
        else:
            outcome = CaseOutcome.LOST
            settlement = None

        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"pay-{i}",
            outcome=outcome,
            defenses_used=["payment"],
            amount_claimed_cents=100000,
            settlement_amount_cents=settlement,
            county="SavingsCounty",
        )

    rates = await patched_engine.get_defense_success_rates(county="SavingsCounty", min_cases=3)
    payment = next(r for r in rates if r.defense_code == "payment")

    assert payment.total_uses == 20
    assert payment.wins == 7
    assert payment.partial_wins == 10
    assert payment.losses == 3
    # win_rate = (wins + 0.5 * partial) / total = (7 + 5) / 20
    assert payment.win_rate == 0.6
    # 20 uses gives high confidence.
    assert payment.confidence == "high"
    # avg savings = (5 * (100000 - 50000) + 5 * (100000 - 30000)) // 10
    assert payment.avg_settlement_savings_cents == 60000


# =============================================================================
# Judge and landlord patterns
# =============================================================================


@pytest.mark.anyio
async def test_get_judge_patterns(patched_engine):
    """get_judge_patterns should aggregate per-judge statistics."""
    for i in range(4):
        outcome = CaseOutcome.WON if i < 2 else CaseOutcome.LOST
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"judge-{i}",
            outcome=outcome,
            defenses_used=["improper_notice", "habitability"],
            judge_name="Judge Test",
            county="JudgeCounty",
            served_date=datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC),
        )

    # Different county with the same judge should be ignored.
    await patched_engine.record_case_outcome(
        user_id="U",
        case_number="judge-other-county",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice"],
        judge_name="Judge Test",
        county="OtherCounty",
    )

    # Different judge in the same county with fewer than 3 cases should be ignored.
    await patched_engine.record_case_outcome(
        user_id="U",
        case_number="other-judge",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice"],
        judge_name="Judge Other",
        county="JudgeCounty",
    )

    patterns = await patched_engine.get_judge_patterns(county="JudgeCounty")
    assert len(patterns) == 1

    pattern = patterns[0]
    assert pattern.judge_name == "Judge Test"
    assert pattern.total_cases == 4
    assert pattern.tenant_win_rate == 0.5
    assert pattern.favored_defenses == ["improper_notice", "habitability"]
    assert pattern.avg_days_to_decision == 5
    assert pattern.motion_grant_rate == 0.5  # placeholder value in source


@pytest.mark.anyio
async def test_get_landlord_patterns(patched_engine):
    """get_landlord_patterns should aggregate per-landlord settlement behavior."""
    for i in range(3):
        outcome = CaseOutcome.SETTLED if i < 2 else CaseOutcome.LOST
        settlement = 60000 if i == 0 else 80000
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"ll-{i}",
            outcome=outcome,
            defenses_used=["payment"],
            landlord_type="property_management",
            landlord_attorney="Lawyer X",
            amount_claimed_cents=100000,
            settlement_amount_cents=settlement if outcome == CaseOutcome.SETTLED else None,
            county="LandlordCounty",
        )

    patterns = await patched_engine.get_landlord_patterns()
    assert len(patterns) == 1

    pattern = patterns[0]
    assert pattern.landlord_name == "Lawyer X"
    assert pattern.total_cases == 3
    assert pattern.settlement_rate == round(2 / 3, 3)
    assert pattern.avg_settlement_percent == 0.7
    assert pattern.typical_attorney == "Lawyer X"
    assert pattern.common_violations == []


@pytest.mark.anyio
async def test_get_landlord_patterns_filtered(patched_engine):
    """get_landlord_patterns should filter by landlord name when requested."""
    for i in range(2):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"ll-x-{i}",
            outcome=CaseOutcome.SETTLED,
            defenses_used=[],
            landlord_type="corporate",
            landlord_attorney="Lawyer X",
            amount_claimed_cents=100000,
            settlement_amount_cents=60000,
            county="LandlordCounty",
        )

    for i in range(3):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"ll-y-{i}",
            outcome=CaseOutcome.LOST,
            defenses_used=[],
            landlord_type="individual",
            landlord_attorney="Lawyer Y",
            county="LandlordCounty",
        )

    patterns = await patched_engine.get_landlord_patterns(landlord_name="Lawyer Y")
    assert len(patterns) == 1
    assert patterns[0].landlord_name == "Lawyer Y"
    assert patterns[0].settlement_rate == 0.0


# =============================================================================
# Strategy recommendations
# =============================================================================


@pytest.mark.anyio
async def test_get_recommended_strategy(patched_engine):
    """get_recommended_strategy should combine defense, judge, and landlord data."""
    # Defense rates in the default county (Dakota).
    for i in range(5):
        outcome = CaseOutcome.WON if i < 4 else CaseOutcome.LOST
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"rec-imp-{i}",
            outcome=outcome,
            defenses_used=["improper_notice"],
            county="Dakota",
        )

    for i in range(3):
        outcome = CaseOutcome.WON if i == 0 else CaseOutcome.LOST
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"rec-hab-{i}",
            outcome=outcome,
            defenses_used=["habitability"],
            county="Dakota",
        )

    # Judge pattern data.
    for i in range(3):
        outcome = CaseOutcome.WON if i < 2 else CaseOutcome.SETTLED
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"rec-judge-{i}",
            outcome=outcome,
            defenses_used=["improper_notice"],
            judge_name="Judge Test",
            county="Dakota",
        )

    # Landlord pattern data.
    for i in range(2):
        await patched_engine.record_case_outcome(
            user_id="U",
            case_number=f"rec-ll-{i}",
            outcome=CaseOutcome.SETTLED,
            defenses_used=[],
            landlord_type="corporate",
            landlord_attorney="Big Landlord LLC",
            amount_claimed_cents=100000,
            settlement_amount_cents=60000 if i == 0 else 50000,
            county="Dakota",
        )

    recommendation = await patched_engine.get_recommended_strategy(
        notice_type="14-day",
        amount_claimed_cents=150000,
        available_defenses=["procedural", "improper_notice", "habitability"],
        judge_name="Judge Test",
        landlord_name="Big Landlord LLC",
    )

    assert recommendation["primary_defense"] == "improper_notice"
    assert recommendation["secondary_defenses"] == ["procedural", "habitability"]
    assert "motion_to_dismiss" in recommendation["motions_to_consider"]
    assert recommendation["settlement_likelihood"] == 1.0
    assert recommendation["expected_outcome"] == "unknown"
    # 5 + 3 + 3 + 2 = 13 cases recorded, so confidence stays low.
    assert recommendation["confidence"] == "low"

    notes = recommendation["notes"]
    assert any("Judge Test" in note and "tenant-favorable" in note for note in notes)
    assert any("improper_notice" in note for note in notes)
    assert any("settles" in note and "claimed amount" in note for note in notes)


@pytest.mark.anyio
async def test_get_recommended_strategy_no_data(patched_engine):
    """With no learning data, the engine should return a low-confidence baseline."""
    recommendation = await patched_engine.get_recommended_strategy(
        notice_type="nonpayment",
        amount_claimed_cents=0,
        available_defenses=["procedural", "habitability"],
    )

    assert recommendation["primary_defense"] == "procedural"  # first available at baseline 0.4
    assert recommendation["secondary_defenses"] == ["habitability"]
    assert recommendation["motions_to_consider"] == []
    assert recommendation["settlement_likelihood"] == 0.0
    assert recommendation["expected_outcome"] == "unknown"
    assert recommendation["confidence"] == "low"
    assert recommendation["notes"] == []


# =============================================================================
# Learning stats
# =============================================================================


@pytest.mark.anyio
async def test_get_learning_stats(patched_engine):
    """get_learning_stats should summarize all recorded learning data."""
    case = await patched_engine.record_case_outcome(
        user_id="U1",
        case_number="25-CV-1000",
        outcome=CaseOutcome.WON,
        defenses_used=["improper_notice"],
        county="Dakota",
    )

    await patched_engine.record_case_outcome(
        user_id="U2",
        case_number="25-CV-1001",
        outcome=CaseOutcome.LOST,
        defenses_used=["habitability"],
        county="Hennepin",
    )

    await patched_engine.record_defense_effectiveness(
        case_outcome_id=case.id,
        defense_code="improper_notice",
        effectiveness=DefenseEffectiveness.EFFECTIVE,
    )

    await patched_engine.record_motion_outcome(
        case_outcome_id=case.id,
        motion_type="motion_to_dismiss",
        outcome=MotionOutcome.GRANTED,
    )

    stats = await patched_engine.get_learning_stats()
    assert stats["total_cases_recorded"] == 2
    assert stats["total_defense_outcomes"] == 1
    assert stats["total_motion_outcomes"] == 1
    assert set(stats["counties_covered"]) == {"Dakota", "Hennepin"}
    assert stats["date_range"]["earliest"] == FIXED_NOW
    assert stats["date_range"]["latest"] == FIXED_NOW


@pytest.mark.anyio
async def test_get_learning_stats_empty(patched_engine):
    """get_learning_stats should return None for date_range when no cases exist."""
    stats = await patched_engine.get_learning_stats()
    assert stats["total_cases_recorded"] == 0
    assert stats["total_defense_outcomes"] == 0
    assert stats["total_motion_outcomes"] == 0
    assert stats["counties_covered"] == []
    assert stats["date_range"] is None


# =============================================================================
# Dependency injection
# =============================================================================


@pytest.mark.anyio
async def test_get_learning_engine(monkeypatch):
    """get_learning_engine should create a singleton and seed it once."""
    mock_seed = AsyncMock()
    monkeypatch.setattr(
        "app.services.eviction.seed_court_data.seed_learning_engine",
        mock_seed,
    )
    monkeypatch.setattr(
        "app.services.eviction.court_learning._learning_engine",
        None,
    )
    monkeypatch.setattr(
        "app.services.eviction.court_learning._seeded",
        False,
    )

    engine = await get_learning_engine()
    assert isinstance(engine, CourtLearningEngine)
    mock_seed.assert_awaited_once_with(engine, num_cases=200)

    second_engine = await get_learning_engine()
    assert second_engine is engine
    assert mock_seed.await_count == 1
