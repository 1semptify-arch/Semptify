"""Page Composer Assembly Formula.

Implements the deterministic rule:
    (user_context, subject/intent, jurisdiction) -> PageConfig + components

Phase order (immutable):
  1. Resolve inputs
  2. Compute intensity
  3. Classify major_pillar
  4. Select blend
  5. Gather blocks
  6. Build PageConfig
  7. Apply capability filter
  8. Apply GOVERN floor/override rules
  9. Emit PageConfig + legacy UI Composer components
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.page_composer.models import PageAssemblyResult
from app.modules.page_composer.service import compose_page
from app.modules.page_shell.blends import get_blend
from app.modules.page_shell.govern import apply_govern_rules
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

    # 5. Gather blocks
    page_data = await compose_page(
        subject=subject,
        jurisdiction=jurisdiction,
        user_id=user_id,
        fact_limit=fact_limit,
        story_limit=story_limit,
    )
    blocks = _gather_blocks(page_data, context)

    # 6. Build PageConfig
    risk_tier = _resolve_risk_tier(subject, context)
    zones = _distribute_blocks(channels, blocks)
    page_config = PageConfig(
        page_id=f"{subject}:{jurisdiction}:{user_id or 'anonymous'}",
        major_pillar=major_pillar,  # type: ignore[arg-type]
        blend=blend_name,
        channels=channels,
        zones=zones,
        intensity_override=intensity,
        intensity_source="formula",
    )

    # 7. Apply capability filter (best-effort, no DB required)
    page_config = _apply_capability_filter(page_config, user_id, context)

    # 8. Apply GOVERN rules
    govern_report = apply_govern_rules(page_config, risk_tier)

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
            "major_pillar": major_pillar,
            "blend": blend_name,
            "intensity": intensity,
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
    """Merge user_context with any available Context Engine state."""
    merged = dict(user_context)
    if user_id:
        try:
            from app.services.context_loop import context_loop

            state = context_loop.get_state(user_id)
            if state and isinstance(state, dict):
                merged.update(state.get("context", {}))
                merged.update(state.get("summary", {}))
        except Exception as exc:
            logger.debug("No context loop state for %s: %s", user_id, exc)
    return merged


def _compute_intensity(subject: str, context: dict[str, Any]) -> int:
    """Return 0-100 urgency/intensity score.

    Heuristic: urgency cues in context + subject base weight.
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
    """Transform composed page data into Page Shell blocks per pillar."""
    blocks: dict[str, list[AnyBlock]] = {"record": [], "know": [], "act": [], "govern": []}

    facts = page_data.get("facts", [])
    stories = page_data.get("stories", [])
    case = page_data.get("case")

    for idx, fact in enumerate(facts):
        tags = fact.get("tags") or []
        source_name = fact.get("source_name", "verified source")
        _fact_label(fact)
        reading = _fact_reading_level(tags)
        blocks["know"].append(
            InfoBlock(
                block_id=f"fact_{idx}",
                content_ref=fact.get("claim", ""),
                reading_level=reading,  # type: ignore[arg-type]
                collapsed_by_default=True,
                summary=f"Source: {source_name}",
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

    if case:
        case_items = case.get("items") or []
        blocks["record"].append(
            InputBlock(
                block_id="case_status_input",
                input_type="text",
                label=f"Case status: {case.get('count', 0)} active",
                required=False,
                writes_to="case_builder",
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

    Best-effort: if we cannot determine capabilities, pass through unchanged.
    """
    if not user_id:
        return page_config

    try:
        # Synchronous DB access not available here; skip unless we already
        # have cached capabilities in context.
        cached_caps = context.get("capabilities")
        if cached_caps:
            allowed = set(cached_caps)
            zones = page_config.zones or {}
            for pillar, zone in zones.items():
                zone.blocks = [b for b in zone.blocks if _block_allowed(b, allowed, pillar)]
            page_config.zones = zones
    except Exception as exc:
        logger.debug("Capability filter skipped: %s", exc)

    return page_config


def _block_allowed(block: AnyBlock, allowed: set[str], pillar: str) -> bool:
    """Return True if block's module dependency is allowed for the user."""
    # Block kinds do not currently carry module_name; treat all as allowed.
    return True


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
        "document_count": context.get("documents", 0),
        "upcoming_deadlines": context.get("deadlines", 0),
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
