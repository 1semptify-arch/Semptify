"""Regression guard for admin-login availability under DEPLOY_TARGET=render_mvp.

Incident (task-262491a5 / intake-830ab9ec): on deploy be3026ec the
/admin/login page rendered a working-looking form while POST
/admin/api/login-step1 and /login-step2 returned 404 — admin_auth and
admin_api were ADMIN tier and excluded from the MVP allowlist. Brad's
2026-11-11 decision (PR #340) allow-listed both routers; these tests keep
that from regressing and pin the login page's honest "unavailable" state
for any deployment where the API is not mounted.
"""

import pytest
from fastapi import FastAPI

from app.core.admin_gating import admin_login_api_mounted
from app.core.product_manifest import (
    ProductTier,
    get_mvp_allowed_modules,
    register_tiers,
)


def test_admin_routers_in_mvp_allowlist():
    allowed = get_mvp_allowed_modules()
    assert "app.modules.admin_auth.router" in allowed
    assert "app.modules.admin_api.router" in allowed


def test_render_mvp_mounts_admin_login_api(monkeypatch):
    """register_tiers under DEPLOY_TARGET=render_mvp must mount the login API."""
    monkeypatch.setenv("DEPLOY_TARGET", "render_mvp")
    app = FastAPI()
    register_tiers(
        app,
        ProductTier.CORE,
        ProductTier.EXTENDED,
        ProductTier.ADVOCATE,
        ProductTier.ADMIN,
        ProductTier.RESEARCH,
        ProductTier.DEV,
    )
    assert app.url_path_for("admin_login_step1") == "/admin/api/login-step1"
    assert app.url_path_for("admin_login_step2") == "/admin/api/login-step2"
    assert app.url_path_for("admin_verify_api") == "/admin/api/verify"


def test_admin_login_api_mounted_helper():
    """The login page's mount check is False without the router, True with it."""
    from app.modules.admin_auth.router import router as admin_auth_router

    bare = FastAPI()
    assert admin_login_api_mounted(bare) is False

    bare.include_router(admin_auth_router)
    assert admin_login_api_mounted(bare) is True


async def test_admin_login_page_renders_form_when_api_mounted(client):
    """On a normal build /admin/login serves the login form (not the 503 state)."""
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    assert 'id="step1"' in resp.text
    assert "not available on this deployment" not in resp.text
