"""Tests for the shared guide-page explanation helper (ADR-0008 Wave 2)."""

from __future__ import annotations

import types
from unittest.mock import AsyncMock, patch

import pytest

from app.core.context_envelope import (
    ObjectEnvelope,
    ObjectType,
    Pillar,
    Provenance,
    TemporalValidity,
    Who,
)
from app.modules.context_engine.explanation_entries import create_explanation_entry
from app.modules.ui_composer.explanation import get_explanation_for_guide
from app.modules.ui_composer.tapering import get_tapering_context


@pytest.mark.anyio
async def test_get_explanation_for_guide_returns_entry_and_context():
    """The helper returns a tapered explanation plus the tapering context."""
    entry = await create_explanation_entry(
        subject="timeline",
        jurisdiction="MN",
        upl_risk_tier="LOW",
        pillar="RECORD",
        review_status="VETTED",
        variant_trust="Why this record matters.",
        variant_mechanics="What to log and why.",
        variant_reinforcement="Short reminder.",
        variant_minimal="Logged.",
    )

    request = types.SimpleNamespace(
        cookies={},
        state=types.SimpleNamespace(),
    )

    # Patch the exposure loader so the helper does not need a real DB session
    # or cookie plumbing; it only needs the exposure count for tapering.
    async def fake_load(request, object_type, db=None):
        from app.core.experience_token import ExperienceToken, record_exposure
        token = ExperienceToken()
        count, token = record_exposure(token, object_type)
        return token, False

    with patch(
        "app.modules.ui_composer.explanation.get_tapering_context",
        new=AsyncMock(side_effect=lambda request, object_type, db=None: {
            "intensity_level": "HIGH",
            "exposure_count": 1,
            "experience_token": None,
            "experience_token_saved_to_cloud": False,
        }),
    ):
        contract = types.SimpleNamespace(module="timeline", group_name="timeline_create_event")
        result = await get_explanation_for_guide(
            request,
            contract,
            Pillar.RECORD,
            "Create a dated timeline event to build a chronological record.",
            ["timeline", "record", "event", "chronology", "evidence"],
            db=None,
        )

    assert result["explanation"] is not None
    assert result["explanation"] == "What to log and why."
    assert result["tapering_ctx"]["exposure_count"] == 1
