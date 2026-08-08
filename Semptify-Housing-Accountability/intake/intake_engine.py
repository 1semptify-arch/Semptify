"""Evidence intake workflows for housing accountability documentation."""

from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.utc import utc_now


def extract_metadata(file: dict[str, Any]) -> dict[str, Any]:
    """Extract basic metadata from an intake file descriptor.

    The file descriptor is expected to contain at least a `filename` and
    optionally `content_type` and `size`.
    """
    filename = file.get("filename", "")
    path = Path(filename)
    return {
        "filename": filename,
        "extension": path.suffix.lower().lstrip("."),
        "content_type": file.get("content_type", "application/octet-stream"),
        "size_bytes": file.get("size", 0),
        "extracted_at": utc_now().isoformat(),
    }


def tag_category(file: dict[str, Any]) -> str:
    """Assign a broad evidence category based on filename keywords."""
    filename = (file.get("filename", "") or "").lower()
    categories = [
        ("lease", ["lease", "rental", "rent agreement"]),
        ("notice", ["notice", "eviction", "summons", "complaint"]),
        ("payment", ["receipt", "payment", "invoice", "rent"]),
        ("repair", ["repair", "maintenance", "habitability", "mold"]),
        ("photo", ["photo", "image", "jpg", "jpeg", "png"]),
        ("communication", ["email", "text", "letter", "message"]),
    ]
    for category, keywords in categories:
        if any(kw in filename for kw in keywords):
            return category
    return "uncategorized"


def append_to_timeline(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize and append an intake event to the module timeline."""
    return {
        "event_id": event.get("event_id") or str(uuid4()),
        "title": event.get("title", "Intake event"),
        "date": event.get("date") or utc_now().isoformat(),
        "type": event.get("type", "intake"),
        "details": dict(event.get("details", {})),
    }


def save_intake_record(record: dict[str, Any]) -> dict[str, Any]:
    """Persist an intake record by returning a normalized copy with an ID."""
    saved = dict(record)
    saved.setdefault("record_id", str(uuid4()))
    saved.setdefault("saved_at", utc_now().isoformat())
    return saved
