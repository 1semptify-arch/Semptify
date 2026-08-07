"""Housing-pattern analysis workflows for tenant advocacy."""

from typing import Any


def detect_repeated_fees(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect recurring fees that appear across multiple tenant records."""
    fee_counts: dict[str, int] = {}
    for record in records:
        fee_type = record.get("fee_type")
        if fee_type:
            fee_counts[str(fee_type)] = fee_counts.get(str(fee_type), 0) + 1
    return [
        {"fee_type": fee, "count": count, "pattern": "repeated_fee"} for fee, count in fee_counts.items() if count >= 2
    ]


def detect_eviction_patterns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect eviction-related patterns across tenant records."""
    return [
        {
            "pattern": "eviction_pattern",
            "tenant_id": record.get("tenant_id"),
            "event": record.get("event"),
            "date": record.get("date"),
        }
        for record in records
        if "eviction" in str(record.get("event", "")).lower()
    ]


def detect_subsidy_interference(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect landlord actions that may interfere with housing subsidy programs."""
    return [
        {
            "pattern": "subsidy_interference",
            "tenant_id": record.get("tenant_id"),
            "event": record.get("event"),
            "date": record.get("date"),
        }
        for record in records
        if any(
            kw in str(record.get("event", "")).lower() for kw in ("section 8", "voucher", "subsidy", "housing choice")
        )
    ]


def detect_court_order_violations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect potential violations of court orders or settlement terms."""
    return [
        {
            "pattern": "court_order_violation",
            "tenant_id": record.get("tenant_id"),
            "event": record.get("event"),
            "date": record.get("date"),
        }
        for record in records
        if any(
            kw in str(record.get("event", "")).lower()
            for kw in ("court order", "settlement", "injunction", "violation")
        )
    ]


def generate_pattern_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a summary of all detected patterns across tenant records."""
    return {
        "repeated_fees": detect_repeated_fees(records),
        "eviction_patterns": detect_eviction_patterns(records),
        "subsidy_interference": detect_subsidy_interference(records),
        "court_order_violations": detect_court_order_violations(records),
    }
