"""FastAPI router for the Page Shell system.

Endpoints:
  GET  /api/page-shell/skeletons   — list the four skeletons
  GET  /api/page-shell/blends      — list named blends
  POST /api/page-shell/render      — render a page config to HTML
  GET  /api/page-shell/demo        — render two sample configs (record_focus + govern_focus)
  GET  /api/page-shell/health      — health check

This module is the SHELL only. It does not pick blends or compute
intensity — feed it a validated config, get back HTML.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.utc import utc_now
from app.modules.page_shell.blends import BLEND_PRESETS, known_blends
from app.modules.page_shell.loader import ConfigRejected, load_page_config, load_page_config_from_file
from app.modules.page_shell.renderer import render_page_shell
from app.modules.page_shell.skeletons import all_skeletons, skeleton_for

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Page Shell"])

# Sample configs ship with the module — two different major_pillars to
# visibly exercise both a wide (record_focus) and a structurally
# different (govern_focus) skeleton.
SAMPLE_CONFIG_DIR = Path(__file__).parent / "sample_configs"
SAMPLE_CONFIGS = {
    "record_focus": SAMPLE_CONFIG_DIR / "record_focus_demo.json",
    "govern_focus": SAMPLE_CONFIG_DIR / "govern_focus_demo.json",
}


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "module": "page_shell",
        "lifecycle": "dev_only",
        "timestamp": utc_now().isoformat(),
    }


@router.get("/skeletons")
async def get_skeletons() -> dict:
    """List the four skeleton layouts (§10)."""
    return {"skeletons": all_skeletons()}


@router.get("/blends")
async def get_blends() -> dict:
    """List named blend presets (§2)."""
    return {
        "blends": {name: levels.model_dump() for name, levels in BLEND_PRESETS.items()},
        "known": known_blends(),
    }


@router.post("/render")
async def render_config(payload: dict[str, Any]) -> dict:
    """Render a page config (posted as JSON) to shell HTML.

    Returns:
        {
          "html": "<div class='page-shell ...'>...</div>",
          "skeleton": "record_focus",
          "blend": "first_contact",
          "govern_report": {...},
          "config": {...}  # the validated + clamped config
        }
    """
    try:
        config, report = load_page_config(payload)
    except ConfigRejected as e:
        raise HTTPException(
            status_code=422,
            detail={"reason": e.reason, "field": e.field},
        ) from e
    html_out = render_page_shell(config)
    return {
        "html": html_out,
        "skeleton": skeleton_for(config.major_pillar),
        "blend": config.blend,
        "govern_report": report,
        "config": config.model_dump(),
    }


@router.get("/demo")
async def get_demo() -> dict:
    """Render both sample configs — one record_focus, one govern_focus.

    Visibly exercises a wide skeleton (record_focus: RECORD spans 2/3
    width, 2 rows) and a structurally different one (govern_focus: GOVERN
    is a full-width top strip, three secondary zones share a single row
    underneath).
    """
    out: dict[str, Any] = {}
    for name, path in SAMPLE_CONFIGS.items():
        try:
            config, report = load_page_config_from_file(path)
            out[name] = {
                "html": render_page_shell(config),
                "skeleton": skeleton_for(config.major_pillar),
                "blend": config.blend,
                "govern_report": report,
                "config": config.model_dump(),
            }
        except ConfigRejected as e:
            out[name] = {"error": e.reason, "field": e.field}
    return out
