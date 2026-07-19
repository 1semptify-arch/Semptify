"""Regression tests for PatternDetectionService.detect_repeated_fees().

Run locally: python -m pytest app/modules/housing_accountability/tests/ -v
"""

from typing import Any

from app.modules.housing_accountability.router import PatternDetectionService


def _service() -> PatternDetectionService:
    return PatternDetectionService()


class TestDetectRepeatedFees:
    def test_no_fee_history_or_evidence_returns_insufficient_data(self):
        result = _service().detect_repeated_fees({"jurisdiction": "MN"})
        assert result["patterns"] == []
        assert result["reason"] == "insufficient_data"

    def test_explicit_fee_history_detects_recurring_late_fees(self):
        data: dict[str, Any] = {
            "jurisdiction": "MN",
            "fee_history": [
                {"type": "late fee", "amount": 50, "date": "2026-06-01"},
                {"type": "late fee", "amount": 50, "date": "2026-06-05"},
                {"type": "late fee", "amount": 50, "date": "2026-06-10"},
            ],
        }
        result = _service().detect_repeated_fees(data)
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "repeated_fees"
        assert result["patterns"][0]["jurisdiction"] == "MN"
        assert result["confidence"] > 0.3

    def test_evidence_data_fallback_extracts_fees(self):
        """The /patterns/detect endpoint passes evidence_data, not fee_history."""
        data: dict[str, Any] = {
            "jurisdiction": "NY",
            "evidence_data": [
                {
                    "document_type": "receipt",
                    "metadata": {
                        "type": "late fee",
                        "amount": "$75.00",
                        "date": "2026-05-01",
                    },
                },
                {
                    "document_type": "receipt",
                    "metadata": {
                        "type": "late fee",
                        "amount": "$75",
                        "date": "2026-05-08",
                    },
                },
            ],
        }
        result = _service().detect_repeated_fees(data)
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "repeated_fees"
        assert result["patterns"][0]["jurisdiction"] == "NY"

    def test_non_recurring_fees_return_no_patterns(self):
        data: dict[str, Any] = {
            "jurisdiction": "MN",
            "fee_history": [
                {"type": "late fee", "amount": 50, "date": "2026-06-01"},
                {"type": "late fee", "amount": 200, "date": "2026-07-01"},
            ],
        }
        result = _service().detect_repeated_fees(data)
        assert result["patterns"] == []
        assert result["reason"] == "no_recurring_patterns_detected"
