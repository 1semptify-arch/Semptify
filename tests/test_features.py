"""Tests for app.core.features — current DB-backed feature flag manager."""

import pytest

from app.core.features import (
    DEFAULT_ENABLED,
    ROUTE_FEATURE_MAP,
    ROUTE_GATE_FLAGS,
    Feature,
    FeatureFlagManager,
    RouteFeatureGateMiddleware,
    features,
    require_feature,
    require_feature_for_user,
    route_feature_for_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fresh_manager() -> FeatureFlagManager:
    """Return a manager that ignores process-wide env overrides for isolation."""
    m = FeatureFlagManager()
    m._env_loaded = False
    m._env_overrides = {}
    m._cache = {}
    m._cache_detail = {}
    m._cache_loaded_at = 0.0
    return m


# ---------------------------------------------------------------------------
# Feature enum
# ---------------------------------------------------------------------------
class TestFeatureEnum:
    def test_is_str_enum(self):
        assert isinstance(Feature.AI_COPILOT, str)
        assert Feature.AI_COPILOT == "ai_copilot"

    def test_has_expected_members(self):
        names = {f.name for f in Feature}
        assert "AI_COPILOT" in names
        assert "BETA_DASHBOARD" in names
        assert "REDIS_CACHE" in names
        assert "RATE_LIMITING" in names


# ---------------------------------------------------------------------------
# DEFAULT_ENABLED
# ---------------------------------------------------------------------------
class TestDefaultEnabled:
    def test_core_features_enabled(self):
        assert DEFAULT_ENABLED[Feature.AI_COPILOT.value] is True
        assert DEFAULT_ENABLED[Feature.AI_DOCUMENT_ANALYSIS.value] is True

    def test_experimental_features_disabled(self):
        assert DEFAULT_ENABLED[Feature.EXPERIMENTAL_AI_MODEL.value] is False
        assert DEFAULT_ENABLED[Feature.EXPERIMENTAL_UI.value] is False


# ---------------------------------------------------------------------------
# FeatureFlagManager
# ---------------------------------------------------------------------------
class TestFeatureFlagManager:
    @pytest.mark.anyio
    async def test_is_enabled_default_true(self):
        m = _fresh_manager()
        assert await m.is_enabled(Feature.AI_COPILOT) is True

    @pytest.mark.anyio
    async def test_is_enabled_default_false(self):
        m = _fresh_manager()
        assert await m.is_enabled(Feature.EXPERIMENTAL_AI_MODEL) is False

    @pytest.mark.anyio
    async def test_is_enabled_env_override(self, monkeypatch):
        monkeypatch.setenv("FEATURE_AI_COPILOT", "false")
        m = _fresh_manager()
        assert await m.is_enabled(Feature.AI_COPILOT) is False

    @pytest.mark.anyio
    async def test_is_enabled_env_override_true_variants(self, monkeypatch):
        for val in ("true", "1", "yes", "on"):
            monkeypatch.setenv("FEATURE_EXPERIMENTAL_AI_MODEL", val)
            m = _fresh_manager()
            assert await m.is_enabled(Feature.EXPERIMENTAL_AI_MODEL) is True, f"Failed for {val}"

    @pytest.mark.anyio
    async def test_is_enabled_for_user_default(self):
        m = _fresh_manager()
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u1") is True

    @pytest.mark.anyio
    async def test_is_enabled_for_user_rollout_zero(self):
        m = _fresh_manager()
        await m._ensure_fresh()
        m._cache_detail[Feature.AI_COPILOT.value]["rollout_percent"] = 0
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u1") is False

    @pytest.mark.anyio
    async def test_is_enabled_for_user_rollout_100(self):
        m = _fresh_manager()
        await m._ensure_fresh()
        m._cache_detail[Feature.AI_COPILOT.value]["rollout_percent"] = 100
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u1") is True

    @pytest.mark.anyio
    async def test_is_enabled_for_role_allowed(self):
        m = _fresh_manager()
        await m._ensure_fresh()
        m._cache_detail[Feature.AI_COPILOT.value]["allowed_roles"] = ["admin"]
        assert await m.is_enabled_for_role(Feature.AI_COPILOT, "admin") is True

    @pytest.mark.anyio
    async def test_is_enabled_for_role_denied(self):
        m = _fresh_manager()
        await m._ensure_fresh()
        m._cache_detail[Feature.AI_COPILOT.value]["allowed_roles"] = ["admin"]
        assert await m.is_enabled_for_role(Feature.AI_COPILOT, "user") is False

    @pytest.mark.anyio
    async def test_get_all_flags(self):
        m = _fresh_manager()
        flags = await m.get_all_flags()
        assert isinstance(flags, dict)
        assert "ai_copilot" in flags
        assert "enabled" in flags["ai_copilot"]
        assert "rollout_percent" in flags["ai_copilot"]

    @pytest.mark.anyio
    async def test_get_status(self):
        m = _fresh_manager()
        status = await m.get_status()
        assert isinstance(status, dict)
        assert status["total_features"] == len(Feature)
        assert "enabled_features" in status
        assert "disabled_features" in status

    def test_invalidate_cache(self):
        m = _fresh_manager()
        m._cache_loaded_at = 123.0
        m.invalidate_cache()
        assert m._cache_loaded_at == 0.0


# ---------------------------------------------------------------------------
# require_feature decorators
# ---------------------------------------------------------------------------
class TestRequireFeatureDecorator:
    @pytest.mark.anyio
    async def test_passes_when_enabled(self):
        @require_feature(Feature.AI_COPILOT)
        async def endpoint():
            return "ok"

        assert await endpoint() == "ok"

    @pytest.mark.anyio
    async def test_raises_when_disabled(self):
        from fastapi import HTTPException

        original = features._env_overrides.get(Feature.EXPERIMENTAL_AI_MODEL.value)
        features._env_overrides[Feature.EXPERIMENTAL_AI_MODEL.value] = False
        features._env_loaded = True

        @require_feature(Feature.EXPERIMENTAL_AI_MODEL)
        async def endpoint():
            return "ok"

        try:
            with pytest.raises(HTTPException):
                await endpoint()
        finally:
            if original is None:
                features._env_overrides.pop(Feature.EXPERIMENTAL_AI_MODEL.value, None)
            else:
                features._env_overrides[Feature.EXPERIMENTAL_AI_MODEL.value] = original

    @pytest.mark.anyio
    async def test_require_feature_for_user_passes(self):
        @require_feature_for_user(Feature.AI_COPILOT, user_id_param="user_id")
        async def endpoint(user_id: str):
            return "ok"

        assert await endpoint(user_id="u1") == "ok"


# ---------------------------------------------------------------------------
# Route kill-switches — migrated from app/core/feature_flags.py (2026-08-26)
# ---------------------------------------------------------------------------
class TestRouteFeatureGate:
    def test_route_feature_map_matches_old_prefixes(self):
        """The old ROUTE_FLAG_MAP prefixes must all still be gated by something."""
        expected_prefixes = {
            "/admin",
            "/api/copilot",
            "/tenant/copilot",
            "/api/voice",
            "/api/import",
            "/api/resources",
            "/tenant/resources",
        }
        assert expected_prefixes == set(ROUTE_FEATURE_MAP.keys())

    def test_route_feature_for_path_resolves_admin(self):
        assert route_feature_for_path("/admin/dashboard") == Feature.ADMIN_ACCESS

    def test_route_feature_for_path_resolves_copilot(self):
        assert route_feature_for_path("/api/copilot/chat") == Feature.COPILOT_ROUTE
        assert route_feature_for_path("/tenant/copilot/chat") == Feature.COPILOT_ROUTE

    def test_route_feature_for_path_ungated_returns_none(self):
        assert route_feature_for_path("/api/journal/") is None

    def test_route_gate_flags_default_true(self):
        """Route kill-switches must default to enabled, matching the old
        in-memory feature_flags.py defaults, so migration is a no-op for
        current behavior."""
        for flag_name in ROUTE_GATE_FLAGS:
            assert DEFAULT_ENABLED[flag_name] is True

    @pytest.mark.anyio
    async def test_middleware_allows_enabled_route(self):
        middleware = RouteFeatureGateMiddleware(app=None)

        request = type("R", (), {"url": type("U", (), {"path": "/api/journal/"})()})()

        async def call_next(_request):
            return "next-called"

        result = await middleware.dispatch(request, call_next)
        assert result == "next-called"

    @pytest.mark.anyio
    async def test_middleware_blocks_disabled_route(self, monkeypatch):
        monkeypatch.setenv("FEATURE_ADMIN_ACCESS", "false")
        features._env_loaded = False
        features._env_overrides = {}

        middleware = RouteFeatureGateMiddleware(app=None)
        request = type("R", (), {"url": type("U", (), {"path": "/admin/dashboard"})()})()

        async def call_next(_request):
            raise AssertionError("call_next should not run when the flag is disabled")

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 503

        features._env_loaded = False
        features._env_overrides = {}
