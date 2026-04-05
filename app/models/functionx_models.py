from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FunctionXActionSetCreate(BaseModel):
    """Create a new FunctionX action set."""

    name: str = Field(min_length=1, max_length=120)
    actions: list[str] = Field(min_length=1)
    metadata: dict[str, Any] | None = None


class FunctionXActionSetSummary(BaseModel):
    """Summary view for an action set."""

    set_id: str
    name: str
    status: str
    actions_count: int
    created_at: datetime


class FunctionXActionSetDetail(FunctionXActionSetSummary):
    """Full detail view for an action set."""

    actions: list[str]
    metadata: dict[str, Any] | None = None
    last_executed_at: datetime | None = None


class FunctionXExecuteRequest(BaseModel):
    """Execution request for an existing action set."""

    dry_run: bool = True


class FunctionXExecuteResponse(BaseModel):
    """Execution result payload for FunctionX action set execution."""

    set_id: str
    status: str
    processed_actions: int
    dry_run: bool
    message: str
