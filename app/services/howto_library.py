"""How-To Guides library — loads first-hand procedural guides for the
tenant library's ``how_to`` subject.

Content source: ``app/data/howto/guides.json``. Entries are authored by
Brad from first-hand experience; the file carries its own entry template
under ``_entry_template``. Only entries with ``status == "published"``
are served — ``placeholder`` and ``draft`` stay hidden so the section can
be scaffolded ahead of the content.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GUIDES_PATH = Path(__file__).resolve().parent.parent / "data" / "howto" / "guides.json"

# Valid related-subject references are enforced loosely — a typo in
# related_subjects just means the link does not render, so we warn rather
# than reject the whole file.


def _load_raw() -> dict[str, Any]:
    """Read guides.json. Missing or malformed file -> empty guides list."""
    try:
        return json.loads(GUIDES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("howto guides.json not found at %s", GUIDES_PATH)
    except json.JSONDecodeError as e:
        logger.warning("howto guides.json is not valid JSON: %s", e)
    return {"guides": []}


def load_guides(*, include_unpublished: bool = False) -> list[dict[str, Any]]:
    """Return guide entries in file order.

    Only ``status == "published"`` entries are returned unless
    ``include_unpublished`` is set (admin/preview use).
    """
    raw = _load_raw()
    guides = raw.get("guides") or []
    if not isinstance(guides, list):
        logger.warning("howto guides.json 'guides' is not a list")
        return []
    if include_unpublished:
        return [g for g in guides if isinstance(g, dict)]
    return [g for g in guides if isinstance(g, dict) and g.get("status") == "published"]


def guides_as_components(guides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map guide entries to howto_card component dicts for the UI Composer."""
    components: list[dict[str, Any]] = []
    for guide in guides:
        components.append(
            {
                "type": "howto_card",
                "data": {
                    "title": guide.get("title") or "Untitled guide",
                    "summary": guide.get("summary") or "",
                    "steps": guide.get("steps") or [],
                    "tips": guide.get("tips") or [],
                    "related_subjects": guide.get("related_subjects") or [],
                },
            }
        )
    return components
