"""
Dev Mode Middleware — strict logging for modules in development.

When a module has dev_mode=True in module_registry:
- Every request/response is logged with full detail
- Errors are caught, logged, and re-raised with context
- Execution time is tracked and logged
- Response body preview is captured (truncated at 1KB)

Attach to FastAPI app via:
    app.add_middleware(DevModeMiddleware)
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logger = logging.getLogger("dev_mode")

# Max body preview size in bytes
MAX_BODY_PREVIEW = 1024


class DevModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts requests to modules in dev_mode.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Determine which module this request targets
        module_name = self._extract_module_name(request.url.path)

        # Check if this module is in dev_mode
        dev_mode = await self._is_dev_mode(module_name) if module_name else False

        if not dev_mode:
            # Normal flow, no extra logging
            return await call_next(request)

        # DEV MODE: strict logging path
        start_time = time.monotonic()
        request_body: bytes | None = None
        response_body: bytes | None = None

        # Capture request body
        if request.method in ("POST", "PUT", "PATCH"):
            request_body = await self._capture_body(request)

        # Log request
        logger.warning(
            "[DEV_MODE] REQUEST | %s %s | module=%s | client=%s | body=%s",
            request.method,
            request.url.path,
            module_name,
            request.client.host if request.client else "unknown",
            self._preview(request_body) if request_body else "<empty>",
        )

        # Call endpoint with error capture
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.exception(
                "[DEV_MODE] EXCEPTION | %s %s | module=%s | duration=%.1fms | error=%s",
                request.method,
                request.url.path,
                module_name,
                duration_ms,
                str(exc),
            )
            raise

        duration_ms = (time.monotonic() - start_time) * 1000

        # Capture response body (only for JSON/HTML/text, not binary)
        if response.headers.get("content-type", "").startswith(("application/json", "text/")):
            response_body = await self._capture_response_body(response)

        # Log response
        logger.warning(
            "[DEV_MODE] RESPONSE | %s %s | module=%s | status=%d | duration=%.1fms | body=%s",
            request.method,
            request.url.path,
            module_name,
            response.status_code,
            duration_ms,
            self._preview(response_body) if response_body else "<stream/binary>",
        )

        return response

    def _extract_module_name(self, path: str) -> str | None:
        """Extract module name from URL path."""
        # /api/vault/... -> vault
        # /api/documents/... -> documents
        # /modules/case_builder/... -> case_builder
        parts = path.strip("/").split("/")
        if len(parts) < 2:
            return None
        # Common prefixes
        if parts[0] == "api" and len(parts) > 1:
            return parts[1]
        if parts[0] == "modules" and len(parts) > 1:
            return parts[1]
        if parts[0] == "admin" and len(parts) > 1:
            return f"admin_{parts[1]}"
        return parts[0]

    async def _is_dev_mode(self, module_name: str) -> bool:
        """Check module_registry for dev_mode flag."""
        try:
            from app.core.module_overlay import module_overlay

            return await module_overlay.is_module_in_dev_mode(module_name)
        except Exception:
            return False

    async def _capture_body(self, request: Request) -> bytes | None:
        """Capture request body without consuming it."""
        body = await request.body()

        # Re-populate the receive interface for downstream
        async def receive() -> Message:
            return {"type": "http.request", "body": body}

        request._receive = receive
        return body if body else None

    async def _capture_response_body(self, response: Response) -> bytes | None:
        """Capture response body content."""
        # For streaming responses, we can't easily capture without breaking
        # This is a best-effort for standard responses
        if hasattr(response, "body"):
            return response.body
        return None

    def _preview(self, data: bytes | None) -> str:
        """Create truncated preview of body data."""
        if not data:
            return "<empty>"
        try:
            text = data.decode("utf-8", errors="replace")
            if len(text) > MAX_BODY_PREVIEW:
                return text[:MAX_BODY_PREVIEW] + f"... [{len(data)} bytes total]"
            return text
        except Exception:
            return f"<binary {len(data)} bytes>"
