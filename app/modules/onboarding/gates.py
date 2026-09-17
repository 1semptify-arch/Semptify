"""
Gate system — serial gating for onboarding progress.

Gates are stored as comma-separated values in User.completed_groups.
Each gate must be passed in order. A gate is never removed once set.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User

logger = logging.getLogger(__name__)

# Terminal gates — a one-way valve. Once set they can never be unset by any
# code path (spec: handoffs/onboarding-full-rebuild-spec-2026-09-16.md).
# document_uploaded completes onboarding; a later per-document problem is a
# separate concern and must never touch this flag. Any writer that removes
# gates from User.completed_groups MUST route through unmark_gate() or check
# TERMINAL_GATES first.
TERMINAL_GATES = frozenset({"document_uploaded"})


async def get_user_gates(db: AsyncSession, user_id: str) -> set[str]:
    """Read the set of completed gates for a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return set()
    raw = user.completed_groups or ""
    gates = {g.strip() for g in raw.split(",") if g.strip()}
    return gates


async def check_gate(db: AsyncSession, user_id: str, gate_name: str) -> bool:
    """Check if a specific gate has been passed."""
    gates = await get_user_gates(db, user_id)
    return gate_name in gates


async def mark_gate(db: AsyncSession, user_id: str, gate_name: str) -> bool:
    """
    Mark a gate as complete. Idempotent — safe to call multiple times.

    Returns True if the gate was newly marked, False if already set.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("mark_gate: user %s not found", user_id[:6] + "***")
        return False

    existing = {g.strip() for g in (user.completed_groups or "").split(",") if g.strip()}
    if gate_name in existing:
        return False

    existing.add(gate_name)
    user.completed_groups = ",".join(sorted(existing))
    await db.commit()
    logger.info("Gate '%s' marked for user %s", gate_name, user_id[:6] + "***")
    return True


async def unmark_gate(db: AsyncSession, user_id: str, gate_name: str) -> bool:
    """
    Remove a gate from a user's completed set.

    Terminal gates (TERMINAL_GATES) are a one-way valve: attempting to unset
    one raises ValueError loudly rather than silently regressing onboarding
    completion. Returns True if the gate was removed, False if not set.
    """
    if gate_name in TERMINAL_GATES:
        logger.error(
            "unmark_gate: REFUSED to unset terminal gate '%s' for user %s — one-way valve",
            gate_name,
            user_id[:6] + "***",
        )
        raise ValueError(
            f"Gate '{gate_name}' is a terminal onboarding gate and cannot be unset. "
            "A later per-document problem must be handled outside onboarding state."
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False

    existing = {g.strip() for g in (user.completed_groups or "").split(",") if g.strip()}
    if gate_name not in existing:
        return False

    existing.discard(gate_name)
    user.completed_groups = ",".join(sorted(existing)) if existing else None
    await db.commit()
    logger.warning("Gate '%s' unmarked for user %s", gate_name, user_id[:6] + "***")
    return True


async def get_first_incomplete_gate(
    db: AsyncSession,
    user_id: str,
    required_gates: list,
) -> str | None:
    """
    Given an ordered list of required gates, return the first one
    that is NOT complete. Returns None if all gates are passed.
    """
    completed = await get_user_gates(db, user_id)
    for gate in required_gates:
        if gate not in completed:
            return gate
    return None
