"""
Module Flag Overlay Admin Router — Phase 2.4

Endpoints:
  GET  /admin/api/module-flags           — List all modules with flags + overrides
  POST /admin/api/module-flags/{path}    — Set/update override
  DELETE /admin/api/module-flags/{path}  — Remove override (revert to manifest)
  POST /admin/api/module-flags/reload    — Reload overrides from DB
  GET  /admin/api/module-flags/preview   — Preview what a user sees (test-as-user)

All endpoints require admin auth via _stealth_admin (returns 404 to non-admins).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capabilities import require_capability
from app.core.database import get_db
from app.core.module_overrides import (
    delete_override,
    list_overrides,
    load_overrides,
    set_override,
)
from app.core.module_resolver import get_user_module_summary, invalidate_all_caches
from app.core.product_manifest import MANIFEST
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/api/module-flags",
    tags=["Module Flag Overlay"],
    dependencies=[Depends(require_capability("admin_module_flags"))],
)


# =============================================================================
# Auth — reuse stealth admin from admin_console
# =============================================================================

async def _stealth_admin(request: Request):
    """Stealth admin guard — returns 404 to non-admins."""
    from app.modules.admin_console.router import _stealth_admin as _admin
    return await _admin(request)


# =============================================================================
# Request models
# =============================================================================

class OverrideRequest(BaseModel):
    """Set or update an override for a module."""
    lifecycle: str | None = Field(
        default=None,
        description="Override lifecycle: stable|beta|experimental|dev_only|preview|internal",
    )
    feature_flag: str | None = Field(
        default=None,
        description="Override feature flag (Feature enum value or empty string to clear)",
    )
    disabled: bool | None = Field(
        default=None,
        description="If True, module is hidden from all non-admin users",
    )
    notes: str = Field(default="", description="Admin notes about this override")


class PreviewRequest(BaseModel):
    """Test-as-user request."""
    role: str = Field(..., description="Role to preview as: tenant|advocate|admin|manager|legal|judge|research|dev")
    jurisdiction: str | None = Field(default=None, description="Jurisdiction code (e.g. MN)")
    gates: list[str] = Field(default_factory=list, description="Gates the user has (e.g. vault_initialized)")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_module_flags(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """List every module with its declared flags and any active overrides.

    Returns modules grouped by tier with:
      - module_path, tier, lifecycle, origin, requires_role, requires_jurisdiction
      - requires_gate, feature_flag, dev_notes, visibility_label
      - override (if any): lifecycle, feature_flag, disabled, notes
    """
    overrides_map = {o["module_path"]: o["override"] for o in await list_overrides(db)}

    modules = []
    for entry in MANIFEST.all():
        override = overrides_map.get(entry.module_path)
        modules.append({
            "module_path": entry.module_path,
            "router_attr": entry.router_attr,
            "tier": entry.tier.value,
            "prefix": entry.prefix,
            "tags": list(entry.tags),
            "lifecycle": entry.lifecycle,
            "origin": entry.origin,
            "requires_role": list(entry.requires_role),
            "requires_jurisdiction": list(entry.requires_jurisdiction),
            "requires_gate": entry.requires_gate,
            "feature_flag": entry.feature_flag,
            "dev_notes": entry.dev_notes,
            "visibility_label": entry.visibility_label,
            "is_external": entry.is_external,
            "is_dev_only": entry.is_dev_only,
            "is_preview": entry.is_preview,
            "override": override,
        })

    # Sort by tier then module_path for stable display
    tier_order = {"core": 0, "extended": 1, "advocate": 2, "admin": 3, "research": 4, "dev": 5}
    modules.sort(key=lambda m: (tier_order.get(m["tier"], 99), m["module_path"]))

    return {
        "modules": modules,
        "summary": MANIFEST.summary(),
        "override_count": len(overrides_map),
        "generated_at": utc_now().isoformat(),
    }


@router.post("/{module_path:path}")
async def set_module_override(
    module_path: str,
    body: OverrideRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Set or update a runtime override for a module.

    The module_path is the dotted Python path (e.g. app.modules.vault.router).
    """
    # Validate module exists
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    try:
        override = await set_override(
            db=db,
            module_path=module_path,
            lifecycle=body.lifecycle,
            feature_flag=body.feature_flag,
            disabled=body.disabled,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Invalidate all resolver caches so changes take effect immediately
    await invalidate_all_caches()

    logger.info(
        "ModuleFlags: override set by admin for %s — lifecycle=%s ff=%s disabled=%s",
        module_path, body.lifecycle, body.feature_flag, body.disabled,
    )

    return {
        "status": "ok",
        "module_path": module_path,
        "override": override,
        "declared": {
            "lifecycle": entry.lifecycle,
            "feature_flag": entry.feature_flag,
        },
        "updated_at": utc_now().isoformat(),
    }


@router.delete("/{module_path:path}")
async def remove_module_override(
    module_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Remove a runtime override, reverting to the static MANIFEST declaration."""
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_path}' not found in manifest",
        )

    deleted = await delete_override(db, module_path)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No override exists for '{module_path}'",
        )

    await invalidate_all_caches()

    logger.info("ModuleFlags: override removed by admin for %s", module_path)

    return {
        "status": "ok",
        "module_path": module_path,
        "reverted_to": {
            "lifecycle": entry.lifecycle,
            "feature_flag": entry.feature_flag,
        },
        "updated_at": utc_now().isoformat(),
    }


@router.post("/reload")
async def reload_overrides(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Force reload all overrides from DB into the in-process cache.

    Useful after manual DB edits or if cache is stale.
    """
    await load_overrides(db)
    await invalidate_all_caches()
    return {
        "status": "ok",
        "message": "Overrides reloaded from DB",
        "loaded_at": utc_now().isoformat(),
    }


@router.post("/preview")
async def preview_as_user(
    body: PreviewRequest,
    request: Request,
    _admin=Depends(_stealth_admin),
) -> dict:
    """Preview what modules a user with the given context would see.

    This is the 'Test as user' feature — admin specifies a role,
    jurisdiction, and gates, and gets back the resolved module set.
    """
    allowed_roles = {"tenant", "advocate", "admin", "manager", "legal", "judge", "research", "dev"}
    if body.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{body.role}'. Allowed: {sorted(allowed_roles)}",
        )

    summary = await get_user_module_summary(
        role=body.role,
        jurisdiction=body.jurisdiction,
        gates=body.gates,
    )
    return summary


# =============================================================================
# Module Contracts — SSOT signatures
# =============================================================================

try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(FunctionGroupContract(
        module="admin_console",
        group_name="module_flags_list",
        title="Module Flag Overlay List (SSOT)",
        description=(
            "CANONICAL list of all modules with declared flags and runtime overrides. "
            "GET /admin/api/module-flags. Stealth admin guard enforced."
        ),
        inputs=("admin_user_id",),
        outputs=("modules", "summary", "override_count"),
        dependencies=("app.modules.admin_console.module_flags", "app.core.product_manifest.MANIFEST"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="admin_console",
        group_name="module_flags_set",
        title="Module Flag Override Set (SSOT)",
        description=(
            "CANONICAL set/update a runtime override for a module. "
            "POST /admin/api/module-flags/{module_path}. "
            "Override fields: lifecycle, feature_flag, disabled, notes. "
            "Invalidates resolver caches on success."
        ),
        inputs=("module_path", "lifecycle", "feature_flag", "disabled", "notes", "admin_user_id"),
        outputs=("status", "module_path", "override"),
        dependencies=("app.modules.admin_console.module_flags", "app.core.module_overrides"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="admin_console",
        group_name="module_flags_delete",
        title="Module Flag Override Delete (SSOT)",
        description=(
            "CANONICAL remove a runtime override, reverting to MANIFEST declaration. "
            "DELETE /admin/api/module-flags/{module_path}. "
            "Invalidates resolver caches on success."
        ),
        inputs=("module_path", "admin_user_id"),
        outputs=("status", "module_path", "reverted_to"),
        dependencies=("app.modules.admin_console.module_flags", "app.core.module_overrides"),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="admin_console",
        group_name="module_flags_preview",
        title="Module Flag Test-as-User Preview (SSOT)",
        description=(
            "CANONICAL preview what modules a user with the given context would see. "
            "POST /admin/api/module-flags/preview. "
            "Inputs: role, jurisdiction, gates. Returns module visibility by tier."
        ),
        inputs=("role", "jurisdiction", "gates", "admin_user_id"),
        outputs=("role", "jurisdiction", "gates", "by_tier", "total_modules"),
        dependencies=("app.modules.admin_console.module_flags", "app.core.module_resolver"),
        deterministic=True,
    ))

except Exception:
    pass
