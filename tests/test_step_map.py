"""Step-map integrity: every step has prerequisites, tools, instructions, and a valid neighbourhood."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.portal import step_map  # noqa: E402
from app.modules.portal.registry import PortalRegistry  # noqa: E402


def test_step_map_valid():
    assert step_map.validate() == []


def test_every_visible_service_has_a_pillar():
    pillars = {*PortalRegistry.PILLARS, "partner"}
    for s in PortalRegistry.get_visible_services():
        assert s.pillar in pillars, s.id
        assert s.audiences, f"{s.id} has no audience"


def test_context_window_is_two_each_side():
    mid = step_map.TENANT_JOURNEY[2].id
    ctx = step_map.context(mid)
    assert [s.id for s in ctx["previous"]] == ["know", "research"]
    assert [s.id for s in ctx["next"]] == ["organize", "collaborate"]
    first = step_map.context(step_map.TENANT_JOURNEY[0].id)
    assert first["previous"] == [] and len(first["next"]) == 2


def test_no_banned_cost_copy_in_registry():
    banned = ("free", "$0", "no cost", "no-cost", "premium", "subscription", "account")
    for s in PortalRegistry.get_visible_services():
        text = f"{s.name} {s.short_description} {s.description_long}".lower()
        assert not any(re.search(r'(?<![\w-])' + re.escape(b) + r'(?![\w-])', text) for b in banned), s.id


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
