"""
Example External Module — Models

Pydantic models for request/response validation. External modules
must NOT define SQLAlchemy DB models — only Pydantic models.
"""

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    """Request to create a timeline event."""

    type: str = Field(default="external", description="Event type")
    title: str = Field(..., min_length=1, max_length=200, description="Event title")
    description: str = Field(default="", max_length=2000, description="Event description")
    metadata: dict = Field(default_factory=dict, description="Event metadata")


class EventResponse(BaseModel):
    """Response after creating an event."""

    status: str
    event_id: str
    created_at: str
