from datetime import UTC, date, datetime
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request


def make_request(path="/dashboard", headers=None, user=None):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
        "client": ("127.0.0.1", 8000),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    }
    request = Request(scope)
    request.state.user = user
    return request


def test_permission_set_and_external_context():
    from app.sdk.external.context import ExternalModuleContext
    from app.sdk.external.permissions import Permission, PermissionDeniedError, PermissionSet

    permissions = PermissionSet([Permission.DOCUMENT_READ.value, Permission.DOCUMENT_READ.value])
    assert permissions.has(Permission.DOCUMENT_READ.value)
    assert Permission.DOCUMENT_READ.value in permissions
    assert len(permissions) == 1
    assert permissions.to_list() == [Permission.DOCUMENT_READ.value]
    assert "PermissionSet" in repr(permissions)
    permissions.require(Permission.DOCUMENT_READ.value, "read")
    with pytest.raises(PermissionDeniedError):
        permissions.require(Permission.DOCUMENT_WRITE.value, "write")
    with pytest.raises(ValueError):
        PermissionSet(["unknown.permission"])

    context = ExternalModuleContext(
        module_name="test-module",
        vendor="test-vendor",
        user_id="user-1",
        permissions=permissions,
        request_id="request-1",
        jurisdiction="MN",
    )
    assert context.to_dict()["permissions"] == [Permission.DOCUMENT_READ.value]
    assert context.to_dict()["jurisdiction"] == "MN"


def test_generated_module_contract_registrations():
    from pathlib import Path

    from app.core.module_contracts import contract_registry

    root = Path(__file__).parents[1] / "app" / "modules"
    module_names = [
        ".".join(path.relative_to(root.parents[1]).with_suffix("").parts)
        for path in root.rglob("register.py")
        if "_template" not in path.parts and "tests" not in path.parts
    ]
    assert module_names
    for module_name in module_names:
        importlib.reload(importlib.import_module(module_name))
    assert contract_registry.validate()["status"] == "pass"


def test_calendar_service_covers_date_and_event_branches():
    from app.services.calendar_service import CalendarEventType, CalendarService

    service = CalendarService()
    assert service._extract_date({"date": date(2026, 1, 1)}) == date(2026, 1, 1)
    assert service._extract_date({"event_date": datetime(2026, 1, 2, 3)}) == datetime(2026, 1, 2, 3)
    assert service._extract_date({"deadline": "2026-01-03"}) == date(2026, 1, 3)
    assert service._extract_date({"date": "invalid"}) is None

    expected = {
        "court hearing": CalendarEventType.COURT_HEARING,
        "notice deadline": CalendarEventType.NOTICE_DEADLINE,
        "payment due": CalendarEventType.PAYMENT_DUE,
        "document deadline": CalendarEventType.DOCUMENT_DEADLINE,
        "inspection": CalendarEventType.INSPECTION,
        "mediation": CalendarEventType.MEDIATION,
        "other": CalendarEventType.OTHER,
    }
    for event_type, calendar_type in expected.items():
        event = service._create_calendar_event(
            {"title": event_type, "description": "description", "type": event_type},
            date(2026, 1, 1),
        )
        assert event.event_type == calendar_type
        assert event.reminders

    events = asyncio_run(service.generate_events_from_timeline([
        {"date": "2026-01-01", "type": "court", "title": "Hearing"},
        SimpleNamespace(to_dict=lambda: {"date": "2026-01-02", "type": "payment"}),
        {"description": "No date"},
    ]))
    assert len(events) == 2


def test_duplicate_detection_original_and_duplicate_paths():
    from app.services.duplicate_detection_service import detect_duplicates, get_all_duplicates

    manager = SimpleNamespace(
        get_overlays=AsyncMock(return_value=SimpleNamespace(success=True, overlays=[])),
        create_overlay=AsyncMock(),
        update_overlay=AsyncMock(),
    )
    original = asyncio_run(detect_duplicates("user", "vault-1", "hash", "lease.pdf", manager))
    assert original["is_duplicate"] is False
    manager.create_overlay.assert_awaited_once()

    existing = SimpleNamespace(
        overlay_id="overlay-1",
        document_id="vault-1",
        payload={"sha256_hash": "hash", "original_vault_id": "vault-1", "duplicate_count": 1, "filename": "lease.pdf"},
    )
    manager.get_overlays = AsyncMock(return_value=SimpleNamespace(success=True, overlays=[existing]))
    duplicate = asyncio_run(detect_duplicates("user", "vault-2", "hash", "copy.pdf", manager))
    assert duplicate == {"is_duplicate": True, "original_vault_id": "vault-1", "duplicate_count": 2}
    manager.update_overlay.assert_awaited_once()

    manager.get_overlays = AsyncMock(return_value=SimpleNamespace(success=True, overlays=[existing, SimpleNamespace(
        document_id="vault-2",
        payload={"sha256_hash": "hash", "is_duplicate": True, "filename": "copy.pdf", "created_at": "now"},
    )]))
    groups = asyncio_run(get_all_duplicates("user", manager))
    assert groups[0]["duplicate_count"] == 2
    assert groups[0]["duplicates"][0]["vault_id"] == "vault-2"


def test_email_service_no_key_and_helpers(monkeypatch):
    import app.services.email_service as email_service

    monkeypatch.setattr(email_service, "_RESEND_API_KEY", "")
    assert asyncio_run(email_service.send_email("a@example.com", "subject", "<p>x</p>")) is False
    assert asyncio_run(email_service.send_support_notification("subject", "<p>x</p>")) is False
    assert asyncio_run(email_service.send_feedback_email(None, "feedback")) is False
    assert asyncio_run(email_service.send_contact_email("Name", "a@example.com", "message")) is False

    monkeypatch.setattr(email_service, "_RESEND_API_KEY", "key")
    response = SimpleNamespace(status_code=201, text="")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return self

        async def post(self, *args, **kwargs):
            return response

    monkeypatch.setattr(email_service.httpx, "AsyncClient", lambda timeout: Client())
    assert asyncio_run(email_service.send_email(
        ["a@example.com"], "subject", "<p>x</p>", reply_to="reply@example.com"
    ))


def test_audit_logger_event_helpers(tmp_path):
    from app.core.audit_logger import (
        AuditEvent,
        AuditEventType,
        AuditLogger,
        AuditSeverity,
        log_document_access,
        log_security_event,
    )

    logger = AuditLogger(str(tmp_path / "audit.log"))
    event = AuditEvent(
        event_type=AuditEventType.SYSTEM_ERROR,
        user_id="user",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        severity=AuditSeverity.HIGH,
        ip_address="127.0.0.1",
        user_agent="test",
        resource_id=None,
        resource_type=None,
        action="test",
        details={"key": "value"},
        success=False,
    )
    assert event.to_dict()["event_type"] == "system_error"
    logger.log_event(event)
    logger.document_uploaded("user", "doc", "file.pdf", 10, "pdf", "127.0.0.1", "test")
    logger.document_downloaded("user", "doc", "file.pdf", "127.0.0.1", "test")
    logger.document_viewed("user", "doc", "file.pdf", "127.0.0.1", "test")
    logger.document_deleted("user", "doc", "file.pdf", "127.0.0.1", "test")
    assert logger.get_user_events("user")
    assert logger.get_audit_summary()["total_events"] >= 5

    import app.core.audit_logger as audit_module

    original = audit_module.audit_logger
    audit_module.audit_logger = logger
    try:
        audit_module.log_document_upload("user", "doc", "file.pdf", 10, "pdf", "127.0.0.1", "test")
        log_document_access("user", "doc", "file.pdf", "download", "127.0.0.1", "test")
        log_document_access("user", "doc", "file.pdf", "view", "127.0.0.1", "test")
        log_security_event("user", "security", {"reason": "test"}, "127.0.0.1", "test")
    finally:
        audit_module.audit_logger = original


def test_advanced_rate_limiter_paths():
    from app.core.advanced_rate_limiter import AdvancedRateLimiter, RateLimitConfig, RateLimitStrategy

    limiter = AdvancedRateLimiter()
    assert limiter.classify_endpoint("GET", "/items") == "read"
    assert limiter.classify_endpoint("POST", "/upload/file") == "upload"
    assert limiter.classify_endpoint("POST", "/auth/login") == "auth"
    assert limiter.classify_endpoint("POST", "/copilot") == "ai"
    assert limiter.classify_endpoint("DELETE", "/items") == "write"
    assert limiter.get_user_tier("user").value == "basic"

    allowed, details = limiter.is_allowed("user", "127.0.0.1", "GET", "/items")
    assert allowed is True
    assert details["remaining"] >= 0
    key = limiter.get_client_key("other-user", "127.0.0.1", "read")
    assert limiter._sliding_window_check(key, 1, 60, 100.0)[0] is True
    assert limiter._sliding_window_check(key, 1, 60, 100.0)[0] is False
    bucket_config = RateLimitConfig(1, 60, RateLimitStrategy.TOKEN_BUCKET)
    bucket_key = limiter.get_client_key("user", "127.0.0.1", "upload")
    assert limiter._apply_rate_limit(bucket_key, bucket_config, "upload")[0] is True
    limiter.update_load_factors(global_load=3, endpoint_loads={"read": 0})
    assert limiter.global_load_factor == 2.0
    assert limiter.endpoint_load_factors["read"] == 0.1
    assert limiter.get_stats()["total_requests"] == 1
    assert limiter.get_client_status("user", "127.0.0.1")
    limiter.reset_client("user", "127.0.0.1")
    assert limiter.get_client_status("user", "127.0.0.1") == {}


def test_data_deletion_manager_lifecycle():
    from app.core.data_deletion import DataDeletionManager, DeletionScope, DeletionStatus

    manager = DataDeletionManager()
    request_id = manager.create_deletion_request("user", DeletionScope.USER_DATA, reason="request")
    request = manager.get_deletion_request(request_id)
    assert request.status == DeletionStatus.PENDING
    assert manager.get_user_deletion_requests("user") == [request]
    assert manager.execute_deletion(request_id) is True
    assert request.status == DeletionStatus.COMPLETED
    assert manager.execute_deletion(request_id) is False
    cancelled_id = manager.create_deletion_request("user", DeletionScope.ALL_DOCUMENTS)
    assert manager.cancel_deletion_request(cancelled_id) is True
    assert manager.cancel_deletion_request("missing") is False
    summary = manager.get_deletion_summary("user")
    assert summary["total_requests"] == 2
    assert summary["completed"] == 1
    assert summary["pending"] == 0
    assert manager.execute_deletion("missing") is False


def test_route_guard_contract_and_request_paths(monkeypatch):
    from app.core.page_contracts import UserRole
    from app.core.route_guards import GuardResult, RouteGuard

    guard = RouteGuard()
    guard.configure(login_url="/signin", unauthorized_url="/denied")
    assert guard._get_session_user(make_request(user={"id": "u"}))["id"] == "u"
    assert guard._get_session_user(make_request(headers={"authorization": "Bearer token"}))["id"] == "token_user"
    assert guard._get_session_user(make_request()) is None
    assert guard._infer_page_id(make_request("/some-page/detail")) == "some_page_detail"
    assert guard._check_contract_access("missing", None).result == GuardResult.ALLOW
    assert guard._check_contract_access("dashboard", None).result in {GuardResult.REDIRECT, GuardResult.ALLOW}

    async def endpoint(request):
        return {"ok": True}

    wrapped = guard.require_auth(page_id="missing")(endpoint)
    assert asyncio_run(wrapped(make_request(user=None))) == {"ok": True}
    roles_wrapped = guard.require_roles([UserRole.ADMIN], page_id="missing")(endpoint)
    assert roles_wrapped._is_guarded is True


def test_page_recipe_registry_and_serialization():
    from app.core.page_recipe import (
        ComponentType,
        PageComponent,
        PageIntent,
        PageRecipe,
        PageStep,
        RecipeRegistry,
        create_document_intake_recipe,
    )

    recipe = PageRecipe(
        page_id="test",
        page_title="Test",
        intent=PageIntent.COLLECT,
        purpose="purpose",
        user_intent="intent",
        success_criteria=["done"],
        components=[
            PageComponent(ComponentType.UI_COMPONENT, "ready", "ready", implemented=True),
            PageComponent(ComponentType.SERVICE_FUNCTION, "missing", "missing", required=True),
        ],
        steps=[PageStep(2, "second", "system"), PageStep(1, "first", "user")],
    )
    assert recipe.validate()["complete"] is False
    assert recipe.get_dependency_graph()["ready"] == []
    serialized = recipe.to_dict()
    assert serialized["steps"][0]["order"] == 1
    RecipeRegistry.register(recipe)
    assert RecipeRegistry.get("test") is recipe
    assert recipe in RecipeRegistry.by_intent(PageIntent.COLLECT)
    assert RecipeRegistry.incomplete()
    intake = create_document_intake_recipe()
    assert intake.validate()["total_components"] > 0


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
