"""Auto-generated regression test for agent_orchestrator."""

from tools.module_health import check_agent_orchestrator


def test_agent_orchestrator():
    """Verify agent_orchestrator imports, has routes, and has no exposure issues."""
    ok, msg = check_agent_orchestrator()
    assert ok, msg
