"""Page Envelope — page-level context metadata for the Information Orchestrator.

Defines the grammar-parallel schema from ADR-0008 §2.6. A Page Envelope gives the
whole page a consistent skeleton: subject, objectives, actions, relations, and
factual state. `page_actions` is populated at render time from the Object
Envelopes present on that page.

Standing rule from ADR-0008 §2.6:
    page_state must stay factual/descriptive only — no alarmist adjectives.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.context_envelope import EncounterContext, ObjectEnvelope, resolve_envelope


class PageRelation(BaseModel):
    """A relational connection between the page subject and another entity.

    Modeled on prepositions: *from* the landlord, *since* a date,
    *in response to* another document. Keeps the page tied into the tenant's
    larger timeline without leading the sentence.
    """

    relation: str = Field(
        ...,
        description="Preposition-style relation: from, since, in_response_to, etc.",
    )
    target: str = Field(
        ...,
        description="The entity the page subject relates to (landlord, date, document, etc.).",
    )

    model_config = {"extra": "forbid"}


class PageEnvelope(BaseModel):
    """Structured context metadata declared once per page template.

    - `page_subject` leads the page: one clear topic, not a menu.
    - `page_objectives` states what the page helps the tenant *do* as goals.
    - `page_actions` are the buttons/tasks on the page, each backed by an
      Object Envelope from `app.core.context_envelope`.
    - `page_relations` describes how the subject connects to everything else.
    - `page_state` is a list of honest, factual state descriptors only; it must
      never include alarmist or adversarial language.
    """

    page_subject: str = Field(
        ...,
        description="Single clear topic that leads the page (e.g. 'Your Lease').",
    )
    page_objectives: list[str] = Field(
        ...,
        min_length=1,
        description="What the page helps the tenant do, stated as goals, not features.",
    )
    page_actions: list[ObjectEnvelope] = Field(
        default_factory=list,
        description="Object Envelopes for the actions/buttons/tasks on this page.",
    )
    page_relations: list[PageRelation] = Field(
        default_factory=list,
        description="How the page subject connects to the tenant's larger timeline.",
    )
    page_state: list[str] = Field(
        default_factory=list,
        description="Factual state descriptors only (e.g. pending, unread, resolved, time-sensitive).",
    )

    model_config = {"extra": "forbid"}


def resolve_page_actions(
    page: PageEnvelope,
    context: EncounterContext,
) -> PageEnvelope:
    """Return a copy of `page` with every `page_action` resolved for this encounter.

    Each Object Envelope in `page_actions` gets its `journey_stage` computed
    per-tenant/per-encounter by `resolve_envelope()`. The original page is not
    mutated.
    """
    resolved_actions = [resolve_envelope(action, context) for action in page.page_actions]
    return page.model_copy(update={"page_actions": resolved_actions})


__all__ = [
    "PageRelation",
    "PageEnvelope",
    "resolve_page_actions",
]
