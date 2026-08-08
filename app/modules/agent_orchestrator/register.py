"""Agent Orchestrator module registration helper — FunctionGroupContracts."""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="agent_orchestrator",
        group_name="agent_orchestrator_tasks",
        title="Agent Orchestrator List Tasks (GET) (SSOT)",
        description="GET /api/agent-orchestrator/tasks",
        inputs=(),
        outputs=("tasks", "total"),
        dependencies=("app.modules.agent_orchestrator.router",),
        deterministic=True,
    )
)


register_function_group(
    FunctionGroupContract(
        module="agent_orchestrator",
        group_name="agent_orchestrator_create_task",
        title="Agent Orchestrator Create Task (POST) (SSOT)",
        description="POST /api/agent-orchestrator/tasks",
        inputs=("title", "target_model"),
        outputs=("task",),
        dependencies=("app.modules.agent_orchestrator.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="agent_orchestrator",
        group_name="agent_orchestrator_batch_create",
        title="Agent Orchestrator Batch Create Tasks (POST) (SSOT)",
        description="POST /api/agent-orchestrator/batch",
        inputs=("tasks[]",),
        outputs=("created", "total"),
        dependencies=("app.modules.agent_orchestrator.router",),
        deterministic=False,
    )
)


register_function_group(
    FunctionGroupContract(
        module="agent_orchestrator",
        group_name="agent_orchestrator_models",
        title="Agent Orchestrator List Models (GET) (SSOT)",
        description="GET /api/agent-orchestrator/models",
        inputs=(),
        outputs=("models",),
        dependencies=("app.modules.agent_orchestrator.router",),
        deterministic=True,
    )
)
