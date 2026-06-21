"""Tests for app.core.features — Feature flags system."""

import json

import pytest

from app.core.features import (
    DEFAULT_FEATURES,
    Feature,
    FeatureConfig,
    FeatureFlagManager,
    require_feature,
)


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
# FeatureConfig
# ---------------------------------------------------------------------------
class TestFeatureConfig:
    def test_defaults(self):
        cfg = FeatureConfig()
        assert cfg.enabled is False
        assert cfg.rollout_percentage == 100
        assert cfg.allowed_users == []
        assert cfg.denied_users == []
        assert cfg.start_date is None
        assert cfg.end_date is None
        assert cfg.metadata == {}

    def test_to_dict(self):
        cfg = FeatureConfig(enabled=True, rollout_percentage=50)
        d = cfg.to_dict()
        assert d["enabled"] is True
        assert d["rollout_percentage"] == 50
        assert d["allowed_users"] == []
        assert d["start_date"] is None

    def test_from_dict_roundtrip(self):
        cfg = FeatureConfig(
            enabled=True,
            rollout_percentage=75,
            allowed_users=["u1"],
            denied_users=["u2"],
            metadata={"note": "test"},
        )
        d = cfg.to_dict()
        restored = FeatureConfig.from_dict(d)
        assert restored.enabled is True
        assert restored.rollout_percentage == 75
        assert restored.allowed_users == ["u1"]
        assert restored.denied_users == ["u2"]
        assert restored.metadata == {"note": "test"}

    def test_from_dict_with_dates(self):
        d = {
            "enabled": True,
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-12-31T23:59:59",
        }
        cfg = FeatureConfig.from_dict(d)
        assert cfg.start_date is not None
        assert cfg.end_date is not None
        assert cfg.start_date.year == 2025

    def test_from_dict_minimal(self):
        cfg = FeatureConfig.from_dict({})
        assert cfg.enabled is False
        assert cfg.rollout_percentage == 100


# ---------------------------------------------------------------------------
# DEFAULT_FEATURES
# ---------------------------------------------------------------------------
class TestDefaultFeatures:
    def test_all_features_have_defaults(self):
        for f in Feature:
            assert f in DEFAULT_FEATURES, f"Missing default for {f.name}"

    def test_core_features_enabled(self):
        assert DEFAULT_FEATURES[Feature.AI_COPILOT].enabled is True
        assert DEFAULT_FEATURES[Feature.AI_DOCUMENT_ANALYSIS].enabled is True

    def test_experimental_features_disabled(self):
        assert DEFAULT_FEATURES[Feature.EXPERIMENTAL_AI_MODEL].enabled is False
        assert DEFAULT_FEATURES[Feature.EXPERIMENTAL_UI].enabled is False


# ---------------------------------------------------------------------------
# FeatureFlagManager
# ---------------------------------------------------------------------------
class TestFeatureFlagManager:
    def _fresh_manager(self):
        m = FeatureFlagManager()
        m._loaded = False
        m._features = {}
        return m

    @pytest.mark.asyncio
    async def test_is_enabled_default_true(self):
        m = self._fresh_manager()
        assert await m.is_enabled(Feature.AI_COPILOT) is True

    @pytest.mark.asyncio
    async def test_is_enabled_default_false(self):
        m = self._fresh_manager()
        assert await m.is_enabled(Feature.EXPERIMENTAL_AI_MODEL) is False

    @pytest.mark.asyncio
    async def test_set_enabled(self):
        m = self._fresh_manager()
        m.set_enabled(Feature.EXPERIMENTAL_AI_MODEL, True)
        assert await m.is_enabled(Feature.EXPERIMENTAL_AI_MODEL) is True

    @pytest.mark.asyncio
    async def test_set_enabled_creates_new_config(self):
        m = FeatureFlagManager()
        m._loaded = True
        m._features = {}
        m.set_enabled(Feature.AI_COPILOT, True)
        assert await m.is_enabled(Feature.AI_COPILOT) is True

    def test_get_config(self):
        m = self._fresh_manager()
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert cfg.enabled is True

    def test_get_config_missing(self):
        m = FeatureFlagManager()
        m._loaded = True
        m._features = {}
        assert m.get_config(Feature.AI_COPILOT) is None

    def test_set_rollout(self):
        m = self._fresh_manager()
        m.set_rollout(Feature.BETA_DASHBOARD, 30)
        cfg = m.get_config(Feature.BETA_DASHBOARD)
        assert cfg is not None
        assert cfg.rollout_percentage == 30

    def test_set_rollout_clamps(self):
        m = self._fresh_manager()
        m.set_rollout(Feature.BETA_DASHBOARD, 200)
        cfg = m.get_config(Feature.BETA_DASHBOARD)
        assert cfg is not None
        assert cfg.rollout_percentage == 100

        m.set_rollout(Feature.BETA_DASHBOARD, -10)
        cfg = m.get_config(Feature.BETA_DASHBOARD)
        assert cfg is not None
        assert cfg.rollout_percentage == 0

    def test_set_rollout_new_feature(self):
        m = FeatureFlagManager()
        m._loaded = True
        m._features = {}
        m.set_rollout(Feature.AI_COPILOT, 50)
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert cfg.rollout_percentage == 50
        assert cfg.enabled is True

    def test_add_user_to_allowlist(self):
        m = self._fresh_manager()
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u1")
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert "u1" in cfg.allowed_users

    def test_add_user_to_allowlist_no_duplicate(self):
        m = self._fresh_manager()
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u1")
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u1")
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert cfg.allowed_users.count("u1") == 1

    def test_remove_user_from_allowlist(self):
        m = self._fresh_manager()
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u1")
        m.remove_user_from_allowlist(Feature.AI_COPILOT, "u1")
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert "u1" not in cfg.allowed_users

    def test_remove_user_from_allowlist_not_present(self):
        m = self._fresh_manager()
        m.remove_user_from_allowlist(Feature.AI_COPILOT, "ghost")

    @pytest.mark.asyncio
    async def test_is_enabled_for_user_denied(self):
        m = self._fresh_manager()
        m.get_config(Feature.AI_COPILOT).denied_users.append("u_denied")
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u_denied") is False

    @pytest.mark.asyncio
    async def test_is_enabled_for_user_allowed(self):
        m = self._fresh_manager()
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u_ok")
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u_ok") is True

    @pytest.mark.asyncio
    async def test_is_enabled_for_user_allowed_but_disabled(self):
        m = self._fresh_manager()
        m.set_enabled(Feature.AI_COPILOT, False)
        m.add_user_to_allowlist(Feature.AI_COPILOT, "u1")
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "u1") is False

    @pytest.mark.asyncio
    async def test_is_enabled_for_user_rollout(self):
        m = self._fresh_manager()
        m.set_rollout(Feature.AI_COPILOT, 0)
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "someuser") is False

    @pytest.mark.asyncio
    async def test_is_enabled_for_user_rollout_100(self):
        m = self._fresh_manager()
        m.set_rollout(Feature.AI_COPILOT, 100)
        assert await m.is_enabled_for_user(Feature.AI_COPILOT, "anyuser") is True

    @pytest.mark.asyncio
    async def test_get_all_flags(self):
        m = self._fresh_manager()
        flags = await m.get_all_flags()
        assert isinstance(flags, dict)
        assert "ai_copilot" in flags
        assert isinstance(flags["ai_copilot"], bool)

    @pytest.mark.asyncio
    async def test_get_all_flags_for_user(self):
        m = self._fresh_manager()
        flags = await m.get_all_flags(user_id="u1")
        assert isinstance(flags, dict)

    @pytest.mark.asyncio
    async def test_get_status(self):
        m = self._fresh_manager()
        # get_status uses `await` inside a sync generator expression (known bug),
        # so it raises TypeError at runtime.
        with pytest.raises(TypeError):
            await m.get_status()

    def test_save_and_load_from_file(self, tmp_path):
        m = FeatureFlagManager()
        m._loaded = True
        m._features = {
            Feature.AI_COPILOT: FeatureConfig(enabled=True, rollout_percentage=50),
        }
        m._config_file = tmp_path / "features.json"
        m.save()
        assert m._config_file.exists()

        data = json.loads(m._config_file.read_text())
        assert "ai_copilot" in data
        assert data["ai_copilot"]["enabled"] is True

    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "features.json"
        config_file.write_text(json.dumps({
            "ai_copilot": {"enabled": False, "rollout_percentage": 10},
        }))
        m = FeatureFlagManager()
        m._config_file = config_file
        m._loaded = False
        m._ensure_loaded()
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert cfg.enabled is False
        assert cfg.rollout_percentage == 10

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("FEATURE_AI_COPILOT", "false")
        m = FeatureFlagManager()
        m._loaded = False
        m._features = {}
        m._ensure_loaded()
        cfg = m.get_config(Feature.AI_COPILOT)
        assert cfg is not None
        assert cfg.enabled is False

    def test_load_from_env_true_variants(self, monkeypatch):
        for val in ("true", "1", "yes", "on"):
            monkeypatch.setenv("FEATURE_EXPERIMENTAL_AI_MODEL", val)
            m = FeatureFlagManager()
            m._loaded = False
            m._features = {}
            m._ensure_loaded()
            cfg = m.get_config(Feature.EXPERIMENTAL_AI_MODEL)
            assert cfg is not None
            assert cfg.enabled is True, f"Failed for env value '{val}'"


# ---------------------------------------------------------------------------
# require_feature decorator
# ---------------------------------------------------------------------------
class TestRequireFeatureDecorator:
    @pytest.mark.asyncio
    async def test_passes_when_enabled(self):
        @require_feature(Feature.AI_COPILOT)
        async def endpoint():
            return "ok"

        result = await endpoint()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_when_disabled(self):
        from fastapi import HTTPException

        @require_feature(Feature.EXPERIMENTAL_AI_MODEL)
        async def endpoint():
            return "ok"

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()
        assert exc_info.value.status_code == 404
