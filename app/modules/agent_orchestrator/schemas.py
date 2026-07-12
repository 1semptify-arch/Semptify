"""Pydantic schemas for the Agent Orchestrator module."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Kanban-style status for an agent task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ModelId(str, Enum):
    """Unlimited model identifiers available in Windsurf / Devin Desktop."""

    GLM_5_2 = "glm-5.2"
    SWE_1_6 = "swe-1.6"
    SWE_1_7 = "swe-1.7"
    KIMI_2_7 = "kimi-2.7"


class TaskCategory(str, Enum):
    """Broad work category used to tailor generated prompts."""

    STUB_FIX = "stub_fix"
    DUPLICATE_RESOLVE = "duplicate_resolve"
    TEST_ADD = "test_add"
    DOC_UPDATE = "doc_update"
    REFACTOR = "refactor"
    OTHER = "other"


class TaskPriority(str, Enum):
    """Severity mapped from the workbook HIGH/MEDIUM/LOW ratings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentTaskCreate(BaseModel):
    """Request body to create a single agent task."""

    title: str = Field(..., min_length=1, description="Short task title")
    description: str = Field(default="", description="Details / acceptance criteria")
    category: TaskCategory = Field(default=TaskCategory.STUB_FIX)
    target_model: ModelId
    file_path: str = Field(default="", description="Repo-relative file to touch")
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)


class AgentTaskUpdate(BaseModel):
    """Request body to update mutable task fields."""

    status: TaskStatus | None = None
    target_model: ModelId | None = None
    notes: str | None = None


class AgentTaskResponse(BaseModel):
    """Full task representation returned by the API."""

    id: str
    title: str
    description: str
    category: TaskCategory
    target_model: ModelId
    status: TaskStatus
    file_path: str
    line_start: int | None
    line_end: int | None
    priority: TaskPriority
    notes: str
    prompt: str
    created_at: datetime
    updated_at: datetime


class BatchCreateRequest(BaseModel):
    """Create several tasks at once from workbook rows."""

    tasks: list[AgentTaskCreate] = Field(..., min_length=1)


class BatchCreateResponse(BaseModel):
    """Result of a batch create."""

    created: list[str]
    total: int


class ModelListResponse(BaseModel):
    """Available models with brief notes."""

    models: list[dict]
