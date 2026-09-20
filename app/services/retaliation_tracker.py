"""
Retaliation Tracker — correlates protected tenant actions with subsequent
adverse landlord actions using the user's own timeline events.

Two timeline event_type values carry the record:
  - ``protected_action`` — things the law protects: repair requests, complaints
    to housing/code enforcement, tenant organizing, documented rent
    withholding, fair-housing complaints, consulting legal aid.
  - ``adverse_action`` — things the landlord does after: eviction notice,
    rent increase, service/utility reduction, threats, lockout, lease
    non-renewal, refusal to repair.

The correlation is deliberately factual: it reports what happened, when, and
how many days apart — then flags proximity against known presumption
windows. It never declares "this is retaliation"; that is a legal conclusion
for a court. Language follows UPL guardrails (suggests / may / potential).

Minnesota presumption: Minn. Stat. § 504B.441 — an eviction action filed
within 90 days after certain protected activities raises a rebuttable
presumption of retaliation. The tactics engine uses a stricter 30-day
threshold for counterclaim urgency; both tiers are surfaced here.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vocabularies (stored in TimelineEvent.tags as JSON arrays)
# ---------------------------------------------------------------------------

PROTECTED_SUBTYPES: dict[str, str] = {
    "repair_request": "Repair or maintenance request",
    "agency_complaint": "Complaint to housing/code enforcement",
    "code_violation_report": "Reported a code violation",
    "tenant_organizing": "Organizing with other tenants",
    "rent_withholding": "Documented rent withholding / escrow",
    "legal_consult": "Consulted legal aid or attorney",
    "fair_housing_complaint": "Fair housing / discrimination complaint",
    "other": "Other protected activity",
}

ADVERSE_SUBTYPES: dict[str, str] = {
    "eviction_notice": "Eviction notice or filing",
    "rent_increase": "Rent increase",
    "service_reduction": "Reduced services (parking, laundry, amenities)",
    "utility_shutoff": "Utility shutoff or interference",
    "threats_harassment": "Threats, intimidation, or harassment",
    "lockout": "Lockout or changed locks",
    "lease_nonrenewal": "Lease non-renewal",
    "refusal_to_repair": "Refusal to repair after request",
    "entry_without_notice": "Entered without proper notice",
    "other": "Other adverse action",
}

EVENT_TYPE_PROTECTED = "protected_action"
EVENT_TYPE_ADVERSE = "adverse_action"

# ---------------------------------------------------------------------------
# Presumption windows (days). Known jurisdictions only — anything unknown
# falls back to generic guidance language, never an invented statute.
# ---------------------------------------------------------------------------

PRESUMPTION_WINDOWS: dict[str, dict[str, Any]] = {
    "minnesota": {
        "days": 90,
        "statute": "Minn. Stat. § 504B.441",
        "label": "Minnesota presumes retaliation when an eviction action is filed within 90 days of a protected activity.",
    },
}

# Tactics engine's stricter urgency threshold — surfaced as the stronger flag.
STRONG_PROXIMITY_DAYS = 30

_JURISDICTION_ALIASES = {
    "mn": "minnesota",
    "minn": "minnesota",
    "minnesota": "minnesota",
}


def _jurisdiction_key(jurisdiction: str | None) -> str | None:
    if not jurisdiction:
        return None
    return _JURISDICTION_ALIASES.get(jurisdiction.strip().lower())


def presumption_window_for(jurisdiction: str | None) -> dict[str, Any] | None:
    """Return the presumption window for a jurisdiction, or None if unknown."""
    key = _jurisdiction_key(jurisdiction)
    return PRESUMPTION_WINDOWS.get(key) if key else None


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


@dataclass
class TrackerEvent:
    """Normalized view of one timeline event for the tracker."""

    id: str
    kind: str  # "protected" | "adverse"
    subtype: str
    subtype_label: str
    title: str
    description: str | None
    event_date: datetime
    urgency: str
    attached_document_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "subtype": self.subtype,
            "subtype_label": self.subtype_label,
            "title": self.title,
            "description": self.description,
            "event_date": self.event_date.isoformat(),
            "urgency": self.urgency,
            "attached_document_ids": self.attached_document_ids,
        }


@dataclass
class RetaliationPair:
    """An adverse action correlated with the nearest prior protected action."""

    protected_event: TrackerEvent
    adverse_event: TrackerEvent
    days_between: int
    in_strong_window: bool  # <=30 days (tactics counterclaim threshold)
    in_presumption_window: bool  # within jurisdiction presumption window
    presumption_days: int | None  # window size, None when jurisdiction unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "protected_event": self.protected_event.to_dict(),
            "adverse_event": self.adverse_event.to_dict(),
            "days_between": self.days_between,
            "in_strong_window": self.in_strong_window,
            "in_presumption_window": self.in_presumption_window,
            "presumption_days": self.presumption_days,
        }


def parse_event_tags(raw: str | None) -> list[str]:
    """Decode the JSON tags column into a plain list of strings."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(parsed, list):
        return [str(t) for t in parsed]
    if isinstance(parsed, str):
        return [parsed]
    return []


def normalize_event(event: Any) -> TrackerEvent | None:
    """Convert a TimelineEvent row into a TrackerEvent; None if not tracker-relevant."""
    event_type = getattr(event, "event_type", "") or ""
    if event_type == EVENT_TYPE_PROTECTED:
        kind, vocab = "protected", PROTECTED_SUBTYPES
    elif event_type == EVENT_TYPE_ADVERSE:
        kind, vocab = "adverse", ADVERSE_SUBTYPES
    else:
        return None

    tags = parse_event_tags(getattr(event, "tags", None))
    subtype = tags[0] if tags else "other"
    attached = parse_event_tags(getattr(event, "attached_document_ids", None))

    event_date = getattr(event, "event_date", None)
    if event_date is None:
        return None

    return TrackerEvent(
        id=event.id,
        kind=kind,
        subtype=subtype,
        subtype_label=vocab.get(subtype, vocab["other"]),
        title=getattr(event, "title", "") or "",
        description=getattr(event, "description", None),
        event_date=event_date,
        urgency=getattr(event, "urgency", "normal") or "normal",
        attached_document_ids=attached,
    )


def correlate(
    timeline_events: list[Any],
    jurisdiction: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Correlate protected and adverse timeline events.

    For every adverse action, find the most recent protected action that
    preceded it and measure the gap. Protected actions with no adverse action
    yet still matter — the presumption window may still be open.
    """
    window = presumption_window_for(jurisdiction)
    window_days: int | None = window["days"] if window else None

    tracker_events = [e for e in (normalize_event(ev) for ev in timeline_events) if e]
    protected = sorted((e for e in tracker_events if e.kind == "protected"), key=lambda e: e.event_date)
    adverse = sorted((e for e in tracker_events if e.kind == "adverse"), key=lambda e: e.event_date)

    pairs: list[RetaliationPair] = []
    unmatched_adverse: list[TrackerEvent] = []

    for adv in adverse:
        prior = [p for p in protected if p.event_date <= adv.event_date]
        if not prior:
            unmatched_adverse.append(adv)
            continue
        closest = prior[-1]
        days = (adv.event_date - closest.event_date).days
        pairs.append(
            RetaliationPair(
                protected_event=closest,
                adverse_event=adv,
                days_between=days,
                in_strong_window=days <= STRONG_PROXIMITY_DAYS,
                in_presumption_window=window_days is not None and days <= window_days,
                presumption_days=window_days,
            )
        )

    # Protected actions whose presumption window is still open right now.
    open_windows: list[dict[str, Any]] = []
    if window_days is not None and now is not None:
        latest_adverse = adverse[-1].event_date if adverse else None
        for p in protected:
            if latest_adverse and p.event_date <= latest_adverse:
                continue  # already consumed by a pair
            window_end_days = (now - p.event_date).days
            if 0 <= window_end_days <= window_days:
                open_windows.append(
                    {
                        "protected_event": p.to_dict(),
                        "days_remaining": window_days - window_end_days,
                        "window_days": window_days,
                    }
                )

    flagged = [p for p in pairs if p.in_strong_window or p.in_presumption_window]

    return {
        "pairs": [p.to_dict() for p in pairs],
        "flagged_count": len(flagged),
        "unmatched_adverse": [e.to_dict() for e in unmatched_adverse],
        "protected_events": [e.to_dict() for e in protected],
        "adverse_events": [e.to_dict() for e in adverse],
        "open_windows": open_windows,
        "presumption": (
            {
                "days": window["days"],
                "statute": window["statute"],
                "label": window["label"],
            }
            if window
            else {
                "days": None,
                "statute": None,
                "label": (
                    "Many states presume retaliation when a landlord acts within "
                    "roughly 90–180 days of a protected activity — check your "
                    "state's rule."
                ),
            }
        ),
        "summary": _summary_line(len(protected), len(adverse), len(flagged), window),
    }


# ---------------------------------------------------------------------------
# Assessment — how strong the documented record is
# ---------------------------------------------------------------------------
#
# What retaliation claims generally turn on (educational, not advice):
#   - Proof the protected activity happened and reached the landlord
#     (written repair request, agency complaint record, inspection report —
#     Central Housing v. Olson, 929 N.W.2d 398 (Minn. 2019), protects
#     good-faith complaints made directly TO the landlord under MN common law)
#   - Dates for both events — proximity drives presumption windows
#     (Minn. Stat. § 504B.441: burden shifts to the landlord within 90 days)
#   - Attached documents, not just narrative
#   - The landlord's stated reason vs. timing — courts weigh both
#     (Davies v. Simba, No. A24-0002 (Minn. Ct. App. 2024): non-retaliatory
#     reasons for non-renewal defeated the defense)
#   - Good faith — § 504B.441 requires the complaint be made in good faith
#
# This is a RECORD-READINESS assessment: which pieces of the user's own
# record exist and which are missing. It never says "this is retaliation" —
# that is a legal conclusion for a court.


@dataclass
class AssessmentElement:
    """One element of record readiness."""

    key: str
    label: str
    present: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "present": self.present,
            "detail": self.detail,
        }


def assess(correlation_result: dict[str, Any], *, jurisdiction: str | None = None) -> dict[str, Any]:
    """Evaluate the retaliation record produced by ``correlate()``.

    Takes the dict returned by ``correlate(timeline_events, ...)`` and
    reports which record elements are documented, which are missing, and
    plain-language guidance on what would strengthen the record. Output
    wording follows the UPL-safe pattern used throughout this module —
    it describes the record, never concludes "retaliation happened".
    """
    protected = correlation_result.get("protected_events", [])
    adverse = correlation_result.get("adverse_events", [])
    pairs = correlation_result.get("pairs", [])
    flagged = correlation_result.get("flagged_count", 0)
    open_windows = correlation_result.get("open_windows", [])
    presumption = correlation_result.get("presumption", {})

    has_docs = any(e.get("attached_document_ids") for e in protected + adverse)

    elements = [
        AssessmentElement(
            key="protected_documented",
            label="Protected activity on record",
            present=bool(protected),
            detail=(
                f"{len(protected)} protected action(s) logged."
                if protected
                else "No protected actions logged — repair requests, agency complaints, "
                "and tenant organizing are what the law protects."
            ),
        ),
        AssessmentElement(
            key="adverse_documented",
            label="Adverse action on record",
            present=bool(adverse),
            detail=(
                f"{len(adverse)} adverse action(s) logged."
                if adverse
                else "No adverse actions logged — if the landlord raised rent, "
                "cut services, or served notice, log it with its date."
            ),
        ),
        AssessmentElement(
            key="proximity_flagged",
            label="Close timing flagged",
            present=bool(flagged),
            detail=(
                f"{flagged} adverse action(s) landed inside a presumption or "
                "urgency window — proximity is what raises the retaliation question."
                if flagged
                else "No adverse action landed inside a presumption window. "
                "After the window, the burden of proof stays on the tenant in "
                "most states — the pattern can still matter."
            ),
        ),
        AssessmentElement(
            key="documents_attached",
            label="Documents attached to events",
            present=has_docs,
            detail=(
                "Events have attached documents — dated written proof carries "
                "more weight than recollection."
                if has_docs
                else "No documents attached yet. Attaching the letter, notice, "
                "or inspection report to an event makes the record much stronger."
            ),
        ),
        AssessmentElement(
            key="pattern_multiple",
            label="Pattern of protected activity",
            present=len(protected) >= 2,
            detail=(
                f"{len(protected)} protected actions — a repeated pattern shows "
                "ongoing exercise of rights, not a one-off."
                if len(protected) >= 2
                else "A single protected action can still matter, but a pattern "
                "of requests/complaints is harder to dismiss."
            ),
        ),
        AssessmentElement(
            key="open_window",
            label="Presumption window open now",
            present=bool(open_windows),
            detail=(
                f"{len(open_windows)} protected action(s) still inside the "
                f"{presumption.get('days')}-day presumption window."
                if open_windows and presumption.get("days")
                else "No open presumption window right now."
                if presumption.get("days")
                else "Presumption window unknown for this jurisdiction — "
                "check your state's rule."
            ),
        ),
    ]

    present = [e for e in elements if e.present]
    gaps = [e for e in elements if not e.present]

    gap_guidance = []
    if not protected:
        gap_guidance.append(
            "Log every protected step — repair requests, calls to inspectors, "
            "organizing — with the date it happened. The date starts the clock."
        )
    if not adverse:
        gap_guidance.append(
            "If the landlord acts against you — notice, rent increase, cut "
            "services, lockout — log it the day it happens."
        )
    if not has_docs and (protected or adverse):
        gap_guidance.append(
            "Attach the document itself (letter, notice, inspection report, "
            "photo of the notice) to the matching timeline event."
        )
    if adverse and not flagged:
        gap_guidance.append(
            "Timing didn't fall inside a presumption window — the pattern may "
            "still matter, but expect to carry the burden of proof. Talk to "
            "legal aid about whether the record is enough."
        )
    if flagged:
        gap_guidance.append(
            "Flagged proximity is the strongest piece you have — take this "
            "record to legal aid while the window context is fresh."
        )

    return {
        "elements": [e.to_dict() for e in elements],
        "present_count": len(present),
        "total_count": len(elements),
        "gaps": [e.key for e in gaps],
        "guidance": gap_guidance,
        "jurisdiction": jurisdiction,
        "note": (
            "This describes what is in your record, not whether retaliation "
            "occurred — that is a legal question for a court or attorney."
        ),
    }


# ---------------------------------------------------------------------------
# Document indicators — suggest timeline candidates from recognized documents
# ---------------------------------------------------------------------------
#
# document_recognition.py classifies vault documents into DocumentType values.
# Several of those types map directly onto the tracker's vocabularies — an
# eviction notice is an adverse action; a repair request is a protected one.
# ``suggest_from_documents`` turns recognized documents into candidate
# timeline events the user can confirm (nothing is logged automatically —
# the user decides).

DOC_TYPE_TO_INDICATOR: dict[str, tuple[str, str]] = {
    # protected — things the law protects
    "repair_request": ("protected", "repair_request"),
    "inspection": ("protected", "agency_complaint"),
    "condition_report": ("protected", "code_violation_report"),
    "work_order": ("protected", "repair_request"),
    # adverse — things the landlord does after
    "eviction_notice": ("adverse", "eviction_notice"),
    "eviction_filing": ("adverse", "eviction_notice"),
    "summons": ("adverse", "eviction_notice"),
    "notice_to_quit": ("adverse", "eviction_notice"),
    "rent_increase": ("adverse", "rent_increase"),
    "non_renewal": ("adverse", "lease_nonrenewal"),
    "entry_notice": ("adverse", "entry_without_notice"),
    "lease_violation": ("adverse", "other"),
    "late_notice": ("adverse", "other"),
}


def suggest_from_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Suggest protected/adverse timeline candidates from recognized documents.

    Each item in ``documents`` is a normalized dict with at least ``id`` and
    ``doc_type`` (a DocumentType value); ``title``, ``date`` (ISO string or
    datetime), and ``description`` are used when present. Documents whose
    type has no indicator mapping are skipped. Returns candidate dicts —
    callers present them for the user to confirm; nothing is written here.
    """
    suggestions: list[dict[str, Any]] = []
    for doc in documents:
        doc_type = (doc.get("doc_type") or "").lower()
        mapping = DOC_TYPE_TO_INDICATOR.get(doc_type)
        if not mapping:
            continue
        kind, subtype = mapping
        vocab = PROTECTED_SUBTYPES if kind == "protected" else ADVERSE_SUBTYPES
        suggestions.append(
            {
                "document_id": doc.get("id"),
                "suggested_event_type": EVENT_TYPE_PROTECTED if kind == "protected" else EVENT_TYPE_ADVERSE,
                "suggested_subtype": subtype,
                "subtype_label": vocab.get(subtype, vocab["other"]),
                "title": doc.get("title") or vocab.get(subtype, "Document"),
                "description": doc.get("description"),
                "event_date": doc.get("date") or doc.get("event_date"),
                "reason": (
                    f"This document was recognized as '{doc_type.replace('_', ' ')}', "
                    "which may be a "
                    + ("protected step you took." if kind == "protected" else "landlord action worth logging.")
                ),
            }
        )
    return suggestions


def _summary_line(
    n_protected: int,
    n_adverse: int,
    n_flagged: int,
    window: dict[str, Any] | None,
) -> str:
    if n_protected == 0 and n_adverse == 0:
        return (
            "Nothing logged yet. When you ask for a repair, contact an agency, "
            "or take another protected step — log it here. That date starts "
            "the clock the law cares about."
        )
    if n_protected == 0:
        return (
            f"{n_adverse} adverse action(s) logged but no protected actions. "
            "If you made repair requests or complaints earlier, log them too — "
            "proximity to a protected action is what makes retaliation arguable."
        )
    if n_adverse == 0:
        extra = f" The {window['days']}-day presumption window may still be open." if window else ""
        return f"{n_protected} protected action(s) on record, no adverse actions logged.{extra}"
    if n_flagged:
        return (
            f"{n_flagged} of {n_adverse} adverse action(s) landed close enough to a "
            "protected action to raise a retaliation question. Talk to legal aid "
            "about whether it applies to you."
        )
    return (
        f"{n_adverse} adverse action(s) logged — none fell inside a presumption "
        "window, but the pattern may still matter. Keep documenting."
    )
