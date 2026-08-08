"""Auto-generated regression test for law_library."""

from tools.module_health import check_law_library


def test_law_library():
    """Verify law_library imports, has routes, and has no exposure issues."""
    ok, msg = check_law_library()
    assert ok, msg
