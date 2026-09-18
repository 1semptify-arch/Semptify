"""Case Builder service facade used by other modules.

This module exposes the internal case data model to trusted consumers such as
Page Composer. Route handlers should use `app.modules.case_builder.router`;
backend consumers should import from this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UserCase:
    """Minimal, page-composer-friendly case record."""

    id: str
    title: str
    status: str
    updated_at: datetime


async def get_cases_for_user(
    user_id: str,
    subject: str | None = None,
) -> list[UserCase]:
    """Return the user's cases, optionally filtered by subject.

    Args:
        user_id: The tenant user ID.
        subject: Optional Context Engine subject to filter by. Matches
            `Incident.incident_type` or `incident_metadata.case_type/subject`.

    Returns:
        A list of `UserCase` records ordered by `updated_at` descending.
    """
    from app.services.incident_store import list_incidents_for_user_id

    incidents = await list_incidents_for_user_id(user_id)

    cases: list[UserCase] = []
    for inc in incidents:
        if subject and not _incident_matches_subject(inc, subject):
            continue
        cases.append(
            UserCase(
                id=str(inc.incident_id),
                title=inc.title or "Untitled case",
                status=inc.status or "active",
                updated_at=inc.updated_at,
            )
        )

    logger.debug(
        "get_cases_for_user: user=%s*** subject=%s found=%d",
        user_id[:6],
        subject,
        len(cases),
    )
    return cases


def _incident_matches_subject(inc, subject: str) -> bool:
    if inc.incident_type == subject:
        return True
    meta = inc.incident_metadata or {}
    if meta.get("case_type") == subject:
        return True
    if meta.get("subject") == subject:
        return True
    return False
