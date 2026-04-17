"""
Core Module Middleware

Provides global middleware for the application including:
- Security headers
- Maintenance mode
- Request logging
"""

import time
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .services import LoggingService

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp

        return response

class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Middleware to handle maintenance mode"""

    def __init__(self, app, maintenance_mode: bool = False):
        super().__init__(app)
        self.maintenance_mode = maintenance_mode

    async def dispatch(self, request: Request, call_next):
        if self.maintenance_mode and request.url.path not in ['/health', '/maintenance']:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head><title>Maintenance</title></head>
                <body style="text-align center; padding: 50px;">
                    <h1>🚧 Under Maintenance</h1>
                    <p>Semptify is currently undergoing maintenance. Please check back soon.</p>
                </body>
                </html>
                """,
                status_code=503
            )

        return await call_next(request)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        LoggingService.info(
            "http",
            f"Request: {request.method} {request.url.path}",
            {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            LoggingService.info(
                "http",
                f"Response: {response.status_code} ({duration:.2f}s)",
                {
                    "status_code": response.status_code,
                    "duration": duration,
                    "path": request.url.path
                }
            )

            return response

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            LoggingService.error(
                "http",
                f"Request failed: {str(e)} ({duration:.2f}s)",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration": duration
                }
            )
            raise

def setup_middleware(app: FastAPI):
    """Setup all middleware for the application"""

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://localhost:3000"],  # TODO: Configurable
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]  # TODO: Configurable
    )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MaintenanceModeMiddleware, maintenance_mode=False)