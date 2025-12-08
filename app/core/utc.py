"""
UTC DateTime Utilities for Semptify.

Provides consistent UTC datetime handling across the entire codebase.
All datetimes should be stored and handled in UTC with timezone awareness.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    This is the standard function for all timestamps in Semptify.
    Always returns a datetime with tzinfo=timezone.utc.
    
    Use this for:
    - Database timestamps (with DateTime(timezone=True) columns)
    - API responses
    - Comparisons
    - Audit logging
    
    Example:
        from app.core.utc import utc_now
        
        created_at = utc_now()  # 2025-12-08 03:00:00+00:00
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO 8601 string with Z suffix.
    
    Returns format: "2025-12-08T03:00:00.123456Z"
    
    Use this for:
    - JSON/API responses where string format is needed
    - Logging
    - Human-readable timestamps
    """
    return utc_now().isoformat().replace("+00:00", "Z")


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC timezone-aware datetime.
    
    - If naive: assumes UTC and adds timezone
    - If aware: converts to UTC
    
    Args:
        dt: Input datetime (naive or aware)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Aware datetime - convert to UTC
        return dt.astimezone(timezone.utc)


def parse_iso(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware UTC datetime.
    
    Handles:
    - "2025-12-08T03:00:00Z"
    - "2025-12-08T03:00:00+00:00"
    - "2025-12-08T03:00:00" (assumes UTC)
    
    Args:
        iso_string: ISO 8601 formatted datetime string
        
    Returns:
        Timezone-aware datetime in UTC
    """
    # Handle Z suffix
    cleaned = iso_string.replace("Z", "+00:00")
    
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        # Try parsing without timezone for naive strings
        dt = datetime.fromisoformat(iso_string)
    
    return to_utc(dt)
