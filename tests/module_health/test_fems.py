"""Auto-generated regression test for fems."""

from tools.module_health import check_fems


def test_fems():
    """Verify fems imports, has routes, and has no exposure issues."""
    ok, msg = check_fems()
    assert ok, msg
