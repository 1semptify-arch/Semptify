"""Press and narrative output workflows for public-interest communication."""

from typing import Any, Dict, List

from app.core.utc import utc_now


def build_fact_summary(facts: List[Dict[str, Any]]) -> str:
    """Build a plain-language summary of verified facts."""
    if not facts:
        return "No verified facts available."
    lines = ["Verified Facts\n"]
    for fact in facts:
        lines.append(f"- {fact.get('claim', str(fact))}")
        if fact.get("source"):
            lines.append(f"  Source: {fact['source']}")
    return "\n".join(lines)


def build_timeline_narrative(events: List[Dict[str, Any]]) -> str:
    """Build a chronological narrative from a list of events."""
    if not events:
        return "No timeline events available."
    sorted_events = sorted(events, key=lambda e: e.get("date") or "")
    lines = ["Timeline\n"]
    for event in sorted_events:
        lines.append(f"- {event.get('date', '')}: {event.get('title', str(event))}")
        if event.get("description"):
            lines.append(f"  {event['description']}")
    return "\n".join(lines)


def build_public_money_analysis(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a summary of public-money issues (subsidies, tax credits, etc.)."""
    total = len(records)
    relevant = [
        r for r in records
        if any(kw in str(r.get("description", "")).lower() for kw in ("subsidy", "tax credit", "public money", "housing voucher", "section 8"))
    ]
    return {
        "total_records": total,
        "relevant_records": len(relevant),
        "relevant_descriptions": [r.get("description", str(r)) for r in relevant],
        "generated_at": utc_now().isoformat(),
    }


def export_press_packet(
    fact_summary: str,
    timeline: str,
    public_money: Dict[str, Any],
    title: str = "Semptify Coalition Press Packet",
) -> str:
    """Export a complete press packet as markdown."""
    lines = [
        f"# {title}",
        f"_Generated: {utc_now().isoformat()}_",
        "",
        fact_summary,
        "",
        timeline,
        "",
        "## Public Money Analysis",
        f"- Relevant records: {public_money.get('relevant_records', 0)} of {public_money.get('total_records', 0)}",
    ]
    for desc in public_money.get("relevant_descriptions", []):
        lines.append(f"- {desc}")
    return "\n".join(lines)
