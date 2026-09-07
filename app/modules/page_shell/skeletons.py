"""Four skeleton layouts — §10 of the spec.

`major_pillar` selects which skeleton renders. No other logic overrides
this selection (per task scope). All four skeletons contain all four zones
— only arrangement/dominance changes. GOVERN always has its own dedicated
grid area (§10 rule), exposed to the tenant as a calm safety strip rather
than a labeled quadrant.

The CSS grid area names are intent-based (primary/secondary/tertiary/
quaternary/safety), not the internal pillar names. The renderer still
maps RECORD/KNOW/ACT/GOVERN zones to these areas using
`SKELETON_ZONE_AREAS`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.page_shell.models import MajorPillar

# §10 — grid-template-areas for each skeleton, using flow-based area names
# so the rendered page reads as a single cohesive page, not four visible
# quadrants. GOVERN is always the `safety` strip, except in govern_focus
# where the safety material is the primary focus.
SKELETON_AREAS: dict[str, list[str]] = {
    "record_focus": [
        "primary   primary   secondary",
        "primary   primary   tertiary",
        "safety    safety    safety",
    ],
    "know_focus": [
        "primary   primary   secondary",
        "primary   primary   tertiary",
        "safety    safety    safety",
    ],
    "act_focus": [
        "primary   primary   secondary",
        "primary   primary   tertiary",
        "safety    safety    safety",
    ],
    "govern_focus": [
        "primary   primary   primary",
        "secondary tertiary  quaternary",
    ],
}


# Map each skeleton's internal zones to flow-based grid areas.
SKELETON_ZONE_AREAS: dict[str, dict[str, str]] = {
    "record_focus": {
        "record": "primary",
        "know": "secondary",
        "act": "tertiary",
        "govern": "safety",
    },
    "know_focus": {
        "know": "primary",
        "record": "secondary",
        "act": "tertiary",
        "govern": "safety",
    },
    "act_focus": {
        "act": "primary",
        "know": "secondary",
        "record": "tertiary",
        "govern": "safety",
    },
    "govern_focus": {
        "govern": "primary",
        "know": "secondary",
        "act": "tertiary",
        "record": "quaternary",
    },
}


# Mobile/sequential rendering order for each skeleton. The DOM follows this
# order so the page is a single flow; CSS grid assigns desktop positions
# via grid-area, and the mobile flex layout respects natural source order.
SKELETON_ZONE_ORDER: dict[str, tuple[str, ...]] = {
    "record_focus": ("record", "know", "act", "govern"),
    "know_focus": ("know", "record", "act", "govern"),
    "act_focus": ("act", "know", "record", "govern"),
    "govern_focus": ("govern", "know", "act", "record"),
}


# Map major_pillar → skeleton name. One-to-one, no fallback chain.
PILLAR_TO_SKELETON: dict[str, str] = {
    "record": "record_focus",
    "know": "know_focus",
    "act": "act_focus",
    "govern": "govern_focus",
}


def skeleton_for(pillar: MajorPillar) -> str:
    """Return the skeleton name for a major_pillar. Raises on unknown."""
    if pillar not in PILLAR_TO_SKELETON:
        raise ValueError(f"Unknown major_pillar '{pillar}'. Must be one of {sorted(PILLAR_TO_SKELETON.keys())}")
    return PILLAR_TO_SKELETON[pillar]


def zone_area_for(skeleton: str, zone: str) -> str:
    """Return the flow-based grid area name for a zone in a skeleton."""
    if skeleton not in SKELETON_ZONE_AREAS:
        raise ValueError(f"Unknown skeleton '{skeleton}'")
    mapping = SKELETON_ZONE_AREAS[skeleton]
    if zone not in mapping:
        raise ValueError(f"Unknown zone '{zone}' for skeleton '{skeleton}'")
    return mapping[zone]


def zone_order_for(skeleton: str) -> tuple[str, ...]:
    """Return the render/scroll order of zone names for a skeleton."""
    if skeleton not in SKELETON_ZONE_ORDER:
        raise ValueError(f"Unknown skeleton '{skeleton}'")
    return SKELETON_ZONE_ORDER[skeleton]


def grid_template_areas(skeleton: str) -> str:
    """Return CSS grid-template-areas value (quoted, multi-line) for a skeleton."""
    if skeleton not in SKELETON_AREAS:
        raise ValueError(f"Unknown skeleton '{skeleton}'")
    return "\n".join(f'"{row}"' for row in SKELETON_AREAS[skeleton])


def grid_template_rows(skeleton: str) -> str:
    """Return grid-template-rows for a skeleton.

    Focus skeletons: 3 rows — dominant spans the first two (1fr each),
    safety strip is a fixed-height strip (auto) on the bottom.
    Govern_focus: 2 rows — safety strip on top as the primary focus,
    bottom row 1fr shared equally by the three secondary zones.

    The fr-by-level dynamic row sizing mentioned in §9 is NOT implemented
    here — the shell shape is sacred (§7) and level drives block
    count/prominence WITHIN a zone (§8), not the zone's row size. See
    README for the assumption note.
    """
    if skeleton == "govern_focus":
        return "auto 1fr"
    if skeleton in ("record_focus", "know_focus", "act_focus"):
        return "1fr 1fr auto"
    raise ValueError(f"Unknown skeleton '{skeleton}'")


def all_skeletons() -> dict[str, dict[str, object]]:
    """Return introspection data for all skeletons."""
    return {
        name: {
            "grid_template_areas": SKELETON_AREAS[name],
            "grid_template_rows": grid_template_rows(name),
            "major_pillar": next(p for p, s in PILLAR_TO_SKELETON.items() if s == name),
        }
        for name in SKELETON_AREAS
    }
