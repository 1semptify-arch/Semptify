# API Routers - Semptify 5.0
# Storage-based authentication: user's cloud storage = identity

from app.routers import auth, vault, copilot, health, storage, intake

try:
    from app.routers import timeline, calendar
    __all__ = ["auth", "vault", "timeline", "calendar", "copilot", "health", "storage", "intake"]
except ImportError:
    # Optional database-backed routers when SQLAlchemy is installed
    __all__ = ["auth", "vault", "copilot", "health", "storage", "intake"]
