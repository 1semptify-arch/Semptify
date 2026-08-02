"""Auto-generated regression test for documentation."""

from tools.module_health import check_documentation


def test_documentation():
    """Verify documentation imports, has routes, and has no exposure issues."""
    ok, msg = check_documentation()
    assert ok, msg
