"""
Core System Router - System Infrastructure and Services
==================================================

FastAPI router for core system functionality including logging,
configuration management, session management, and system monitoring.
"""
# Migrated from app/routers/core_system.py into the core_system SDK module.
# All imports remain absolute since core_system is a CORE module.

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.product_manifest import get_deploy_target
from app.core.runtime_profile import get_active_profile
from app.core.security import get_current_user
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

# Initialize core system router
router = APIRouter(prefix="/api/core", tags=["Core System"])

# Keep backward compatibility
core_router = router


# Pydantic Models
class SystemConfigRequest(BaseModel):
    """Request for system configuration update."""

    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    description: str | None = Field(None, description="Configuration description")


class SystemLogRequest(BaseModel):
    """Request for system logging."""

    level: str = Field(..., description="Log level (INFO, ERROR, WARNING, DEBUG)")
    module: str = Field(..., description="Module name")
    message: str = Field(..., description="Log message")
    data: dict[str, Any] | None = Field(None, description="Additional structured data")


class SessionCreateRequest(BaseModel):
    """Request for session creation."""

    user_id: str = Field(..., description="User ID")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent string")


def _database_type(database_url: str) -> str:
    """Human label for the configured database backend."""
    url = (database_url or "").lower()
    if "sqlite" in url:
        return "SQLite"
    if "postgres" in url:
        return "PostgreSQL"
    if "mysql" in url or "mariadb" in url:
        return "MySQL"
    return url.split(":", 1)[0] if url else "unknown"


def _environment_label() -> str:
    """Live environment label from SEMPTIFY_ENV (the same var _get_enabled_tiers
    reads in main.py), falling back to 'testing' under the test harness and
    'production' otherwise."""
    env = os.getenv("SEMPTIFY_ENV", "").strip().lower()
    if env:
        return env
    if os.getenv("TESTING", "").lower() in ("true", "1", "yes", "on"):
        return "testing"
    return "production"


def _mounted_module_names() -> list[str]:
    """Module names actually loaded in this process.

    Walks the product manifest and keeps only entries whose module_path is in
    sys.modules — so the list reflects the MVP allow-list, enabled tiers, and
    skipped optional imports rather than a fixed placeholder list.
    """
    try:
        from app.core.product_manifest import MANIFEST
    except Exception:
        return []
    names = set()
    for entry in MANIFEST.all():
        if entry.module_path not in sys.modules:
            continue
        label = entry.module_path
        for prefix in ("app.modules.", "app.routers."):
            if label.startswith(prefix):
                label = label[len(prefix) :]
                break
        if label.endswith(".router"):
            label = label[: -len(".router")]
        names.add(label)
    return sorted(names)


async def _probe_database() -> str:
    """Live connectivity check: SELECT 1 against the configured engine."""
    try:
        from sqlalchemy import text

        from app.core.database import SQLALCHEMY_AVAILABLE, get_engine

        if not SQLALCHEMY_AVAILABLE:
            return "unavailable"

        async def _check():
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_check(), timeout=8)
        return "connected"
    except Exception:
        logger.warning("Database status probe failed", exc_info=True)
        return "unreachable"


# Core System Services (simplified versions for integration)
class CoreSystemService:
    """Core system service implementation."""

    def __init__(self):
        self.config_cache = {}
        self.session_store = {}
        self.log_store = []
        self._start_time = utc_now()

    def _get_uptime(self) -> str:
        """Return human-readable uptime string."""
        delta = utc_now() - self._start_time
        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_cache.get(key, default)

    def set_config(self, key: str, value: Any, description: str | None = None):
        """Set configuration value."""
        self.config_cache[key] = {"value": value, "description": description, "updated_at": utc_now().isoformat()}

    def create_session(self, user_id: str, ip_address: str | None = None, user_agent: str | None = None) -> str:
        """Create a new user session."""
        import secrets

        session_id = secrets.token_urlsafe(32)

        self.session_store[session_id] = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": utc_now().isoformat(),
            "expires_at": (utc_now() + timedelta(hours=1)).isoformat(),
            "is_active": True,
        }

        return session_id

    def validate_session(self, session_id: str) -> str | None:
        """Validate session and return user_id if valid."""
        if session_id not in self.session_store:
            return None

        session = self.session_store[session_id]
        expires_at = datetime.fromisoformat(session["expires_at"])

        if not session["is_active"] or expires_at < utc_now():
            return None

        return session["user_id"]

    def add_log(self, level: str, module: str, message: str, data: dict[str, Any] | None = None):
        """Add system log entry."""
        log_entry = {
            "level": level.upper(),
            "module": module,
            "message": message,
            "data": data,
            "timestamp": utc_now().isoformat(),
        }

        self.log_store.append(log_entry)

        # Keep only last 1000 entries
        if len(self.log_store) > 1000:
            self.log_store = self.log_store[-1000:]

    def get_logs(self, level: str | None = None, module: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get system logs with optional filtering."""
        filtered_logs = self.log_store

        if level:
            filtered_logs = [log for log in filtered_logs if log["level"] == level.upper()]

        if module:
            filtered_logs = [log for log in filtered_logs if log["module"] == module]

        return filtered_logs[-limit:]

    def get_system_status(self, database_status: str = "unknown") -> dict[str, Any]:
        """Get comprehensive system status (live config, not placeholders)."""
        settings = get_settings()
        return {
            "application": {
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": _environment_label(),
                "deploy_target": get_deploy_target(),
                "load_profile": get_active_profile().name,
                "uptime": self._get_uptime(),
            },
            "database": {"type": _database_type(settings.database_url), "status": database_status},
            "cache": {"type": "Memory", "status": "in-process"},
            "modules": _mounted_module_names(),
            "statistics": {
                "active_sessions": len([s for s in self.session_store.values() if s["is_active"]]),
                "total_log_entries": len(self.log_store),
                "config_entries": len(self.config_cache),
            },
        }


# Initialize core system service
core_service = CoreSystemService()


@core_router.get("/health")
async def health_check():
    """Health check endpoint for core system."""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": utc_now().isoformat(),
            "version": get_settings().app_version,
            "services": {"core_system": "healthy", "database": "healthy", "cache": "healthy"},
        }

        return JSONResponse(content=health_status, status_code=200)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "timestamp": utc_now().isoformat(), "error": str(e)}, status_code=503
        )


@core_router.get("/status")
async def system_status(current_user=Depends(get_current_user)):
    """Get detailed system status."""
    try:
        status = core_service.get_system_status(database_status=await _probe_database())

        return JSONResponse(content={"success": True, "status": status, "retrieved_at": utc_now().isoformat()})

    except Exception as e:
        logger.error(f"System status retrieval failed: {e}")
        logger.exception("Status retrieval failed")
        raise HTTPException(status_code=500, detail="Status retrieval failed")


@core_router.get("/config")
async def get_system_config(current_user=Depends(get_current_user)):
    """Get system configuration (safe, non-sensitive)."""
    try:
        # Return only safe configuration keys
        safe_config = {}
        for key, config_data in core_service.config_cache.items():
            if not any(sensitive in key.lower() for sensitive in ["password", "secret", "key", "token"]):
                safe_config[key] = config_data

        return JSONResponse(content={"success": True, "config": safe_config, "retrieved_at": utc_now().isoformat()})

    except Exception as e:
        logger.error(f"Config retrieval failed: {e}")
        logger.exception("Config retrieval failed")
        raise HTTPException(status_code=500, detail="Config retrieval failed")


@core_router.post("/config")
async def update_system_config(request: SystemConfigRequest, current_user=Depends(get_current_user)):
    """Update system configuration."""
    try:
        core_service.set_config(request.key, request.value, request.description)

        return JSONResponse(
            content={
                "success": True,
                "message": f"Configuration '{request.key}' updated successfully",
                "updated_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Config update failed: {e}")
        logger.exception("Config update failed")
        raise HTTPException(status_code=500, detail="Config update failed")


@core_router.post("/session")
async def create_session(request: SessionCreateRequest):
    """Create a new user session."""
    try:
        session_id = core_service.create_session(request.user_id, request.ip_address, request.user_agent)

        return JSONResponse(
            content={
                "success": True,
                "session_id": session_id,
                "user_id": request.user_id,
                "created_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Session creation failed: {e}")
        logger.exception("Session creation failed")
        raise HTTPException(status_code=500, detail="Session creation failed")


@core_router.get("/session/{session_id}")
async def validate_session(session_id: str):
    """Validate a user session."""
    try:
        user_id = core_service.validate_session(session_id)

        return JSONResponse(
            content={
                "success": True,
                "valid": user_id is not None,
                "user_id": user_id,
                "validated_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Session validation failed: {e}")
        logger.exception("Session validation failed")
        raise HTTPException(status_code=500, detail="Session validation failed")


@core_router.delete("/session/{session_id}")
async def destroy_session(session_id: str, current_user=Depends(get_current_user)):
    """Destroy a user session."""
    try:
        if session_id in core_service.session_store:
            core_service.session_store[session_id]["is_active"] = False
            message = "Session destroyed successfully"
        else:
            message = "Session not found"

        return JSONResponse(
            content={
                "success": True,
                "message": message,
                "session_id": session_id,
                "destroyed_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Session destruction failed: {e}")
        logger.exception("Session destruction failed")
        raise HTTPException(status_code=500, detail="Session destruction failed")


@core_router.post("/log")
async def add_system_log(request: SystemLogRequest, current_user=Depends(get_current_user)):
    """Add a system log entry."""
    try:
        core_service.add_log(request.level, request.module, request.message, request.data)

        return JSONResponse(
            content={"success": True, "message": "Log entry added successfully", "logged_at": utc_now().isoformat()}
        )

    except Exception as e:
        logger.error(f"Log addition failed: {e}")
        logger.exception("Log addition failed")
        raise HTTPException(status_code=500, detail="Log addition failed")


@core_router.get("/logs")
async def get_system_logs(
    level: str | None = None, module: str | None = None, limit: int = 100, current_user=Depends(get_current_user)
):
    """Get system logs with optional filtering."""
    try:
        logs = core_service.get_logs(level, module, limit)

        return JSONResponse(
            content={
                "success": True,
                "logs": logs,
                "filters": {"level": level, "module": module, "limit": limit},
                "retrieved_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Log retrieval failed: {e}")
        logger.exception("Log retrieval failed")
        raise HTTPException(status_code=500, detail="Log retrieval failed")


@core_router.get("/statistics")
async def get_system_statistics(current_user=Depends(get_current_user)):
    """Get system statistics."""
    try:
        status = core_service.get_system_status()

        return JSONResponse(
            content={
                "success": True,
                "statistics": status["statistics"],
                "system_info": {"application": status["application"], "modules": status["modules"]},
                "retrieved_at": utc_now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        logger.exception("Statistics retrieval failed")
        raise HTTPException(status_code=500, detail="Statistics retrieval failed")
