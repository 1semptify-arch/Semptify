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


async def get_user_gates(db: AsyncSession, user_id: str) -> set[str]:
    """Read the set of completed gates for a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return set()
    raw = user.completed_groups or ""
    gates = set(g.strip() for g in raw.split(",") if g.strip())
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

    existing = set(g.strip() for g in (user.completed_groups or "").split(",") if g.strip())
    if gate_name in existing:
        return False

    existing.add(gate_name)
    user.completed_groups = ",".join(sorted(existing))
    await db.commit()
    logger.info("Gate '%s' marked for user %s", gate_name, user_id[:6] + "***")
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
