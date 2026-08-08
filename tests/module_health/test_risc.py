"""Auto-generated regression test for risc."""

from tools.module_health import check_risc


def test_risc():
    """Verify risc imports, has routes, and has no exposure issues."""
    ok, msg = check_risc()
    assert ok, msg
