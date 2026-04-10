import pytest
from app.services.positronic_brain import get_brain


@pytest.mark.anyio
async def test_workflow_route_returns_tenant_b2_when_documents_present(client):
    response = await client.post(
        "/api/workflow/route",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_process"] == "B2"
    assert payload["next_route"] == "/tenant"


@pytest.mark.anyio
async def test_workflow_route_infers_documents_present_from_overlay_ids(client):
    response = await client.post(
        "/api/workflow/route",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": False,
            "overlay_record_ids": ["ovl_abc123"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_process"] == "B2"
    assert payload["next_route"] == "/tenant"


@pytest.mark.anyio
async def test_workflow_route_returns_role_specific_professional_route(client):
    response = await client.post(
        "/api/workflow/route",
        json={
            "role": "legal",
            "storage_state": "already_connected",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_process"] == "B4"
    assert payload["next_route"] == "/legal"
    assert "generate_court_filing" in payload["allowed_actions"]


@pytest.mark.anyio
async def test_workflow_contract_endpoint_returns_welcome_contract(client):
    response = await client.get("/api/workflow/contracts/welcome")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_id"] == "welcome"
    assert payload["route"] == "/"
    assert payload["group_coverage"]["welcome"] == "active"


@pytest.mark.anyio
async def test_workflow_contract_endpoint_returns_tenant_help_contract(client):
    response = await client.get("/api/workflow/contracts/tenant_help")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_id"] == "tenant_help"
    assert payload["route"] == "/tenant/help"
    assert payload["group_coverage"]["help_contacts"] == "active"


@pytest.mark.anyio
async def test_workflow_contract_endpoint_returns_functionx_contract(client):
    response = await client.get("/api/workflow/contracts/functionx_workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page_id"] == "functionx_workspace"
    assert payload["route"] == "/functionx"
    assert payload["group_coverage"]["functions_actions"] == "active"


@pytest.mark.anyio
async def test_root_renders_template_welcome_contract_link(client):
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 200
    assert "/api/workflow/contracts/welcome" in response.text
    assert "Process A" in response.text


@pytest.mark.anyio
async def test_tenant_help_route_renders_with_valid_tenant_cookie(client):
    response = await client.get(
        "/tenant/help",
        follow_redirects=False,
        cookies={"semptify_uid": "GUabc12345"},
    )

    assert response.status_code == 200
    assert "Get Help" in response.text


@pytest.mark.anyio
async def test_help_telemetry_summary_aggregates_help_clicks(client):
    brain = get_brain()
    brain.event_history.clear()

    await client.post(
        "/brain/events",
        json={
            "event_type": "user.action",
            "source_module": "ui",
            "data": {
                "page": "tenant_help",
                "action": "hotline_211",
                "href": "tel:211",
            },
        },
    )
    await client.post(
        "/brain/events",
        json={
            "event_type": "user.action",
            "source_module": "ui",
            "data": {
                "page": "tenant_help",
                "action": "hotline_211",
                "href": "tel:211",
            },
        },
    )
    await client.post(
        "/brain/events",
        json={
            "event_type": "user.action",
            "source_module": "ui",
            "data": {
                "page": "welcome",
                "action": "welcome_county_hennepin",
                "href": "tel:612-348-3000",
            },
        },
    )

    response = await client.get("/api/workflow/help-telemetry-summary?limit=200")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["help_events_total"] >= 3

    actions = {item["action"]: item["count"] for item in payload["top_actions"]}
    assert actions["hotline_211"] == 2
    assert actions["welcome_county_hennepin"] == 1


@pytest.mark.anyio
async def test_help_telemetry_summary_filters_by_page(client):
    brain = get_brain()
    brain.event_history.clear()

    await client.post(
        "/brain/events",
        json={
            "event_type": "user.action",
            "source_module": "ui",
            "data": {
                "page": "tenant_help",
                "action": "hotline_home_line",
                "href": "tel:612-728-5767",
            },
        },
    )
    await client.post(
        "/brain/events",
        json={
            "event_type": "user.action",
            "source_module": "ui",
            "data": {
                "page": "welcome",
                "action": "welcome_call_211",
                "href": "tel:211",
            },
        },
    )

    response = await client.get("/api/workflow/help-telemetry-summary?page=tenant_help")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["help_events_total"] == 1
    assert payload["top_pages"][0]["page"] == "tenant_help"


@pytest.mark.anyio
async def test_workflow_advance_blocks_when_welcome_requirements_missing(client):
    response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "welcome",
            "role": "user",
            "storage_state": "already_connected",
            "completed_actions": ["role_selected"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "storage_status_set" in payload["missing_requirements"]
    assert "process_start_clicked" in payload["missing_requirements"]


@pytest.mark.anyio
async def test_workflow_advance_routes_when_welcome_requirements_complete(client):
    response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "welcome",
            "role": "legal",
            "storage_state": "already_connected",
            "completed_actions": [
                "role_selected",
                "storage_status_set",
                "process_start_clicked",
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "advance"
    assert payload["next_process"] == "B4"
    assert payload["next_route"] == "/legal"


@pytest.mark.anyio
async def test_workflow_advance_infers_documents_present_from_overlay_ids(client):
    response = await client.post(
        "/api/workflow/advance",
        json={
            "current_page": "welcome",
            "role": "user",
            "storage_state": "already_connected",
            "completed_actions": [
                "role_selected",
                "storage_status_set",
                "process_start_clicked",
            ],
            "documents_present": False,
            "overlay_record_ids": ["ovl_doc_present"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "advance"
    assert payload["next_process"] == "B2"
    assert payload["next_route"] == "/tenant"


@pytest.mark.anyio
async def test_workflow_next_step_routes_tenant_to_upload_when_no_docs(client):
    response = await client.post(
        "/api/workflow/next-step",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": False,
            "timeline_events": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_route"] == "/tenant/documents"
    assert payload["next_action"] == "upload_documents"


@pytest.mark.anyio
async def test_workflow_next_step_routes_tenant_to_timeline_when_docs_exist(client):
    response = await client.post(
        "/api/workflow/next-step",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": True,
            "timeline_events": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_route"] == "/tenant/timeline"
    assert payload["next_action"] == "review_timeline"


@pytest.mark.anyio
async def test_workflow_next_step_routes_zoom_when_hearing_scheduled(client):
    response = await client.post(
        "/api/workflow/next-step",
        json={
            "role": "user",
            "storage_state": "already_connected",
            "documents_present": True,
            "timeline_events": 3,
            "defense_started": True,
            "court_packet_ready": True,
            "hearing_scheduled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_route"] == "/zoom-court"
    assert payload["next_action"] == "run_zoom_court_prep"


@pytest.mark.anyio
async def test_workflow_case_state_returns_valid_schema(client):
    """GET /api/workflow/case-state returns all expected fields with correct types."""
    response = await client.get("/api/workflow/case-state")

    assert response.status_code == 200
    payload = response.json()
    assert "defense_started" in payload
    assert "court_packet_ready" in payload
    assert "hearing_scheduled" in payload
    assert "documents_present" in payload
    assert "document_count" in payload
    assert "timeline_events" in payload
    assert "role" in payload
    assert "storage_connected" in payload
    assert "current_process" in payload
    assert "current_stage_title" in payload
    assert "urgency_level" in payload
    assert "urgency_reason" in payload
    assert "stage_cards" in payload
    assert "alerts" in payload
    assert "computed_at" in payload
    assert isinstance(payload["defense_started"], bool)
    assert isinstance(payload["court_packet_ready"], bool)
    assert isinstance(payload["hearing_scheduled"], bool)
    assert isinstance(payload["document_count"], int)
    assert isinstance(payload["timeline_events"], int)
    assert isinstance(payload["current_process"], str)
    assert isinstance(payload["current_stage_title"], str)
    assert isinstance(payload["urgency_level"], str)
    assert isinstance(payload["urgency_reason"], str)
    assert isinstance(payload["stage_cards"], list)
    assert isinstance(payload["alerts"], list)


@pytest.mark.anyio
async def test_workflow_case_state_anonymous_user_returns_safe_defaults(client):
    """No cookie → anonymous user gets zeroed counts and False flags."""
    response = await client.get("/api/workflow/case-state", cookies={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_connected"] is False
    assert payload["defense_started"] is False
    assert payload["court_packet_ready"] is False
    assert payload["hearing_scheduled"] is False
    assert payload["current_process"] == "A"
    assert payload["current_stage_title"] == "A - Welcome"
    assert payload["urgency_level"] == "Low"
    assert isinstance(payload["stage_cards"], list)
    assert isinstance(payload["alerts"], list)


@pytest.mark.anyio
async def test_workflow_case_state_connected_tenant_defaults_to_b1_without_docs(client):
    response = await client.get(
        "/api/workflow/case-state",
        cookies={"semptify_uid": "GUtenant1234"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "user"
    assert payload["storage_connected"] is True
    assert payload["current_process"] == "B1"
    assert payload["current_stage_title"] == "B1 - Documents"
    assert len(payload["stage_cards"]) == 5
    titles = [item["title"] for item in payload["stage_cards"]]
    assert "3. Research & Knowledge" in titles
    assert "5. Help & Contacts" in titles
    assert len(payload["alerts"]) >= 2


@pytest.mark.anyio
async def test_workflow_case_state_professional_role_maps_to_b4(client):
    response = await client.get(
        "/api/workflow/case-state",
        cookies={"semptify_uid": "GLlegal1234"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "legal"
    assert payload["storage_connected"] is True
    assert payload["current_process"] == "B4"
    assert payload["current_stage_title"] == "B4 - Hearing / Review"
    assert len(payload["stage_cards"]) == 4
    titles = [item["title"] for item in payload["stage_cards"]]
    assert "1. Professional Workspace" in titles
    assert "2. Research & Knowledge" in titles
    assert "3. Functions & Actions" in titles
    assert "4. Output & Delivery" in titles


@pytest.mark.anyio
async def test_workflow_case_state_normalizes_partial_stage_cards_and_alerts(client, monkeypatch):
    from app.routers import workflow as workflow_router

    monkeypatch.setattr(
        workflow_router,
        "_build_home_stage_cards",
        lambda **_: [
            {"title": "Only Title"},
            {},
        ],
    )
    monkeypatch.setattr(
        workflow_router,
        "_build_home_alerts",
        lambda **_: [
            {"level": "warning"},
            {},
        ],
    )

    response = await client.get("/api/workflow/case-state", cookies={"semptify_uid": "GUtenant1234"})

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["stage_cards"]) == 2
    first_card = payload["stage_cards"][0]
    second_card = payload["stage_cards"][1]
    for card in (first_card, second_card):
        assert "card_id" in card
        assert "title" in card
        assert "description" in card
        assert "route" in card
        assert "state" in card
        assert "button_label" in card
        assert "button_variant" in card

    assert first_card["title"] == "Only Title"
    assert first_card["route"] == "/"
    assert second_card["title"] == "Stage 2"

    assert len(payload["alerts"]) == 2
    first_alert = payload["alerts"][0]
    second_alert = payload["alerts"][1]
    for alert in (first_alert, second_alert):
        assert "level" in alert
        assert "message" in alert

    assert first_alert["level"] == "warning"
    assert first_alert["message"] == "No active alerts right now."
    assert second_alert["level"] == "good"