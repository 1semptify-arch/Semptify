"""Eviction Timeline Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime


class TimelineEventSource(StrEnum):
    MANUAL = "manual"
    DOCUMENT = "document"
    COURT = "court"
    EMAIL = "email"


class EvictionTimelineEventCreate(BaseModel):
    """Create an eviction timeline event."""

    subject_id: str | None = Field(None, max_length=36)
    event_type: str = Field(..., max_length=50)
    event_date: datetime
    source: TimelineEventSource = Field(TimelineEventSource.MANUAL)
    source_document_id: str | None = Field(None, max_length=36)
    content_overlay_id: str | None = Field(None, max_length=36)
    jurisdiction: str = Field("MN", max_length=10)


class EvictionTimelineEventRead(BaseModel):
    """Eviction timeline event as returned by the API."""

    id: str
    user_id: str
    subject_id: str | None
    event_type: str
    event_date: datetime
    source: TimelineEventSource
    source_document_id: str | None
    content_overlay_id: str | None
    jurisdiction: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvictionTimelineEventUpdate(BaseModel):
    """Partial update of an eviction timeline event."""

    subject_id: str | None = Field(None, max_length=36)
    event_type: str | None = Field(None, max_length=50)
    event_date: datetime | None = None
    source: TimelineEventSource | None = None
    source_document_id: str | None = Field(None, max_length=36)
    content_overlay_id: str | None = Field(None, max_length=36)
    jurisdiction: str | None = Field(None, max_length=10)
