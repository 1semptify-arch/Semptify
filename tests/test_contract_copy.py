from app.core.contract_copy import get_display


def test_generic_contract_strips_markers_and_capitalizes():
    title, desc = get_display(
        {
            "title": "Core System Health Check (SSOT)",
            "description": "CANONICAL health check for core system.",
            "module": "core_system",
            "group_name": "core_system_health_check",
        }
    )
    assert title == "Health Check"
    assert desc == "Health check for core system."


def test_override_wins():
    title, _ = get_display({"module": "journal", "group_name": "journal_create", "title": "x (SSOT)"})
    assert title == "Write a journal note"
