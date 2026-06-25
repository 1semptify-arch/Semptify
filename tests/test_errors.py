"""Tests for app.core.errors — standardized error classes and handlers."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AIProviderError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    ErrorDetail,
    ErrorResponse,
    NotFoundError,
    RateLimitError,
    SemptifyError,
    ServiceUnavailableError,
    StorageError,
    ValidationError,
    generic_exception_handler,
    get_request_id,
    http_exception_handler,
    semptify_error_handler,
    setup_exception_handlers,
    validation_exception_handler,
)

# ── Error models ─────────────────────────────────────────────────────────────

class TestErrorModels:
    def test_error_detail_defaults(self):
        detail = ErrorDetail(msg="oops", type="value_error")
        assert detail.loc is None
        assert detail.msg == "oops"

    def test_error_response_defaults(self):
        resp = ErrorResponse(error="not_found", message="gone")
        assert resp.details is None
        assert resp.request_id is None
        assert resp.documentation is None


# ── Custom exceptions ────────────────────────────────────────────────────────

class TestSemptifyError:
    def test_defaults(self):
        err = SemptifyError("boom")
        assert err.message == "boom"
        assert err.error_code == "semptify_error"
        assert err.status_code == 500
        assert err.details is None

    def test_custom_fields(self):
        err = SemptifyError("bad", error_code="custom", status_code=418, details=[{"x": 1}])
        assert err.error_code == "custom"
        assert err.status_code == 418
        assert err.details == [{"x": 1}]

    def test_str_is_message(self):
        err = SemptifyError("hello")
        assert str(err) == "hello"


class TestNotFoundError:
    def test_without_identifier(self):
        err = NotFoundError("Document")
        assert err.status_code == 404
        assert err.error_code == "not_found"
        assert "Document not found" in err.message

    def test_with_identifier(self):
        err = NotFoundError("Document", "abc-123")
        assert "'abc-123'" in err.message


class TestAuthenticationError:
    def test_defaults(self):
        err = AuthenticationError()
        assert err.status_code == 401
        assert err.error_code == "authentication_required"

    def test_custom_message(self):
        err = AuthenticationError("Token expired")
        assert err.message == "Token expired"


class TestAuthorizationError:
    def test_defaults(self):
        err = AuthorizationError()
        assert err.status_code == 403
        assert err.error_code == "permission_denied"


class TestValidationError:
    def test_defaults(self):
        err = ValidationError("Invalid input")
        assert err.status_code == 422
        assert err.error_code == "validation_error"

    def test_with_details(self):
        details = [{"field": "name", "msg": "required"}]
        err = ValidationError("Invalid", details=details)
        assert err.details == details


class TestConflictError:
    def test_defaults(self):
        err = ConflictError()
        assert err.status_code == 409
        assert err.error_code == "conflict"


class TestRateLimitError:
    def test_defaults(self):
        err = RateLimitError()
        assert err.status_code == 429
        assert "60 seconds" in err.message
        assert err.details == [{"retry_after": 60}]

    def test_custom_retry(self):
        err = RateLimitError(retry_after=120)
        assert "120 seconds" in err.message
        assert err.details == [{"retry_after": 120}]


class TestServiceUnavailableError:
    def test_defaults(self):
        err = ServiceUnavailableError()
        assert err.status_code == 503

    def test_custom_service(self):
        err = ServiceUnavailableError("Redis")
        assert "Redis" in err.message


class TestAIProviderError:
    def test_includes_provider(self):
        err = AIProviderError("OpenAI", "quota exceeded")
        assert err.status_code == 502
        assert "OpenAI" in err.message
        assert "quota exceeded" in err.message


class TestStorageError:
    def test_defaults(self):
        err = StorageError()
        assert err.status_code == 502
        assert "Storage" in err.message

    def test_custom(self):
        err = StorageError("Dropbox", "upload failed")
        assert "Dropbox" in err.message
        assert "upload failed" in err.message


# ── Exception handlers ───────────────────────────────────────────────────────

def _mock_request(path: str = "/test", request_id: str | None = None) -> MagicMock:
    request = MagicMock()
    request.url.path = path
    request.method = "GET"
    request.headers = MagicMock()
    request.headers.get = MagicMock(return_value=request_id)
    return request


class TestGetRequestId:
    def test_present(self):
        req = _mock_request(request_id="req-abc")
        assert get_request_id(req) == "req-abc"

    def test_absent(self):
        req = _mock_request()
        assert get_request_id(req) is None


@pytest.mark.asyncio
class TestSemptifyErrorHandler:
    async def test_returns_json(self):
        req = _mock_request()
        exc = NotFoundError("User", 42)
        resp = await semptify_error_handler(req, exc)
        assert resp.status_code == 404
        import json
        body = json.loads(resp.body.decode())
        assert body["error"] == "not_found"


@pytest.mark.asyncio
class TestHttpExceptionHandler:
    async def test_known_status(self):
        req = _mock_request()
        exc = StarletteHTTPException(status_code=404, detail="not here")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 404
        import json
        body = json.loads(resp.body.decode())
        assert body["error"] == "not_found"
        assert body["message"] == "not here"

    async def test_unknown_status(self):
        req = _mock_request()
        exc = StarletteHTTPException(status_code=418, detail="teapot")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 418
        import json
        body = json.loads(resp.body.decode())
        assert body["error"] == "error"


@pytest.mark.asyncio
class TestValidationExceptionHandler:
    async def test_returns_422(self):
        req = _mock_request()
        exc = RequestValidationError(
            errors=[
                {"loc": ("body", "name"), "msg": "required", "type": "missing"},
            ]
        )
        resp = await validation_exception_handler(req, exc)
        assert resp.status_code == 422
        import json
        body = json.loads(resp.body.decode())
        assert body["error"] == "validation_error"
        assert len(body["details"]) == 1


@pytest.mark.asyncio
class TestGenericExceptionHandler:
    async def test_returns_500(self):
        req = _mock_request()
        resp = await generic_exception_handler(req, RuntimeError("boom"))
        assert resp.status_code == 500
        import json
        body = json.loads(resp.body.decode())
        assert body["error"] == "internal_error"
        assert "boom" not in body["message"]


# ── setup_exception_handlers ─────────────────────────────────────────────────

class TestSetupExceptionHandlers:
    def test_registers_handlers(self):
        app = FastAPI()
        setup_exception_handlers(app)
        assert SemptifyError in app.exception_handlers
        assert StarletteHTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
        assert Exception in app.exception_handlers
