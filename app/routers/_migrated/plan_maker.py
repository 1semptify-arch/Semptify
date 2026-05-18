"""
Semptify — Plan Maker Router
=============================
REST API for creating, viewing, and exporting structured accountability plans.

Endpoints
---------
POST   /api/plan-maker/plans                 Create a new plan
GET    /api/plan-maker/plans/{plan_id}        Get plan as JSON
GET    /api/plan-maker/plans/{plan_id}/export Export plan as Markdown or JSON file
POST   /api/plan-maker/plans/{plan_id}/entity Add an entity to a plan
POST   /api/plan-maker/plans/{plan_id}/evidence Add an evidence item
POST   /api/plan-maker/plans/{plan_id}/steps  Add a next step
PATCH  /api/plan-maker/plans/{plan_id}/steps/{index}/complete  Mark step done

All plan data is returned to the client for vault storage — nothing is
retained server-side beyond the lifetime of the request.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.plan_maker_service import (
    AccountabilityPlan,
    EntityRecord,
    EvidenceItem,
    NextStep,
    create_plan,
    add_entity,
    add_evidence,
    add_next_step,
    mark_step_complete,
    plan_from_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plan-maker", tags=["Plan Maker"])


# =============================================================================
# Request / Response Schemas
# =============================================================================

class CreatePlanRequest(BaseModel):
    title: str = ""
    landlord_name: str = ""
    property_name: str = ""
    property_address: str = ""
    issues: list[str] = []
    narrative: str = ""
    lihtc_angle: str = ""
    core_objectives: list[str] = []
    desired_outcomes: str = ""
    include_default_steps: bool = True


class PlanStateRequest(BaseModel):
    """
    The client submits the current plan state (from vault) when making
    mutations — stateless design, no server-side plan storage.
    """
    plan: dict


class AddEntityRequest(BaseModel):
    name: str
    role: str = ""
    address: str = ""
    registered_agent: str = ""
    notes: str = ""


class AddEntityBody(PlanStateRequest):
    """Combined body: current plan state + entity fields."""
    name: str
    role: str = ""
    address: str = ""
    registered_agent: str = ""
    notes: str = ""


class AddEvidenceBody(PlanStateRequest):
    """Combined body: current plan state + evidence fields."""
    description: str
    vault_id: Optional[str] = None
    date_obtained: Optional[str] = None
    status: str = "pending"


class AddStepBody(PlanStateRequest):
    """Combined body: current plan state + step fields."""
    action: str
    due_date: Optional[str] = None
    notes: str = ""


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/plans", summary="Create a new accountability plan")
async def create_accountability_plan(
    body: CreatePlanRequest,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Create a new structured accountability plan.

    Returns the complete plan as a JSON dict.
    The client should save this to the vault — it is not retained server-side.
    """
    plan = create_plan(
        user_id=user.user_id,
        title=body.title,
        landlord_name=body.landlord_name,
        property_name=body.property_name,
        property_address=body.property_address,
        issues=body.issues,
        narrative=body.narrative,
        lihtc_angle=body.lihtc_angle,
        core_objectives=body.core_objectives,
        desired_outcomes=body.desired_outcomes,
        include_default_steps=body.include_default_steps,
    )
    return {"plan_id": plan.plan_id, "plan": plan.to_dict()}


@router.post("/plans/{plan_id}/view", summary="View a plan from submitted state")
async def view_plan(
    plan_id: str,
    body: PlanStateRequest,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Deserialise and return a plan the client submits from their vault.
    Validates ownership before returning.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid plan structure: {exc}")

    if plan.plan_id != plan_id:
        raise HTTPException(status_code=400, detail="plan_id path param does not match plan body")
    if plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return plan.to_dict()


@router.post("/plans/{plan_id}/export", summary="Export a plan as Markdown or JSON")
async def export_plan(
    plan_id: str,
    body: PlanStateRequest,
    format: str = Query("markdown", description="'markdown' or 'json'"),
    user: StorageUser = Depends(require_user),
) -> Response:
    """
    Export the plan as a downloadable Markdown or JSON file.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid plan structure: {exc}")

    if plan.plan_id != plan_id:
        raise HTTPException(status_code=400, detail="plan_id mismatch")
    if plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    safe_title = plan.title.replace(" ", "_")[:40]
    if format == "json":
        content = plan.to_json()
        filename = f"{plan.plan_id}_{safe_title}.json"
        media_type = "application/json"
    else:
        content = plan.to_markdown()
        filename = f"{plan.plan_id}_{safe_title}.md"
        media_type = "text/markdown"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/plans/{plan_id}/entity", summary="Add an entity to the plan")
async def add_entity_to_plan(
    plan_id: str,
    body: AddEntityBody,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Add a landlord entity, property manager, or registered agent to the plan.
    Returns the updated plan dict for the client to save back to vault.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if plan.plan_id != plan_id or plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    entity_data = {"name": body.name, "role": body.role, "address": body.address,
                   "registered_agent": body.registered_agent, "notes": body.notes}
    updated = add_entity(plan, EntityRecord(**entity_data))
    return {"plan": updated.to_dict()}


@router.post("/plans/{plan_id}/evidence", summary="Add an evidence item")
async def add_evidence_to_plan(
    plan_id: str,
    body: AddEvidenceBody,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Attach an evidence item (with optional vault_id reference) to the plan.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if plan.plan_id != plan_id or plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item_data = {"description": body.description, "vault_id": body.vault_id,
                 "date_obtained": body.date_obtained, "status": body.status}
    updated = add_evidence(plan, EvidenceItem(**item_data))
    return {"plan": updated.to_dict()}


@router.post("/plans/{plan_id}/steps", summary="Add a next step / action item")
async def add_step_to_plan(
    plan_id: str,
    body: AddStepBody,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Add a next-step action item to the plan's checklist.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if plan.plan_id != plan_id or plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated = add_next_step(plan, NextStep(action=body.action, due_date=body.due_date, notes=body.notes))
    return {"plan": updated.to_dict()}


@router.patch("/plans/{plan_id}/steps/{step_index}/complete", summary="Mark a step complete")
async def complete_step(
    plan_id: str,
    step_index: int,
    body: PlanStateRequest,
    user: StorageUser = Depends(require_user),
) -> dict:
    """
    Mark a checklist step as completed.
    Returns the updated plan for vault storage.
    """
    try:
        plan = plan_from_dict(dict(body.plan))
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if plan.plan_id != plan_id or plan.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if step_index < 0 or step_index >= len(plan.next_steps):
        raise HTTPException(status_code=400, detail=f"Step index {step_index} out of range")

    updated = mark_step_complete(plan, step_index)
    return {"plan": updated.to_dict()}


@router.get("/templates/default-steps", summary="Get the default next-step templates")
async def get_default_steps() -> dict:
    """
    Returns the default checklist items pre-populated when creating a new plan.
    Useful for UI autocomplete or template display.
    """
    from app.services.plan_maker_service import DEFAULT_NEXT_STEPS, DEFAULT_MODULES
    return {
        "default_steps": DEFAULT_NEXT_STEPS,
        "default_modules": DEFAULT_MODULES,
    }
