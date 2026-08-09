"""
Production Security Middleware
Enforces security policies, rate limiting, CORS, and headers
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import timedelta

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests: int = 100, period: int = 60):
        self.requests = requests
        self.period = period
        self.clients = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request"""
        now = utc_now()
        cutoff = now - timedelta(seconds=self.period)

        # Clean old requests
        self.clients[client_id] = [req_time for req_time in self.clients[client_id] if req_time > cutoff]

        # Check rate limit
        if len(self.clients[client_id]) >= self.requests:
            return False

        # Add current request
        self.clients[client_id].append(now)
        return True


class SecurityHeaders:
    """Security headers middleware"""

    @staticmethod
    def add_headers(response):
        """Add security headers to response"""
        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://static.cloudflareinsights.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://cloudflareinsights.com wss:;"
        )

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


async def secure_middleware(request: Request, call_next: Callable):
    """Main security middleware"""

    # Check HTTPS in production
    if request.app.state.security_settings.HTTPS_ONLY and request.url.scheme != "https":
        if request.app.state.security_settings.ENVIRONMENT == "production":
            # Allow localhost for development
            if request.client.host not in ["127.0.0.1", "localhost"]:
                logger.warning(f"Non-HTTPS request from {request.client.host}")
                return JSONResponse(
                    status_code=403, content={"error": "HTTPS required", "message": "Secure connection required"}
                )

    # Rate limiting
    if request.app.state.security_settings.RATE_LIMIT_ENABLED:
        client_id = request.client.host if request.client else "unknown"

        if not request.app.state.rate_limiter.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for {client_id}")
            return JSONResponse(
                status_code=429, content={"error": "Rate limit exceeded", "message": "Too many requests"}
            )

    # IP Whitelist check
    if request.app.state.security_settings.IP_WHITELIST_ENABLED:
        client_ip = request.client.host if request.client else None
        if client_ip not in request.app.state.security_settings.IP_WHITELIST:
            logger.warning(f"IP not whitelisted: {client_ip}")
            return JSONResponse(
                status_code=403, content={"error": "Access denied", "message": "IP address not whitelisted"}
            )

    # Check request size
    if request.headers.get("content-length"):
        try:
            content_length = int(request.headers.get("content-length"))
            if content_length > request.app.state.security_settings.MAX_REQUEST_SIZE:
                logger.warning(f"Request too large: {content_length} bytes")
                return JSONResponse(
                    status_code=413, content={"error": "Payload too large", "message": "Request exceeds size limit"}
                )
        except ValueError:
            pass

    # Add timing header
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as e:
        import traceback

        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"Request error: {error_msg}")
        logger.error(f"Traceback: {traceback_str}")
        # Return detailed error for debugging
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": error_msg,
                "type": type(e).__name__,
                "traceback": traceback_str,
            },
        )

    # Calculate elapsed time
    elapsed = time.time() - start_time
    response.headers["X-Process-Time"] = str(elapsed)

    # Add security headers
    response = SecurityHeaders.add_headers(response)

    # Log request
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {elapsed:.3f}s")

    return response
