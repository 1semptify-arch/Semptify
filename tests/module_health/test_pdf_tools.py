"""Auto-generated regression test for pdf_tools."""

from tools.module_health import check_pdf_tools


def test_pdf_tools():
    """Verify pdf_tools imports, has routes, and has no exposure issues."""
    ok, msg = check_pdf_tools()
    assert ok, msg
