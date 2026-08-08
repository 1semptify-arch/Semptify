"""
Dev Ideas — Phase 3.1b / 3.6

Idea submission pipeline: Idea → Spec → Dev Module → Experimental → Beta → Stable

Endpoints:
  GET  /dev/lab/ideas           — List all submitted ideas
  POST /dev/lab/ideas           — Submit a new idea
  GET  /dev/lab/ideas/{id}      — Get idea details
  POST /dev/lab/ideas/{id}/promote — Promote idea (scaffold dev module or generate SDK template)
  DELETE /dev/lab/ideas/{id}    — Delete an idea

Ideas are stored in the `dev_ideas` PostgreSQL table.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.utc import utc_now
from app.core.upl_guardrails import UPLRiskTier

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dev Ideas"])


# =============================================================================
# Auth — reuse stealth admin
# =============================================================================

async def _stealth_admin(request: Request):
    from app.modules.admin_console.router import _stealth_admin as _admin
    return await _admin(request)


# =============================================================================
# Models
# =============================================================================

class IdeaCreate(BaseModel):
    """Submit a new idea."""
    name: str = Field(..., min_length=1, max_length=200, description="Idea name")
    description: str = Field(..., min_length=1, max_length=5000, description="What does it do?")
    target_role: str = Field("tenant", description="Who is this for? tenant|advocate|admin|manager|legal|judge|research|dev")
    target_tier: str = Field("core", description="Which tier? core|extended|advocate|admin|research|dev")
    origin: str = Field("internal", description="internal (first-party) or external (third-party)")
    dependencies: str = Field(default="", description="Comma-separated SDK clients or modules needed")
    success_criteria: str = Field(default="", description="How do we know this is done?")
    submitted_by: str = Field(default="anonymous", description="Who submitted this idea?")


class IdeaPromote(BaseModel):
    """Promote an idea to a dev module."""
    module_name: str = Field(..., description="Module name (e.g. 'court_forms_ny')")
    action: str = Field("scaffold", description="scaffold (internal) or sdk_template (external)")


# =============================================================================
# Schema
# =============================================================================

async def ensure_ideas_schema(db: AsyncSession) -> None:
    """Create dev_ideas table if it doesn't exist."""
    try:
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS dev_ideas (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_role TEXT NOT NULL DEFAULT 'tenant',
                    target_tier TEXT NOT NULL DEFAULT 'core',
                    origin TEXT NOT NULL DEFAULT 'internal',
                    dependencies TEXT NOT NULL DEFAULT '',
                    success_criteria TEXT NOT NULL DEFAULT '',
                    submitted_by TEXT NOT NULL DEFAULT 'anonymous',
                    status TEXT NOT NULL DEFAULT 'submitted',
                    promoted_module_name TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("DevIdeas: schema init failed: %s", e)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_ideas(
    request: Request,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,
    origin_filter: Optional[str] = None,
    _admin=Depends(_stealth_admin),
) -> dict:
    """List all submitted ideas, optionally filtered by status or origin."""
    await ensure_ideas_schema(db)

    query = "SELECT * FROM dev_ideas"
    conditions = []
    params = {}
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter
    if origin_filter:
        conditions.append("origin = :origin")
        params["origin"] = origin_filter
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    ideas = []
    for row in rows:
        ideas.append({
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "target_role": row.target_role,
            "target_tier": row.target_tier,
            "origin": row.origin,
            "dependencies": row.dependencies,
            "success_criteria": row.success_criteria,
            "submitted_by": row.submitted_by,
            "status": row.status,
            "promoted_module_name": row.promoted_module_name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        })

    return {
        "ideas": ideas,
        "total": len(ideas),
        "generated_at": utc_now().isoformat(),
    }


@router.post("")
async def submit_idea(
    body: IdeaCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Submit a new idea."""
    await ensure_ideas_schema(db)

    # Validate origin
    if body.origin not in ("internal", "external"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="origin must be 'internal' or 'external'",
        )

    try:
        result = await db.execute(
            text(
                """
                INSERT INTO dev_ideas
                (name, description, target_role, target_tier, origin, dependencies, success_criteria, submitted_by)
                VALUES
                (:name, :desc, :role, :tier, :origin, :deps, :criteria, :by)
                RETURNING id, created_at
                """
            ),
            {
                "name": body.name,
                "desc": body.description,
                "role": body.target_role,
                "tier": body.target_tier,
                "origin": body.origin,
                "deps": body.dependencies,
                "criteria": body.success_criteria,
                "by": body.submitted_by,
            },
        )
        row = result.fetchone()
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit idea: {e}",
        )

    logger.info("DevIdeas: new idea '%s' submitted by %s (id=%s)", body.name, body.submitted_by, row.id)

    return {
        "status": "ok",
        "idea_id": row.id,
        "name": body.name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/{idea_id}")
async def get_idea(
    idea_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Get details of a specific idea."""
    await ensure_ideas_schema(db)

    result = await db.execute(text("SELECT * FROM dev_ideas WHERE id = :id"), {"id": idea_id})
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Idea {idea_id} not found")

    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "target_role": row.target_role,
        "target_tier": row.target_tier,
        "origin": row.origin,
        "dependencies": row.dependencies,
        "success_criteria": row.success_criteria,
        "submitted_by": row.submitted_by,
        "status": row.status,
        "promoted_module_name": row.promoted_module_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/{idea_id}/promote")
async def promote_idea(
    idea_id: int,
    body: IdeaPromote,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Promote an idea — either scaffold an internal dev module or generate SDK template.

    This marks the idea as 'promoted' and records the module name.
    The actual scaffolding (copying _template/) is a manual step for now.
    """
    await ensure_ideas_schema(db)

    # Validate action
    if body.action not in ("scaffold", "sdk_template"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'scaffold' or 'sdk_template'",
        )

    # Get the idea
    result = await db.execute(text("SELECT * FROM dev_ideas WHERE id = :id"), {"id": idea_id})
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Idea {idea_id} not found")

    if row.status == "promoted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Idea {idea_id} already promoted to '{row.promoted_module_name}'",
        )

    # Mark as promoted
    try:
        await db.execute(
            text(
                "UPDATE dev_ideas SET status = 'promoted', promoted_module_name = :name, updated_at = :ts WHERE id = :id"
            ),
            {"name": body.module_name, "ts": utc_now(), "id": idea_id},
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote idea: {e}",
        )

    action_desc = {
        "scaffold": f"Copy app/modules/_template/ to app/modules/{body.module_name}/ and register in product_manifest.py with lifecycle='dev_only'",
        "sdk_template": f"Generate external SDK template package for developer (app/sdk/external/_template/)",
    }

    logger.info("DevIdeas: idea %d '%s' promoted to module '%s' (action=%s)", idea_id, row.name, body.module_name, body.action)

    return {
        "status": "ok",
        "idea_id": idea_id,
        "idea_name": row.name,
        "module_name": body.module_name,
        "action": body.action,
        "next_steps": action_desc[body.action],
        "promoted_at": utc_now().isoformat(),
    }


@router.delete("/{idea_id}")
async def delete_idea(
    idea_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(_stealth_admin),
) -> dict:
    """Delete an idea."""
    await ensure_ideas_schema(db)

    try:
        result = await db.execute(
            text("DELETE FROM dev_ideas WHERE id = :id RETURNING id"),
            {"id": idea_id},
        )
        deleted = result.fetchone() is not None
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete idea: {e}",
        )

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Idea {idea_id} not found")

    return {"status": "ok", "deleted_idea_id": idea_id}


# =============================================================================
# Module Contracts
# =============================================================================

try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="ideas_list",
        title="Dev Ideas List (SSOT)",
        description="CANONICAL list of submitted dev ideas. GET /dev/lab/ideas.",
        inputs=("status_filter", "origin_filter", "admin_user_id"),
        outputs=("ideas", "total"),
        dependencies=("app.modules.dev_lab.ideas",),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="ideas_submit",
        title="Dev Idea Submit (SSOT)",
        description="CANONICAL submit a new dev idea. POST /dev/lab/ideas.",
        inputs=("name", "description", "target_role", "target_tier", "origin", "admin_user_id"),
        outputs=("status", "idea_id"),
        dependencies=("app.modules.dev_lab.ideas",),
        deterministic=True,
    ))

    register_function_group(FunctionGroupContract(
        module="dev_lab",
        group_name="ideas_promote",
        title="Dev Idea Promote (SSOT)",
        description="CANONICAL promote an idea to a dev module. POST /dev/lab/ideas/{id}/promote.",
        inputs=("idea_id", "module_name", "action", "admin_user_id"),
        outputs=("status", "module_name", "action", "next_steps"),
        dependencies=("app.modules.dev_lab.ideas",),
        deterministic=True,
    ))

except Exception:
    pass
