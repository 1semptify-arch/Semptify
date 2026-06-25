"""
Example External Module — Router

This is a scaffold for external (third-party) modules. It uses ONLY
app.sdk.* imports — no direct DB, Redis, or internal module access.

Allowed imports:
  - app.sdk.external.* (vault_client, timeline_client, overlay_client, etc.)
  - app.sdk.vault.* (VaultFolderSpec, etc.)
  - fastapi, pydantic, typing, datetime, etc.

Forbidden imports (will raise ExternalModuleSecurityError at load time):
  - app.core.database, app.core.redis
  - app.services.* (except via SDK clients)
  - app.modules.* (other internal modules)
  - sqlalchemy, asyncpg, redis
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.sdk.external import (
    ExternalModuleContext,
    Permission,
    PermissionSet,
    TimelineClient,
    VaultClient,
)
from app.sdk.vault import TENANT_VAULT

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Example External"])


def get_external_context(request: Request) -> ExternalModuleContext:
    """Build the external module context from the request.

    In production, the external_loader injects this. For development,
    we build it from the authenticated user's session.
    """
    # TODO: Replace with proper context injection from external_loader
    permissions = PermissionSet(["vault.read", "timeline.write"])
    return ExternalModuleContext(
        module_name="example-external-module",
        vendor="example-vendor",
        user_id=getattr(request.state, "user_id", "unknown"),
        permissions=permissions,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/health")
async def health():
    """Health check — no auth required."""
    return {"status": "ok", "module": "example-external-module"}


@router.get("/documents")
async def list_documents(
    request: Request,
    ctx: ExternalModuleContext = Depends(get_external_context),
) -> dict:
    """List vault documents for the current user."""
    # Get provider and access token from request state (set by middleware)
    provider = getattr(request.state, "storage_provider", "local")
    access_token = getattr(request.state, "storage_access_token", "")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storage provider connected",
        )

    vault = VaultClient(
        ctx=ctx,
        provider=provider,
        access_token=access_token,
        folder_spec=TENANT_VAULT,
    )

    files = await vault.list_files("documents")
    return {"documents": files, "count": len(files)}


@router.post("/events")
async def create_event(
    request: Request,
    body: dict,
    ctx: ExternalModuleContext = Depends(get_external_context),
) -> dict:
    """Create a timeline event."""
    timeline = TimelineClient(ctx=ctx)
    event = await timeline.create_event(
        event_type=body.get("type", "external"),
        title=body.get("title", "External module event"),
        description=body.get("description", ""),
        metadata=body.get("metadata", {}),
    )
    return {"status": "ok", "event": event}
