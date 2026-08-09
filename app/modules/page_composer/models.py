"""Page Composer data models."""

from typing import Any

from pydantic import BaseModel, Field

from app.modules.page_shell.models import PageConfig


class PageAssemblyRequest(BaseModel):
    """Payload for the generic POST /api/page/assemble endpoint."""

    subject: str
    jurisdiction: str = "MN"
    intent: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    fact_limit: int = Field(default=10, ge=1, le=50)
    story_limit: int = Field(default=5, ge=1, le=20)
    render: bool = False


class PageAssemblyMetadata(BaseModel):
    """Diagnostic metadata for a page assembly."""

    subject: str | None
    jurisdiction: str
    major_pillar: str
    blend: str
    intensity: int = Field(ge=0, le=100)
    risk_tier: str


class PageAssemblyResult(BaseModel):
    """Output of the Page Composer assembly formula.

    Contains the Page Shell config, a legacy UI Composer component list,
    and a GOVERN audit report.
    """

    page_config: PageConfig
    components: list[dict]
    govern_report: dict
    metadata: PageAssemblyMetadata
