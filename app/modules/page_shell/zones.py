"""Zone level → block count / prominence / visual weight.

§8 threshold rule (prominence):
    level 0–25   → 0-1 blocks, collapsed/low-emphasis styling
    level 26–60  → 1-2 blocks, standard styling
    level 61–100 → up to max_blocks, high-emphasis styling

§11 threshold rule (visual weight):
    level 0–30   → minimal/near-invisible shade shift
    level 31–70  → moderate shade/gradient shift
    level 71–100 → deepest shade shift used anywhere on the page

Both are implemented as ONE configurable function each — not hardcoded
per zone — because the spec says these thresholds are expected to be
hand-tuned later. Every zone uses both helpers; no per-zone special cases.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prominence:
    """How prominent a zone's blocks should be (§8)."""

    block_count: int  # how many blocks to render
    emphasis: str  # "low" | "standard" | "high"
    collapsed: bool  # whether the zone starts collapsed


@dataclass(frozen=True)
class VisualWeight:
    """How heavy a zone's background shade should be (§11).

    Drives background-color/gradient depth — never borders, shadows,
    or alert styling. GOVERN at 'deep' gets the deepest shade on the
    page, but still no warning-banner treatment.
    """

    weight: str  # "low" | "moderate" | "deep"


# Hand-tunable thresholds. Change here once, affects every zone.
LOW_MAX = 25
STANDARD_MAX = 60
# Above STANDARD_MAX → high emphasis.

# §11 visual-weight thresholds.
VW_LOW_MAX = 30
VW_MODERATE_MAX = 70
# Above VW_MODERATE_MAX → deep.


def level_to_prominence(level: int, max_blocks: int = 4) -> Prominence:
    """Map a zone's level (0-100) to its prominence.

    Single source of truth for the threshold rule. Every zone uses this —
    no per-zone overrides, no hardcoded special cases.
    """
    if level < 0 or level > 100:
        raise ValueError(f"level must be 0-100, got {level}")

    if level <= LOW_MAX:
        # 0-1 blocks, low emphasis, collapsed
        count = 1 if level > 0 else 0
        return Prominence(block_count=count, emphasis="low", collapsed=True)

    if level <= STANDARD_MAX:
        # 1-2 blocks, standard emphasis
        # Scale within the band: 26→1, 60→2
        scaled = 1 + (level - LOW_MAX - 1) // ((STANDARD_MAX - LOW_MAX) // 1)
        count = min(max(scaled, 1), 2)
        return Prominence(block_count=count, emphasis="standard", collapsed=False)

    # 61-100 → up to max_blocks, high emphasis
    # Scale within the band: 61→2, 100→max_blocks
    band = 100 - STANDARD_MAX
    extra = (level - STANDARD_MAX) // max(band // max(1, max_blocks - 2), 1)
    count = min(2 + extra, max_blocks)
    return Prominence(block_count=count, emphasis="high", collapsed=False)


def level_to_visual_weight(level: int) -> VisualWeight:
    """Map a zone's level (0-100) to its visual weight (§11).

    Single source of truth for the shade-intensity threshold rule. Every
    zone uses this — GOVERN included. No per-skeleton special cases; the
    `act_focus` skeleton does NOT get a specially-heavier GOVERN treatment
    (spec §11 explicitly deletes that earlier open question).

    Returns one of: "low" (0–30), "moderate" (31–70), "deep" (71–100).
    """
    if level < 0 or level > 100:
        raise ValueError(f"level must be 0-100, got {level}")

    if level <= VW_LOW_MAX:
        return VisualWeight(weight="low")
    if level <= VW_MODERATE_MAX:
        return VisualWeight(weight="moderate")
    return VisualWeight(weight="deep")
