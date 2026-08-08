"""Auto-generated regression test for advanced."""

from tools.module_health import check_advanced


def test_advanced():
    """Verify advanced imports, has routes, and has no exposure issues."""
    ok, msg = check_advanced()
    assert ok, msg
