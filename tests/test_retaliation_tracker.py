"""Retaliation tracker — correlation, assessment, and document suggestions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.services.retaliation_tracker import (
    ADVERSE_SUBTYPES,
    PROTECTED_SUBTYPES,
    assess,
    correlate,
    suggest_from_documents,
)


@dataclass
class FakeEvent:
    """Minimal stand-in for a TimelineEvent row (no DB needed)."""

    id: str
    event_type: str
    title: str
    event_date: datetime
    tags: str | None = None
    description: str | None = None
    urgency: str = "normal"
    attached_document_ids: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.tags, list):
            self.tags = json.dumps(self.tags)
        if isinstance(self.attached_document_ids, list):
            self.attached_document_ids = json.dumps(self.attached_document_ids)


def _protected(idx: int, subtype: str, date: datetime, docs: list[str] | None = None) -> FakeEvent:
    return FakeEvent(
        id=f"p{idx}",
        event_type="protected_action",
        title=f"protected {idx}",
        event_date=date,
        tags=[subtype],
        attached_document_ids=docs or [],
    )


def _adverse(idx: int, subtype: str, date: datetime, docs: list[str] | None = None) -> FakeEvent:
    return FakeEvent(
        id=f"a{idx}",
        event_type="adverse_action",
        title=f"adverse {idx}",
        event_date=date,
        tags=[subtype],
        attached_document_ids=docs or [],
    )


def test_correlate_pairs_adverse_to_nearest_prior_protected():
    base = datetime(2026, 1, 1)
    result = correlate(
        [
            _protected(1, "repair_request", base),
            _adverse(1, "rent_increase", base + timedelta(days=10)),
        ],
        jurisdiction="MN",
        now=base + timedelta(days=10),
    )
    assert len(result["pairs"]) == 1
    pair = result["pairs"][0]
    assert pair["days_between"] == 10
    assert pair["in_strong_window"] is True
    assert pair["in_presumption_window"] is True
    assert pair["presumption_days"] == 90


def test_correlate_unknown_jurisdiction_never_invents_statute():
    base = datetime(2026, 1, 1)
    result = correlate(
        [_protected(1, "repair_request", base), _adverse(1, "lockout", base + timedelta(days=5))],
        jurisdiction="atlantis",
        now=base,
    )
    assert result["presumption"]["statute"] is None
    assert result["presumption"]["days"] is None
    assert result["pairs"][0]["in_presumption_window"] is False


def test_correlate_unmatched_adverse_has_no_prior_protected():
    base = datetime(2026, 1, 1)
    result = correlate(
        [_adverse(1, "eviction_notice", base), _protected(1, "legal_consult", base + timedelta(days=3))],
        jurisdiction="MN",
        now=base + timedelta(days=3),
    )
    assert len(result["pairs"]) == 0
    assert len(result["unmatched_adverse"]) == 1


def test_assess_reports_elements_and_gaps():
    base = datetime(2026, 1, 1)
    result = correlate(
        [
            _protected(1, "repair_request", base, docs=["doc1"]),
            _protected(2, "agency_complaint", base + timedelta(days=2)),
            _adverse(1, "eviction_notice", base + timedelta(days=20), docs=["doc2"]),
        ],
        jurisdiction="MN",
        now=base + timedelta(days=20),
    )
    a = assess(result, jurisdiction="MN")
    assert a["present_count"] >= 4
    assert a["present_count"] == len([e for e in a["elements"] if e["present"]])
    assert a["total_count"] == len(a["elements"])
    keys = {e["key"] for e in a["elements"]}
    assert keys == {
        "protected_documented",
        "adverse_documented",
        "proximity_flagged",
        "documents_attached",
        "pattern_multiple",
        "open_window",
    }
    assert a["gaps"] == [e["key"] for e in a["elements"] if not e["present"]]
    assert a["note"]  # always carries the not-a-legal-conclusion note


def test_assess_empty_record_lists_everything_missing():
    result = correlate([], jurisdiction="MN", now=datetime(2026, 1, 1))
    a = assess(result, jurisdiction="MN")
    assert a["present_count"] == 0
    assert len(a["gaps"]) == a["total_count"]
    assert a["guidance"]  # missing-everything record still gets guidance


def test_suggest_from_documents_maps_recognized_types():
    suggestions = suggest_from_documents(
        [
            {"id": "d1", "doc_type": "eviction_notice", "title": "Notice", "date": "2026-02-01"},
            {"id": "d2", "doc_type": "repair_request", "title": "Fix sink"},
            {"id": "d3", "doc_type": "lease", "title": "Lease"},
        ]
    )
    assert len(suggestions) == 2
    by_id = {s["document_id"]: s for s in suggestions}
    assert by_id["d1"]["suggested_event_type"] == "adverse_action"
    assert by_id["d1"]["suggested_subtype"] == "eviction_notice"
    assert by_id["d1"]["subtype_label"] == ADVERSE_SUBTYPES["eviction_notice"]
    assert by_id["d2"]["suggested_event_type"] == "protected_action"
    assert by_id["d2"]["suggested_subtype"] == "repair_request"
    assert by_id["d2"]["subtype_label"] == PROTECTED_SUBTYPES["repair_request"]
    # unmapped types are skipped, not guessed
    assert "d3" not in by_id


def test_suggest_from_documents_resolves_mapped_subtype_labels():
    for s in suggest_from_documents([{"id": "x", "doc_type": "non_renewal"}]):
        assert s["suggested_subtype"] in ADVERSE_SUBTYPES
        assert s["subtype_label"] == ADVERSE_SUBTYPES[s["suggested_subtype"]]
