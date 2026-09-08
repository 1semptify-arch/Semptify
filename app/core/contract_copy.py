"""Central display copy for FunctionGroupContracts.

Contracts keep their internal, canonical `title` and `description` fields
(Module Contract Mandate: "<Human Title> (SSOT)" / "CANONICAL ...").  This
module produces the plain-language, tenant-facing version shown in the UI.

Exposed as Jinja globals `contract_title` and `contract_description` so every
template can access the same central copy pass without per-page patches.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

#: Manual overrides for user-facing guide pages and any other contracts whose
#: internal title/description should not leak into the UI.
#: Keyed by "module::group_name" (lowercase).
DISPLAY_OVERRIDES: dict[str, dict[str, str]] = {
    "journal::journal_create": {
        "title": "Write a journal note",
        "description": (
            "Write a dated note about what happened — a conversation, a repair "
            "request, an incident, or anything else about your tenancy."
        ),
    },
    "law_library::law_library_get_statute": {
        "title": "Look up a Minnesota statute",
        "description": (
            "Read the full text of a Minnesota statute or court rule, with a "
            "plain-language summary to help you understand the rule or right."
        ),
    },
    "eviction_defense::eviction_defense_calculate_deadlines": {
        "title": "Calculate your eviction deadlines",
        "description": (
            "Enter the date you were served with an eviction notice and get the "
            "key deadlines for your response. This is a planning tool, not a court filing."
        ),
    },
    "timeline::timeline_create_event": {
        "title": "Add a timeline event",
        "description": (
            "Add a dated event to your personal timeline to build a clear, "
            "chronological record of your housing situation."
        ),
    },
}


def _extract_text(contract: Any, field: str, default: str = "") -> str:
    """Read a field from a contract object or dict."""
    if isinstance(contract, dict):
        return contract.get(field, default) or default
    return getattr(contract, field, default) or default


def _contract_key(contract: Any) -> str | None:
    """Build a "module::group_name" key from a contract object or dict."""
    module = _extract_text(contract, "module").strip().lower()
    group_name = _extract_text(contract, "group_name").strip().lower()
    if module and group_name:
        return f"{module}::{group_name}"
    return None


def _remove_internal_markers(text: str) -> str:
    """Strip (SSOT), (POST), (GET), and leading CANONICAL markers."""
    text = re.sub(r"\s*\(\s*(?:SSOT|POST|GET)\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*CANONICAL\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _humanize_title(title: str) -> str:
    """Return a title that is safe for tenant-facing display."""
    title = _remove_internal_markers(title)
    # If the title is still snake_case, convert to title case.
    if "_" in title and title.islower():
        title = title.replace("_", " ").title()
    return title


def _humanize_description(description: str) -> str:
    """Return a description safe for tenant-facing display."""
    description = _remove_internal_markers(description)
    # Remove leading HTTP method + path fragments like "POST /process".
    description = re.sub(
        r"^\s*(?:POST|GET|PUT|DELETE|PATCH)\s+\S+\s*[-:]?\s*",
        "",
        description,
        flags=re.IGNORECASE,
    )
    return description


def get_display(contract: Any) -> tuple[str, str]:
    """Return (display_title, display_description) for a contract."""
    key = _contract_key(contract)
    override = DISPLAY_OVERRIDES.get(key) if key else None
    if override:
        return override["title"], override["description"]

    return _humanize_title(_extract_text(contract, "title")), _humanize_description(
        _extract_text(contract, "description")
    )


def contract_title(contract: Any) -> str:
    """Jinja global — tenant-facing title for a contract."""
    return get_display(contract)[0]


def contract_description(contract: Any) -> str:
    """Jinja global — tenant-facing description for a contract."""
    return get_display(contract)[1]
