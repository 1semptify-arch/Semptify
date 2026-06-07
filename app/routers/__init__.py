# API Routers - Semptify 5.0
# Storage-based authentication: user's cloud storage = identity
# NOTE: This directory is deprecated. Use app.modules.* for new routers.

from app.routers import vault, copilot, health, storage, intake
import logging
logger = logging.getLogger(__name__)

try:
    from app.routers import timeline, calendar
    __all__ = ["vault", "timeline", "calendar", "copilot", "health", "storage", "intake"]
except ImportError:
    # Optional database-backed routers when SQLAlchemy is installed
    __all__ = ["vault", "copilot", "health", "storage", "intake"]
