"""
Core Module

Provides foundational services, middleware, and utilities for the Semptify application.
This module contains shared components used across all other modules.
"""

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
import logging
from pathlib import Path

# Module configuration
MODULE_NAME = "core"
MODULE_VERSION = "1.0.0"

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./semptify.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Redis configuration
REDIS_URL = "redis://localhost:6379"
redis_client = redis.from_url(REDIS_URL)

# Template configuration
templates = Jinja2Templates(directory="modules/core/templates")

# Logger
logger = logging.getLogger(__name__)

# Import services and models
from .services import (
    SystemService,
    LoggingService,
    ConfigService,
    SessionService,
    FileService,
    system_service,
    logging_service,
    config_service,
    session_service,
    file_service
)

from .middleware import (
    SecurityHeadersMiddleware,
    MaintenanceModeMiddleware,
    RequestLoggingMiddleware,
    setup_middleware
)

from .models import (
    SystemConfig
)

async def get_db():
    """Database session dependency"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_redis():
    """Redis client dependency"""
    try:
        yield redis_client
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        yield None

def init_app(app: FastAPI):
    """Initialize core module in FastAPI application"""

    # Mount static files
    app.mount("/static/core", StaticFiles(directory="modules/core/static"), name="core-static")

    # Include module routes
    from .routes import router
    app.include_router(router, prefix="/core", tags=["core"])

    # Add middleware
    setup_middleware(app)

    logger.info(f"Core module v{MODULE_VERSION} initialized")

def get_template_path(template_name: str) -> str:
    """Get full path to a core template"""
    return f"modules/core/templates/{template_name}"

def render_template(request: Request, template_name: str, **context):
    """Render a core template with context"""
    return templates.TemplateResponse(
        get_template_path(template_name),
        {"request": request, **context}
    )

__all__ = [
    # Services
    'SystemService',
    'ConfigService',
    'FileService',
    'system_service',
    'config_service',
    'file_service',

    # Middleware
    'SecurityHeadersMiddleware',
    'MaintenanceModeMiddleware',
    'setup_middleware',

    # Models
    'SystemConfig',

    # Utilities
    'get_db',
    'get_redis',
    'init_app',
    'get_template_path',
    'render_template'
]