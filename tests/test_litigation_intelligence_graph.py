"""Tests for the litigation intelligence graph engine endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.cookie_auth import sign_user_id
from app.main import app


def _client() -> AsyncClient:
    """Return an async test client with a valid signed user cookie."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set("semptify_uid", sign_user_id("GU7x9kM2pQ"))
    return client


@pytest.mark.anyio
async def test_graph_build_returns_graph_data():
    """POST /api/litigation-intelligence/graph/build returns nodes and edges."""
    payload = {
        "entities": [
            {"id": "tenant_1", "name": "Tenant A", "type": "person"},
            {"id": "landlord_x", "name": "Landlord X", "type": "person"},
            {"id": "case_123", "name": "Case 123", "type": "case"},
        ],
        "relationship_data": [
            {"source": "tenant_1", "target": "case_123", "type": "party_in", "weight": 1.0},
            {"source": "landlord_x", "target": "case_123", "type": "party_in", "weight": 1.0},
        ],
    }
    async with _client() as client:
        response = await client.post("/api/litigation-intelligence/graph/build", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["graph"]["node_count"] == 3
    assert data["graph"]["edge_count"] == 2


@pytest.mark.anyio
async def test_graph_shortest_path():
    """Shortest path finds the connection between two entities."""
    payload = {
        "entities": [
            {"id": "a", "name": "A"},
            {"id": "b", "name": "B"},
            {"id": "c", "name": "C"},
            {"id": "d", "name": "D"},
        ],
        "relationship_data": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "d"},
        ],
    }
    async with _client() as client:
        response = await client.post("/api/litigation-intelligence/graph/path/a/d", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["path"] == ["a", "b", "c", "d"]


@pytest.mark.anyio
async def test_graph_visualization_returns_data():
    """Visualization endpoint returns a base64 PNG or SVG image payload."""
    payload = {
        "entities": [
            {"id": "x", "name": "X"},
            {"id": "y", "name": "Y"},
        ],
        "relationship_data": [{"source": "x", "target": "y"}],
        "visualization_options": {"format": "png"},
    }
    async with _client() as client:
        response = await client.post("/api/litigation-intelligence/graph/visualize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    viz = data["visualization"]
    assert viz["format"] in ("png", "svg")
    assert viz["data"]


@pytest.mark.anyio
async def test_lis_statistics_includes_graph():
    """GET /api/litigation-intelligence/statistics returns graph statistics."""
    async with _client() as client:
        response = await client.get("/api/litigation-intelligence/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "graph" in data["statistics"]
    assert "node_count" in data["statistics"]["graph"]
    assert data["statistics"]["graph"]["status"] == "operational"
