"""
Rate Limiting Configuration for Semptify API.

Uses slowapi with configurable limits per endpoint category.
Supports Redis backend for production distributed rate limiting.
"""

import logging
import os
from typing import Callable, Iterable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import (
    SlowAPIMiddleware,
    _should_exempt,
    sync_check_limits,
)
from slowapi.util import get_remote_address
from starlette.applications import Starlette
from starlette.middleware.base import RequestResponseEndpoint
from starlette.routing import BaseRoute, Match
from starlette.types import Scope

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get rate limit key based on user identity.
    Uses storage token if authenticated, falls back to IP address.
    """
    # Check for storage token (authenticated user)
    storage_token = request.cookies.get("storage_token")
    if storage_token:
        # Use first 16 chars of token as identifier (enough for uniqueness)
        return f"user:{storage_token[:16]}"

    # Check X-Forwarded-For for proxy setups
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain (original client)
        return f"ip:{forwarded.split(',')[0].strip()}"

    # Fall back to direct client IP
    return f"ip:{get_remote_address(request)}"


# Create limiter with user identifier
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["200/minute", "1000/hour"],  # Default for all endpoints
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Use Redis URI for production
    strategy="fixed-window",  # Options: fixed-window, moving-window
)


# =============================================================================
# Rate Limit Presets (use as decorators)
# =============================================================================

# Standard API endpoints
RATE_STANDARD = "60/minute"

# Read-heavy endpoints (documents, timeline, etc.)
RATE_READ = "120/minute"

# Write endpoints (create, update, delete)
RATE_WRITE = "30/minute"

# AI/LLM endpoints (expensive operations)
RATE_AI = "10/minute"

# Authentication endpoints (prevent brute force)
RATE_AUTH = "5/minute"

# Health/metrics (allow more frequent checks)
RATE_HEALTH = "300/minute"

# File uploads (resource intensive)
RATE_UPLOAD = "20/minute"

# Search/query endpoints
RATE_SEARCH = "30/minute"

# Court packet generation (very expensive)
RATE_COURT_PACKET = "5/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns a user-friendly JSON response with retry information.
    """
    # Extract limit details
    limit_value = str(exc.detail) if hasattr(exc, "detail") else "Rate limit exceeded"

    # Log rate limit hit
    identifier = get_user_identifier(request)
    logger.warning("Rate limit exceeded: %s on %s %s", identifier, request.method, request.url.path)

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "detail": limit_value,
            "retry_after": 60,  # seconds
            "documentation": "https://semptify.org/docs/api/rate-limits",
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": limit_value,
        },
    )


# =============================================================================
# Helper decorators for common patterns
# =============================================================================


def limit_ai(func):
    """Decorator for AI/LLM endpoints."""
    return limiter.limit(RATE_AI)(func)


def limit_auth(func):
    """Decorator for authentication endpoints."""
    return limiter.limit(RATE_AUTH)(func)


def limit_upload(func):
    """Decorator for file upload endpoints."""
    return limiter.limit(RATE_UPLOAD)(func)


def limit_search(func):
    """Decorator for search endpoints."""
    return limiter.limit(RATE_SEARCH)(func)


def limit_court_packet(func):
    """Decorator for court packet generation."""
    return limiter.limit(RATE_COURT_PACKET)(func)


# =============================================================================
# FastAPI >=0.141 lazy-router compatibility
# =============================================================================
#
# FastAPI 0.141 made ``include_router`` lazy: ``app.routes`` holds
# ``_IncludedRouter`` proxy nodes instead of concrete routes. Those proxies
# have no ``endpoint`` attribute and ``matches()`` returns an empty
# child_scope, so stock ``slowapi.middleware._find_route_handler`` resolves
# ``None`` and ``_should_exempt`` skips the request entirely — the global
# ``default_limits`` never engaged on any lazily-included router (proven live:
# 210 same-path requests, zero 429s).
#
# ``LazyRouterSlowAPIMiddleware`` resolves the real endpoint by walking each
# proxy's ``effective_route_contexts()`` — every candidate's ``matches()``
# already knows its include prefix and its child_scope carries the endpoint.
# Detection is duck-typed, so the resolver degrades to stock behaviour if
# FastAPI ever returns to eager route inclusion.


def find_route_handler(
    routes: Iterable[BaseRoute], scope: Scope
) -> Optional[Callable]:
    """
    Drop-in replacement for ``slowapi.middleware._find_route_handler`` that
    can see through FastAPI >=0.141 ``_IncludedRouter`` lazy proxies.

    Keeps the stock contract: last FULL match wins across ``app.routes``;
    within one lazy router the first FULL match wins, mirroring the first-
    match dispatch order of ``_IncludedRouter._match``.
    """
    handler = None
    for route in routes:
        effective_contexts = getattr(route, "effective_route_contexts", None)
        if effective_contexts is not None:
            for candidate in effective_contexts():
                match, child_scope = candidate.matches(scope)
                if match != Match.FULL:
                    continue
                endpoint = child_scope.get("endpoint") or getattr(
                    candidate, "endpoint", None
                )
                if endpoint is not None:
                    handler = endpoint
                    break
            continue
        match, _ = route.matches(scope)
        if match == Match.FULL:
            endpoint = getattr(route, "endpoint", None)
            if endpoint is not None:
                handler = endpoint
    return handler


class LazyRouterSlowAPIMiddleware(SlowAPIMiddleware):
    """
    SlowAPIMiddleware that applies ``default_limits`` (and honouring of
    ``@limiter.limit`` / ``@limiter.exempt`` lookups) to endpoints reached
    through FastAPI >=0.141 lazy ``include_router`` proxies.

    Stock ``SlowAPIMiddleware`` scans ``app.routes`` for a FULL match with an
    ``endpoint`` attribute; ``_IncludedRouter`` nodes have neither, so every
    lazily-included endpoint fell through to ``_should_exempt`` and was never
    limited. Behaviour is otherwise identical to stock — same check order,
    same exception flow, same header injection.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        app: Starlette = request.app
        app_limiter: Limiter = app.state.limiter

        if not app_limiter.enabled:
            return await call_next(request)

        handler = find_route_handler(app.routes, request.scope)
        if _should_exempt(app_limiter, handler):
            return await call_next(request)

        error_response, should_inject_headers = sync_check_limits(
            app_limiter, request, handler, app
        )
        if error_response is not None:
            return error_response

        response = await call_next(request)
        if should_inject_headers:
            response = app_limiter._inject_headers(
                response, request.state.view_rate_limit
            )
        return response
