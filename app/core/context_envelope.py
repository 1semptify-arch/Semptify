"""Object Context Envelope — per-object metadata for the Information Orchestrator.

This module defines the foundational schema declared in ADR-0008 §2.1 and the
resolver that computes `journey_stage` per-tenant, per-encounter at read time.
It is intentionally metadata-only: no UI wiring, no storage, no retrieval layer.

Standing rule from ADR-0008 §2.1.1:
    journey_stage is computed live, not hardcoded per object type.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ObjectType(str, Enum):
    """Kinds of UI/UX objects that can carry explanation."""

    FIELD = "field"
    BLOCK = "block"
    BUTTON = "button"
    MODULE_OUTPUT = "module_output"
    PAGE_ZONE = "page_zone"


class Pillar(str, Enum):
    """Product pillars that set tone and framing for an object."""

    RECORD = "RECORD"
    KNOW = "KNOW"
    ACT = "ACT"
    GOVERN = "GOVERN"


class JourneyStage(str, Enum):
    """Tenant journey stages an object can be in for a given encounter.

    These are NOT static properties of the object definition. The resolver
    below computes them per tenant, per encounter, based on real context.
    """

    ORIENTATION = "orientation"
    DECISION = "decision"
    ACTION = "action"
    REFLECTION = "reflection"


class Who(str, Enum):
    """Audience lens the object is tuned for."""

    TENANT = "tenant"
    ADVOCATE = "advocate"
    AGENCY = "agency"
    RESEARCHER = "researcher"
    LEGAL = "legal"
    DONOR = "donor"


class Provenance(str, Enum):
    """Where the object's underlying value came from."""

    USER_ENTERED = "user_entered"
    OCR_EXTRACTED = "ocr_extracted"
    SYSTEM_COMPUTED = "system_computed"
    SEMANTICALLY_RETRIEVED = "semantically_retrieved"


class TemporalValidity(str, Enum):
    """How long the object value remains meaningfully current."""

    STATIC = "static"
    TIME_BOUND = "time_bound"
    EVENT_TRIGGERED = "event_triggered"


class ObjectEnvelope(BaseModel):
    """Structured context metadata declared alongside every explainable object.

    The `journey_stage` field is optional here because its value is computed by
    `resolve_journey_stage()` at read time, per tenant and per encounter. A raw
    ObjectEnvelope (e.g. from a template or database) is created with
    `journey_stage=None`; the resolved copy returned by `resolve_envelope()`
    carries the live stage.
    """

    object_id: str = Field(..., description="Unique identifier for this object type.")
    object_type: ObjectType = Field(..., description="Kind of UI/UX object.")
    pillar: Pillar = Field(..., description="Product pillar that sets tone/framing.")
    journey_stage: JourneyStage | None = Field(
        default=None,
        description="Live journey stage for this tenant/encounter — always computed, never stored.",
    )
    who: Who = Field(..., description="Audience lens this object is tuned for.")
    why: str = Field(
        ...,
        description="One-line rationale for the object's existence; used to query, not shown verbatim.",
    )
    provenance: Provenance = Field(..., description="Origin of the object's underlying value.")
    temporal_validity: TemporalValidity = Field(..., description="Temporal behavior of the value.")
    subject_tags: list[str] = Field(
        default_factory=list,
        description="Free-text tags for semantic matching (e.g. ['late fee', 'MN', 'lease clause']).",
    )

    model_config = {"extra": "forbid"}


class EncounterContext(BaseModel):
    """Per-tenant, per-encounter inputs used to compute `journey_stage`.

    This is intentionally a small, plain context object so later tasks (Layer 2
    retrieval, Familiarity Tapering, Momentum Checkpoints) can extend it without
    coupling the envelope schema to any one of them.
    """

    exposure_count: int = Field(
        default=0,
        ge=0,
        description="How many times this tenant has encountered this object type before.",
    )
    has_derived_deadline: bool = Field(
        default=False,
        description="Whether a derived deadline now exists for this object (moves to decision).",
    )
    has_action_been_taken: bool = Field(
        default=False,
        description="Whether the tenant has taken action on this object (moves to action).",
    )
    is_reflection_phase: bool = Field(
        default=False,
        description="Whether the tenant is in a reflection phase for this object (moves to reflection).",
    )

    model_config = {"extra": "forbid"}


def resolve_journey_stage(
    envelope: ObjectEnvelope,
    context: EncounterContext,
) -> JourneyStage:
    """Compute the live journey stage for an object in a specific tenant encounter.

    Critical: this is computed at read time from encounter context, never
    hardcoded per `object_type`. The same `eviction_notice_date` object can be
    `orientation` on first encounter and `decision` once a derived deadline exists.

    Stage progression: orientation -> decision -> action -> reflection.
    """
    # Reflection is the terminal stage and overrides everything else.
    if context.is_reflection_phase:
        return JourneyStage.REFLECTION

    # Action stage means the tenant has already acted.
    if context.has_action_been_taken:
        return JourneyStage.ACTION

    # Decision stage is reached when a derived deadline or other decision context exists.
    if context.has_derived_deadline:
        return JourneyStage.DECISION

    # First encounter (or any encounter without a milestone) starts in orientation.
    # This is the safe, trust-first default.
    return JourneyStage.ORIENTATION


def resolve_envelope(
    envelope: ObjectEnvelope,
    context: EncounterContext,
) -> ObjectEnvelope:
    """Return a copy of `envelope` with `journey_stage` resolved for this encounter.

    The original envelope is not mutated. Callers should use the returned copy.
    """
    return envelope.model_copy(
        update={"journey_stage": resolve_journey_stage(envelope, context)}
    )


__all__ = [
    "ObjectType",
    "Pillar",
    "JourneyStage",
    "Who",
    "Provenance",
    "TemporalValidity",
    "ObjectEnvelope",
    "EncounterContext",
    "resolve_journey_stage",
    "resolve_envelope",
]
