from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOverlayCreate(BaseModel):
    document_id: str = Field(min_length=1)
    overlay_type: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    vault_id: str | None = None
    metadata: dict | None = None


class DocumentOverlaySummary(BaseModel):
    overlay_id: str
    document_id: str
    overlay_type: str
    vault_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentOverlayDetail(DocumentOverlaySummary):
    payload: dict = Field(default_factory=dict)
    metadata: dict | None = None
    applied_at: datetime | None = None


class DocumentOverlayApplyRequest(BaseModel):
    dry_run: bool = False


class DocumentOverlayApplyResponse(BaseModel):
    overlay_id: str
    status: str
    dry_run: bool
    message: str
