"""End-to-end tests for the Page Composer assembly API endpoints."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest


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


def _assembly_patches(page_data: dict[str, Any] | None = None):
    """Return a context manager that stubs upstream dependencies."""
    data = page_data if page_data is not None else PAGE_DATA
    stack = ExitStack()
    stack.enter_context(patch("app.modules.page_composer.assembly.compose_page", new=AsyncMock(return_value=data)))
    stack.enter_context(patch("app.modules.page_composer.assembly.ui_compose_page", new=Mock(return_value={"components": [{"type": "mock"}]})))
    stack.enter_context(patch("app.modules.context_loop.service.context_loop.get_state", new=Mock(return_value={})))
    return stack


@pytest.mark.anyio
async def test_post_assemble_returns_page_config_and_metadata(authenticated_client):
    with _assembly_patches():
        response = await authenticated_client.post(
            "/api/page/assemble",
            json={"subject": "repair", "jurisdiction": "MN"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_config"]["major_pillar"] == "act"
    assert payload["metadata"]["subject"] == "repair"
    assert payload["metadata"]["blend"]
    assert "components" in payload
    assert "govern_report" in payload


@pytest.mark.anyio
async def test_post_assemble_with_render_flag_includes_html(authenticated_client):
    with _assembly_patches():
        response = await authenticated_client.post(
            "/api/page/assemble",
            json={"subject": "repair", "jurisdiction": "MN", "render": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "html" in payload
    assert "page-shell" in payload["html"]


@pytest.mark.anyio
async def test_get_assemble_returns_page_config(authenticated_client):
    with _assembly_patches():
        response = await authenticated_client.get("/api/page/repair/assemble")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_config"]["major_pillar"] == "act"
    assert payload["metadata"]["subject"] == "repair"


@pytest.mark.anyio
async def test_get_render_returns_html_and_skeleton(authenticated_client):
    with _assembly_patches():
        response = await authenticated_client.get("/api/page/repair/render")

    assert response.status_code == 200
    payload = response.json()
    assert "html" in payload
    assert "page-shell" in payload["html"]
    assert payload["skeleton"]
    assert payload["blend"]


@pytest.mark.anyio
async def test_post_assemble_very_high_risk_returns_govern_fallback(authenticated_client):
    with _assembly_patches():
        response = await authenticated_client.post(
            "/api/page/assemble",
            json={
                "subject": "repair",
                "jurisdiction": "MN",
                "context": {"risk_tier": "very_high_do_not_build"},
                "render": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["major_pillar"] == "govern"
    assert payload["metadata"]["blend"] == "govern_fallback"
    assert payload["govern_report"]["fallback"] is True
    assert payload["page_config"]["channels"]["govern"] == 100
    assert payload["page_config"]["channels"]["act"] == 0
    assert "html" in payload
    assert "page-shell" in payload["html"]


@pytest.mark.anyio
async def test_post_assemble_rejects_unknown_subject(authenticated_client):
    response = await authenticated_client.post(
        "/api/page/assemble",
        json={"subject": "not-a-subject", "jurisdiction": "MN"},
    )

    assert response.status_code == 400
    assert "Unknown subject" in response.text


@pytest.mark.anyio
async def test_get_assemble_rejects_unknown_subject(authenticated_client):
    response = await authenticated_client.get("/api/page/not-a-subject/assemble")

    assert response.status_code == 400
    assert "Unknown subject" in response.text
