"""GOVERN hard rules — §3 of the spec.

Two non-negotiable rules:
  1. GOVERN floor — no blend may set GOVERN below the minimum required for
     the page's UPL risk tier. If a config violates this, the loader clamps
     GOVERN up to the floor (and records the clamp).
  2. GOVERN ceiling override — if a block in GOVERN's zone sets
     `suppresses_act_block`, the named ACT block must NOT render, regardless
     of ACT's level.

These are the safety layer. Build early, test hard (§6 build order).
"""

from __future__ import annotations

from app.modules.page_shell.models import (
    OutputBlock,
    PageConfig,
    RiskTier,
    Zone,
)

# GOVERN floor by risk_tier. Monotonically non-decreasing with risk.
# The spec says "If risk tier = red, GOVERN has a hard floor (e.g. 60)".
# The codebase's UPLRiskTier uses a 6-step scale; we map each to a floor.
# These thresholds are hand-tunable — the spec explicitly says the level
# thresholds are "expected to be hand-tuned later".
GOVERN_FLOOR_BY_RISK: dict[RiskTier, int] = {
    "low": 20,
    "low_medium": 30,
    "medium": 40,
    "medium_high": 60,
    "high": 80,
    "very_high_do_not_build": 100,  # effectively: reject the page entirely
}


def govern_floor_for(risk_tier: RiskTier) -> int:
    """Return the minimum GOVERN level for a risk tier."""
    return GOVERN_FLOOR_BY_RISK.get(risk_tier, 60)


def clamp_govern_to_floor(config: PageConfig, risk_tier: RiskTier) -> tuple[int, bool]:
    """Return (effective_govern_level, was_clamped).

    If the config's GOVERN level is below the floor for its risk tier,
    clamp it up. Return the effective level and whether clamping happened.

    If risk_tier is 'very_high_do_not_build', raise ValueError — per
    UPLRiskTier docstring, these features MUST NOT be built. The loader
    rejects the config.
    """
    if risk_tier == "very_high_do_not_build":
        raise ValueError(
            "risk_tier='very_high_do_not_build' — this page must not be built (UPLRiskTier policy). Rejecting config."
        )
    floor = govern_floor_for(risk_tier)
    current = config.channels.govern
    if current < floor:
        return floor, True
    return current, False


def collect_suppressed_act_blocks(govern_zone: Zone) -> set[str]:
    """Return the set of ACT block_ids that GOVERN suppresses.

    Scans the GOVERN zone's blocks for OutputBlocks with
    `suppresses_act_block` set. Those ACT blocks will be filtered out
    during render, regardless of ACT's level (§3 GOVERN ceiling override).
    """
    suppressed: set[str] = set()
    for block in govern_zone.blocks:
        if isinstance(block, OutputBlock) and block.suppresses_act_block:
            suppressed.add(block.suppresses_act_block)
    return suppressed


def apply_govern_rules(config: PageConfig, risk_tier: RiskTier) -> dict:
    """Apply GOVERN floor + override rules to a config in place.

    Returns a report dict describing what was applied (for audit logging).
    """
    report: dict = {
        "risk_tier": risk_tier,
        "govern_clamped": False,
        "govern_original": config.channels.govern,
        "govern_effective": config.channels.govern,
        "suppressed_act_blocks": [],
    }

    # Floor rule
    effective, clamped = clamp_govern_to_floor(config, risk_tier)
    if clamped:
        config.channels = config.channels.model_copy(update={"govern": effective})
        report["govern_clamped"] = True
        report["govern_effective"] = effective

    # Override rule — collect suppressions from GOVERN zone if present
    if config.zones and "govern" in config.zones:
        suppressed = collect_suppressed_act_blocks(config.zones["govern"])
        report["suppressed_act_blocks"] = sorted(suppressed)

    return report
