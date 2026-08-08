"""Auto-generated regression test for document_converter."""

from tools.module_health import check_document_converter


def test_document_converter():
    """Verify document_converter imports, has routes, and has no exposure issues."""
    ok, msg = check_document_converter()
    assert ok, msg
