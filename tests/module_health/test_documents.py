"""Auto-generated regression test for documents."""

from tools.module_health import check_documents


def test_documents():
    """Verify documents imports, has routes, and has no exposure issues."""
    ok, msg = check_documents()
    assert ok, msg
