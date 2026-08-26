"""FCA/Qui Tam case readiness unit tests.

Pure-function tests for the issue-spotting checklist, score, and packet export.
No live storage or database required.
"""

import io
import json
import zipfile
from typing import Any

from app.core.upl_guardrails import UPL_DISCLAIMER
from app.modules.case_builder.fca_packet_export import build_fca_readiness_pdf, build_fca_readiness_zip
from app.modules.case_builder.fca_service import (
    build_default_checklist,
    build_readiness_summary,
    calculate_readiness_score,
    get_referral_resources,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_case() -> dict[str, Any]:
    return {
        "case_id": "123",
        "narrative": "",
        "harm_description": "",
        "timeline": [],
        "exhibit_refs": [],
        "readiness_checklist": [],
        "created_at": "2026-08-26T00:00:00",
    }


def _sample_checklist() -> list[dict]:
    return [
        {"id": "fca_001", "framework": "false_claims_act", "label": "Identify false claim", "required": True, "completed": True, "notes": ""},
        {"id": "fca_002", "framework": "false_claims_act", "label": "Program", "required": True, "completed": False, "notes": ""},
        {"id": "fh_001", "framework": "fair_housing", "label": "Protected class", "required": True, "completed": True, "notes": ""},
        {"id": "fh_002", "framework": "fair_housing", "label": "Comparison", "required": False, "completed": False, "notes": ""},
    ]


def _full_case() -> dict[str, Any]:
    return {
        "case_id": "456",
        "narrative": "Landlord served notice after we asked for repairs.",
        "harm_description": "Facing eviction.",
        "timeline": [
            {"date": "2026-01-05", "description": "Repair request sent", "source": "email"},
            {"date": "2026-01-20", "description": "Notice to vacate received", "source": "notice"},
        ],
        "exhibit_refs": ["doc_001", "doc_002"],
        "readiness_checklist": _sample_checklist(),
        "created_at": "2026-08-26T00:00:00",
    }


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


def test_default_checklist_includes_three_frameworks():
    checklist = build_default_checklist()
    frameworks = {item["framework"] for item in checklist}
    assert "false_claims_act" in frameworks
    assert "fair_housing" in frameworks
    assert "mn_anti_retaliation" in frameworks
    assert all(item.get("id") for item in checklist)
    assert all(item.get("label") for item in checklist)


def test_default_checklist_filtered_by_framework():
    checklist = build_default_checklist(["fair_housing"])
    assert all(item["framework"] in ("fair_housing", "cross_cutting") for item in checklist)


def test_calculate_readiness_score():
    checklist = _sample_checklist()
    # 2 of 3 required completed -> 66.67% truncated to 66
    assert calculate_readiness_score(checklist) == 66


def test_calculate_readiness_score_empty():
    assert calculate_readiness_score([]) == 0


def test_build_readiness_summary():
    summary = build_readiness_summary(_sample_checklist(), "Narrative present")
    assert summary["score"] == 66
    assert summary["total_items"] == 4
    assert summary["completed_items"] == 2
    assert summary["missing_required_count"] == 1
    assert summary["narrative_present"] is True
    assert "by_framework" in summary


def test_referral_resources_present():
    resources = get_referral_resources()
    assert len(resources) > 0
    assert all(r.get("name") and r.get("description") for r in resources)


# ---------------------------------------------------------------------------
# Packet export tests
# ---------------------------------------------------------------------------


def test_build_fca_readiness_pdf_bytes():
    case = _full_case()
    pdf_bytes = build_fca_readiness_pdf(case)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_build_fca_readiness_zip():
    case = _full_case()
    zip_bytes, filename = build_fca_readiness_zip(case)
    assert isinstance(zip_bytes, bytes)
    assert filename.startswith("fca-readiness-")
    assert filename.endswith(".zip")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "fca_readiness_packet.pdf" in names
        assert "fca_readiness_summary.json" in names

        summary = json.loads(zf.read("fca_readiness_summary.json"))
        assert summary["disclaimer"] == UPL_DISCLAIMER
        assert summary["readiness_score"] == 66
        assert summary["narrative_present"] is True


def test_build_fca_readiness_pdf_empty_case():
    case = _empty_case()
    pdf_bytes = build_fca_readiness_pdf(case)
    assert pdf_bytes.startswith(b"%PDF")
