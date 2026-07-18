"""Pydantic models for the Page Shell system.

Mirrors §4 (Page Config Schema), §8 (Zone + Block object model) of the
pillar-mixer backbone spec. These are the data contracts every renderer
codes against — no renderer invents fields outside these models.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

# §8 — Block kinds. Three kinds cover everything currently spec'd.
BlockKind = Literal["input", "info", "output"]

# §10 — major_pillar selects the skeleton. Exactly four values.
MajorPillar = Literal["record", "know", "act", "govern"]

# §4 — risk_tier. The spec uses informal red/yellow/green in prose; the
# codebase's canonical UPLRiskTier enum (app.core.upl_guardrails) uses a
# 6-step monotonic scale. We accept the canonical values here and map them
# to GOVERN floors in govern.py.
RiskTier = Literal[
    "low",
    "low_medium",
    "medium",
    "medium_high",
    "high",
    "very_high_do_not_build",
]


# ---------------------------------------------------------------------------
# Block models — §8
# ---------------------------------------------------------------------------


class InputBlock(BaseModel):
    """RECORD-zone block — captures something from the tenant."""

    block_id: str
    kind: Literal["input"] = "input"
    input_type: Literal["file_upload", "text", "date", "select", "signature"] = "text"
    label: str
    required: bool = False
    writes_to: str | None = None
    # Optional UI hint — does NOT override zone prominence; purely cosmetic.
    placeholder: str | None = None


class InfoBlock(BaseModel):
    """KNOW-zone block — surfaces verified facts/explanations. Also used
    inside GOVERN for disclaimers."""

    block_id: str
    kind: Literal["info"] = "info"
    content_ref: str
    reading_level: Literal["plain", "intermediate", "legal"] = "plain"
    collapsed_by_default: bool = False
    # Spec-confirmed field (§8): human-readable summary shown in the
    # collapsed view. Official part of the schema, not an assumption.
    summary: str | None = None


class OutputBlock(BaseModel):
    """ACT-zone block — an action the tenant can take. Also used in GOVERN
    for escalation banners."""

    block_id: str
    kind: Literal["output"] = "output"
    action_type: Literal["button", "form", "link", "banner"] = "button"
    label: str
    risk_tier: RiskTier = "low"
    on_trigger: str
    # GOVERN override hook — if True, this block (when placed in the GOVERN
    # zone) suppresses the ACT block whose block_id matches `suppresses_act_block`.
    # Implements §3 "GOVERN ceiling override". Empty by default.
    suppresses_act_block: str | None = None


# A block is one of these three. Pydantic discriminated union on `kind`.
AnyBlock = Annotated[
    InputBlock | InfoBlock | OutputBlock,
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Zone model — §8
# ---------------------------------------------------------------------------


class Zone(BaseModel):
    """Container for one pillar's blocks."""

    zone_id: Literal["record", "know", "act", "govern"]
    level: int = Field(ge=0, le=100)
    max_blocks: int = Field(default=4, ge=1, le=12)
    blocks: list[AnyBlock] = Field(default_factory=list)
    layout: Literal["stack", "row", "grid"] = "stack"


# ---------------------------------------------------------------------------
# Page Config — §4
# ---------------------------------------------------------------------------


class ChannelLevels(BaseModel):
    """The four channel levels (0-100). All four always present (§3)."""

    record: int = Field(ge=0, le=100)
    know: int = Field(ge=0, le=100)
    act: int = Field(ge=0, le=100)
    govern: int = Field(ge=0, le=100)


class AuditHook(BaseModel):
    log_on_render: bool = True
    log_on_action_taken: bool = True
    fields: list[str] = Field(default_factory=lambda: ["page_id", "blend", "channels", "timestamp"])


class Escalation(BaseModel):
    threshold_govern: int = Field(default=85, ge=0, le=100)
    escalation_action: str = "surface_legal_aid_contact_banner"


class PageConfig(BaseModel):
    """Full page config — §4 schema + §10 major_pillar field."""

    page_id: str
    major_pillar: MajorPillar
    blend: str
    channels: ChannelLevels
    zones: dict[str, Zone] | None = None  # optional; can be derived from channels
    audit_hook: AuditHook = Field(default_factory=AuditHook)
    escalation: Escalation = Field(default_factory=Escalation)
    intensity_override: int | None = None
    intensity_source: str | None = None

    @field_validator("major_pillar")
    @classmethod
    def _major_pillar_required(cls, v: str) -> str:
        # §10 — major_pillar is mandatory. Reject empty/None explicitly.
        if not v:
            raise ValueError("major_pillar is required (selects skeleton)")
        return v
