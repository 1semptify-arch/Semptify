"""Named blend presets — §2 of the spec.

A page requests a blend NAME, not four raw numbers. Raw numbers stay tunable
here in one file. Adding a new blend = adding one entry. Do NOT scatter
channel numbers through page code.
"""

from __future__ import annotations

from app.modules.page_shell.models import ChannelLevels

# §2 — six named blends. Values are the spec's exact presets.
BLEND_PRESETS: dict[str, ChannelLevels] = {
    "first_contact": ChannelLevels(record=70, know=60, act=15, govern=30),
    "orientation": ChannelLevels(record=20, know=80, act=20, govern=20),
    "quiet_capture": ChannelLevels(record=90, know=10, act=5, govern=25),
    "urgent_action": ChannelLevels(record=15, know=25, act=90, govern=70),
    "post_filing_calm": ChannelLevels(record=30, know=40, act=30, govern=50),
    "high_stakes_review": ChannelLevels(record=20, know=30, act=40, govern=90),
}


def get_blend(name: str) -> ChannelLevels:
    """Return the channel levels for a named blend.

    Raises ValueError on unknown blend name — the loader rejects configs
    with an unrecognized blend (per task scope).
    """
    if name not in BLEND_PRESETS:
        raise ValueError(f"Unknown blend '{name}'. Known blends: {sorted(BLEND_PRESETS.keys())}")
    return BLEND_PRESETS[name]


def known_blends() -> list[str]:
    """Return sorted list of blend names (for introspection endpoints)."""
    return sorted(BLEND_PRESETS.keys())
