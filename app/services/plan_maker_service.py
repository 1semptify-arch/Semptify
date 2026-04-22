"""
Semptify — Plan Maker Service
==============================
Builds structured, exportable accountability plans for tenants.

A Plan captures:
  - Who is accountable (landlord entity, property, registered agent)
  - What the issues / violations are
  - What evidence exists and what is still needed
  - Which Semptify modules are relevant
  - A timestamped checklist of next steps
  - Export to structured dict, Markdown, and JSON

All plan data lives in the vault (user-controlled storage).
No plan content is retained server-side after the request.
"""

from __future__ import annotations

from app.core.id_gen import make_id
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EntityRecord:
    """A named party with optional address and role."""
    name: str
    role: str = ""
    address: str = ""
    registered_agent: str = ""
    notes: str = ""


@dataclass
class EvidenceItem:
    """A single piece of evidence linked to this plan."""
    description: str
    vault_id: Optional[str] = None
    date_obtained: Optional[str] = None
    status: str = "pending"  # pending | attached | missing


@dataclass
class NextStep:
    """An action item the user or advocate needs to take."""
    action: str
    due_date: Optional[str] = None
    completed: bool = False
    notes: str = ""


@dataclass
class AccountabilityPlan:
    """
    The full structured accountability plan for a tenant situation.

    Designed to be:
      - Exportable to Markdown for court / oversight packets
      - Exportable to JSON for vault storage and portability
      - Passable to other Semptify modules (case_builder, public_exposure, etc.)
    """
    plan_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str

    # --- Subject ---
    landlord_name: str = ""
    property_name: str = ""
    property_address: str = ""
    entities: list[EntityRecord] = field(default_factory=list)

    # --- Issues & Violations ---
    issues: list[str] = field(default_factory=list)
    timeline_notes: str = ""

    # --- Evidence ---
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    narrative: str = ""
    lihtc_angle: str = ""

    # --- Semptify Modules Activated ---
    modules_needed: list[str] = field(default_factory=list)

    # --- Goals ---
    core_objectives: list[str] = field(default_factory=list)
    desired_outcomes: str = ""

    # --- Next Steps ---
    next_steps: list[NextStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        now = self.updated_at
        lines = [
            f"# Accountability Plan: {self.title}",
            f"**Plan ID:** `{self.plan_id}`  ",
            f"**Updated:** {now}",
            "",
            "---",
            "",
            "## 1. Subject",
            f"- **Landlord / Entity:** {self.landlord_name or 'TBD'}",
            f"- **Property:** {self.property_name or 'TBD'}",
            f"- **Address:** {self.property_address or 'TBD'}",
        ]

        if self.entities:
            lines += ["", "### Entities & Registered Agents"]
            for e in self.entities:
                lines.append(
                    f"- **{e.name}** ({e.role}) — {e.address}"
                    + (f" | RA: {e.registered_agent}" if e.registered_agent else "")
                )

        lines += ["", "---", "", "## 2. Issues & Violations"]
        if self.issues:
            for issue in self.issues:
                lines.append(f"- {issue}")
        else:
            lines.append("_No issues recorded yet._")

        if self.timeline_notes:
            lines += ["", f"**Timeline Notes:** {self.timeline_notes}"]

        lines += ["", "---", "", "## 3. Evidence"]
        if self.evidence_items:
            for ev in self.evidence_items:
                vault_ref = f" (vault: `{ev.vault_id}`)" if ev.vault_id else ""
                lines.append(f"- [{ev.status.upper()}] {ev.description}{vault_ref}")
        else:
            lines.append("_No evidence items recorded yet._")

        if self.narrative:
            lines += ["", f"**Narrative:** {self.narrative}"]
        if self.lihtc_angle:
            lines += ["", f"**LIHTC / Subsidy Angle:** {self.lihtc_angle}"]

        lines += ["", "---", "", "## 4. Semptify Modules"]
        if self.modules_needed:
            for m in self.modules_needed:
                lines.append(f"- {m}")
        else:
            lines.append("_No modules selected yet._")

        lines += ["", "---", "", "## 5. Objectives & Outcomes"]
        if self.core_objectives:
            for obj in self.core_objectives:
                lines.append(f"- {obj}")
        if self.desired_outcomes:
            lines += ["", f"**Desired Outcomes:** {self.desired_outcomes}"]

        lines += ["", "---", "", "## 6. Next Steps"]
        if self.next_steps:
            for step in self.next_steps:
                checkbox = "[x]" if step.completed else "[ ]"
                due = f" _(due: {step.due_date})_" if step.due_date else ""
                lines.append(f"- {checkbox} {step.action}{due}")
        else:
            lines.append("_No next steps recorded yet._")

        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# Default Next-Step Templates
# =============================================================================

DEFAULT_NEXT_STEPS: list[str] = [
    "Map all entities and addresses (lease, registered agent, management, owners).",
    "Assemble evidence (notices, emails, photos, filings) into vault.",
    "Draft a narrative timeline from first issue to present.",
    "Run Case Builder to generate a legal summary.",
    "Generate oversight/reporting packet using Public Exposure Suite.",
    "Log all landlord responses and non-responses with dates.",
]

DEFAULT_MODULES: list[str] = [
    "case_builder",
    "public_exposure",
    "fraud_exposure",
    "documents",
    "timeline",
    "briefcase",
]


# =============================================================================
# Service Functions
# =============================================================================

def create_plan(
    user_id: str,
    title: str,
    landlord_name: str = "",
    property_name: str = "",
    property_address: str = "",
    issues: Optional[list[str]] = None,
    narrative: str = "",
    lihtc_angle: str = "",
    core_objectives: Optional[list[str]] = None,
    desired_outcomes: str = "",
    include_default_steps: bool = True,
) -> AccountabilityPlan:
    """
    Create a new AccountabilityPlan with sensible defaults.
    Returns the plan object — caller is responsible for vault storage.
    """
    now = datetime.now(timezone.utc).isoformat()
    plan_id = make_id("plan")

    next_steps = (
        [NextStep(action=s) for s in DEFAULT_NEXT_STEPS]
        if include_default_steps
        else []
    )

    plan = AccountabilityPlan(
        plan_id=plan_id,
        user_id=user_id,
        title=title or f"Accountability Plan — {landlord_name or 'New Plan'}",
        created_at=now,
        updated_at=now,
        landlord_name=landlord_name,
        property_name=property_name,
        property_address=property_address,
        issues=issues or [],
        narrative=narrative,
        lihtc_angle=lihtc_angle,
        modules_needed=list(DEFAULT_MODULES),
        core_objectives=core_objectives or [],
        desired_outcomes=desired_outcomes,
        next_steps=next_steps,
    )
    logger.info("Plan created: %s for user %s", plan_id, user_id)
    return plan


def add_entity(plan: AccountabilityPlan, entity: EntityRecord) -> AccountabilityPlan:
    plan.entities.append(entity)
    plan.updated_at = datetime.now(timezone.utc).isoformat()
    return plan


def add_evidence(plan: AccountabilityPlan, item: EvidenceItem) -> AccountabilityPlan:
    plan.evidence_items.append(item)
    plan.updated_at = datetime.now(timezone.utc).isoformat()
    return plan


def add_next_step(plan: AccountabilityPlan, step: NextStep) -> AccountabilityPlan:
    plan.next_steps.append(step)
    plan.updated_at = datetime.now(timezone.utc).isoformat()
    return plan


def mark_step_complete(
    plan: AccountabilityPlan, step_index: int
) -> AccountabilityPlan:
    if 0 <= step_index < len(plan.next_steps):
        plan.next_steps[step_index].completed = True
        plan.updated_at = datetime.now(timezone.utc).isoformat()
    return plan


def plan_from_dict(data: dict) -> AccountabilityPlan:
    """Deserialise a plan previously exported with to_dict()."""
    entities = [EntityRecord(**e) for e in data.pop("entities", [])]
    evidence_items = [EvidenceItem(**e) for e in data.pop("evidence_items", [])]
    next_steps = [NextStep(**s) for s in data.pop("next_steps", [])]
    return AccountabilityPlan(
        **data,
        entities=entities,
        evidence_items=evidence_items,
        next_steps=next_steps,
    )
