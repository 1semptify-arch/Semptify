"""Auto-generated regression test for legal_filing_module."""

from tools.module_health import check_legal_filing_module


def test_legal_filing_module():
    """Verify legal_filing_module imports, has routes, and has no exposure issues."""
    ok, msg = check_legal_filing_module()
    assert ok, msg
