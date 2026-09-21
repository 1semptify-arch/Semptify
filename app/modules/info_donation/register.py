"""Info Donation registration — FunctionGroupContracts + event wiring.

Contracts are the SSOT for what this module exposes. The ISSUE_RESOLVED
subscription makes the resolution gate genuinely event-based: any module
that learns a tenant's situation resolved (self-report here today;
dispute status changes, case closes, etc. later) publishes the event and
eligibility flips without the publisher knowing this module exists.
"""

import logging

from app.core.event_bus import EventType, subscribe_async_to_event
from app.core.module_contracts import FunctionGroupContract, register_function_group

logger = logging.getLogger(__name__)

register_function_group(
    FunctionGroupContract(
        module="info_donation",
        group_name="info_donation_donate",
        title="Info Donation — Share What Happened (SSOT)",
        description=(
            "CANONICAL post-resolution info donation. Opt-in, per-item, "
            "anonymized answers gated on the tenant's situation being "
            "resolved; versioned informed consent for server-side "
            "aggregate-only storage; everything is withdrawable."
        ),
        inputs=("items", "consent_version"),
        outputs=("stored", "items", "status"),
        dependencies=("app.modules.info_donation.router", "app.modules.info_donation.service"),
        deterministic=True,
        tier="T2",
        allowed_routes=(
            "/api/info-donation/health",
            "/api/info-donation/status",
            "/api/info-donation/catalog",
            "/api/info-donation/resolved",
            "/api/info-donation/dismiss",
            "/api/info-donation/consent",
            "/api/info-donation/donate",
            "/api/info-donation/mine",
            "/api/info-donation/mine/{item_id}",
            "/api/info-donation/withdraw-all",
            "/help-the-next-tenant",
        ),
        allowed_prefixes=("/api/info-donation", "/help-the-next-tenant"),
    )
)

register_function_group(
    FunctionGroupContract(
        module="info_donation",
        group_name="info_donation_review",
        title="Info Donation — Narrative Review (SSOT)",
        description=(
            "CANONICAL moderation surface for free-text donations. Pending "
            "items are never served until a reviewer (Brad + beta users) "
            "approves them; reject or approve per item. Admin-gated."
        ),
        inputs=("item_id", "decision"),
        outputs=("item",),
        dependencies=("app.modules.info_donation.router", "app.modules.info_donation.service"),
        deterministic=True,
        tier="T3",
        allowed_routes=(
            "/api/info-donation/review/pending",
            "/api/info-donation/review/{item_id}",
        ),
        allowed_prefixes=("/api/info-donation",),
    )
)


async def _on_issue_resolved(event) -> None:
    """Mark donation eligibility when any module reports resolution.
    Idempotent — mark_resolved only records the first resolution."""
    if not event.user_id:
        return
    try:
        from app.core.database import get_db_session
        from app.modules.info_donation import service

        async with get_db_session() as db:
            await service.mark_resolved(db, event.user_id, source=f"event:{event.source}")
    except Exception:
        logger.exception("Info donation: failed to record ISSUE_RESOLVED")


subscribe_async_to_event(EventType.ISSUE_RESOLVED, _on_issue_resolved)
