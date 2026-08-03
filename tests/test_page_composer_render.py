"""Tests for Page Composer to Page Shell rendering integration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.page_composer.models import PageAssemblyMetadata, PageAssemblyResult
from app.modules.page_shell.loader import load_page_config_from_file
from app.modules.page_shell.renderer import render_page_shell


def _assembly_result() -> PageAssemblyResult:
    config, govern_report = load_page_config_from_file(
        Path("app/modules/page_shell/sample_configs/record_focus_demo.json")
    )
    return PageAssemblyResult(
        page_config=config,
        components=[],
        govern_report=govern_report,
        metadata=PageAssemblyMetadata(
            subject="repair",
            jurisdiction="MN",
            major_pillar=config.major_pillar,
            blend=config.blend,
            intensity=42,
            risk_tier="medium",
        ),
    )


def test_page_shell_style_uses_html_safe_grid_area_quotes():
    html = render_page_shell(_assembly_result().page_config)

    style = html.split('style="', 1)[1].split('"', 1)[0]
    assert '"' not in style
    assert "grid-template-areas: 'record record know'" in style
    assert "grid-template-rows:" in style


@pytest.mark.anyio
async def test_page_composer_render_returns_page_shell_html(authenticated_client):
    result = _assembly_result()
    with patch(
        "app.modules.page_composer.router.assemble_page",
        new=AsyncMock(return_value=result),
    ):
        response = await authenticated_client.get("/api/page/repair/render")

    assert response.status_code == 200
    payload = response.json()
    assert "page-shell" in payload["html"]
    assert payload["skeleton"] == "record_focus"
    assert payload["blend"] == result.page_config.blend
    assert payload["metadata"]["subject"] == "repair"
    assert payload["config"]["page_id"] == result.page_config.page_id


@pytest.mark.anyio
async def test_page_composer_render_rejects_unknown_subject(authenticated_client):
    response = await authenticated_client.get("/api/page/not-a-subject/render")

    assert response.status_code == 400
    assert "Unknown subject" in response.json()["error"]["message"]


@pytest.mark.anyio
async def test_assembled_gui_page_returns_html(authenticated_client):
    result = _assembly_result()
    with patch(
        "app.modules.page_composer.assembly.assemble_page",
        new=AsyncMock(return_value=result),
    ):
        response = await authenticated_client.get("/gui/page/repair")

    assert response.status_code == 200
    assert "page-shell" in response.text
    assert "/static/page_shell/page_shell.css" in response.text


@pytest.mark.anyio
async def test_assembled_gui_page_rejects_unknown_subject(authenticated_client):
    response = await authenticated_client.get("/gui/page/not-a-subject")

    assert response.status_code == 404
