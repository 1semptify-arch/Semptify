"""
Unit tests for app.services.eviction.court_procedures.

These tests exercise the public enums, dataclasses, and the CourtProceduresEngine
without requiring a real database. External calls (specifically utc_now) are
replaced with unittest.mock and pytest's monkeypatch.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.services.eviction import court_procedures
from app.services.eviction.court_procedures import (
    CounterclaimType,
    CourtProceduresEngine,
    DefenseCategory,
    MinnesotaEvictionRule,
    MotionTemplate,
    MotionType,
    ObjectionResponse,
    ObjectionType,
    ProcedurePhase,
    ProcedureStep,
    get_procedures_engine,
)


@pytest.fixture(scope="module")
def engine():
    """Create a CourtProceduresEngine once for the test module."""
    return CourtProceduresEngine()


# =============================================================================
# ENUMS
# =============================================================================


class TestMotionTypeEnum:
    """MotionType string-backed enum."""

    @pytest.mark.parametrize(
        "member,expected",
        [
            (MotionType.DISMISS_IMPROPER_SERVICE, "dismiss_improper_service"),
            (MotionType.DISMISS_DEFECTIVE_NOTICE, "dismiss_defective_notice"),
            (MotionType.DISMISS_WRONG_VENUE, "dismiss_wrong_venue"),
            (MotionType.DISMISS_LACK_STANDING, "dismiss_lack_standing"),
            (MotionType.CONTINUANCE, "continuance"),
            (MotionType.STAY_OF_EXECUTION, "stay_of_execution"),
            (MotionType.MOTION_TO_COMPEL, "motion_to_compel"),
            (MotionType.MOTION_FOR_DISCOVERY, "motion_for_discovery"),
            (MotionType.MOTION_TO_QUASH, "motion_to_quash"),
            (MotionType.MOTION_IN_LIMINE, "motion_in_limine"),
            (MotionType.EXPUNGEMENT, "expungement"),
            (MotionType.REDEMPTION, "redemption"),
        ],
    )
    def test_values(self, member, expected):
        """Each member has the expected string value and is reversible."""
        assert member.value == expected
        assert MotionType(expected) is member
        assert isinstance(member, str)


class TestObjectionTypeEnum:
    """ObjectionType string-backed enum."""

    @pytest.mark.parametrize(
        "member,expected",
        [
            (ObjectionType.HEARSAY, "hearsay"),
            (ObjectionType.RELEVANCE, "relevance"),
            (ObjectionType.FOUNDATION, "foundation"),
            (ObjectionType.BEST_EVIDENCE, "best_evidence"),
            (ObjectionType.LEADING_QUESTION, "leading_question"),
            (ObjectionType.SPECULATION, "speculation"),
            (ObjectionType.ARGUMENTATIVE, "argumentative"),
            (ObjectionType.ASKED_AND_ANSWERED, "asked_and_answered"),
            (ObjectionType.BEYOND_SCOPE, "beyond_scope"),
            (ObjectionType.IMPROPER_CHARACTER, "improper_character"),
            (ObjectionType.PAROL_EVIDENCE, "parol_evidence"),
        ],
    )
    def test_values(self, member, expected):
        """Each member has the expected string value and is reversible."""
        assert member.value == expected
        assert ObjectionType(expected) is member


class TestProcedurePhaseEnum:
    """ProcedurePhase string-backed enum."""

    @pytest.mark.parametrize(
        "member,expected",
        [
            (ProcedurePhase.PRE_FILING, "pre_filing"),
            (ProcedurePhase.SUMMONS_SERVICE, "summons_service"),
            (ProcedurePhase.ANSWER_PERIOD, "answer_period"),
            (ProcedurePhase.DISCOVERY, "discovery"),
            (ProcedurePhase.PRE_HEARING_MOTIONS, "pre_hearing_motions"),
            (ProcedurePhase.HEARING, "hearing"),
            (ProcedurePhase.POST_HEARING, "post_hearing"),
            (ProcedurePhase.APPEAL, "appeal"),
            (ProcedurePhase.EXECUTION, "execution"),
        ],
    )
    def test_values(self, member, expected):
        """Each member has the expected string value and is reversible."""
        assert member.value == expected
        assert ProcedurePhase(expected) is member


class TestDefenseCategoryEnum:
    """DefenseCategory string-backed enum."""

    @pytest.mark.parametrize(
        "member,expected",
        [
            (DefenseCategory.PROCEDURAL, "procedural"),
            (DefenseCategory.HABITABILITY, "habitability"),
            (DefenseCategory.RETALIATION, "retaliation"),
            (DefenseCategory.DISCRIMINATION, "discrimination"),
            (DefenseCategory.RENT_ESCROW, "rent_escrow"),
            (DefenseCategory.LEASE_VIOLATION, "lease_violation"),
            (DefenseCategory.PAYMENT, "payment"),
            (DefenseCategory.WAIVER, "waiver"),
            (DefenseCategory.ESTOPPEL, "estoppel"),
        ],
    )
    def test_values(self, member, expected):
        """Each member has the expected string value and is reversible."""
        assert member.value == expected
        assert DefenseCategory(expected) is member


# =============================================================================
# DATACLASSES
# =============================================================================


class TestMinnesotaEvictionRule:
    """MinnesotaEvictionRule dataclass construction."""

    def test_required_fields_and_defaults(self):
        """Required fields are stored; optional fields use sensible defaults."""
        rule = MinnesotaEvictionRule(
            rule_id="test_rule",
            title="Test Rule",
            statute="Minn. Stat. § 000.000",
            summary="A rule for testing.",
        )
        assert rule.rule_id == "test_rule"
        assert rule.title == "Test Rule"
        assert rule.statute == "Minn. Stat. § 000.000"
        assert rule.summary == "A rule for testing."
        assert rule.deadline_days is None
        assert rule.applies_to == []
        assert rule.tenant_action is None
        assert rule.landlord_obligation is None
        assert rule.consequence_if_violated is None

    def test_full_construction(self):
        """All fields can be supplied explicitly."""
        rule = MinnesotaEvictionRule(
            rule_id="notice_14_day",
            title="14-Day Notice",
            statute="Minn. Stat. § 504B.135",
            summary="Landlord must give 14 days notice.",
            deadline_days=14,
            applies_to=[ProcedurePhase.PRE_FILING],
            tenant_action="Pay rent",
            landlord_obligation="Give notice",
            consequence_if_violated="Dismissal",
        )
        assert rule.deadline_days == 14
        assert ProcedurePhase.PRE_FILING in rule.applies_to
        assert rule.tenant_action == "Pay rent"


class TestMotionTemplate:
    """MotionTemplate dataclass construction."""

    def test_construction(self):
        """All required fields are stored."""
        template = MotionTemplate(
            motion_type=MotionType.CONTINUANCE,
            title="Motion for Continuance",
            legal_basis=["Minn. R. Civ. P. 6.02"],
            required_facts=["reason"],
            template_text="MOTION FOR CONTINUANCE",
            supporting_evidence=["record"],
            success_factors=["early request"],
            common_responses=["economic harm"],
        )
        assert template.motion_type is MotionType.CONTINUANCE
        assert template.title == "Motion for Continuance"
        assert template.template_text == "MOTION FOR CONTINUANCE"
        assert "Minn. R. Civ. P. 6.02" in template.legal_basis


class TestObjectionResponse:
    """ObjectionResponse dataclass construction."""

    def test_construction(self):
        """All fields are stored correctly."""
        response = ObjectionResponse(
            objection_type=ObjectionType.HEARSAY,
            definition="Out-of-court statement.",
            when_valid="Offered for truth.",
            how_to_overcome=["party opponent", "business records"],
            example_response="Your Honor, this is not hearsay.",
            supporting_rule="Minn. R. Evid. 801",
        )
        assert response.objection_type is ObjectionType.HEARSAY
        assert response.definition == "Out-of-court statement."
        assert len(response.how_to_overcome) == 2
        assert response.example_response
        assert response.supporting_rule


class TestProcedureStep:
    """ProcedureStep dataclass construction and defaults."""

    def test_construction_and_defaults(self):
        """Required fields are stored and list fields default to empty lists."""
        step = ProcedureStep(
            phase=ProcedurePhase.HEARING,
            step_number=4,
            title="The Hearing",
            description="Present your case.",
        )
        assert step.phase is ProcedurePhase.HEARING
        assert step.step_number == 4
        assert step.title == "The Hearing"
        assert step.deadline is None
        assert step.tenant_tasks == []
        assert step.documents_needed == []
        assert step.tips == []

    def test_optional_fields(self):
        """Optional list fields can be supplied."""
        step = ProcedureStep(
            phase=ProcedurePhase.PRE_FILING,
            step_number=1,
            title="Notice",
            description="Review notice.",
            deadline="14 days",
            tenant_tasks=["read it"],
            documents_needed=["copy"],
            tips=["check dates"],
        )
        assert step.deadline == "14 days"
        assert step.tenant_tasks == ["read it"]
        assert step.documents_needed == ["copy"]
        assert step.tips == ["check dates"]


class TestCounterclaimType:
    """CounterclaimType dataclass construction."""

    def test_construction(self):
        """All required fields are stored."""
        counterclaim = CounterclaimType(
            code="test",
            title="Test Counterclaim",
            legal_basis="Minn. Stat. § 000.000",
            elements_to_prove=["one", "two"],
            damages_available=["rent abatement"],
            evidence_needed=["photos"],
            statute_of_limitations="6 years",
        )
        assert counterclaim.code == "test"
        assert counterclaim.title == "Test Counterclaim"
        assert counterclaim.legal_basis == "Minn. Stat. § 000.000"
        assert counterclaim.elements_to_prove == ["one", "two"]
        assert counterclaim.damages_available == ["rent abatement"]
        assert counterclaim.evidence_needed == ["photos"]
        assert counterclaim.statute_of_limitations == "6 years"


# =============================================================================
# COURT PROCEDURES ENGINE
# =============================================================================


class TestCourtProceduresEngineLoading:
    """Tests that the engine loads the expected static data sets."""

    def test_rules_loaded(self, engine):
        """All Minnesota eviction rules are loaded."""
        rules = engine.get_all_rules()
        assert len(rules) == 8
        assert any(r.rule_id == "notice_14_day" for r in rules)

    def test_motions_loaded(self, engine):
        """All motion templates are loaded."""
        motions = engine.get_all_motions()
        assert len(motions) == 5
        assert any(m.motion_type == MotionType.DISMISS_IMPROPER_SERVICE for m in motions)

    def test_objections_loaded(self, engine):
        """All objection responses are loaded."""
        objections = engine.get_all_objection_responses()
        assert len(objections) == 7
        assert any(o.objection_type == ObjectionType.HEARSAY for o in objections)

    def test_procedure_steps_loaded(self, engine):
        """All procedure steps are loaded and ordered."""
        steps = engine.get_procedure_steps()
        assert len(steps) == 5
        for i, step in enumerate(steps):
            assert step.step_number == i + 1

    def test_counterclaims_loaded(self, engine):
        """All counterclaim types are loaded."""
        counterclaims = engine.get_counterclaim_types()
        assert len(counterclaims) == 5
        assert any(c.code == "breach_habitability" for c in counterclaims)

    def test_defense_strategies_loaded(self, engine):
        """All defense strategy categories are loaded."""
        defenses = engine.get_defense_strategies()
        assert len(defenses) == 4
        assert DefenseCategory.PROCEDURAL in defenses
        assert DefenseCategory.HABITABILITY in defenses
        assert DefenseCategory.RETALIATION in defenses
        assert DefenseCategory.PAYMENT in defenses


class TestCourtProceduresEngineRules:
    """Tests for rule-related public methods."""

    def test_get_rule_found(self, engine):
        """Can retrieve a specific rule by ID."""
        rule = engine.get_rule("notice_14_day")
        assert rule is not None
        assert rule.rule_id == "notice_14_day"
        assert rule.deadline_days == 14
        assert "504B.135" in rule.statute

    def test_get_rule_not_found(self, engine):
        """Missing rule IDs return None."""
        assert engine.get_rule("nonexistent_rule") is None

    @pytest.mark.parametrize(
        "phase,expected_count",
        [
            (ProcedurePhase.PRE_FILING, 3),
            (ProcedurePhase.SUMMONS_SERVICE, 1),
            (ProcedurePhase.ANSWER_PERIOD, 1),
            (ProcedurePhase.DISCOVERY, 0),
            (ProcedurePhase.PRE_HEARING_MOTIONS, 0),
            (ProcedurePhase.HEARING, 2),
            (ProcedurePhase.POST_HEARING, 1),
            (ProcedurePhase.APPEAL, 0),
            (ProcedurePhase.EXECUTION, 1),
        ],
    )
    def test_get_rules_by_phase(self, engine, phase, expected_count):
        """Rules can be filtered by procedure phase."""
        rules = engine.get_rules_by_phase(phase)
        assert len(rules) == expected_count
        assert all(phase in r.applies_to for r in rules)


class TestCourtProceduresEngineMotions:
    """Tests for motion-related public methods."""

    def test_get_motion_template_found(self, engine):
        """Can retrieve a loaded motion template."""
        template = engine.get_motion_template(MotionType.DISMISS_IMPROPER_SERVICE)
        assert template is not None
        assert template.motion_type == MotionType.DISMISS_IMPROPER_SERVICE
        assert template.title
        assert template.template_text
        assert template.legal_basis

    @pytest.mark.parametrize(
        "motion_type",
        [
            MotionType.DISMISS_WRONG_VENUE,
            MotionType.DISMISS_LACK_STANDING,
            MotionType.MOTION_TO_COMPEL,
            MotionType.MOTION_FOR_DISCOVERY,
            MotionType.MOTION_TO_QUASH,
            MotionType.MOTION_IN_LIMINE,
            MotionType.REDEMPTION,
        ],
    )
    def test_get_motion_template_not_loaded(self, engine, motion_type):
        """Motions in the enum that are not loaded return None."""
        assert engine.get_motion_template(motion_type) is None


class TestCourtProceduresEngineObjections:
    """Tests for objection-related public methods."""

    def test_get_objection_response_found(self, engine):
        """Can retrieve a loaded objection response."""
        response = engine.get_objection_response(ObjectionType.HEARSAY)
        assert response is not None
        assert response.objection_type == ObjectionType.HEARSAY
        assert response.definition
        assert len(response.how_to_overcome) > 0
        assert response.example_response

    @pytest.mark.parametrize(
        "objection_type",
        [
            ObjectionType.ARGUMENTATIVE,
            ObjectionType.ASKED_AND_ANSWERED,
            ObjectionType.BEYOND_SCOPE,
            ObjectionType.IMPROPER_CHARACTER,
        ],
    )
    def test_get_objection_response_not_loaded(self, engine, objection_type):
        """Objections in the enum that are not loaded return None."""
        assert engine.get_objection_response(objection_type) is None


class TestCourtProceduresEngineProcedures:
    """Tests for procedure step public methods."""

    def test_get_procedure_steps_all(self, engine):
        """All steps are returned when no phase is supplied."""
        steps = engine.get_procedure_steps()
        assert len(steps) == 5
        phases = {s.phase for s in steps}
        assert ProcedurePhase.PRE_FILING in phases
        assert ProcedurePhase.HEARING in phases

    @pytest.mark.parametrize(
        "phase,expected_title",
        [
            (ProcedurePhase.PRE_FILING, "Notice Period"),
            (ProcedurePhase.SUMMONS_SERVICE, "Service of Summons"),
            (ProcedurePhase.ANSWER_PERIOD, "File Your Answer"),
            (ProcedurePhase.HEARING, "The Hearing"),
            (ProcedurePhase.POST_HEARING, "After the Hearing"),
        ],
    )
    def test_get_procedure_steps_by_phase(self, engine, phase, expected_title):
        """Filtering by phase returns the matching step."""
        steps = engine.get_procedure_steps(phase)
        assert len(steps) == 1
        assert steps[0].phase == phase
        assert steps[0].title == expected_title

    def test_get_procedure_steps_no_match(self, engine):
        """Phases with no steps return an empty list."""
        steps = engine.get_procedure_steps(ProcedurePhase.APPEAL)
        assert steps == []


class TestCourtProceduresEngineCounterclaims:
    """Tests for counterclaim public methods."""

    @pytest.mark.parametrize(
        "code",
        [
            "breach_habitability",
            "retaliation",
            "security_deposit",
            "lockout",
            "housing_code",
        ],
    )
    def test_get_counterclaim(self, engine, code):
        """Each loaded counterclaim can be retrieved by code."""
        counterclaim = engine.get_counterclaim(code)
        assert counterclaim is not None
        assert counterclaim.code == code

    def test_get_counterclaim_not_found(self, engine):
        """Unknown counterclaim codes return None."""
        assert engine.get_counterclaim("missing") is None


class TestCourtProceduresEngineDefenses:
    """Tests for defense strategy public methods."""

    def test_get_defense_strategies_all(self, engine):
        """All loaded defense categories are returned."""
        defenses = engine.get_defense_strategies()
        assert len(defenses) == 4
        assert all(isinstance(v, dict) for v in defenses.values())

    def test_get_defense_strategies_by_category(self, engine):
        """A specific category returns its strategy block."""
        procedural = engine.get_defense_strategies(DefenseCategory.PROCEDURAL)
        assert procedural["name"] == "Procedural Defenses"
        assert "defenses" in procedural
        assert any(d["code"] == "improper_notice" for d in procedural["defenses"])

    def test_get_defense_strategies_missing_category(self, engine):
        """A category with no loaded strategies returns an empty dict."""
        assert engine.get_defense_strategies(DefenseCategory.WAIVER) == {}


class TestCourtProceduresEngineHearing:
    """Tests for hearing and motion generation helpers."""

    def test_get_hearing_checklist(self, engine):
        """Hearing checklist contains the expected sections."""
        checklist = engine.get_hearing_checklist()
        expected_keys = [
            "before_hearing",
            "bring_to_court",
            "during_hearing",
            "what_to_say",
            "after_hearing",
        ]
        for key in expected_keys:
            assert key in checklist
            assert isinstance(checklist[key], list)
            assert len(checklist[key]) > 0


class TestCourtProceduresEngineGenerateMotion:
    """Tests for the generate_motion public method."""

    def _fixed_utc_now(self):
        return datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC)

    def test_generate_motion_with_unittest_mock(self, engine):
        """generate_motion uses a patched utc_now via unittest.mock.patch."""
        with patch("app.services.eviction.court_procedures.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC)

            motion = engine.generate_motion(
                motion_type=MotionType.DISMISS_IMPROPER_SERVICE,
                tenant_name="Jane Doe",
                case_number="27-CV-24-12345",
                facts={
                    "landlord_name": "ABC Properties",
                    "tenant_address": "123 Main St",
                    "tenant_phone": "555-123-4567",
                    "landlord_attorney": "Landlord Attorney",
                    "landlord_address": "456 Oak Ave",
                },
            )

            assert "Jane Doe" in motion
            assert "27-CV-24-12345" in motion
            assert "ABC Properties" in motion
            assert "123 Main St" in motion
            assert "555-123-4567" in motion
            assert "MOTION TO DISMISS FOR IMPROPER SERVICE" in motion
            assert "June 15, 2025" in motion
            assert "Minn. Stat. § 504B.331" in motion
            assert "CERTIFICATE OF SERVICE" in motion
            mock_utc_now.assert_called()

    def test_generate_motion_with_monkeypatch(self, engine, monkeypatch):
        """generate_motion uses a patched utc_now via pytest monkeypatch."""
        monkeypatch.setattr(court_procedures, "utc_now", self._fixed_utc_now)

        motion = engine.generate_motion(
            motion_type=MotionType.STAY_OF_EXECUTION,
            tenant_name="John Smith",
            case_number="27-CV-24-99999",
            facts={"landlord_name": "Bad Landlord LLC"},
        )

        assert "John Smith" in motion
        assert "27-CV-24-99999" in motion
        assert "Bad Landlord LLC" in motion
        assert "MOTION FOR STAY OF EXECUTION OF WRIT" in motion
        assert "June 15, 2025" in motion

    def test_generate_motion_not_found(self, engine):
        """An unknown/unloaded motion type returns a clear error string."""
        result = engine.generate_motion(
            motion_type=MotionType.REDEMPTION,
            tenant_name="No Name",
            case_number="00-CV-00-00000",
            facts={},
        )
        assert "MotionType.REDEMPTION" in result
        assert "not found" in result


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================


class TestGetProceduresEngine:
    """Tests for get_procedures_engine singleton factory."""

    def test_returns_engine_instance(self, monkeypatch):
        """The factory returns a CourtProceduresEngine."""
        monkeypatch.setattr(court_procedures, "_procedures_engine", None)
        engine = get_procedures_engine()
        assert isinstance(engine, CourtProceduresEngine)

    def test_singleton(self, monkeypatch):
        """Repeated calls return the same instance."""
        monkeypatch.setattr(court_procedures, "_procedures_engine", None)
        first = get_procedures_engine()
        second = get_procedures_engine()
        assert first is second

    def test_singleton_caches_engine(self, monkeypatch):
        """The cached engine is reused; creating a separate instance is distinct."""
        monkeypatch.setattr(court_procedures, "_procedures_engine", None)
        from_singleton = get_procedures_engine()
        from_class = CourtProceduresEngine()
        assert from_singleton is not from_class
        assert isinstance(from_class, CourtProceduresEngine)
