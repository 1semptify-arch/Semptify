"""Toolbox catalog guardrails — every promised service has one honest entry."""

import re
from pathlib import Path

from app.modules.portal.pages import portal_pages
from app.modules.portal.registry import portal
from app.modules.portal.toolbox import ENGINES, LEVELS, SLOTS, STATUSES, WINGS, toolbox

REPO = Path(__file__).resolve().parents[2]
BANNED = re.compile(
    r"\b(free|account|accounts|log in|login|sign up|subscription|premium|pricing|trial|upgrade)\b",
    re.IGNORECASE,
)


def test_ids_unique_and_fields_valid():
    ids = [e.id for e in toolbox.all()]
    assert len(ids) == len(set(ids)), "duplicate toolbox ids"
    for e in toolbox.all():
        assert e.status in STATUSES, e.id
        assert e.level in LEVELS, e.id
        assert e.engine in ENGINES, e.id
        assert e.group in toolbox.GROUPS, e.id
        assert e.slot == "" or e.slot in SLOTS, e.id
        assert e.wing in WINGS, e.id
        assert e.name and e.purpose and e.today, e.id


def test_backed_by_modules_exist():
    for e in toolbox.all():
        for mod in e.backed_by:
            assert (REPO / "app" / "modules" / mod).is_dir(), f"{e.id}: missing app/modules/{mod}"


def test_unbuilt_entries_explain_themselves():
    for e in toolbox.all():
        if e.status in ("planned", "vision"):
            assert e.today, f"{e.id}: unbuilt entry must say what a person can do today"


def test_public_copy_has_no_banned_words():
    for e in toolbox.all():
        for text in (e.name, e.purpose, e.today, e.note):
            assert not BANNED.search(text), f"{e.id}: banned word in {text!r}"


def test_portal_service_links_to_toolbox_resolve():
    for s in portal.SERVICES:
        if s.cta_path.startswith("/toolbox/"):
            assert toolbox.get(s.cta_path.rsplit("/", 1)[1]), f"{s.id} -> {s.cta_path}"


def test_template_toolbox_links_resolve():
    pattern = re.compile(r'href="/toolbox/([a-z_]+)"')
    for tpl in (REPO / "app" / "templates" / "public").glob("*.html"):
        for eid in pattern.findall(tpl.read_text(encoding="utf-8")):
            assert toolbox.get(eid), f"{tpl.name} links to unknown toolbox entry {eid}"


def test_toolbox_page_registered():
    page = portal_pages.get_page("toolbox")
    assert page and page.path == "/toolbox"
    assert (REPO / "app" / "templates" / page.template).exists()
    assert (REPO / "app" / "templates" / "public" / "toolbox_entry.html").exists()
