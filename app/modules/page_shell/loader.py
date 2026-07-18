"""Page config loader/validator.

Validates a raw dict against §4 schema + §10 major_pillar requirement +
§2 blend name requirement. Applies GOVERN floor/override rules from §3.

Rejects configs:
  - missing `major_pillar` (§10 mandate)
  - with an unrecognized `blend` name (§2)
  - with risk_tier='very_high_do_not_build' (UPL policy — spec-confirmed
    permanent rule per §3/§11, not a judgment call. A future agent must
    not second-guess this: pages at this risk tier MUST NOT be built.)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.modules.page_shell.blends import known_blends
from app.modules.page_shell.govern import apply_govern_rules
from app.modules.page_shell.models import PageConfig, RiskTier, Zone
from app.modules.page_shell.skeletons import skeleton_for

logger = logging.getLogger(__name__)


class ConfigRejected(Exception):
    """Raised when a page config is rejected by the loader.

    Carries a structured reason so callers can surface it to the user
    (or to the admin in the Forge demo).
    """

    def __init__(self, reason: str, field: str | None = None):
        self.reason = reason
        self.field = field
        super().__init__(reason)


def load_page_config(raw: dict[str, Any]) -> tuple[PageConfig, dict]:
    """Load + validate a page config from a raw dict.

    Returns (config, report) where report describes any GOVERN clamping
    or suppression applied. Raises ConfigRejected on hard rejection.
    """
    # Hard reject: missing major_pillar (§10 mandate)
    if "major_pillar" not in raw or not raw["major_pillar"]:
        raise ConfigRejected(
            "major_pillar is required — it selects the skeleton (§10).",
            field="major_pillar",
        )

    # Hard reject: unknown blend (§2 — page requests a blend NAME)
    blend_name = raw.get("blend")
    if not blend_name:
        raise ConfigRejected(
            "blend is required — page must request a named blend (§2).",
            field="blend",
        )
    if blend_name not in known_blends():
        raise ConfigRejected(
            f"Unknown blend '{blend_name}'. Known blends: {known_blends()}",
            field="blend",
        )

    # Validate against the Pydantic schema (§4 + §8)
    try:
        config = PageConfig.model_validate(raw)
    except ValidationError as e:
        # Surface the first error field for the admin
        first = e.errors()[0] if e.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", []))
        raise ConfigRejected(
            f"Schema validation failed: {first.get('msg', str(e))}",
            field=loc or None,
        ) from e

    # Validate major_pillar selects a real skeleton (defense in depth —
    # Pydantic Literal already constrains, but this makes the error
    # friendlier than a generic Literal validation message).
    try:
        skeleton_for(config.major_pillar)
    except ValueError as e:
        raise ConfigRejected(str(e), field="major_pillar") from e

    # If zones are not supplied, derive empty zones from channels. The
    # renderer will populate them from block config in a real system; for
    # the shell demo we accept configs that include zones explicitly.
    if config.zones is None:
        config.zones = {
            pillar: Zone(zone_id=pillar, level=getattr(config.channels, pillar))
            for pillar in ("record", "know", "act", "govern")
        }

    # Determine risk_tier for GOVERN floor. We look at the govern zone's
    # OutputBlocks (escalation banners carry risk_tier) and fall back to
    # the highest risk_tier among ACT-zone OutputBlocks. If none, 'low'.
    risk_tier = _infer_risk_tier(config)
    report = apply_govern_rules(config, risk_tier)
    report["skeleton"] = skeleton_for(config.major_pillar)
    report["blend"] = config.blend
    report["risk_tier_inferred"] = risk_tier

    return config, report


def load_page_config_from_file(path: str | Path) -> tuple[PageConfig, dict]:
    """Load a page config from a JSON file on disk."""
    p = Path(path)
    if not p.exists():
        raise ConfigRejected(f"Config file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigRejected(f"Invalid JSON in {p}: {e}") from e
    if not isinstance(raw, dict):
        raise ConfigRejected(f"Top-level JSON in {p} must be an object, got {type(raw).__name__}")
    return load_page_config(raw)


def _infer_risk_tier(config: PageConfig) -> RiskTier:
    """Infer the page's risk tier from its blocks.

    Scans OutputBlocks in govern + act zones for the highest risk_tier.
    Falls back to 'low' if none declared. This is a simple heuristic —
    the real context engine (out of scope) will compute this from case
    state. See README.
    """
    order: list[RiskTier] = [
        "low",
        "low_medium",
        "medium",
        "medium_high",
        "high",
        "very_high_do_not_build",
    ]
    best_idx = 0
    if config.zones:
        for zone in config.zones.values():
            for block in zone.blocks:
                rt = getattr(block, "risk_tier", None)
                if rt and rt in order:
                    idx = order.index(rt)
                    if idx > best_idx:
                        best_idx = idx
    return order[best_idx]
