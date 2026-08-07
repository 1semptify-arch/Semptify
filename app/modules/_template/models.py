"""
Module Template — Pydantic Models

Replace with your module's request/response models. Keep models thin —
business logic belongs in service.py.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.utc import utc_now


class ItemCreate(BaseModel):
    """Example create request."""

    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    description: str | None = Field(None, max_length=2000, description="Item description")


class ItemUpdate(BaseModel):
    """Example update request."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)


class ItemResponse(BaseModel):
    """Example response model."""

    id: str
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str
