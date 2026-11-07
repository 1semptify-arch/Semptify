"""Pillar front pages — the six public "doors" onto the path.

`SEMPTIFY_ORG_ARCHITECTURE_DRAFT.md` §2 names the six pillars (the path a
person walks, in the order they need it) and §4.2 lists the spaces inside
each one. This module is the SSOT for those front pages: what each door
says, which spaces it lists, and which pillar it hands off to next.

Each space's honest status is resolved from the Toolbox catalog: a space
shows its backing toolbox entries, each linked to its own /toolbox page,
and a space is only as ready as its least-ready entry. A space with no
backing entry renders "Planned" — promised in the inventory, nothing built
behind it yet. Until plugins exist this *is* the slot fill (draft §7): a
slot with no plugin still lands on a truthful page, never a dead end.

Merge-time reconciliation note: `app/modules/portal/registry.py` on main
carries a parallel `PILLARS` table for the /portal page (numbers, labels,
questions, blurbs). That work does not exist on this branch — this module
keeps its own copy so it does not touch registry.py and stays conflict-free
on merge. The two tables should later collapse into one pillar SSOT.
"""

from __future__ import annotations

from dataclasses import dataclass

from .toolbox import STATUS_CLASSES, STATUS_LABELS, ToolboxEntry, toolbox

# Readiness order — a space is only as ready as its least-ready entry.
_STATUS_RANK = {"vision": 0, "planned": 1, "partial": 2, "live": 3}

# Where the six front pages live. `/path/*` is a dedicated namespace: flat
# top-level names like `/research` are already taken by other surfaces
# (PageContract page_id="research"), and one prefix makes the set readable
# as what it is — the path.
PATH_PREFIX = "/path"


@dataclass(frozen=True)
class PillarSpace:
    """One space inside a pillar — a slot from the draft's §4.2 inventory."""

    slot: str  # pNN.* slot id; the toolbox entries carrying this slot back the space
    name: str
    purpose: str  # what the space is for, in one plain clause


@dataclass(frozen=True)
class Pillar:
    """One pillar front page — a door plus its toolbox entries."""

    id: str  # page id + URL key (e.g. "information" -> /path/information)
    number: str  # 1..6, in the order a person needs them
    label: str  # the door's name (draft §2: Information .. Be heard)
    question: str  # the person's question this pillar answers
    blurb: str  # one-line promise, shown under the question
    intro: str  # door copy — what this pillar is for, in plain language
    front_slot: str  # the pNN.front slot this page itself fills
    front_entry: str  # toolbox entry id backing the front slot
    spaces: tuple[PillarSpace, ...]  # the §4.2 inventory for this pillar, in order

    @property
    def path(self) -> str:
        return f"{PATH_PREFIX}/{self.id.replace('_', '-')}"


PILLAR_FRONTS: tuple[Pillar, ...] = (
    Pillar(
        id="information",
        number="1",
        label="Information",
        question="What are my rights?",
        blurb="Plain-language, sourced answers about tenant rights and process.",
        intro=(
            "Know your rights before the dispute starts. Everything here is plain "
            "language, and every fact shows its official source — so you can check "
            "it yourself instead of taking our word for it."
        ),
        front_slot="p01.front",
        front_entry="front_information",
        spaces=(
            PillarSpace("p01.library", "Law library", "Verified law, with the official source shown for every fact."),
            PillarSpace("p01.guides", "Situation guides", "Short 'do this now' steps for tonight, before details are lost."),
            PillarSpace("p01.states", "Know your rights by state", "State-by-state pages with the depth of each one honestly labeled."),
            PillarSpace("p01.glossary", "Glossary", "Plain words for legal words."),
        ),
    ),
    Pillar(
        id="research",
        number="2",
        label="Research",
        question="What applies to my situation?",
        blurb="Go deeper than the general rules: statutes, records, and patterns.",
        intro=(
            "The general rule is the start, not the answer. This is where you check "
            "the law, the records, and the patterns against the facts of your own "
            "situation — still no personal data involved."
        ),
        front_slot="p02.front",
        front_entry="front_research",
        spaces=(
            PillarSpace("p02.research", "Situation research", "The statutes, cases, and agency rules that fit your facts."),
            PillarSpace("p02.cases", "Case law reader", "Read a cited case: a plain summary next to the verbatim text."),
            PillarSpace("p02.credit", "Credit report guide", "Pull and read your own credit reports — we never see them."),
        ),
    ),
    Pillar(
        id="documentation",
        number="3",
        label="Documentation",
        question="What do I write down, and how?",
        blurb="A dated record of every notice, payment, repair request, and conversation.",
        intro=(
            "A paper trail you can trust. Record things as they happen, with dates, "
            "in your own storage — whether or not you ever need to show it to anyone."
        ),
        front_slot="p03.front",
        front_entry="front_documentation",
        spaces=(
            PillarSpace("p03.tools", "The record tools", "Journal, calendar, contacts and call log, rent ledger, quick capture."),
            PillarSpace("p03.vault", "Document vault", "Connect your own Google Drive, Dropbox, or OneDrive."),
            PillarSpace("p03.seal", "Dated fingerprint", "Prove a file has not been changed since a date."),
            PillarSpace("p03.checklists", "What to write down", "Situation checklists: what to photograph, write, and keep."),
        ),
    ),
    Pillar(
        id="organize",
        number="4",
        label="Organize",
        question="How do I turn this pile into a story?",
        blurb="Turn scattered photos, texts, and papers into one coherent record.",
        intro=(
            "Scattered texts, photos, and receipts become one record a stranger can "
            "follow from start to end — in order, readable, ready to hand over."
        ),
        front_slot="p04.front",
        front_entry="front_organize",
        spaces=(
            PillarSpace("p04.timeline", "Timeline", "Every event in your tenancy, in order, in one place."),
            PillarSpace("p04.center", "Document center", "See and sort everything you have saved."),
            PillarSpace("p04.case", "Case builder", "Pull your records together into one organized case."),
            PillarSpace("p04.fems", "Scans and imports (FEMS)", "Camera roll and text imports into a credible record."),
            PillarSpace("p04.export", "Export and share", "Download your record, or share it with legal aid by consent."),
            PillarSpace("p04.utilities", "Stand-alone utilities", "PDF tools, document converter, and a forms browser — no setup."),
        ),
    ),
    Pillar(
        id="collaborate",
        number="5",
        label="Collaborate",
        question="Who else is dealing with this?",
        blurb="Find a tenants association or advocate, or start one.",
        intro=(
            "You are probably not the only one. Find a tenant group or an advocate "
            "near you — and if none exists, there is a plain guide for starting one."
        ),
        front_slot="p05.front",
        front_entry="front_collaborate",
        spaces=(
            PillarSpace("p05.finder", "Find a tenant group", "Local tenant organizations — approved listings only."),
            PillarSpace("p05.start", "Start a tenant group", "A field guide: structure, outreach, funding, limits."),
            PillarSpace("p05.kit", "Group toolkit", "Meeting notes, shared calendar templates, sign-in sheets."),
        ),
    ),
    Pillar(
        id="be_heard",
        number="6",
        label="Be heard",
        question="How do I make it count?",
        blurb="File a legitimate complaint and pass your story to whoever will listen.",
        intro=(
            "Put it on the record where it counts: the right agency, the right "
            "forms, your legislators, and your story — in your own words."
        ),
        front_slot="p06.front",
        front_entry="front_be_heard",
        spaces=(
            PillarSpace("p06.complaint", "Complaint wizard", "The right office for your problem, step by step."),
            PillarSpace("p06.eviction", "Eviction defense and deadlines", "From a notice to the deadlines to the courtroom."),
            PillarSpace("p06.court", "Court forms, packet, and prep", "Forms filled, records labeled, ready for a hearing."),
            PillarSpace("p06.letters", "Sample letters", "Repair requests, deposit requests, records-preservation requests."),
            PillarSpace("p06.legislators", "Reach your legislators", "Official lookup plus how to write, through government channels only."),
            PillarSpace("p06.story", "Tell your story", "Anonymous stories that inform the bill and public policy."),
        ),
    ),
)

_BY_ID = {p.id: p for p in PILLAR_FRONTS}
PAGE_IDS = frozenset(_BY_ID)


def get_pillar(pillar_id: str) -> Pillar | None:
    return _BY_ID.get(pillar_id)


def _entry_view(e: ToolboxEntry) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "purpose": e.purpose,
        "status_label": STATUS_LABELS[e.status],
        "status_class": STATUS_CLASSES[e.status],
    }


def _space_status(entries: list[ToolboxEntry]) -> str:
    """A space is only as ready as its least-ready entry; empty means planned."""
    if not entries:
        return "planned"
    return min((e.status for e in entries), key=lambda s: _STATUS_RANK[s])


def page_context(pillar_id: str) -> dict:
    """Template context for one pillar front page.

    Resolves every space's toolbox entries and its honest roll-up status,
    plus the single next step on the path (the next pillar, or real help
    after the last one).
    """
    pillar = _BY_ID.get(pillar_id)
    if pillar is None:
        return {}

    idx = PILLAR_FRONTS.index(pillar)
    next_pillar = PILLAR_FRONTS[idx + 1] if idx + 1 < len(PILLAR_FRONTS) else None

    return {
        "pillar": pillar,
        "next_pillar": next_pillar,
        "spaces": [
            {
                "slot": sp.slot,
                "name": sp.name,
                "purpose": sp.purpose,
                "status_label": STATUS_LABELS[status],
                "status_class": STATUS_CLASSES[status],
                "entries": [_entry_view(e) for e in entries],
            }
            for sp in pillar.spaces
            for entries in [[e for e in toolbox.all() if e.slot == sp.slot]]
            for status in [_space_status(entries)]
        ],
        "status_label": STATUS_LABELS,
        "status_class": STATUS_CLASSES,
    }
