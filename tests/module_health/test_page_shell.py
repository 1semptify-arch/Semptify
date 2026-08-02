"""Auto-generated regression test for page_shell."""

from tools.module_health import check_page_shell


def test_page_shell():
    """Verify page_shell imports, has routes, and has no exposure issues."""
    ok, msg = check_page_shell()
    assert ok, msg
