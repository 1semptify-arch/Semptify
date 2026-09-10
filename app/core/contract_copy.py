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


def _humanize_title(title: str, module: str = "", group_name: str = "") -> str:
    """Return a title that is safe for tenant-facing display."""
    title = _remove_internal_markers(title)

    # Strip leading module name so "Briefcase Add Tag" becomes "Add Tag".
    lowered = title.lower()
    for prefix in (module, group_name.split("_")[0] if group_name else ""):
        if prefix:
            prefix_text = prefix.lower().replace("_", " ").strip()
            if lowered.startswith(prefix_text + " "):
                title = title[len(prefix_text) :].strip()
                lowered = title.lower()

    # If the title is still snake_case or all-lowercase, convert to title case.
    if title.islower():
        title = title.replace("_", " ").title()
    elif lowered and title[0].islower():
        title = title[0].upper() + title[1:]

    return title


def _humanize_description(description: str, module: str = "", group_name: str = "") -> str:
    """Return a description safe for tenant-facing display."""
    description = _remove_internal_markers(description)

    # Strip leading module name so descriptions read like tenant copy, not code.
    lowered = description.lower()
    for prefix in (module, group_name.split("_")[0] if group_name else ""):
        if prefix:
            prefix_text = prefix.lower().replace("_", " ").strip()
            if lowered.startswith(prefix_text + " "):
                description = description[len(prefix_text) :].strip()
                lowered = description.lower()

    # Remove "via POST /path" and leading HTTP method + path fragments.
    description = re.sub(
        r"(?:^|\s)via\s+(?:POST|GET|PUT|DELETE|PATCH)\s+\S+",
        "",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"^\s*(?:POST|GET|PUT|DELETE|PATCH)\s+\S+\s*[-:]?\s*",
        "",
        description,
        flags=re.IGNORECASE,
    )
    # Remove trailing auth/audit notes and method markers that leak implementation.
    description = re.sub(
        r"(?:[.\s]|\-|—|:)\s*(?:Stealth(?:\s+\w+)?\s+guard(?:\s+\w+)?|Audit\s+logged|admin[-\s]?only|dev[-\s]?only).*",
        "",
        description,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return description


def get_display(contract: Any) -> tuple[str, str]:
    """Return (display_title, display_description) for a contract."""
    key = _contract_key(contract)
    override = DISPLAY_OVERRIDES.get(key) if key else None
    if override:
        return override["title"], override["description"]

    module = _extract_text(contract, "module")
    group_name = _extract_text(contract, "group_name")
    return _humanize_title(
        _extract_text(contract, "title"), module, group_name
    ), _humanize_description(_extract_text(contract, "description"), module, group_name)


def contract_title(contract: Any) -> str:
    """Jinja global — tenant-facing title for a contract."""
    return get_display(contract)[0]


def contract_description(contract: Any) -> str:
    """Jinja global — tenant-facing description for a contract."""
    return get_display(contract)[1]
