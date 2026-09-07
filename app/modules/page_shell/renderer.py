"""Data-driven renderer for the Page Shell.

One renderer per block KIND (not per page). A zone is an ordered list of
blocks, filtered/ranked by the zone's level via zones.level_to_prominence.

GOVERN override authority (§3): if a block in GOVERN's zone suppresses an
ACT block, that ACT block is filtered out before rendering — regardless
of ACT's level.

Output: HTML string for the shell. The shell loads its CSS from
/static/page_shell/page_shell.css (mounted by main.py's StaticFiles).

The four pillars (RECORD/KNOW/ACT/GOVERN) are an internal reasoning model.
They are not rendered as visible labels, quadrants, or colored zones. The
output is a single cohesive page with flow-based sections (primary,
secondary, tertiary, quaternary, safety) and a calm safety strip when
GOVERN material is present.
"""

from __future__ import annotations

import html
import logging

from app.core.law_source_registry import link_citations
from app.modules.page_shell.govern import collect_suppressed_act_blocks
from app.modules.page_shell.models import (
    InfoBlock,
    InputBlock,
    OutputBlock,
    PageConfig,
    Zone,
)
from app.modules.page_shell.skeletons import (
    grid_template_areas,
    grid_template_rows,
    skeleton_for,
    zone_area_for,
    zone_order_for,
)
from app.modules.page_shell.zones import level_to_prominence, level_to_visual_weight

logger = logging.getLogger(__name__)


def render_page_shell(config: PageConfig) -> str:
    """Render a full page shell from a validated config.

    The shell is a single <div class="page-shell skeleton-NAME"> containing
    ordered <section class="zone section-FLOW" data-flow="FLOW"> elements.
    Each section contains its blocks, filtered by level_to_prominence. The
    internal pillar names are mapped to flow-based grid areas and are not
    exposed as visible labels.
    """
    skeleton = skeleton_for(config.major_pillar)
    areas = grid_template_areas(skeleton)
    rows = grid_template_rows(skeleton)

    # GOVERN override: collect suppressed ACT block ids
    suppressed: set[str] = set()
    if config.zones and "govern" in config.zones:
        suppressed = collect_suppressed_act_blocks(config.zones["govern"])
        if suppressed:
            logger.info(
                "GOVERN override: suppressing ACT blocks %s",
                sorted(suppressed),
            )

    zones_html: list[str] = []
    zone_order = zone_order_for(skeleton)
    for pillar in zone_order:
        zone = config.zones.get(pillar) if config.zones else None
        if zone is None:
            continue
        rendered = _render_zone(zone, pillar, skeleton, suppressed, config.jurisdiction, config.county)
        if rendered:
            zones_html.append(rendered)

    # CSS grid area strings use single quotes so the inline style remains a
    # valid double-quoted HTML attribute.
    safe_areas = areas.replace('"', "'")
    style = f"grid-template-areas: {safe_areas}; grid-template-rows: {rows};"
    return f'<div class="page-shell skeleton-{skeleton}" style="{style}">\n' + "\n".join(zones_html) + "\n</div>"


def _render_zone(
    zone: Zone,
    pillar: str,
    skeleton: str,
    suppressed: set[str],
    state: str | None = None,
    county: str | None = None,
) -> str:
    """Render one flow section + its blocks, filtered by level.

    Two level-driven helpers apply:
      - level_to_prominence (§8): block count + emphasis class
      - level_to_visual_weight (§11): background shade depth class

    Returns an empty string if no blocks are visible, so empty zones do not
    clutter the page.
    """
    flow = zone_area_for(skeleton, pillar)
    prominence = level_to_prominence(zone.level, zone.max_blocks)
    visual_weight = level_to_visual_weight(zone.level)

    # Filter blocks: drop suppressed ACT blocks, then cap to prominence.block_count
    blocks = list(zone.blocks)
    if pillar == "act" and suppressed:
        blocks = [b for b in blocks if b.block_id not in suppressed]

    # Cap to the prominence-derived count. We take the FIRST N blocks —
    # the spec says block order is meaningful (zone is an ordered list).
    visible = blocks[: prominence.block_count]
    if not visible:
        return ""

    safety_class = " is-safety-strip" if pillar == "govern" else ""
    blocks_html = "".join(_render_block(b, prominence.emphasis, state, county) for b in visible)
    emphasis_class = f"emphasis-{prominence.emphasis}"
    vw_class = f"visual-weight-{visual_weight.weight}"
    collapsed_attr = ' data-collapsed="true"' if prominence.collapsed else ""

    return (
        f'<section class="zone section-{flow} {emphasis_class} {vw_class}{safety_class}" '
        f'data-flow="{flow}"{collapsed_attr}>\n'
        f'<div class="zone-blocks">{blocks_html}</div>\n'
        f"</section>"
    )


def _render_block(
    block: object,
    emphasis: str,
    state: str | None = None,
    county: str | None = None,
) -> str:
    """Dispatch to the right renderer by block kind.

    One renderer per KIND — not per page. Adding a new block of an
    existing kind requires zero renderer changes.
    """
    if isinstance(block, InputBlock):
        return _render_input_block(block, emphasis)
    if isinstance(block, InfoBlock):
        return _render_info_block(block, emphasis, state, county)
    if isinstance(block, OutputBlock):
        return _render_output_block(block, emphasis)
    # Unknown block kind — render nothing rather than crashing the whole
    # page. Log it so the admin sees the issue in the Forge demo.
    logger.warning("Unknown block kind: %s (block_id=%s)", type(block).__name__, getattr(block, "block_id", "?"))
    return ""


def _render_input_block(b: InputBlock, emphasis: str) -> str:
    """InputBlock renderer — RECORD zone primarily."""
    label = html.escape(b.label)
    required = ' aria-required="true"' if b.required else ""
    required_mark = ' <span class="required" aria-hidden="true">*</span>' if b.required else ""
    placeholder = html.escape(b.placeholder) if b.placeholder else ""

    if b.input_type == "file_upload":
        field = (
            f'<input type="file" name="{html.escape(b.block_id)}"'
            f' data-writes-to="{html.escape(b.writes_to or "")}"{required}>'
        )
    elif b.input_type == "date":
        field = f'<input type="date" name="{html.escape(b.block_id)}"{required}>'
    elif b.input_type == "select":
        # Options come from config in a real system; for the shell demo
        # we render an empty select with a data attribute signaling that
        # options are external. No hardcoded option text.
        field = f'<select name="{html.escape(b.block_id)}"{required} data-options-source="external"></select>'
    elif b.input_type == "signature":
        field = (
            f'<input type="text" name="{html.escape(b.block_id)}"'
            f' class="signature-input" placeholder="{placeholder}"{required}>'
        )
    else:  # text
        field = f'<input type="text" name="{html.escape(b.block_id)}" placeholder="{placeholder}"{required}>'

    return (
        f'<div class="block block-input emphasis-{emphasis}" data-block-id="{html.escape(b.block_id)}">\n'
        f'  <label for="{html.escape(b.block_id)}">{label}{required_mark}</label>\n'
        f"  {field}\n"
        f"</div>\n"
    )


def _render_info_block(
    b: InfoBlock,
    emphasis: str,
    state: str | None = None,
    county: str | None = None,
) -> str:
    """InfoBlock renderer — KNOW zone primarily, also GOVERN disclaimers.

    Renders the content_ref text as HTML with citations linked to their
    official sources. Jurisdiction (state + county) is used so county
    citations resolve to the user's location.
    """
    summary = html.escape(b.summary) if b.summary else ""
    collapsed_attr = ' data-collapsed="true"' if b.collapsed_by_default else ""
    reading = html.escape(b.reading_level)
    content_html = link_citations(b.content_ref, state=state, county=county)
    return (
        f'<div class="block block-info emphasis-{emphasis}" '
        f'data-block-id="{html.escape(b.block_id)}" '
        f'data-content-ref="{html.escape(b.content_ref)}" '
        f'data-reading-level="{reading}"{collapsed_attr}>\n'
        f'  <div class="block-info-summary">{summary}</div>\n'
        f'  <div class="block-info-content" role="region">{content_html}</div>\n'
        f"</div>\n"
    )


def _render_output_block(b: OutputBlock, emphasis: str) -> str:
    """OutputBlock renderer — ACT zone primarily, also GOVERN escalation.

    §11: no alert-style bright colors, no warning-banner treatment.
    risk_tier is kept as a data attribute for the composer/audit layer;
    it does NOT drive any visual styling. Visual weight comes from the
    section's level via level_to_visual_weight, not from the block's risk.
    """
    label = html.escape(b.label)
    return (
        f'<div class="block block-output emphasis-{emphasis}" '
        f'data-block-id="{html.escape(b.block_id)}" '
        f'data-action-type="{html.escape(b.action_type)}" '
        f'data-risk-tier="{html.escape(b.risk_tier)}" '
        f'data-on-trigger="{html.escape(b.on_trigger)}">\n'
        f'  <button type="button" class="output-trigger output-{html.escape(b.action_type)}">'
        f"{label}</button>\n"
        f"</div>\n"
    )
