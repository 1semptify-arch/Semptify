"""LoadProfile resolution: render_balanced flags + selection paths."""
import os
from unittest.mock import patch

from app.core.runtime_profile import get_active_profile


def test_render_balanced_flags():
    with patch.dict(os.environ, {"LOAD_PROFILE": "render_balanced"}):
        p = get_active_profile()
    assert p.name == "render_balanced"
    assert p.flags() == {
        "positronic_brain": False,
        "module_hub": True,
        "mesh_network": False,
        "embedding_model": True,
        "performance_monitoring": False,
    }


def test_render_balanced_via_override_not_default():
    # DEPLOY_TARGET alone still derives render_mvp — balanced is opt-in.
    env = {"DEPLOY_TARGET": "render_mvp"}
    with patch.dict(os.environ, env, clear=True):
        assert get_active_profile().name == "render_mvp"
    env["LOAD_PROFILE"] = "render_balanced"
    with patch.dict(os.environ, env, clear=True):
        assert get_active_profile().name == "render_balanced"


def test_unknown_profile_falls_back():
    env = {"DEPLOY_TARGET": "render_mvp", "LOAD_PROFILE": "bogus"}
    with patch.dict(os.environ, env, clear=True):
        assert get_active_profile().name == "render_mvp"
