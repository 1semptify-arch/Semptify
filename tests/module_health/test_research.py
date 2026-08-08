"""Auto-generated regression test for research."""

from tools.module_health import check_research


def test_research():
    """Verify research imports, has routes, and has no exposure issues."""
    ok, msg = check_research()
    assert ok, msg
