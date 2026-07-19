"""Attorney Intake Packet scaffold tests — Forge-compatible.

Run via Forge UI: POST /dev/lab/app.modules.case_builder.router/test
Run locally:     python -m pytest app/modules/case_builder/tests/ -v

These tests validate the _build_attorney_intake_packet() scaffold without
requiring a live server or DB. All tests are pure-function unit tests against
the canonical JSON shape defined in router.py:2501-2601.
"""

from datetime import datetime
from typing import Any

from app.modules.case_builder.router import (
    _build_attorney_intake_packet,
    _sort_chronological,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _empty_case() -> dict[str, Any]:
    """Case dict with no timeline, evidence, or deadlines."""
    return {
        "case_number": None,
        "court": None,
        "case_type": None,
        "status": None,
        "property_address": None,
        "filing_date": None,
        "hearing_date": None,
        "plaintiff": {},
        "defendant": {},
        "dates": {},
        "timeline": [],
        "evidence": [],
        "deadlines": [],
    }


def _full_case() -> dict[str, Any]:
    """Case dict with a complete set of facts."""
    return {
        "case_number": "CV-2026-12345",
        "court": "District Court - Hennepin County",
        "case_type": "eviction",
        "status": "active",
        "property_address": "123 Main St, Minneapolis, MN 55401",
        "filing_date": "2026-06-15",
        "hearing_date": "2026-07-20",
        "plaintiff": {
            "name": "Acme Properties LLC",
            "role": "plaintiff",
            "type": "business",
        },
        "defendant": {
            "name": "Jane Doe",
            "role": "defendant",
            "type": "individual",
            "is_pro_se": True,
        },
        "dates": {
            "filing_date": "2026-06-15",
            "answer_deadline": "2026-07-05",
        },
        "timeline": [
            {
                "date": "2026-06-20",
                "title": "Repair request submitted",
                "description": "Tenant submitted written repair request for heater.",
                "category": "repair",
                "importance": "high",
                "source": "journal",
            },
            {
                "date": "2026-06-10",
                "title": "Lease signed",
                "description": "Original lease signed by both parties.",
                "category": "lease",
                "importance": "high",
                "source": "document",
            },
            {
                "date": "2026-06-25",
                "title": "Notice to vacate received",
                "description": "Landlord served 30-day notice.",
                "category": "notice",
                "importance": "critical",
                "source": "document",
            },
        ],
        "evidence": [
            {
                "title": "Lease Agreement",
                "evidence_type": "contract",
                "date_obtained": "2026-06-10",
                "date_of_event": "2026-06-10",
                "source": "vault",
                "relevance": "core",
                "file_path": "/vault/lease.pdf",
            },
            {
                "title": "Repair Request Email",
                "evidence_type": "communication",
                "date_obtained": "2026-06-20",
                "date_of_event": "2026-06-20",
                "source": "email",
                "relevance": "supporting",
                "file_path": "/vault/repair_email.pdf",
            },
        ],
        "deadlines": [
            {
                "deadline": "2026-07-05",
                "title": "File answer",
                "description": "Respond to eviction complaint.",
                "priority": "critical",
                "status": "pending",
                "completed": False,
            },
            {
                "deadline": "2026-06-01",
                "title": "Submit discovery",
                "description": "Discovery requests served.",
                "priority": "high",
                "status": "completed",
                "completed": True,
            },
        ],
    }


# ---------------------------------------------------------------------------
# _sort_chronological tests
# ---------------------------------------------------------------------------


class TestSortChronological:
    def test_empty_list(self):
        assert _sort_chronological([], "date") == []

    def test_single_item(self):
        items = [{"date": "2026-06-15", "title": "one"}]
        assert _sort_chronological(items, "date") == items

    def test_sorts_ascending_by_date(self):
        items = [
            {"date": "2026-06-25", "title": "c"},
            {"date": "2026-06-10", "title": "a"},
            {"date": "2026-06-20", "title": "b"},
        ]
        result = _sort_chronological(items, "date")
        assert [r["title"] for r in result] == ["a", "b", "c"]

    def test_missing_date_sorts_to_end(self):
        items = [
            {"date": "2026-06-20", "title": "b"},
            {"date": None, "title": "x"},
            {"date": "2026-06-10", "title": "a"},
        ]
        result = _sort_chronological(items, "date")
        assert [r["title"] for r in result] == ["a", "b", "x"]

    def test_non_destructive(self):
        items = [
            {"date": "2026-06-25", "title": "c"},
            {"date": "2026-06-10", "title": "a"},
        ]
        original = list(items)
        _sort_chronological(items, "date")
        assert items == original, "input list must not be mutated"


# ---------------------------------------------------------------------------
# _build_attorney_intake_packet tests
# ---------------------------------------------------------------------------


class TestBuildAttorneyIntakePacket:
    def test_empty_case_returns_expected_shape(self):
        packet = _build_attorney_intake_packet(_empty_case())
        assert packet["packet_type"] == "attorney_intake"
        assert packet["packet_version"] == "0.1.0-scaffold"
        assert "generated_at" in packet
        assert packet["timeline"] == []
        assert packet["evidence_index"] == []
        assert packet["pending_deadlines"] == []
        assert packet["counts"] == {
            "timeline_events": 0,
            "evidence_items": 0,
            "pending_deadlines": 0,
        }

    def test_full_case_case_identification(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        ident = packet["case_identification"]
        assert ident["case_number"] == "CV-2026-12345"
        assert ident["court"] == "District Court - Hennepin County"
        assert ident["case_type"] == "eviction"
        assert ident["status"] == "active"
        assert ident["property_address"] == "123 Main St, Minneapolis, MN 55401"
        assert ident["filing_date"] == "2026-06-15"
        assert ident["hearing_date"] == "2026-07-20"
        assert ident["answer_deadline"] == "2026-07-05"
        assert ident["plaintiff"]["name"] == "Acme Properties LLC"
        assert ident["plaintiff"]["type"] == "business"
        assert ident["defendant"]["name"] == "Jane Doe"
        assert ident["defendant"]["is_pro_se"] is True

    def test_timeline_is_chronological(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        dates = [evt["date"] for evt in packet["timeline"]]
        assert dates == ["2026-06-10", "2026-06-20", "2026-06-25"]

    def test_timeline_preserves_fields(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        first = packet["timeline"][0]
        assert first["title"] == "Lease signed"
        assert first["category"] == "lease"
        assert first["importance"] == "high"
        assert first["source"] == "document"

    def test_evidence_index_labels_sequential(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        labels = [ev["label"] for ev in packet["evidence_index"]]
        assert labels == ["EX-001", "EX-002"]

    def test_evidence_index_preserves_fields(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        first = packet["evidence_index"][0]
        assert first["title"] == "Lease Agreement"
        assert first["evidence_type"] == "contract"
        assert first["date_obtained"] == "2026-06-10"
        assert first["file_path"] == "/vault/lease.pdf"
        assert first["relevance"] == "core"

    def test_pending_deadlines_excludes_completed(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        titles = [d["title"] for d in packet["pending_deadlines"]]
        assert "Submit discovery" not in titles
        assert "File answer" in titles

    def test_pending_deadlines_chronological(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        deadlines = [d["deadline"] for d in packet["pending_deadlines"]]
        assert deadlines == sorted(deadlines)

    def test_counts_match_actual_lengths(self):
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        assert packet["counts"]["timeline_events"] == 3
        assert packet["counts"]["evidence_items"] == 2
        assert packet["counts"]["pending_deadlines"] == 1

    def test_no_recommendations_or_editorializing(self):
        """Packet must contain facts only — no recommendations, summaries, or next steps."""
        case = _full_case()
        packet = _build_attorney_intake_packet(case)
        forbidden_keys = {"recommendations", "summary", "next_steps", "analysis", "advice"}
        for key in forbidden_keys:
            assert key not in packet, f"Packet must not contain '{key}' — facts only"

    def test_generated_at_is_iso_format(self):
        packet = _build_attorney_intake_packet(_empty_case())
        generated_at = packet["generated_at"]
        # Must be parseable as ISO 8601
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        assert parsed is not None

    def test_missing_optional_fields_does_not_raise(self):
        """Case with missing plaintiff/defendant/dates should not raise."""
        case = _empty_case()
        # Remove optional dicts entirely
        case.pop("plaintiff", None)
        case.pop("defendant", None)
        case.pop("dates", None)
        packet = _build_attorney_intake_packet(case)
        assert packet["case_identification"]["plaintiff"] == {
            "name": None,
            "role": None,
            "type": None,
        }
        assert packet["case_identification"]["defendant"]["is_pro_se"] is None

    def test_evidence_label_format_is_zero_padded(self):
        """Evidence labels must be EX-001 format (zero-padded to 3 digits)."""
        case = _empty_case()
        case["evidence"] = [{"title": f"doc{i}", "evidence_type": "test"} for i in range(5)]
        packet = _build_attorney_intake_packet(case)
        labels = [ev["label"] for ev in packet["evidence_index"]]
        assert labels == ["EX-001", "EX-002", "EX-003", "EX-004", "EX-005"]
