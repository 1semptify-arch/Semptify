"""Auto-generated regression test for preamble."""

from tools.module_health import check_preamble


def test_preamble():
    """Verify preamble imports, has routes, and has no exposure issues."""
    ok, msg = check_preamble()
    assert ok, msg
