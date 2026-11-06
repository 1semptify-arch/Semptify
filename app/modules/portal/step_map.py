"""Step map — the "brain" for each step of the public tenant journey.

SSOT for step order, prerequisites, tools, and instructions. Pages and agents
read this instead of assuming. For any step you can ask `context(step_id)` and
get the 2 steps before and 2 steps after, so nobody builds a step without
knowing what led to it and what it leads to.

Rules (enforced by tests/test_step_map.py):
- Every step names a real pillar and real portal services as its tools.
- Every step states what you need first, how to do it, and when it is done.
- Order follows the six core functions in docs/admin/MOTIVATIONS.md §3.
- previous/next are DERIVED from list order — never hand-written, so they cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from .registry import PortalRegistry

CONTEXT_WINDOW = 2


@dataclass(frozen=True)
class Step:
    id: str
    pillar: str  # key in PortalRegistry.PILLARS
    title: str
    needs_first: str  # prerequisite: what must already be true or in hand
    how: str  # plain-language instruction (5th-grade reading floor)
    done_when: str  # observable completion, not a quiz answer
    tools: tuple[str, ...]  # PortalService ids that carry this step


TENANT_JOURNEY: tuple[Step, ...] = (
    Step(
        id="know",
        pillar="information",
        title="Know your rights",
        needs_first="Nothing. This step needs no documents and no sign-in.",
        how="Search the Law Library for your state and your topic. Every answer links to its official source.",
        done_when="You found the rule that applies and opened its official source.",
        tools=("tenant_rights_library",),
    ),
    Step(
        id="research",
        pillar="research",
        title="Check your own situation",
        needs_first="The rule you found in the step before, and the basic facts of your situation.",
        how="Look up the landlord, the property, and court records that relate to your situation.",
        done_when="You can name the records that support or contradict your situation.",
        tools=("legal_research", "advanced_systems"),
    ),
    Step(
        id="document",
        pillar="documentation",
        title="Document what happened",
        needs_first="Your photos, notices, receipts, and messages, even if they are scattered.",
        how="Add each item with its date. Record problems as they happen, not later from memory.",
        done_when="Every item you have sits in your record with a date.",
        tools=("tenant_organizer", "standalone_public_forms"),
    ),
    Step(
        id="organize",
        pillar="organize",
        title="Make it one clear record",
        needs_first="Your dated items from the documentation step.",
        how="Put the items in order by date. Convert or merge files so each page is readable.",
        done_when="Someone who was not there can follow the timeline from start to end.",
        tools=("standalone_pdf_tools", "standalone_document_converter"),
    ),
    Step(
        id="collaborate",
        pillar="collaborate",
        title="Find who is with you",
        needs_first="A clear record, so others can see your situation quickly.",
        how="Find a tenants association or advocacy group near you. If none exists, see how to start one.",
        done_when="You have contacted a group, or you have the steps to start one.",
        tools=("advocate_affiliation", "advocate_start_group"),
    ),
    Step(
        id="be_heard",
        pillar="be_heard",
        title="Put it on the record",
        needs_first="Your organized record and, if you have them, advocates who know your situation.",
        how="Choose the right office and file your complaint step by step in plain language.",
        done_when="Your complaint is filed with an official office and you saved the confirmation.",
        tools=("tenant_complaint_wizard",),
    ),
)

_BY_ID = {s.id: s for s in TENANT_JOURNEY}


def get_step(step_id: str) -> Step | None:
    return _BY_ID.get(step_id)


def context(step_id: str, window: int = CONTEXT_WINDOW) -> dict:
    """The step plus up to `window` steps before it and `window` steps after it."""
    idx = next(i for i, s in enumerate(TENANT_JOURNEY) if s.id == step_id)
    return {
        "step": TENANT_JOURNEY[idx],
        "previous": list(TENANT_JOURNEY[max(0, idx - window) : idx]),
        "next": list(TENANT_JOURNEY[idx + 1 : idx + 1 + window]),
    }


def validate() -> list[str]:
    """Return a list of problems; empty means the map is complete and consistent."""
    problems: list[str] = []
    seen: set[str] = set()
    for s in TENANT_JOURNEY:
        if s.id in seen:
            problems.append(f"duplicate step id: {s.id}")
        seen.add(s.id)
        if s.pillar not in PortalRegistry.PILLARS:
            problems.append(f"{s.id}: unknown pillar {s.pillar!r}")
        for field in ("title", "needs_first", "how", "done_when"):
            if not getattr(s, field).strip():
                problems.append(f"{s.id}: empty {field}")
        if not s.tools:
            problems.append(f"{s.id}: no tools")
        for tool in s.tools:
            svc = PortalRegistry.get_service(tool)
            if svc is None:
                problems.append(f"{s.id}: unknown tool {tool!r}")
            elif svc.pillar != s.pillar:
                problems.append(f"{s.id}: tool {tool!r} belongs to pillar {svc.pillar!r}, not {s.pillar!r}")
    order = [s.pillar for s in TENANT_JOURNEY]
    expected = list(PortalRegistry.PILLARS)
    if order != expected:
        problems.append(f"step order {order} does not match pillar order {expected}")
    return problems
