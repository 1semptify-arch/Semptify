"""Agent Orchestrator — Forge tool for dispatching parallel AI agent tasks.

Provides an admin-only task queue for assigning stub fixes, duplicate resolutions,
and test work to the unlimited model fleet. v1 is in-memory; persistence is
intentionally deferred until the workflow proves useful.
"""

__all__ = ["router"]
