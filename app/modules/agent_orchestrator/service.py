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
            "You are working inside the Semptify FastAPI repo — a housing-rights "
            "and tenant-support product. Read AGENTS.md, ACTIVE_CONTEXT.md, and "
            "BUILD_STATE.md before touching any file.\n\n"
            "HARD RULES (non-negotiable):\n"
            "1. Python 3.11.9 ONLY. Activate venv311 before running anything. "
            "Never introduce a dependency that requires 3.12+.\n"
            "2. Never commit to main. Work on a feature branch.\n"
            "3. Use utc_now() from app.core.utc — never bare datetime.now().\n"
            "4. No bare `except:` blocks. Catch specific exception types.\n"
            "5. No mutable default arguments (def f(items=[]) is a bug).\n"
            "6. SSOT redirects only: use navigation.get_stage() + ssot_redirect(). "
            "No hardcoded redirect URL strings in responses.\n"
            "7. Fix the ROOT CAUSE. Never add downstream compensating checks to "
            "mask upstream failures. Band-aids compound.\n"
            "8. Before calling another service's API, check the FunctionGroupContract "
            "in app/core/module_contracts.py. If a field or method is not in the "
            "contract, it does not exist — do not invent it.\n"
            "9. File rewrite protocol: if a file needs rewriting, ASK THE USER to "
            "rename the original to <name>_old.py first, then write into the "
            "original filename. NEVER create _v2/_new/_fixed/_impl replacement "
            "files — they break every import that points at the original.\n"
            "10. Never delete a static asset (CSS/JS/image) referenced by a template "
            "until the replacement is verified live. Half-finished migrations are "
            "worse than no migration.\n"
            "11. Verify every changed Python file with `python -m py_compile <file>` "
            "before ending the session.\n\n"
            "ORCHESTRATOR TASK STATUS (do this every time, unprompted):\n"
            "- The moment you pick up this task, run:\n"
            "  python tools/mark_task_status.py <task_id> in_progress --agent <your-model>\n"
            "- When finished:\n"
            '  python tools/mark_task_status.py <task_id> resolved --notes "<one-line summary>" --agent <your-model>\n'
            "- If blocked, use `review` instead of `resolved` and explain why in --notes.\n"
            "- This is how the queue stays accurate without a human tracking it by hand.\n\n"
            "KNOWN FAILURE REGISTRY (see AGENTS.md for the full list — do not repeat these):\n"
            "- Vault folder creation: check every create_folder() return value; raise on False.\n"
            "- Dropbox 409: only folder_name_exists is success; all other 409s raise.\n"
            "- Cloudflare 504: never put >20s of work in a single API call behind the tunnel.\n"
            "- Imports always go at the top of the file — never inject mid-file.\n"
            "- Register exception handlers exactly once; search for duplicates first.\n"
            "- Any new model/class used outside its own module must be added to the relevant __init__.py."
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
                "systems live unless there is a documented reason. Follow the "
                "file rewrite protocol in the hard rules if a full rewrite is needed."
            )
        elif category == TaskCategory.TEST_ADD.value:
            body = (
                f"Add tests covering {location}. "
                f"Description: {task['description']}\n\n"
                "Write focused regression tests before or alongside the fix. "
                "Do not weaken existing tests. Run the full test file afterward "
                "to confirm nothing regressed."
            )
        elif category == TaskCategory.DOC_UPDATE.value:
            body = (
                f"Update documentation at {location}. "
                f"Description: {task['description']}\n\n"
                "Update canonical docs before code when AGENTS.md / PROJECT_BIBLE / "
                "BUILD_GUIDE are affected. Keep prose plain and short. Do not "
                "mark something 'working' unless it was actually tested — write "
                "'pending live test' if untested."
            )
        elif category == TaskCategory.REFACTOR.value:
            body = (
                f"Refactor {location}. "
                f"Description: {task['description']}\n\n"
                "Make minimal, focused changes. Preserve behavior. Run existing "
                "tests and py_compile. Never create _v2/_new/_fixed replacement "
                "files — use the rewrite protocol in the hard rules."
            )
        elif category == TaskCategory.BUILD.value:
            body = (
                f"Build/infrastructure task at {location}. "
                f"Description: {task['description']}\n\n"
                "Cover Dockerfile, CI workflows, pre-commit hooks, alembic "
                "migrations, and environment config. Pin base image versions "
                "(never :latest). Do not store secrets in Docker images — use "
                "runtime injection. Use multi-stage builds and .dockerignore. "
                "Verify the build command actually succeeds before marking done."
            )
        elif category == TaskCategory.FEATURE.value:
            body = (
                f"Implement new feature at {location}. "
                f"Description: {task['description']}\n\n"
                "Register a FunctionGroupContract in app/core/module_contracts.py "
                "for any new reusable service API. Export new models/classes from "
                "the relevant __init__.py. Add tests alongside the implementation. "
                "Use async def for I/O-bound endpoints and Pydantic models for "
                "request/response validation. Update ACTIVE_CONTEXT.md when shipped."
            )
        elif category == TaskCategory.BUG_FIX.value:
            body = (
                f"Fix bug at {location}. "
                f"Description: {task['description']}\n\n"
                "Reproduce the problem reliably first, then trace the code path "
                "to the ROOT CAUSE. Never add a downstream workaround for an "
                "upstream failure. Add a failing test that demonstrates the bug, "
                "fix it, and confirm the test now passes. Check the Known Failure "
                "Registry in AGENTS.md — do not repeat a past mistake."
            )
        elif category == TaskCategory.SECURITY.value:
            body = (
                f"Security task at {location}. "
                f"Description: {task['description']}\n\n"
                "Never log or expose secrets, keys, or tokens. Never commit secrets "
                "to the repo. Never modify repository security policies or "
                "compliance controls to work around CI/build failures — escalate "
                "to the user instead. Prefer specific exception types over broad "
                "catches. Validate all inputs with Pydantic models."
            )
        else:
            body = (
                f"Task at {location}. "
                f"Description: {task['description']}\n\n"
                "Implement, test, and verify py_compile passes. Follow every hard "
                "rule above — no exceptions."
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
        """Return the unlimited model fleet with usage notes.

        Notes tie each model to the task categories it handles best. Regardless
        of model, every agent MUST call ``tools/mark_task_status.py`` on pickup
        and on completion — see the prompt base_context for the exact commands.
        """

        return [
            {
                "id": ModelId.SWE_1_7.value,
                "name": "SWE-1.7",
                "note": "Best for stub_fix, bug_fix, test_add, and mechanical "
                "code fixes. Reliable tool calls; verify with py_compile.",
            },
            {
                "id": ModelId.KIMI_2_7.value,
                "name": "Kimi 2.7",
                "note": "Strong for refactor, duplicate_resolve, and doc_update. "
                "Good at preserving behavior across multi-file edits.",
            },
            {
                "id": ModelId.SWE_1_6.value,
                "name": "SWE-1.6",
                "note": "Reliable fallback for stub_fix and build tasks. Slower "
                "than SWE-1.7 but rarely hallucinates APIs.",
            },
            {
                "id": ModelId.GLM_5_2.value,
                "name": "GLM-5.2",
                "note": "Fast for feature and security tasks. Occasionally "
                "returns empty tool calls — always verify output and "
                "re-run if a tool call produced no change.",
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
