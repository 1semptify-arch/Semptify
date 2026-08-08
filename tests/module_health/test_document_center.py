"""Auto-generated regression test for document_center."""

from tools.module_health import check_document_center


def test_document_center():
    """Verify document_center imports, has routes, and has no exposure issues."""
    ok, msg = check_document_center()
    assert ok, msg
