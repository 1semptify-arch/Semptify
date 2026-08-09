"""Unit tests for the Page Composer assembly formula.

Covers each `major_pillar` branch, GOVERN floor clamping, GOVERN override
reporting, and the `very_high_do_not_build` safe fallback.
"""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.modules.page_composer.assembly import assemble_page
from app.modules.page_shell.models import OutputBlock


PAGE_DATA: dict[str, Any] = {
    "subject": "repair",
    "label": "Repair",
    "facts": [
        {
            "claim": "Landlord must repair conditions that affect health and safety.",
            "source_name": "MN Statute",
            "tags": ["law"],
        }
    ],
    "stories": [],
    "case": None,
}


def _patch_assembly(page_data: dict[str, Any] | None = None, gather_blocks=None):
    """Return a context manager that stubs external dependencies."""
    data = page_data if page_data is not None else PAGE_DATA
    stack = ExitStack()
    stack.enter_context(patch("app.modules.page_composer.assembly.compose_page", new=AsyncMock(return_value=data)))
    stack.enter_context(patch("app.modules.page_composer.assembly.ui_compose_page", new=Mock(return_value={"components": [{"type": "mock"}]})))
    stack.enter_context(patch("app.services.context_loop.context_loop.get_state", new=Mock(return_value={})))
    if gather_blocks is not None:
        stack.enter_context(patch("app.modules.page_composer.assembly._gather_blocks", new=gather_blocks))
    return stack


@pytest.mark.anyio
async def test_assemble_page_intent_record_selects_record_pillar():
    with _patch_assembly():
        result = await assemble_page(
            subject="repair",
            jurisdiction="MN",
            user_id="GUowner123",
            intent="record",
        )

    assert result.metadata.major_pillar == "record"
    assert result.metadata.blend == "quiet_capture"
    assert result.page_config.channels.record == 90
    assert result.page_config.major_pillar == "record"


@pytest.mark.anyio
async def test_assemble_page_intent_learn_selects_know_pillar():
    with _patch_assembly():
        result = await assemble_page(
            subject="repair",
            jurisdiction="MN",
            user_id="GUowner123",
            intent="learn",
        )

    assert result.metadata.major_pillar == "know"
    assert result.metadata.blend == "orientation"
    assert result.page_config.channels.know == 80


@pytest.mark.anyio
async def test_assemble_page_active_case_selects_act_pillar():
    context = {"urgency_cues": ["deadline_soon"], "case_count": 1}
    with _patch_assembly(page_data={**PAGE_DATA, "case": {"count": 1, "items": [{"id": "c1", "title": "Repair case"}]}}):
        result = await assemble_page(
            subject="repair",
            jurisdiction="MN",
            user_id="GUowner123",
            context=context,
        )

    assert result.metadata.major_pillar == "act"
    assert result.metadata.blend == "urgent_action"
    assert result.page_config.channels.act == 90


@pytest.mark.anyio
async def test_assemble_page_eviction_selects_govern_and_clamps_floor():
    with _patch_assembly():
        result = await assemble_page(
            subject="eviction",
            jurisdiction="MN",
            user_id="GUowner123",
        )

    assert result.metadata.major_pillar == "govern"
    assert result.metadata.blend == "urgent_action"
    assert result.metadata.risk_tier == "high"
    assert result.govern_report["govern_clamped"] is True
    assert result.govern_report["govern_effective"] == 80
    assert result.page_config.channels.govern == 80


@pytest.mark.anyio
async def test_assemble_page_very_high_risk_returns_govern_fallback():
    with _patch_assembly():
        result = await assemble_page(
            subject="unlawful_detainer",
            jurisdiction="MN",
            user_id="GUowner123",
        )

    assert result.metadata.major_pillar == "govern"
    assert result.metadata.blend == "govern_fallback"
    assert result.metadata.risk_tier == "very_high_do_not_build"
    assert result.govern_report["fallback"] is True
    assert result.page_config.channels.govern == 100
    assert result.page_config.channels.record == 0
    assert result.page_config.channels.act == 0
    assert result.page_config.zones["govern"].blocks
    assert result.components == []


@pytest.mark.anyio
async def test_govern_override_reports_suppressed_act_block():
    def fake_gather(page_data, context):
        return {
            "record": [],
            "know": [],
            "act": [
                OutputBlock(
                    block_id="act_file_complaint",
                    action_type="button",
                    label="File complaint",
                    risk_tier="low",
                    on_trigger="/complaints/file",
                )
            ],
            "govern": [
                OutputBlock(
                    block_id="govern_time_barred",
                    action_type="banner",
                    label="Deadline has passed; do not file.",
                    risk_tier="high",
                    on_trigger="/legal-aid",
                    suppresses_act_block="act_file_complaint",
                )
            ],
        }

    with _patch_assembly(gather_blocks=fake_gather):
        result = await assemble_page(
            subject="security_deposit",
            jurisdiction="MN",
            user_id="GUowner123",
        )

    assert result.govern_report["suppressed_act_blocks"] == ["act_file_complaint"]
