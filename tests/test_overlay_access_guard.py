import pytest
from types import SimpleNamespace
from starlette.requests import Request

from fastapi import HTTPException

from app.routers import overlays as overlays_router
from app.routers.overlays import ensure_document_access


def _make_request(method: str = "GET", path: str = "/api/overlays/doc-1") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.anyio
async def test_ensure_document_access_allows_matching_document():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            return [
                SimpleNamespace(name="abc123.pdf", is_folder=False),
                SimpleNamespace(name="other.txt", is_folder=False),
            ]

    storage = MockStorage()
    await ensure_document_access(storage, "abc123")


@pytest.mark.anyio
async def test_ensure_document_access_denies_missing_document():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            return [
                SimpleNamespace(name="other.pdf", is_folder=False),
            ]

    storage = MockStorage()

    with pytest.raises(HTTPException) as exc:
        await ensure_document_access(storage, "abc123")

    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_ensure_document_access_returns_503_on_provider_failure():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            raise RuntimeError("provider unavailable")

    storage = MockStorage()

    with pytest.raises(HTTPException) as exc:
        await ensure_document_access(storage, "abc123")

    assert exc.value.status_code == 503


@pytest.mark.anyio
async def test_overlay_guard_requires_cookie():
    with pytest.raises(HTTPException) as exc:
        await overlays_router.require_overlay_function_access(
            request=_make_request("GET"),
            document_id="doc-1",
            function_token_header="tok-1",
            semptify_uid=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_overlay_guard_requires_header_token():
    with pytest.raises(HTTPException) as exc:
        await overlays_router.require_overlay_function_access(
            request=_make_request("GET"),
            document_id="doc-1",
            function_token_header=None,
            semptify_uid="GUabc12345",
        )

    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_overlay_guard_uses_read_action_and_document_scope(monkeypatch):
    captured = {}

    def fake_verify(user_id: str, token: str, action: str, document_id: str, refresh: bool = False):
        captured["user_id"] = user_id
        captured["token"] = token
        captured["action"] = action
        captured["document_id"] = document_id
        captured["refresh"] = refresh
        return {"valid": True}

    monkeypatch.setattr(overlays_router, "verify_function_token_for_operation", fake_verify)

    await overlays_router.require_overlay_function_access(
        request=_make_request("GET", "/api/overlays/doc-a"),
        document_id="doc-a",
        function_token_header="tok-read",
        semptify_uid="GUabc12345",
    )

    assert captured["action"] == "overlay:read"
    assert captured["document_id"] == "doc-a"
    assert captured["refresh"] is False


@pytest.mark.anyio
async def test_overlay_guard_uses_write_action_and_rejects_scope_failure(monkeypatch):
    def fake_verify(*_args, **_kwargs):
        return {"valid": False, "reason": "token_scope_denied"}

    monkeypatch.setattr(overlays_router, "verify_function_token_for_operation", fake_verify)

    with pytest.raises(HTTPException) as exc:
        await overlays_router.require_overlay_function_access(
            request=_make_request("POST", "/api/overlays/doc-b/highlights"),
            document_id="doc-b",
            function_token_header="tok-write",
            semptify_uid="GUabc12345",
        )

    assert exc.value.status_code == 401
