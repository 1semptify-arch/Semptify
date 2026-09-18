"""
Onboarding State — Single Source of Truth for gate status.

This is THE one place that reads onboarding gate state from the database.
All middleware and routing logic must defer to this module.
No other code should read User.completed_groups directly for gate checks.

Gates (durable boundary marks — START and FINALE only):
  storage_connected  — START: OAuth completed, provider connected
  document_uploaded  — FINALE: first real document through the full vault
                       pipeline. One-way valve, never unset.

Internal progress (not a gate):
  vault_initialized  — internal progress flag: vault folders, token backup,
                       and live write/read probe pass. Written during the
                       role-home setup flow and read by the setup component
                       to resume mid-flow. Never part of is_fully_onboarded
                       and never a routing requirement — setup happens at
                       the role home page, not in onboarding.

Per the 2026-09-18 Onboarding → Role-Home handoff: onboarding ends at
OAuth (START); everything after that lives at the role home page until
the test-document upload completes (FINALE).
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
    document_uploaded: bool

    @property
    def is_fully_onboarded(self) -> bool:
        """True when both durable boundary gates are complete (START + FINALE).

        vault_initialized is deliberately NOT part of this composite — it is
        internal setup-resume state owned by the role-home flow, not a gate.
        """
        return self.storage_connected and self.document_uploaded

    @property
    def next_required_gate(self) -> str | None:
        """
        Returns the name of the first incomplete durable gate, or None if done.
        This is the single routing decision point for all middleware.

        Only START and FINALE are routing gates. vault_initialized never
        appears here — internal progress is resumed by the role-home setup
        component, not by routing.
        """
        if not self.storage_connected:
            return "storage_connected"
        if not self.document_uploaded:
            return "document_uploaded"
        return None

    @property
    def home_path(self) -> str:
        """The user's role-home landing surface — resolved from user_id role."""
        try:
            from app.core.navigation import navigation
            from app.core.user_id import get_role_from_user_id

            return navigation.get_role_home(get_role_from_user_id(self.user_id))
        except Exception as exc:
            logger.warning("Role-home lookup failed for user %s: %s", self.user_id[:6] + "***", exc)
            return "/tenant/start"

    @property
    def next_required_path(self) -> str | None:
        """
        Returns the SSOT path for the next required step.

        No storage_connected → storage provider selection (still onboarding).
        Anything else incomplete → the user's role home, where install,
        verify, and the mandatory test upload (FINALE) all live now.
        Uses navigation registry — no hardcoded paths.
        Returns None if fully onboarded.
        """
        gate = self.next_required_gate
        if gate is None:
            return None

        if gate == "storage_connected":
            try:
                from app.core.navigation import navigation

                stage = navigation.get_stage("storage_select")
                if stage:
                    return stage.path
            except Exception as exc:
                logger.warning("Navigation lookup failed for gate %s: %s", gate, exc)
            return "/onboarding/providers"

        # document_uploaded (or any post-START incompleteness) → role home
        return self.home_path


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
            document_uploaded=False,
        )

    completed = set(g.strip() for g in row.split(",") if g.strip())

    return OnboardingState(
        user_id=user_id,
        storage_connected="storage_connected" in completed,
        vault_initialized="vault_initialized" in completed,
        document_uploaded="document_uploaded" in completed,
    )


async def get_onboarding_state_no_db(completed_groups_str: str | None, user_id: str) -> OnboardingState:
    """
    Build OnboardingState from an already-fetched completed_groups string.
    Use this when the DB row has already been loaded to avoid a second query.

    Args:
        completed_groups_str: The User.completed_groups value (may be None).
        user_id: Raw user ID string.
    """
    completed = set(g.strip() for g in (completed_groups_str or "").split(",") if g.strip())
    return OnboardingState(
        user_id=user_id,
        storage_connected="storage_connected" in completed,
        vault_initialized="vault_initialized" in completed,
        document_uploaded="document_uploaded" in completed,
    )
