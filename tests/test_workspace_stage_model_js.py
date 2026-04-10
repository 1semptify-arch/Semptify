from pathlib import Path


def _workspace_stage_js() -> str:
    script_path = Path("static/js/workspace-stage-model.js")
    return script_path.read_text(encoding="utf-8")


def test_workspace_stage_model_calls_required_workflow_endpoints():
    source = _workspace_stage_js()

    assert "fetch('/api/workflow/case-state'" in source
    assert "fetch('/api/workflow/next-step'" in source
    assert "buildNextStepRequest(caseState)" in source


def test_workspace_stage_model_has_failure_fallback_path():
    source = _workspace_stage_js()

    assert "catch (_){" in source or "catch (_) {" in source
    assert "Workflow service unavailable. Refresh to retry." in source
    assert "next_action: 'connect_storage'" in source
    assert "next_route: '/storage/providers'" in source


def test_workspace_stage_model_handles_malformed_stage_cards_payload():
    source = _workspace_stage_js()

    assert "Array.isArray(payload.stage_cards) ? payload.stage_cards : []" in source
    assert "container.innerHTML = '';" in source


def test_workspace_stage_model_handles_malformed_alert_payload():
    source = _workspace_stage_js()

    assert "Array.isArray(payload.alerts) ? payload.alerts : []" in source
    assert "No urgent issues detected." in source


def test_workspace_stage_model_builds_safe_next_step_request_defaults():
    source = _workspace_stage_js()

    assert "role: caseState.role || 'user'" in source
    assert "storage_state: caseState.storage_connected ? 'already_connected' : 'need_connect'" in source
    assert "timeline_events: caseState.timeline_events || 0" in source
    assert "defense_started: !!caseState.defense_started" in source
    assert "court_packet_ready: !!caseState.court_packet_ready" in source
    assert "hearing_scheduled: !!caseState.hearing_scheduled" in source
