"""Eviction Timeline Object + Page Envelopes (ADR-0008 pilot surface 1).

This module applies the Object Context Envelope (§2.1) and Page Envelope (§2.6)
schemas to the actual Eviction Timeline page. The Page Envelope is instantiated
at read time and its `page_actions` are resolved per-tenant/per-encounter using
`EncounterContext`.
"""

from __future__ import annotations

from app.core.context_envelope import (
    EncounterContext,
    ObjectEnvelope,
    ObjectType,
    Pillar,
    Provenance,
    TemporalValidity,
    Who,
)
from app.core.page_envelope import PageEnvelope, PageRelation, resolve_page_actions


def _field(
    object_id: str,
    why: str,
    pillar: Pillar,
    subject_tags: list[str],
    temporal_validity: TemporalValidity = TemporalValidity.STATIC,
) -> ObjectEnvelope:
    """Factory for form-field Object Envelopes on the Eviction Timeline page."""
    return ObjectEnvelope(
        object_id=object_id,
        object_type=ObjectType.FIELD,
        pillar=pillar,
        who=Who.TENANT,
        why=why,
        provenance=Provenance.USER_ENTERED,
        temporal_validity=temporal_validity,
        subject_tags=subject_tags,
    )


def _button(object_id: str, why: str, subject_tags: list[str]) -> ObjectEnvelope:
    """Factory for button Object Envelopes on the Eviction Timeline page."""
    return ObjectEnvelope(
        object_id=object_id,
        object_type=ObjectType.BUTTON,
        pillar=Pillar.ACT,
        who=Who.TENANT,
        why=why,
        provenance=Provenance.USER_ENTERED,
        temporal_validity=TemporalValidity.EVENT_TRIGGERED,
        subject_tags=subject_tags,
    )


# Object Envelopes for the add-event form and the event-list block.
EVENT_TYPE_FIELD = _field(
    "et_event_type",
    "Categorizes the eviction-related event so the tenant can track what happened.",
    Pillar.KNOW,
    ["eviction", "timeline", "event_type"],
)

EVENT_DATE_FIELD = _field(
    "et_event_date",
    "The date and time the event happened; drives deadline calculations.",
    Pillar.ACT,
    ["eviction", "timeline", "event_date", "deadline"],
    TemporalValidity.TIME_BOUND,
)

SOURCE_FIELD = _field(
    "et_event_source",
    "Where the event record came from: manual entry, document, court, or email.",
    Pillar.RECORD,
    ["eviction", "timeline", "source", "evidence"],
)

JURISDICTION_FIELD = _field(
    "et_event_jurisdiction",
    "The jurisdiction that governs this event, so tools can apply the right rules.",
    Pillar.GOVERN,
    ["eviction", "timeline", "jurisdiction"],
)

SUBJECT_ID_FIELD = _field(
    "et_event_subject_id",
    "Optional subject identifier linking the event to a larger accountability ledger.",
    Pillar.RECORD,
    ["eviction", "timeline", "subject", "accountability"],
)

ADD_EVENT_BUTTON = _button(
    "et_add_event_button",
    "Creates a new timeline event from the form values.",
    ["eviction", "timeline", "add", "submit"],
)

EVENT_LIST_BLOCK = ObjectEnvelope(
    object_id="et_event_list",
    object_type=ObjectType.BLOCK,
    pillar=Pillar.RECORD,
    who=Who.TENANT,
    why="Displays the tenant's eviction-timeline events in chronological order.",
    provenance=Provenance.SYSTEM_COMPUTED,
    temporal_validity=TemporalValidity.EVENT_TRIGGERED,
    subject_tags=["eviction", "timeline", "event_list"],
)

# Page Envelope for the Eviction Timeline page.
EVICTION_TIMELINE_PAGE = PageEnvelope(
    page_subject="Eviction Timeline",
    page_objectives=[
        "Keep a chronological record of notices, payments, communications, and court events.",
        "Add new events so the tenant can build a complete, defensible timeline.",
    ],
    page_actions=[
        EVENT_TYPE_FIELD,
        EVENT_DATE_FIELD,
        SOURCE_FIELD,
        JURISDICTION_FIELD,
        SUBJECT_ID_FIELD,
        ADD_EVENT_BUTTON,
    ],
    page_relations=[
        PageRelation(relation="about", target="the tenant's eviction case"),
        PageRelation(relation="for", target="tenant"),
    ],
    page_state=[
        "chronological record",
        "tenant-facing",
        "editable",
    ],
)


async def get_eviction_timeline_page(context: EncounterContext | None = None) -> PageEnvelope:
    """Return the Eviction Timeline Page Envelope resolved for this encounter.

    `context` can carry the tenant's actual exposure counts and deadline/action
    flags. If omitted, a default first-encounter context is used.
    """
    if context is None:
        context = EncounterContext()
    return resolve_page_actions(EVICTION_TIMELINE_PAGE, context)


__all__ = [
    "EVENT_TYPE_FIELD",
    "EVENT_DATE_FIELD",
    "SOURCE_FIELD",
    "JURISDICTION_FIELD",
    "SUBJECT_ID_FIELD",
    "ADD_EVENT_BUTTON",
    "EVENT_LIST_BLOCK",
    "EVICTION_TIMELINE_PAGE",
    "get_eviction_timeline_page",
]
