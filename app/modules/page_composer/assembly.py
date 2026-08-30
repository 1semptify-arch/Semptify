"""Page Composer Assembly Formula.

Implements the deterministic rule:
    (user_context, subject/intent, jurisdiction) -> PageConfig + components

Phase order (immutable):
  1. Resolve inputs
  2. Compute intensity
  3. Classify major_pillar
  4. Select blend
  5. Resolve risk tier + apply GOVERN floor to channels (must precede block
     gathering — see note below)
  6. Gather blocks + build PageConfig
  7. Apply capability filter
  8. Apply GOVERN override/suppression rules + audit report
  9. Emit PageConfig + legacy UI Composer components

Why the GOVERN floor is applied before blocks are gathered (step 5, not 8):
a zone's rendered block count is fixed at build time from its channel level
(see page_shell.zones.level_to_prominence). Clamping the channel level
*after* zones already exist does not restore any GOVERN safety content that
was trimmed at the old, lower level — the floor guarantee would be reported
correctly but not actually rendered. Resolving the floor first ensures zones
are built at the level they will actually be reported at.
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.page_composer.models import PageAssemblyResult
from app.modules.page_composer.service import compose_page
from app.modules.page_shell.blends import get_blend
from app.modules.page_shell.govern import apply_govern_rules, govern_floor_for
from app.modules.page_shell.models import (
    AnyBlock,
    ChannelLevels,
    InfoBlock,
    InputBlock,
    OutputBlock,
    PageConfig,
    Zone,
)
from app.modules.page_shell.zones import level_to_prominence
from app.services.ui_composer import compose_page as ui_compose_page

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_JURISDICTION = "MN"

# Subject -> preferred major pillar. If none, infer from intensity bands.
SUBJECT_MAJOR_PILLAR: dict[str, str] = {
    "notice": "record",
    "lease": "record",
    "repair": "act",
    "rent_escrow": "act",
    "eviction": "govern",
    "unlawful_detainer": "govern",
    "security_deposit": "know",
    "tenant_rights": "know",
}

# Subject -> default risk tier (UPL). Overridden by case data if present.
SUBJECT_RISK_TIER: dict[str, str] = {
    "eviction": "high",
    "unlawful_detainer": "very_high_do_not_build",
    "rent_escrow": "medium_high",
    "repair": "medium",
    "notice": "low",
    "lease": "low_medium",
    "security_deposit": "low_medium",
    "tenant_rights": "low",
}

# Which facts become which block kinds.
_FACT_TO_READING_LEVEL: dict[str, str] = {
    "law": "legal",
    "deadline": "intermediate",
    "default": "plain",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def assemble_page(
    subject: str,
    jurisdiction: str = DEFAULT_JURISDICTION,
    county: str | None = None,
    user_id: str | None = None,
    intent: str | None = None,
    user_context: dict[str, Any] | None = None,
    fact_limit: int = 10,
    story_limit: int = 5,
) -> PageAssemblyResult:
    """Assemble a PageConfig from user context, subject, and jurisdiction.

    This is the single entry point for the Page Composer assembly formula.
    """
    # 1. Resolve inputs
    user_context = user_context or {}
    context = await _resolve_context(user_id, user_context)

    # 2. Compute intensity
    intensity = _compute_intensity(subject, context)

    # 3. Classify major_pillar
    major_pillar = _classify_major_pillar(subject, intent, intensity)

    # 4. Select blend
    blend_name = _select_blend(subject, intent, intensity)
    channels = get_blend(blend_name)

    # 5b. Resolve risk tier and GOVERN floor BEFORE gathering blocks.
    #
    # BUG FIX: a zone's block count is fixed at build time by its channel
    # level (see zones.level_to_prominence) — `_distribute_blocks` trims the
    # gathered blocks down to that count. The floor rule only meant anything
    # if the level it clamps to is the level zones are actually built with.
    # The previous implementation built zones from the raw blend level and
    # only clamped `channels.govern` afterward (in step 8, on the already
    # -built PageConfig), so a page correctly reported a higher GOVERN level
    # but never actually surfaced the extra safety-net content the floor is
    # supposed to guarantee. Resolving the floor first fixes that.
    risk_tier = _resolve_risk_tier(subject, context)
    if risk_tier == "very_high_do_not_build":
        return _build_govern_fallback_page(
            subject=subject,
            jurisdiction=jurisdiction,
            county=county,
            user_id=user_id,
            context=context,
            risk_tier=risk_tier,
        )
    pre_floor_govern = channels.govern
    floor = govern_floor_for(risk_tier)
    if channels.govern < floor:
        channels = channels.model_copy(update={"govern": floor})

    # 6. Gather blocks + build PageConfig (zones now built at the correct,
    #    floor-adjusted GOVERN level).
    page_data = await compose_page(
        subject=subject,
        jurisdiction=jurisdiction,
        user_id=user_id,
        fact_limit=fact_limit,
        story_limit=story_limit,
    )
    blocks = _gather_blocks(page_data, context)
    zones = _distribute_blocks(channels, blocks)
    page_config = PageConfig(
        page_id=f"{subject}:{jurisdiction}:{user_id or 'anonymous'}",
        major_pillar=major_pillar,  # type: ignore[arg-type]
        blend=blend_name,
        channels=channels,
        zones=zones,
        intensity_override=intensity,
        intensity_source="formula",
        jurisdiction=jurisdiction,
        county=county,
    )

    # 7. Apply capability filter (best-effort, no DB required)
    page_config = _apply_capability_filter(page_config, user_id, context)

    # 8. Apply GOVERN rules — floor is already satisfied above, so this call
    # now only performs the override/suppression collection (§3 rule 2) and
    # produces the audit report. We restore the true pre-floor level into
    # the report so the audit trail still shows whether a clamp happened.
    govern_report = apply_govern_rules(page_config, risk_tier)
    govern_report["govern_original"] = pre_floor_govern
    govern_report["govern_clamped"] = pre_floor_govern < govern_report["govern_effective"]

    # 9. Emit legacy UI Composer components
    components: list[dict] = []
    try:
        ui_intent = _ui_intent_for(major_pillar)
        ui_context = _build_ui_context(context, page_config, jurisdiction, page_data)
        ui_page = ui_compose_page(
            user_id=user_id or "anonymous",
            page_intent=ui_intent,
            context=ui_context,
        )
        components = ui_page.get("components", [])
    except Exception as exc:
        logger.warning("UI Composer fallback: %s", exc)

    return PageAssemblyResult(
        page_config=page_config,
        components=components,
        govern_report=govern_report,
        metadata={
            "subject": subject,
            "jurisdiction": jurisdiction,
            "county": county,
            "major_pillar": major_pillar,
            "blend": blend_name,
            "intensity": intensity,
            "risk_tier": risk_tier,
        },
    )


def _build_govern_fallback_page(
    subject: str,
    jurisdiction: str,
    county: str | None,
    user_id: str | None,
    context: dict[str, Any],
    risk_tier: str,
) -> PageAssemblyResult:
    """Return a GOVERN-only safe page for very_high_do_not_build risk."""
    legal_aid = context.get("legal_aid_url", "https://www.lawhelpmn.org")
    govern_blocks: list[AnyBlock] = [
        InfoBlock(
            block_id="govern_disclaimer",
            content_ref="Semptify is not a lawyer and cannot represent you.",
            reading_level="plain",
            collapsed_by_default=False,
            summary="This situation has strict legal deadlines and risks.",
        ),
        OutputBlock(
            block_id="contact_legal_aid",
            action_type="link",
            label="Contact a tenant advocate or legal aid office",
            risk_tier="high",  # type: ignore[arg-type]
            on_trigger=legal_aid,
        ),
    ]
    zones: dict[str, Zone] = {
        pillar: Zone(
            zone_id=pillar,  # type: ignore[arg-type]
            level=100 if pillar == "govern" else 0,
            max_blocks=4,
            blocks=govern_blocks if pillar == "govern" else [],
            layout="stack",
        )
        for pillar in ("record", "know", "act", "govern")
    }
    page_config = PageConfig(
        page_id=f"{subject}:{jurisdiction}:{user_id or 'anonymous'}:govern_fallback",
        major_pillar="govern",  # type: ignore[arg-type]
        blend="govern_fallback",
        channels=ChannelLevels(record=0, know=0, act=0, govern=100),
        zones=zones,
        intensity_override=100,
        intensity_source="govern_fallback",
        jurisdiction=jurisdiction,
        county=county,
    )
    govern_report = {
        "risk_tier": risk_tier,
        "fallback": True,
        "reason": "risk_tier='very_high_do_not_build' — page rejected, GOVERN-only fallback returned",
        "suppressed_act_blocks": [],
        "govern_clamped": False,
    }
    return PageAssemblyResult(
        page_config=page_config,
        components=[],
        govern_report=govern_report,
        metadata={
            "subject": subject,
            "jurisdiction": jurisdiction,
            "county": county,
            "major_pillar": "govern",
            "blend": "govern_fallback",
            "intensity": 100,
            "risk_tier": risk_tier,
        },
    )


# ---------------------------------------------------------------------------
# Phase implementations
# ---------------------------------------------------------------------------


async def _resolve_context(
    user_id: str | None,
    user_context: dict[str, Any],
) -> dict[str, Any]:
    """Merge user_context with any available Context Engine state.

    BUG FIX: `context_loop.get_state()` (app.modules.context_loop.service) exposes real
    user state under `documents_count`, `deadlines` (a list of loosely-shaped
    dicts), and `active_issues` — not the `document_count` / `next_deadline` /
    `recent_events` / `urgency_cues` / `case_count` keys the rest of this module
    reads. The previous implementation blindly merged the two dicts, so those
    keys never existed and every page silently rendered as if the user had no
    documents, no deadlines, and no activity, regardless of their real state.
    This normalizes Context Loop's actual shape into the keys the formula uses.
    Caller-supplied `user_context` values always win (set via `setdefault`).
    """
    merged = dict(user_context)
    if user_id:
        try:
            from app.modules.context_loop.service import context_loop

            state = context_loop.get_state(user_id)
            if state and isinstance(state, dict):
                ctx = state.get("context", {}) or {}
                summary = state.get("summary", {}) or {}

                merged.setdefault(
                    "document_count", ctx.get("documents_count", summary.get("documents", 0))
                )

                deadlines = ctx.get("deadlines") or []
                merged.setdefault("deadline_count", len(deadlines))
                next_deadline = _earliest_deadline(deadlines)
                if next_deadline:
                    merged.setdefault("next_deadline", next_deadline)

                active_issues = ctx.get("active_issues") or []
                merged.setdefault("case_count", len(active_issues))
                merged.setdefault("recent_events", active_issues[:3])

                urgency_cues: list[str] = []
                if ctx.get("rights_at_risk"):
                    urgency_cues.append("landlord_threat")
                days_remaining = (next_deadline or {}).get("days_remaining")
                if isinstance(days_remaining, (int, float)):
                    if days_remaining <= 1:
                        urgency_cues.append("deadline_today")
                    elif days_remaining <= 7:
                        urgency_cues.append("deadline_soon")
                merged.setdefault("urgency_cues", urgency_cues)
        except Exception as exc:
            logger.debug("No context loop state for %s: %s", user_id, exc)
    return merged


def _earliest_deadline(deadlines: list[Any]) -> dict[str, Any] | None:
    """Return the nearest upcoming deadline as {title, date, days_remaining}.

    Deadlines come from document-analysis output and are loosely shaped
    (dict with an unreliable "date" key). Unparseable entries are skipped
    rather than guessed at — silence beats fabrication.
    """
    from datetime import datetime

    from app.core.utc import utc_now

    best: dict[str, Any] | None = None
    best_days: float | None = None
    now = utc_now()

    for entry in deadlines:
        if not isinstance(entry, dict):
            continue
        raw_date = entry.get("date") or entry.get("due_date") or entry.get("hearing_date")
        if not raw_date:
            continue
        try:
            parsed = raw_date if isinstance(raw_date, datetime) else datetime.fromisoformat(str(raw_date))
        except (ValueError, TypeError):
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=now.tzinfo)
        days_remaining = (parsed - now).total_seconds() / 86400
        if best_days is None or days_remaining < best_days:
            best_days = days_remaining
            best = {
                "title": entry.get("title") or entry.get("name") or entry.get("type") or "Upcoming deadline",
                "date": raw_date if isinstance(raw_date, str) else parsed.isoformat(),
                "days_remaining": round(days_remaining),
            }
    return best


def _compute_intensity(subject: str, context: dict[str, Any]) -> int:
    """Return 0-100 urgency/intensity score.

    Heuristic: urgency cues in context + subject base weight + deadline proximity.
    """
    score = 0

    # Subject base weight
    subject_weights: dict[str, int] = {
        "eviction": 90,
        "unlawful_detainer": 95,
        "rent_escrow": 70,
        "repair": 60,
        "notice": 40,
        "lease": 30,
        "security_deposit": 35,
        "tenant_rights": 20,
    }
    score += subject_weights.get(subject, 30)

    # Context urgency cues
    urgency_cues = context.get("urgency_cues", [])
    for cue in urgency_cues:
        if cue in ("deadline_today", "court_tomorrow", "eviction_filed"):
            score += 25
        elif cue in ("deadline_soon", "landlord_threat"):
            score += 15

    # Case count boost
    case_count = context.get("case_count", 0)
    score += min(case_count * 5, 20)

    # Upcoming deadline proximity boost
    next_deadline = context.get("next_deadline")
    if isinstance(next_deadline, dict):
        days_remaining = next_deadline.get("days_remaining")
        if isinstance(days_remaining, (int, float)):
            if days_remaining <= 1:
                score += 25
            elif days_remaining <= 7:
                score += 15
            elif days_remaining <= 14:
                score += 5

    return min(100, max(0, score))


def _classify_major_pillar(subject: str, intent: str | None, intensity: int) -> str:
    """Classify the dominant pillar for the page.

    Intent override wins, then subject mapping, then intensity band.
    """
    if intent:
        if intent in ("record", "capture", "upload", "document"):
            return "record"
        if intent in ("learn", "explain", "rights", "know"):
            return "know"
        if intent in ("act", "file", "send", "escalate", "dispute"):
            return "act"
        if intent in ("govern", "review", "compliance", "legal"):
            return "govern"

    if subject in SUBJECT_MAJOR_PILLAR:
        return SUBJECT_MAJOR_PILLAR[subject]

    # Intensity band fallback
    if intensity >= 80:
        return "govern"
    if intensity >= 55:
        return "act"
    if intensity >= 30:
        return "know"
    return "record"


def _select_blend(subject: str, intent: str | None, intensity: int) -> str:
    """Select a named blend from the page_shell blend registry.

    Intent overrides; otherwise map intensity + subject to a preset.
    """
    if intent == "capture" or intent == "record":
        return "quiet_capture"
    if intent == "learn" or intent == "explain":
        return "orientation"
    if intent in ("act", "file", "escalate"):
        return "urgent_action"
    if intent == "review" or intent == "govern":
        return "high_stakes_review"

    if subject in ("eviction", "unlawful_detainer"):
        return "urgent_action" if intensity >= 75 else "high_stakes_review"
    if subject in ("rent_escrow", "repair"):
        return "urgent_action" if intensity >= 65 else "post_filing_calm"
    if subject in ("security_deposit", "notice"):
        return "post_filing_calm" if intensity >= 50 else "first_contact"

    # Default intensity band
    if intensity >= 80:
        return "urgent_action"
    if intensity >= 50:
        return "first_contact"
    if intensity >= 25:
        return "orientation"
    return "quiet_capture"


def _resolve_risk_tier(subject: str, context: dict[str, Any]) -> str:
    """Resolve UPL risk tier from subject and context."""
    explicit = context.get("risk_tier")
    if explicit:
        return explicit

    # Escalate for eviction filings or documented high-stakes cues
    if context.get("eviction_filed") or context.get("court_date"):
        if subject in ("eviction", "unlawful_detainer"):
            return "high"
        return "medium_high"

    return SUBJECT_RISK_TIER.get(subject, "low")


def _gather_blocks(page_data: dict[str, Any], context: dict[str, Any]) -> dict[str, list[AnyBlock]]:
    """Transform composed page data and context signals into Page Shell blocks per pillar."""
    blocks: dict[str, list[AnyBlock]] = {"record": [], "know": [], "act": [], "govern": []}

    facts = page_data.get("facts", [])
    stories = page_data.get("stories", [])
    case = page_data.get("case")

    document_count = context.get("document_count", 0)
    next_deadline = context.get("next_deadline")
    recent_events = context.get("recent_events", [])

    # RECORD blocks — documents / evidence
    if document_count:
        blocks["record"].append(
            InfoBlock(
                block_id="document_count_badge",
                content_ref=f"You have {document_count} document{'s' if document_count != 1 else ''} saved in your vault.",
                reading_level="plain",
                collapsed_by_default=False,
                module_name="vault",
                summary="Vault",
            )
        )
    else:
        blocks["record"].append(
            OutputBlock(
                block_id="upload_first_document",
                action_type="button",
                label="Upload your first document",
                risk_tier="low",  # type: ignore[arg-type]
                on_trigger="/vault/upload",
                module_name="vault",
            )
        )

    # KNOW blocks — verified facts and tenant stories
    for idx, fact in enumerate(facts):
        tags = fact.get("tags") or []
        source_name = fact.get("source_name", "verified source")
        label = _fact_label(fact)
        reading = _fact_reading_level(tags)
        blocks["know"].append(
            InfoBlock(
                block_id=f"fact_{idx}",
                content_ref=fact.get("claim", ""),
                reading_level=reading,  # type: ignore[arg-type]
                collapsed_by_default=True,
                summary=f"{label} — Source: {source_name}" if label else f"Source: {source_name}",
            )
        )

    for idx, story in enumerate(stories):
        blocks["know"].append(
            InfoBlock(
                block_id=f"story_{idx}",
                content_ref=story.get("body", ""),
                reading_level="plain",
                collapsed_by_default=True,
                summary=story.get("title", "Tenant story"),
            )
        )

    # ACT blocks — case actions, deadlines, recent events
    if case:
        case_items = case.get("items") or []
        blocks["record"].append(
            InputBlock(
                block_id="case_status_input",
                input_type="text",
                label=f"Case status: {case.get('count', 0)} active",
                required=False,
                writes_to="case_builder",
                module_name="case_builder",
                placeholder="Review or update your case",
            )
        )
        for idx, item in enumerate(case_items):
            blocks["act"].append(
                OutputBlock(
                    block_id=f"case_action_{idx}",
                    action_type="link",
                    label=f"Open case: {item.get('title', 'case')}",
                    risk_tier="low",  # type: ignore[arg-type]
                    on_trigger=f"/cases/{item.get('id', '')}",
                    module_name="case_builder",
                )
            )

    if isinstance(next_deadline, dict):
        title = next_deadline.get("title", "Upcoming deadline")
        date = next_deadline.get("date", "")
        days = next_deadline.get("days_remaining")
        risk = "high" if isinstance(days, (int, float)) and days <= 7 else "medium"  # type: ignore[arg-type]
        blocks["act"].append(
            OutputBlock(
                block_id="next_deadline_action",
                action_type="link",
                label=f"Next: {title}" + (f" (due {date})" if date else ""),
                risk_tier=risk,
                on_trigger="/calendar",
                module_name="calendar",
            )
        )

    for idx, event in enumerate(recent_events[:3]):
        title = event.get("title", "Event") if isinstance(event, dict) else str(event)
        blocks["act"].append(
            OutputBlock(
                block_id=f"recent_event_{idx}",
                action_type="link",
                label=f"Timeline: {title}",
                risk_tier="low",  # type: ignore[arg-type]
                on_trigger="/timeline",
                module_name="timeline",
            )
        )

    # Always add a primary action for act-focus pages if none exists
    if not blocks["act"] and context.get("can_act", True):
        blocks["act"].append(
            OutputBlock(
                block_id="primary_action",
                action_type="button",
                label="Take the next step",
                risk_tier="low",  # type: ignore[arg-type]
                on_trigger="/act",
            )
        )

    # GOVERN escalation banner when risk is high
    risk_tier = _resolve_risk_tier(page_data.get("subject", ""), context)
    if risk_tier in ("high", "very_high_do_not_build"):
        blocks["govern"].append(
            InfoBlock(
                block_id="govern_warning",
                content_ref="This issue may have legal deadlines. Consider reviewing with a tenant advocate.",
                reading_level="plain",
                collapsed_by_default=False,
                summary="Legal risk detected",
            )
        )

    return blocks


def _distribute_blocks(channels: ChannelLevels, blocks: dict[str, list[AnyBlock]]) -> dict[str, Zone]:
    """Turn channel levels + gathered blocks into zones, trimmed by prominence."""
    zones: dict[str, Zone] = {}
    for pillar in ("record", "know", "act", "govern"):
        level = getattr(channels, pillar)
        prominence = level_to_prominence(level, max_blocks=4)
        zone_blocks = blocks.get(pillar, [])[: prominence.block_count]
        zones[pillar] = Zone(
            zone_id=pillar,  # type: ignore[arg-type]
            level=level,
            max_blocks=4,
            blocks=zone_blocks,
            layout="stack",
        )
    return zones


def _apply_capability_filter(
    page_config: PageConfig,
    user_id: str | None,
    context: dict[str, Any],
) -> PageConfig:
    """Remove blocks for modules the current user cannot load.

    Capabilities should be supplied as a list/set of module names or module
    paths in `context["capabilities"]`. If they are missing, we log a visible
    warning and pass through unchanged rather than gating against empty data.
    """
    if not user_id:
        return page_config

    allowed = context.get("capabilities")
    if allowed is None:
        logger.warning(
            "Capability filter skipped: no capabilities in context for user %s***; "
            "passing all blocks through. Supply resolved_module_paths to assemble_page "
            "via user_context['capabilities'] to enable gating.",
            user_id[:6],
        )
        return page_config

    allowed_set = set(allowed)
    zones = page_config.zones or {}
    for pillar, zone in zones.items():
        before = len(zone.blocks)
        zone.blocks = [b for b in zone.blocks if _block_allowed(b, allowed_set)]
        dropped = before - len(zone.blocks)
        if dropped:
            logger.info(
                "Capability filter dropped %d block(s) in %s zone for user %s***",
                dropped,
                pillar,
                user_id[:6],
            )
    page_config.zones = zones
    return page_config


def _block_allowed(block: AnyBlock, allowed: set[str]) -> bool:
    """Return True if block's module dependency is allowed for the user."""
    module_name = getattr(block, "module_name", None)
    if not module_name:
        return True
    if module_name in allowed:
        return True
    # Allow raw module names like "vault" to match manifest paths
    # "app.modules.vault.router".
    from app.core.module_gate import get_function_module_path

    return get_function_module_path(module_name) in allowed


def _ui_intent_for(major_pillar: str) -> str:
    """Map a major pillar to a legacy UI Composer page_intent."""
    return {
        "record": "documents",
        "know": "library",
        "act": "tools",
        "govern": "workflow_step",
    }.get(major_pillar, "landing")


def _build_ui_context(
    context: dict[str, Any],
    page_config: PageConfig,
    jurisdiction: str,
    page_data: dict[str, Any],
) -> dict[str, Any]:
    """Build a UI Composer-compatible context dict."""
    return {
        **context,
        "document_count": context.get("document_count", 0),
        "upcoming_deadlines": context.get("deadline_count", 0),
        "subject": page_data.get("subject"),
        "label": page_data.get("label"),
        "facts": page_data.get("facts", []),
        "stories": page_data.get("stories", []),
        "page_config": page_config.model_dump(mode="json"),
        "jurisdiction": jurisdiction,
        "intensity": context.get("intensity", 0),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fact_label(fact: dict[str, Any]) -> str:
    """Extract a short display label from a fact."""
    if fact.get("citation"):
        return fact["citation"]
    return fact.get("claim", "Verified fact")[:80]


def _fact_reading_level(tags: list[str]) -> str:
    """Map fact tags to a reading level for InfoBlock."""
    for tag in tags:
        if tag in _FACT_TO_READING_LEVEL:
            return _FACT_TO_READING_LEVEL[tag]
    return _FACT_TO_READING_LEVEL["default"]
