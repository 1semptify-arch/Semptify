"""Auto-generated regression test for legal_analysis."""

from tools.module_health import check_legal_analysis


def test_legal_analysis():
    """Verify legal_analysis imports, has routes, and has no exposure issues."""
    ok, msg = check_legal_analysis()
    assert ok, msg
