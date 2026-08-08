"""
Semptify Navigation SDK — Client
==================================
Clean interface to the navigation SSOT registry.
Zero FastAPI dependencies. Pure Python.
"""

from app.core.navigation import FlowStage, navigation


def get_stage(stage_id: str) -> FlowStage | None:
    """Return a FlowStage by ID, or None if not found."""
    return navigation.get_stage(stage_id)


def get_path(stage_id: str, fallback: str | None = None) -> str | None:
    """
    Return the path for a stage ID.

    Args:
        stage_id: SSOT stage identifier (e.g. 'preamble', 'providers')
        fallback: Return this if stage not found (default: None)

    Returns:
        Path string like '/preamble', or fallback if not found
    """
    stage = navigation.get_stage(stage_id)
    if stage:
        return stage.path
    return fallback


def get_onboarding_start() -> str:
    """Return the canonical onboarding entry point path."""
    return navigation.get_onboarding_start()


def get_reconnect_path() -> str:
    """Return the canonical reconnect flow path."""
    return navigation.get_reconnect_flow()


def get_next_path(current_stage_id: str, fallback: str | None = None) -> str | None:
    """
    Return the path for the next stage after current_stage_id.

    Args:
        current_stage_id: Current stage ID
        fallback: Return this if no next stage found

    Returns:
        Next stage path, or fallback
    """
    stage = navigation.get_stage(current_stage_id)
    if not stage or not stage.next_stage:
        return fallback
    next_stage = navigation.get_stage(stage.next_stage)
    if next_stage:
        return next_stage.path
    return fallback


def is_canonical_path(path: str) -> bool:
    """
    Check if a path is registered in the SSOT navigation registry.
    Used by SSOT guard to validate redirects.
    """
    return navigation.is_canonical_path(path)


def all_paths() -> set[str]:
    """Return all registered canonical paths."""
    return set(navigation._CANONICAL_PATHS)
