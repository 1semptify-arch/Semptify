"""In-memory task store and prompt generator for the Agent Orchestrator.

v1 intentionally stores tasks in memory to avoid migrations while the workflow
is validated. Restarting the dev server resets the queue — that is acceptable
for a dev_only Forge tool.
"""

import logging
import uuid

from app.core.utc import utc_now
from app.modules.agent_orchestrator.schemas import (
    AgentTaskCreate,
    AgentTaskResponse,
    AgentTaskUpdate,
    ModelId,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# In-memory task store. Key: task UUID string.
_tasks: dict[str, dict] = {}


class AgentOrchestratorService:
    """Manage the agent task queue and render prompts."""

    @staticmethod
    def _generate_prompt(task: dict) -> str:
        """Build a copy-paste prompt tailored to the task category."""

        location = task["file_path"] or "(unspecified file)"
        if task.get("line_start") and task.get("line_end"):
            location = f"{location}:{task['line_start']}-{task['line_end']}"
        elif task.get("line_start"):
            location = f"{location}:{task['line_start']}"

        base_context = (
            "You are working inside the Semptify FastAPI repo. "
            "Target Python 3.11.9. Follow AGENTS.md rules: never touch main, "
            "use utc_now(), no bare except blocks, SSOT redirects only, "
            "and fix root causes instead of adding workarounds."
        )

        category = task["category"]
        if category == TaskCategory.STUB_FIX.value:
            body = (
                f"Fix the stub at {location}. "
                f"Description: {task['description']}\n\n"
                "If the behavior is not yet definable, replace the silent empty "
                "return / pass with a clear NotImplementedError so failures are "
                "loud. Otherwise implement the real behavior and add or update "
                "regression tests. Work on a feature branch, not main."
            )
        elif category == TaskCategory.DUPLICATE_RESOLVE.value:
            body = (
                f"Resolve duplicate/overlap at {location}. "
                f"Description: {task['description']}\n\n"
                "Pick the canonical implementation, deprecate or delete the "
                "redundant code, and update all imports. Do not leave both "
                "systems live unless there is a documented reason."
            )
        elif category == TaskCategory.TEST_ADD.value:
            body = (
                f"Add tests covering {location}. "
                f"Description: {task['description']}\n\n"
                "Write focused regression tests before or alongside the fix. "
                "Do not weaken existing tests."
            )
        elif category == TaskCategory.DOC_UPDATE.value:
            body = (
                f"Update documentation at {location}. "
                f"Description: {task['description']}\n\n"
                "Update canonical docs before code when AGENTS.md / BIBLE / "
                "BUILD_GUIDE are affected. Keep prose plain and short."
            )
        elif category == TaskCategory.REFACTOR.value:
            body = (
                f"Refactor {location}. "
                f"Description: {task['description']}\n\n"
                "Make minimal, focused changes. Preserve behavior. Run existing "
                "tests and py_compile."
            )
        else:
            body = (
                f"Task at {location}. "
                f"Description: {task['description']}\n\n"
                "Implement, test, and verify py_compile passes."
            )

        return f"{base_context}\n\n{body}"

    @classmethod
    def create_task(cls, payload: AgentTaskCreate) -> AgentTaskResponse:
        """Create a new task and return its full representation."""

        now = utc_now()
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "title": payload.title,
            "description": payload.description,
            "category": payload.category.value,
            "target_model": payload.target_model.value,
            "status": TaskStatus.PENDING.value,
            "file_path": payload.file_path,
            "line_start": payload.line_start,
            "line_end": payload.line_end,
            "priority": payload.priority.value,
            "notes": "",
            "prompt": "",
            "created_at": now,
            "updated_at": now,
        }
        task["prompt"] = cls._generate_prompt(task)
        _tasks[task_id] = task
        logger.info("Created agent task %s: %s", task_id, payload.title)
        return cls._to_response(task)

    @classmethod
    def list_tasks(
        cls,
        status: TaskStatus | None = None,
        model: ModelId | None = None,
        priority: TaskPriority | None = None,
    ) -> list[AgentTaskResponse]:
        """List tasks, optionally filtered."""

        results = []
        for task in _tasks.values():
            if status and task["status"] != status.value:
                continue
            if model and task["target_model"] != model.value:
                continue
            if priority and task["priority"] != priority.value:
                continue
            results.append(cls._to_response(task))
        return sorted(results, key=lambda t: t.created_at, reverse=True)

    @classmethod
    def get_task(cls, task_id: str) -> AgentTaskResponse | None:
        """Fetch a single task by ID."""

        task = _tasks.get(task_id)
        if not task:
            return None
        return cls._to_response(task)

    @classmethod
    def update_task(cls, task_id: str, update: AgentTaskUpdate) -> AgentTaskResponse | None:
        """Apply a partial update to a task."""

        task = _tasks.get(task_id)
        if not task:
            return None

        if update.status is not None:
            task["status"] = update.status.value
        if update.target_model is not None:
            task["target_model"] = update.target_model.value
        if update.notes is not None:
            task["notes"] = update.notes

        task["updated_at"] = utc_now()
        task["prompt"] = cls._generate_prompt(task)
        return cls._to_response(task)

    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """Remove a task permanently."""

        if task_id not in _tasks:
            return False
        del _tasks[task_id]
        logger.info("Deleted agent task %s", task_id)
        return True

    @classmethod
    def create_batch(cls, payloads: list[AgentTaskCreate]) -> list[str]:
        """Create multiple tasks and return their IDs."""

        created = []
        for payload in payloads:
            response = cls.create_task(payload)
            created.append(response.id)
        return created

    @classmethod
    def get_available_models(cls) -> list[dict]:
        """Return the unlimited model fleet with usage notes."""

        return [
            {
                "id": ModelId.SWE_1_7.value,
                "name": "SWE-1.7",
                "note": "Best for mechanical code fixes and tests.",
            },
            {
                "id": ModelId.KIMI_2_7.value,
                "name": "Kimi 2.7",
                "note": "Strong for refactor and duplicate resolution.",
            },
            {
                "id": ModelId.SWE_1_6.value,
                "name": "SWE-1.6",
                "note": "Reliable fallback for stub fixes.",
            },
            {
                "id": ModelId.GLM_5_2.value,
                "name": "GLM-5.2",
                "note": "Fast but occasionally returns empty tool calls; verify output.",
            },
        ]

    @classmethod
    def _to_response(cls, task: dict) -> AgentTaskResponse:
        """Convert internal dict to Pydantic response model."""

        return AgentTaskResponse(
            id=task["id"],
            title=task["title"],
            description=task["description"],
            category=TaskCategory(task["category"]),
            target_model=ModelId(task["target_model"]),
            status=TaskStatus(task["status"]),
            file_path=task["file_path"],
            line_start=task["line_start"],
            line_end=task["line_end"],
            priority=TaskPriority(task["priority"]),
            notes=task["notes"],
            prompt=task["prompt"],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
        )
