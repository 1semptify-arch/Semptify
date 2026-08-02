"""
Onboarding State — Single Source of Truth for gate status.

This is THE one place that reads onboarding gate state from the database.
All middleware and routing logic must defer to this module.
No other code should read User.completed_groups directly for gate checks.

Gates (in order):
  storage_connected  — OAuth completed, provider connected
  vault_initialized  — Vault folders created in cloud storage, user fully activated
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OnboardingState:
    """Immutable snapshot of a user's gate completion state."""

    user_id: str
    storage_connected: bool
    vault_initialized: bool

    @property
    def is_fully_onboarded(self) -> bool:
        """True when all mandatory onboarding gates are complete."""
        return self.storage_connected and self.vault_initialized

    @property
    def next_required_gate(self) -> str | None:
        """
        Returns the name of the first incomplete gate, or None if all done.
        This is the single routing decision point for all middleware.
        """
        if not self.storage_connected:
            return "storage_connected"
        if not self.vault_initialized:
            return "vault_initialized"
        return None

    @property
    def next_required_path(self) -> str | None:
        """
        Returns the SSOT path for the next required onboarding step.
        Uses navigation registry — no hardcoded paths.
        Returns None if fully onboarded.
        """
        gate = self.next_required_gate
        if gate is None:
            return None

        try:
            from app.core.navigation import navigation

            gate_to_stage = {
                "storage_connected": "storage_select",  # /onboarding/providers (new users)
                "vault_initialized": "vault_setup",  # /onboarding/vault-setup
            }
            stage_id = gate_to_stage.get(gate)
            if stage_id:
                stage = navigation.get_stage(stage_id)
                if stage:
                    return stage.path
        except Exception as exc:
            logger.warning("Navigation lookup failed for gate %s: %s", gate, exc)

        # Fallback paths (only used if navigation registry is unavailable)
        fallbacks = {
            "storage_connected": "/onboarding/providers",
            "vault_initialized": "/onboarding/vault-setup",
        }
        return fallbacks.get(gate, "/onboarding/")


async def get_onboarding_state(
    user_id: str,
    db: AsyncSession,
) -> OnboardingState:
    """
    Read onboarding gate state for a user from the database.

    This is the ONLY function that should read User.completed_groups
    for the purpose of gate enforcement. Single DB read per call.

    Args:
        user_id: Raw (unsigned) user ID string.
        db: Active async database session.

    Returns:
        OnboardingState with all gate flags populated.
        If user not found, all gates are False.
    """
    try:
        from app.models.models import User

        result = await db.execute(select(User.completed_groups).where(User.id == user_id))
        row = result.scalar_one_or_none()
    except Exception as exc:
        logger.warning("get_onboarding_state DB error for user %s: %s", user_id[:6] + "***", exc)
        row = None

    if row is None:
        return OnboardingState(
            user_id=user_id,
            storage_connected=False,
            vault_initialized=False,
        )

    completed = {g.strip() for g in row.split(",") if g.strip()}

    return OnboardingState(
        user_id=user_id,
        storage_connected="storage_connected" in completed,
        vault_initialized="vault_initialized" in completed,
    )


async def get_onboarding_state_no_db(completed_groups_str: str | None, user_id: str) -> OnboardingState:
    """
    Build OnboardingState from an already-fetched completed_groups string.
    Use this when the DB row has already been loaded to avoid a second query.

    Args:
        completed_groups_str: The User.completed_groups value (may be None).
        user_id: Raw user ID string.
    """
    completed = {g.strip() for g in (completed_groups_str or "").split(",") if g.strip()}
    return OnboardingState(
        user_id=user_id,
        storage_connected="storage_connected" in completed,
        vault_initialized="vault_initialized" in completed,
    )
