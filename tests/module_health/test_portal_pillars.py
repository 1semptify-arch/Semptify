"""Pillar front pages — the six doors are registered, backed, and honest."""

import re
from pathlib import Path

from app.modules.portal.pages import portal_pages
from app.modules.portal.pillars import PAGE_IDS, PILLAR_FRONTS, page_context
from app.modules.portal.toolbox import SLOTS, toolbox

REPO = Path(__file__).resolve().parents[2]
BANNED = re.compile(
    r"\b(free|account|accounts|log in|login|sign up|subscription|premium|pricing|trial|upgrade)\b",
    re.IGNORECASE,
)


def test_six_fronts_registered_in_page_registry():
    assert len(PILLAR_FRONTS) == 6
    for p in PILLAR_FRONTS:
        page = portal_pages.get_page(p.id)
        assert page is not None, f"{p.id}: not registered in portal pages"
        assert page.path == p.path
        assert page.template == "public/pillar_front.html"
        assert page.in_sitemap
    assert (REPO / "app" / "templates" / "public" / "pillar_front.html").exists()


def test_front_slots_filled_by_toolbox_entries():
    for p in PILLAR_FRONTS:
        assert p.front_slot in SLOTS, f"{p.id}: front_slot {p.front_slot} not declared"
        entry = toolbox.get(p.front_entry)
        assert entry is not None, f"{p.id}: missing toolbox entry {p.front_entry}"
        assert entry.slot == p.front_slot, f"{p.id}: entry slot mismatch"
        assert entry.status == "live", f"{p.id}: the front page itself must be live"
        assert entry.today_path == p.path, f"{p.id}: entry today_path mismatch"


def test_space_slots_declared():
    for p in PILLAR_FRONTS:
        assert p.spaces, f"{p.id}: a door with no spaces is a dead end"
        for sp in p.spaces:
            assert sp.slot in SLOTS, f"{p.id}: space {sp.name} uses undeclared slot {sp.slot}"
            assert sp.slot.startswith(f"p{p.number.zfill(2)}."), f"{p.id}: space {sp.slot} in wrong pillar"


def test_page_context_resolves_status_and_handoff():
    by_slot = toolbox.by_slot()
    for i, p in enumerate(PILLAR_FRONTS):
        ctx = page_context(p.id)
        assert ctx["pillar"] is p
        assert len(ctx["spaces"]) == len(p.spaces)
        for space, rendered in zip(p.spaces, ctx["spaces"]):
            backing = by_slot[space.slot]
            assert [e["id"] for e in rendered["entries"]] == [e.id for e in backing]
        expected_next = PILLAR_FRONTS[i + 1] if i + 1 < len(PILLAR_FRONTS) else None
        assert ctx["next_pillar"] is expected_next


def test_pillar_copy_has_no_banned_words():
    for p in PILLAR_FRONTS:
        for text in (p.label, p.question, p.blurb, p.intro):
            assert not BANNED.search(text), f"{p.id}: banned word in {text!r}"
        for sp in p.spaces:
            assert not BANNED.search(sp.purpose), f"{sp.slot}: banned word in purpose"


def test_unknown_pillar_returns_empty_context():
    assert page_context("not_a_pillar") == {}
    assert PAGE_IDS == frozenset(p.id for p in PILLAR_FRONTS)
