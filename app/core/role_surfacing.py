"""Role landing surfacing — reads the `surfacing` block of role_configs/*.json.

role_configs/*.json live under app/modules/onboarding/ (NO-TOUCH module —
Brad's 2026-09-18 authorization covers the JSON files only, so this loader
lives in app/core and reads the data; it never edits onboarding code).

The surfacing block is additive landing content (intro line, ordered nav
sections, role tools). ROLE_DEFINITIONS in user_context.py remains the
role-metadata SSOT for identity, landing_page, and gating — this module
does not replace or reinterpret it.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "modules" / "onboarding" / "role_configs"

# Legacy role aliases → canonical config key (mirrors role_config.py's
# _BUILTIN_SPECS mapping; kept local so this module has no onboarding import).
_KEY_ALIASES = {
    "user": "tenant",
    "judge": "legal",
    "research": "researcher",
}


@lru_cache(maxsize=32)
def _load_config(config_key: str) -> dict:
    path = CONFIG_DIR / f"{config_key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read role config %s: %s", path.name, exc)
        return {}


def get_role_surfacing(role_key: str | None) -> dict | None:
    """Return the surfacing block for a role, or None.

    Accepts a UserRole value or plain string key. Never raises — a missing
    config or absent surfacing block returns None and callers fall back to
    their built-in landing content.
    """
    if not role_key:
        return None
    key = str(role_key).strip().lower()
    key = _KEY_ALIASES.get(key, key)
    surfacing = _load_config(key).get("surfacing")
    return surfacing if isinstance(surfacing, dict) else None


def get_role_display_name(role_key: str | None) -> str | None:
    """Return the config's display_name for a role, or None. Never raises."""
    if not role_key:
        return None
    key = str(role_key).strip().lower()
    key = _KEY_ALIASES.get(key, key)
    name = _load_config(key).get("display_name")
    return name if isinstance(name, str) and name else None


def get_role_wording(role_key: str | None) -> dict | None:
    """Return the role's `wording` block (role-specific language), or None.

    The setup component reads wording.setup for per-role copy overrides;
    absent keys fall back to the shared defaults. Never raises.
    """
    if not role_key:
        return None
    key = str(role_key).strip().lower()
    key = _KEY_ALIASES.get(key, key)
    wording = _load_config(key).get("wording")
    return wording if isinstance(wording, dict) else None
