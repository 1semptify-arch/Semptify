"""Pydantic schemas for the resource directory module."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResourceContactInfo(BaseModel):
    """Contact points for a resource listing."""

    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None


class ResourceBase(BaseModel):
    """Shared fields for resource requests and responses."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    service_area: str | None = Field(None, max_length=255)
    languages: list[str] = Field(default_factory=list)
    contact_info: ResourceContactInfo = Field(default_factory=ResourceContactInfo)
    source: str | None = Field(None, max_length=255)
    last_verified: datetime | None = None
    is_active: bool = True


class ResourceCreate(ResourceBase):
    """Admin request to create a single resource."""


class ResourceUpdate(BaseModel):
    """Admin request to update a resource."""

    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, min_length=1, max_length=100)
    service_area: str | None = Field(None, max_length=255)
    languages: list[str] | None = None
    contact_info: ResourceContactInfo | None = None
    source: str | None = Field(None, max_length=255)
    last_verified: datetime | None = None
    is_active: bool | None = None


class ResourceRead(ResourceBase):
    """Public response for a resource listing."""

    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    """Public list response."""

    resources: list[ResourceRead]
    total: int


class ResourceImportResponse(BaseModel):
    """Admin CSV import summary."""

    imported: int
    updated: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
