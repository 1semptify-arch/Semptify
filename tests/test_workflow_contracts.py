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