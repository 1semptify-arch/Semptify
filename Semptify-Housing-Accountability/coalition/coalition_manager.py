"""Coalition and group-support workflows for multi-tenant coordination."""

from typing import Any, Dict, List, Optional

from app.core.utc import utc_now


def add_tenant_statement(
    tenant_id: str,
    statement: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a tenant statement as part of a coalition case.

    Returns a normalized statement record with an added timestamp.
    """
    return {
        "tenant_id": tenant_id,
        "statement": statement,
        "tags": list(tags) if tags else [],
        "metadata": dict(metadata) if metadata else {},
        "added_at": utc_now().isoformat(),
    }


def merge_patterns(
    patterns: List[Dict[str, Any]],
    merge_key: str = "type",
) -> Dict[str, List[Dict[str, Any]]]:
    """Merge a list of coalition patterns by a shared key.

    Patterns sharing the same `merge_key` value are grouped together so
    recurring issues can be reviewed as a single cluster.
    """
    merged: Dict[str, List[Dict[str, Any]]] = {}
    for pattern in patterns:
        key = str(pattern.get(merge_key, "uncategorized"))
        merged.setdefault(key, []).append(pattern)
    return merged


def generate_group_summary(
    statements: List[Dict[str, Any]],
    patterns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a high-level summary of coalition statements and patterns."""
    merged = merge_patterns(patterns)
    return {
        "statement_count": len(statements),
        "pattern_count": len(patterns),
        "pattern_categories": list(merged.keys()),
        "patterns_by_category": merged,
        "tenant_ids": sorted({s.get("tenant_id") for s in statements if s.get("tenant_id")}),
        "generated_at": utc_now().isoformat(),
    }
