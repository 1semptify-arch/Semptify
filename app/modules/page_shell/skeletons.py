"""Four skeleton layouts — §10 of the spec.

`major_pillar` selects which skeleton renders. No other logic overrides
this selection (per task scope). All four skeletons contain all four zones
— only arrangement/dominance changes. GOVERN always has its own dedicated
grid area (§10 rule).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.page_shell.models import MajorPillar

# §10 — grid-template-areas for each skeleton. Exactly as specified.
SKELETON_AREAS: dict[str, list[str]] = {
    "record_focus": [
        "record record know",
        "record record act",
        "govern govern govern",
    ],
    "know_focus": [
        "know   know   record",
        "know   know   act",
        "govern govern govern",
    ],
    "act_focus": [
        "act    act    know",
        "act    act    record",
        "govern govern govern",
    ],
    "govern_focus": [
        "govern govern govern",
        "know   act    record",
    ],
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
        raise ValueError(f"Unknown major_pillar '{pillar}'. " f"Must be one of {sorted(PILLAR_TO_SKELETON.keys())}")
    return PILLAR_TO_SKELETON[pillar]


def grid_template_areas(skeleton: str) -> str:
    """Return CSS grid-template-areas value (quoted, multi-line) for a skeleton."""
    if skeleton not in SKELETON_AREAS:
        raise ValueError(f"Unknown skeleton '{skeleton}'")
    return "\n".join(f'"{row}"' for row in SKELETON_AREAS[skeleton])


def grid_template_rows(skeleton: str) -> str:
    """Return grid-template-rows for a skeleton.

    Focus skeletons: 3 rows — dominant spans the first two (1fr each),
    GOVERN is a fixed-height strip (auto) on the bottom.
    Govern_focus: 2 rows — GOVERN auto strip on top, bottom row 1fr
    shared equally by the three secondary zones.

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
