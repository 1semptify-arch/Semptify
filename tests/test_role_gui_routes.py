"""Role GUI route smoke tests to prevent dead-end pages."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/tenant",
        "/tenant/documents",
        "/tenant/timeline",
        "/tenant/help",
        "/advocate",
        "/advocate/clients",
        "/advocate/queue",
        "/advocate/intake",
        "/legal",
        "/legal/cases",
        "/legal/filings",
        "/legal/privileged",
        "/legal/conflicts",
        "/admin",
        "/admin/mission-control",
        "/admin/gui",
        "/admin/mode-selector",
        "/admin/easy-mode",
        "/admin/docs",
    ],
)
async def test_role_gui_routes_exist(client: AsyncClient, path: str):
    """Canonical role GUI routes should render or redirect, never 404."""
    response = await client.get(path, follow_redirects=False)
    assert response.status_code in (200, 302, 307), f"Unexpected status for {path}: {response.status_code}"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/legal/research",
        "/legal/library",
        "/admin/system",
        "/admin/users",
    ],
)
async def test_role_gui_alias_routes_do_not_dead_end(client: AsyncClient, path: str):
    """Alias routes should resolve to active destinations."""
    response = await client.get(path, follow_redirects=False)
    assert response.status_code in (200, 302, 307)
    if response.status_code in (302, 307):
        assert response.headers.get("location")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path,expected_snippet",
    [
        ("/static/advocate/calendar.html", "/timeline"),
        ("/static/legal/work-product.html", "/legal/privileged"),
        ("/static/legal/discovery.html", "/legal/filings"),
        ("/static/legal/calendar.html", "/timeline"),
        ("/static/legal/research.html", "/law-library"),
        ("/static/legal/notes.html", "/legal/privileged"),
        ("/static/tenant/calendar.html", "/timeline"),
    ],
)
async def test_legacy_static_gui_links_redirect_via_shims(
    client: AsyncClient,
    path: str,
    expected_snippet: str,
):
    """Legacy static links should serve shims that point users to active pages."""
    response = await client.get(path, follow_redirects=False)
    assert response.status_code == 200
    assert expected_snippet in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path,expected_home,cookie_user_id",
    [
        ("/tenant/missing", "/tenant", "GUabc12345"),
        ("/advocate/missing", "/advocate", "GVabc12345"),
        ("/legal/missing", "/legal", "GLabc12345"),
        ("/admin/missing", "/admin", "GAabc12345"),
    ],
)
async def test_unknown_role_subpages_redirect_home(
    client: AsyncClient,
    path: str,
    expected_home: str,
    cookie_user_id: str,
):
    """Unknown role subpages should bounce to role home, not 404."""
    response = await client.get(
        path,
        follow_redirects=False,
        cookies={"semptify_uid": cookie_user_id},
    )
    assert response.status_code in (302, 307)
    assert response.headers.get("location") == expected_home


@pytest.mark.anyio
async def test_role_home_redirects_to_storage_for_invalid_cookie(client: AsyncClient):
    """Protected role pages should send invalid storage identities to storage providers."""
    response = await client.get(
        "/tenant",
        follow_redirects=False,
        cookies={"semptify_uid": "abc"},
    )
    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "/storage/providers"


@pytest.mark.anyio
async def test_role_home_redirects_to_canonical_home_on_role_mismatch(client: AsyncClient):
    """Role mismatch should redirect to the user's canonical role home."""
    response = await client.get(
        "/tenant",
        follow_redirects=False,
        cookies={"semptify_uid": "GVabc12345"},
    )
    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "/advocate"
