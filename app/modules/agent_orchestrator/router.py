"""Agent Orchestrator Router.

Admin-only API for queueing parallel agent tasks. v1 is in-memory; use it to
turn workbook rows (Stubs & TODOs, Duplicates) into copy-paste prompts for the
unlimited model fleet in Windsurf / Devin Desktop.

Endpoints:
  GET  /api/agent-orchestrator/tasks              — list tasks
  GET  /api/agent-orchestrator/tasks/{task_id}     — get task
  GET  /api/agent-orchestrator/tasks/{task_id}/prompt — copy-paste prompt
  POST /api/agent-orchestrator/tasks               — create task
  PATCH /api/agent-orchestrator/tasks/{task_id}/status — update status/model/notes
  DELETE /api/agent-orchestrator/tasks/{task_id}  — delete task
  POST /api/agent-orchestrator/batch               — create several tasks at once
  GET /api/agent-orchestrator/models               — list available models
  GET /api/agent-orchestrator/summary              — board counts by status
"""

import logging
import os

logger = logging.getLogger(__name__)

# Explicit environment guard — independent of the product-tier system.
# The Agent Orchestrator is dev-only and must not load in production even if
# the manifest is misconfigured.
if os.getenv("SEMPTIFY_ENV", "production").lower() == "production":
    raise ImportError(
        "Agent Orchestrator router is disabled in production (SEMPTIFY_ENV=production)."
    )

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.modules.agent_orchestrator.schemas import (
    AgentTaskCreate,
    AgentTaskResponse,
    AgentTaskUpdate,
    BatchCreateRequest,
    BatchCreateResponse,
    ModelId,
    ModelListResponse,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)
from app.modules.agent_orchestrator.service import AgentOrchestratorService

router = APIRouter(tags=["Agent Orchestrator"])


# =============================================================================
# Auth — reuse stealth admin from admin_console
# =============================================================================


async def _stealth_admin(request: Request):
    """Stealth admin guard — returns 404 to non-admins."""
    from app.modules.admin_console.router import _stealth_admin as _admin

    return await _admin(request)


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/tasks", response_model=list[AgentTaskResponse])
async def list_tasks(
    request: Request,
    status: TaskStatus | None = Query(default=None),
    model: ModelId | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    category: TaskCategory | None = Query(default=None),
    _admin=Depends(_stealth_admin),
) -> list[AgentTaskResponse]:
    """List queued agent tasks, optionally filtered."""

    tasks = AgentOrchestratorService.list_tasks(
        status=status,
        model=model,
        priority=priority,
    )
    if category is not None:
        tasks = [t for t in tasks if t.category == category]
    return tasks


@router.post("/tasks", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: Request,
    payload: AgentTaskCreate,
    _admin=Depends(_stealth_admin),
) -> AgentTaskResponse:
    """Create a new agent task."""

    return AgentOrchestratorService.create_task(payload)


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    request: Request,
    task_id: str,
    _admin=Depends(_stealth_admin),
) -> AgentTaskResponse:
    """Get a single task by ID."""

    task = AgentOrchestratorService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/tasks/{task_id}/prompt")
async def get_prompt(
    request: Request,
    task_id: str,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Return the generated copy-paste prompt for a task."""

    task = AgentOrchestratorService.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"task_id": task_id, "prompt": task.prompt}


@router.patch("/tasks/{task_id}/status", response_model=AgentTaskResponse)
async def update_task(
    request: Request,
    task_id: str,
    update: AgentTaskUpdate,
    _admin=Depends(_stealth_admin),
) -> AgentTaskResponse:
    """Update task status, assigned model, or notes."""

    task = AgentOrchestratorService.update_task(task_id, update)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    request: Request,
    task_id: str,
    _admin=Depends(_stealth_admin),
) -> None:
    """Delete a task permanently."""

    deleted = AgentOrchestratorService.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post("/batch", response_model=BatchCreateResponse)
async def create_batch(
    request: Request,
    batch: BatchCreateRequest,
    _admin=Depends(_stealth_admin),
) -> BatchCreateResponse:
    """Create several tasks at once from workbook rows."""

    created = AgentOrchestratorService.create_batch(batch.tasks)
    return BatchCreateResponse(created=created, total=len(created))


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    request: Request,
    _admin=Depends(_stealth_admin),
) -> ModelListResponse:
    """List the unlimited model fleet with usage notes."""

    return ModelListResponse(models=AgentOrchestratorService.get_available_models())


@router.get("/summary")
async def get_summary(
    request: Request,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Return board counts by status and priority."""

    tasks = AgentOrchestratorService.list_tasks()
    by_status: dict[str, int] = {}
    by_model: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for task in tasks:
        by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
        by_model[task.target_model.value] = by_model.get(task.target_model.value, 0) + 1
        by_priority[task.priority.value] = by_priority.get(task.priority.value, 0) + 1

    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_model": by_model,
        "by_priority": by_priority,
    }
