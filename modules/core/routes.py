"""
Core Module Routes

Provides core system routes including logging and session management.
"""

import platform
import psutil
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import redis

from . import get_db, get_redis
from .services import LoggingService, ConfigService, SessionService
from .models import SystemLog

router = APIRouter()

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "5.0.0",
        "services": {}
    }

    # Check database
    try:
        await db.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "disabled"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # System info
    health_status["system"] = {
        "platform": platform.system(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@router.get("/status")
async def system_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Detailed system status"""
    return {
        "application": {
            "name": "Semptify",
            "version": "5.0.0",
            "environment": "development",
            "uptime": "0d 0h 0m"  # TODO: Implement uptime tracking
        },
        "database": {
            "type": "SQLite",
            "status": "connected"
        },
        "cache": {
            "type": "Redis",
            "status": "connected" if await get_redis() else "disconnected"
        },
        "modules": [
            "core",
            "auth",
            "storage",
            "vault",
            "documents",
            "timeline",
            "navigation"
        ]
    }

@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get application configuration (safe, non-sensitive)"""
    return {
        "features": {
            "storage_providers": ["google_drive", "dropbox", "onedrive"],
            "ai_processing": True,
            "timeline_automation": True,
            "document_vault": True
        },
        "limits": {
            "max_file_size": ConfigService.get_config('storage.max_file_size'),
            "allowed_file_types": ConfigService.get_config('storage.allowed_types')
        },
        "ui": {
            "theme": ConfigService.get_config('ui.theme'),
            "language": ConfigService.get_config('ui.language')
        }
    }

# Logging endpoints
@router.get("/logs")
async def get_logs(
    db: AsyncSession = Depends(get_db),
    level: str = None,
    module: str = None,
    limit: int = 100
) -> Dict[str, Any]:
    """Get system logs"""
    query = db.query(SystemLog)

    if level:
        query = query.filter(SystemLog.level == level.upper())
    if module:
        query = query.filter(SystemLog.module == module)

    logs = await query.order_by(SystemLog.timestamp.desc()).limit(limit).all()

    return {
        "logs": [
            {
                "id": log.id,
                "level": log.level,
                "module": log.module,
                "message": log.message,
                "data": log.data,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    }

@router.post("/logs")
async def create_log_entry(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a log entry"""
    data = await request.json()
    level = data.get('level', 'INFO')
    module = data.get('module', 'unknown')
    message = data.get('message', '')
    extra_data = data.get('data', {})

    LoggingService.log(level, module, message, extra_data)

    return {"status": "logged"}

# Session endpoints
@router.post("/session")
async def create_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new user session"""
    data = await request.json()
    user_id = data.get('user_id')
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    session_id = SessionService.create_session(user_id, ip_address, user_agent)

    return {
        "session_id": session_id,
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
    }

@router.get("/session/{session_id}")
async def validate_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Validate a session"""
    user_id = SessionService.validate_session(session_id)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    return {"user_id": user_id, "valid": True}

@router.delete("/session/{session_id}")
async def destroy_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Destroy a session"""
    SessionService.destroy_session(session_id)
    return {"status": "destroyed"}

# System configuration endpoints
@router.get("/system/config")
async def get_system_config(
    key: str = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get system configuration"""
    if key:
        value = ConfigService.get_config(key)
        return {key: value}
    else:
        # Return all config (in real app, filter sensitive data)
        return {
            "app.name": ConfigService.get_config('app.name'),
            "app.version": ConfigService.get_config('app.version'),
            "storage.max_file_size": ConfigService.get_config('storage.max_file_size'),
            "ui.theme": ConfigService.get_config('ui.theme')
        }

@router.post("/system/config")
async def set_system_config(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Set system configuration"""
    data = await request.json()
    key = data.get('key')
    value = data.get('value')
    description = data.get('description')

    if not key:
        raise HTTPException(status_code=400, detail="key required")

    ConfigService.set_config(key, value, description)
    return {"status": "updated"}
        "limits": {
            "max_file_size": "100MB",
            "max_documents": 1000,
            "max_timeline_events": 500
        },
        "ui": {
            "theme": "auto",
            "language": "en",
            "timezone": "UTC"
        }
    }

@router.get("/error/{error_code}")
async def error_page(request: Request, error_code: int):
    """Error page template"""
    error_messages = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Page Not Found",
        500: "Internal Server Error"
    }

    return render_template(
        request,
        "error.html",
        error_code=error_code,
        error_message=error_messages.get(error_code, "Unknown Error"),
        current_year=datetime.now().year
    )

# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return render_template(
        request,
        "error.html",
        error_code=exc.status_code,
        error_message=exc.detail,
        current_year=datetime.now().year
    )

# API Routes

@router.get("/api/info")
async def api_info():
    """API information"""
    return {
        "name": "Semptify Core API",
        "version": "1.0.0",
        "description": "Core services for Semptify application",
        "endpoints": [
            "/health",
            "/status",
            "/config",
            "/api/info",
            "/api/log",
            "/api/time"
        ]
    }

@router.post("/api/log")
async def log_event(request: Request):
    """Log client-side events"""
    try:
        data = await request.json()
        level = data.get('level', 'info')
        module = data.get('module', 'client')
        message = data.get('message', '')
        extra_data = data.get('data', {})

        logging_service.log(level, module, message, extra_data)

        return {"status": "logged"}
    except Exception as e:
        logging_service.error('core', f'Failed to log client event: {str(e)}')
        raise HTTPException(status_code=400, detail="Invalid log data")

@router.get("/api/time")
async def server_time():
    """Get server time"""
    return {
        "server_time": datetime.now().isoformat(),
        "timezone": "UTC"
    }

@router.get("/maintenance")
async def maintenance_page(request: Request):
    """Maintenance mode page"""
    return render_template(
        request,
        "maintenance.html",
        title="Under Maintenance",
        message="Semptify is currently undergoing maintenance. Please check back soon."
    )

@router.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    return render_template(
        request,
        "error.html",
        error_code=500,
        error_message="An unexpected error occurred",
        current_year=datetime.now().year
    )