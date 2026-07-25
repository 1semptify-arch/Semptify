"""Funding Forge JSON API router."""

import logging
import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from funding_forge.auth import admin_dependency
from funding_forge.crud import (
    create_contact,
    create_document,
    create_funder,
    create_interaction,
    create_opportunity,
    create_opportunity_step,
    create_task,
    delete_contact,
    delete_document,
    delete_funder,
    delete_interaction,
    delete_opportunity,
    delete_opportunity_step,
    delete_task,
    get_contact,
    get_dashboard_stats,
    get_document,
    get_funder,
    get_interaction,
    get_opportunity,
    get_opportunity_step,
    get_task,
    list_contacts,
    list_documents,
    list_funders,
    list_interactions,
    list_opportunities,
    list_tasks,
    seed_suggested_entities,
    update_contact,
    update_funder,
    update_interaction,
    update_opportunity,
    update_opportunity_step,
    update_task,
)
from funding_forge.database import get_db
from funding_forge.schemas import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DashboardStats,
    DocumentResponse,
    FunderCreate,
    FunderDetail,
    FunderResponse,
    FunderUpdate,
    InteractionCreate,
    InteractionResponse,
    InteractionUpdate,
    OpportunityCreate,
    OpportunityDetail,
    OpportunityResponse,
    OpportunityStepCreate,
    OpportunityStepResponse,
    OpportunityStepUpdate,
    OpportunityUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)

api_router = APIRouter(prefix="/api", dependencies=[Depends(admin_dependency)])
logger = logging.getLogger("funding_forge.api")


def _utcnow() -> str:
    """Return an ISO timestamp string for the current UTC time."""
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _to_funder_response(funder) -> FunderResponse:
    """Build a FunderResponse with relationship counts."""
    response = FunderResponse.model_validate(funder)
    return response.model_copy(
        update={
            "contact_count": len(funder.contacts),
            "opportunity_count": len(funder.opportunities),
        }
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@api_router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Return summary counts for the dashboard."""
    stats = await get_dashboard_stats(db)
    return DashboardStats(**stats)


# ---------------------------------------------------------------------------
# Funders
# ---------------------------------------------------------------------------


@api_router.get("/funders", response_model=list[FunderResponse])
async def read_funders(db: AsyncSession = Depends(get_db)):
    """List all funding entities."""
    funders = await list_funders(db)
    return [_to_funder_response(f) for f in funders]


@api_router.post("/funders", response_model=FunderResponse, status_code=status.HTTP_201_CREATED)
async def create_funder_endpoint(data: FunderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new funding entity."""
    funder = await create_funder(db, data)
    funder = await get_funder(db, funder.id)
    return _to_funder_response(funder)


@api_router.get("/funders/{funder_id}", response_model=FunderDetail)
async def read_funder(funder_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single funder with contacts and opportunities."""
    funder = await get_funder(db, funder_id)
    if not funder:
        raise HTTPException(status_code=404, detail="Funder not found")
    return FunderDetail.model_validate(funder)


@api_router.put("/funders/{funder_id}", response_model=FunderResponse)
async def update_funder_endpoint(funder_id: int, data: FunderUpdate, db: AsyncSession = Depends(get_db)):
    """Update a funding entity."""
    funder = await get_funder(db, funder_id)
    if not funder:
        raise HTTPException(status_code=404, detail="Funder not found")
    await update_funder(db, funder, data)
    updated = await get_funder(db, funder_id)
    return _to_funder_response(updated)


@api_router.delete("/funders/{funder_id}")
async def delete_funder_endpoint(funder_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a funding entity."""
    funder = await get_funder(db, funder_id)
    if not funder:
        raise HTTPException(status_code=404, detail="Funder not found")
    await delete_funder(db, funder)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@api_router.get("/contacts", response_model=list[ContactResponse])
async def read_contacts(db: AsyncSession = Depends(get_db)):
    """List all contacts."""
    contacts = await list_contacts(db)
    return [ContactResponse.model_validate(c) for c in contacts]


@api_router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_endpoint(data: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create a new contact."""
    contact = await create_contact(db, data)
    contact = await get_contact(db, contact.id)
    return ContactResponse.model_validate(contact)


@api_router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def read_contact(contact_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single contact with interactions."""
    contact = await get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@api_router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact_endpoint(contact_id: int, data: ContactUpdate, db: AsyncSession = Depends(get_db)):
    """Update a contact."""
    contact = await get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await update_contact(db, contact, data)
    updated = await get_contact(db, contact_id)
    return ContactResponse.model_validate(updated)


@api_router.delete("/contacts/{contact_id}")
async def delete_contact_endpoint(contact_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a contact."""
    contact = await get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await delete_contact(db, contact)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------


@api_router.get("/opportunities", response_model=list[OpportunityResponse])
async def read_opportunities(db: AsyncSession = Depends(get_db)):
    """List all opportunities."""
    opportunities = await list_opportunities(db)
    return [OpportunityResponse.model_validate(o) for o in opportunities]


@api_router.post("/opportunities", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity_endpoint(data: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    """Create a new opportunity."""
    opportunity = await create_opportunity(db, data)
    opportunity = await get_opportunity(db, opportunity.id)
    return OpportunityResponse.model_validate(opportunity)


@api_router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
async def read_opportunity(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    """Get an opportunity with steps, interactions, and documents."""
    opportunity = await get_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityDetail.model_validate(opportunity)


@api_router.put("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity_endpoint(opportunity_id: int, data: OpportunityUpdate, db: AsyncSession = Depends(get_db)):
    """Update an opportunity."""
    opportunity = await get_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await update_opportunity(db, opportunity, data)
    updated = await get_opportunity(db, opportunity_id)
    return OpportunityResponse.model_validate(updated)


@api_router.delete("/opportunities/{opportunity_id}")
async def delete_opportunity_endpoint(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an opportunity."""
    opportunity = await get_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await delete_opportunity(db, opportunity)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Opportunity steps
# ---------------------------------------------------------------------------


@api_router.post(
    "/opportunities/{opportunity_id}/steps",
    response_model=OpportunityStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_step_endpoint(
    opportunity_id: int,
    data: OpportunityStepCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a step to an opportunity's application process."""
    opportunity = await get_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    step = await create_opportunity_step(db, opportunity, data)
    return OpportunityStepResponse.model_validate(step)


@api_router.put("/opportunities/{opportunity_id}/steps/{step_id}", response_model=OpportunityStepResponse)
async def update_step_endpoint(
    opportunity_id: int,
    step_id: int,
    data: OpportunityStepUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an opportunity step."""
    step = await get_opportunity_step(db, step_id)
    if not step or step.opportunity_id != opportunity_id:
        raise HTTPException(status_code=404, detail="Step not found")
    updated = await update_opportunity_step(db, step, data)
    return OpportunityStepResponse.model_validate(updated)


@api_router.delete("/opportunities/{opportunity_id}/steps/{step_id}")
async def delete_step_endpoint(opportunity_id: int, step_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an opportunity step."""
    step = await get_opportunity_step(db, step_id)
    if not step or step.opportunity_id != opportunity_id:
        raise HTTPException(status_code=404, detail="Step not found")
    await delete_opportunity_step(db, step)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------


@api_router.get("/interactions", response_model=list[InteractionResponse])
async def read_interactions(db: AsyncSession = Depends(get_db)):
    """List all interactions."""
    interactions = await list_interactions(db)
    return [InteractionResponse.model_validate(i) for i in interactions]


@api_router.post("/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_interaction_endpoint(data: InteractionCreate, db: AsyncSession = Depends(get_db)):
    """Create an interaction."""
    interaction = await create_interaction(db, data)
    interaction = await get_interaction(db, interaction.id)
    return InteractionResponse.model_validate(interaction)


@api_router.put("/interactions/{interaction_id}", response_model=InteractionResponse)
async def update_interaction_endpoint(interaction_id: int, data: InteractionUpdate, db: AsyncSession = Depends(get_db)):
    """Update an interaction."""
    interaction = await get_interaction(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    await update_interaction(db, interaction, data)
    updated = await get_interaction(db, interaction_id)
    return InteractionResponse.model_validate(updated)


@api_router.delete("/interactions/{interaction_id}")
async def delete_interaction_endpoint(interaction_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an interaction."""
    interaction = await get_interaction(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    await delete_interaction(db, interaction)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@api_router.get("/tasks", response_model=list[TaskResponse])
async def read_tasks(db: AsyncSession = Depends(get_db)):
    """List all tasks ordered by due date."""
    tasks = await list_tasks(db)
    return [TaskResponse.model_validate(t) for t in tasks]


@api_router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a task."""
    task = await create_task(db, data)
    task = await get_task(db, task.id)
    return TaskResponse.model_validate(task)


@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task_endpoint(task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    """Update a task."""
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await update_task(db, task, data)
    updated = await get_task(db, task_id)
    return TaskResponse.model_validate(updated)


@api_router.delete("/tasks/{task_id}")
async def delete_task_endpoint(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    task = await get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await delete_task(db, task)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@api_router.get("/documents", response_model=list[DocumentResponse])
async def read_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded documents."""
    documents = await list_documents(db)
    return [DocumentResponse.model_validate(d) for d in documents]


@api_router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    related_type: str = Form(""),
    related_id: int = Form(0),
    opportunity_id: int = Form(0),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to the configured storage backend and link it to a record."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    original_filename = file.filename
    extension = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    stored_filename = f"{uuid.uuid4().hex}{f'.{extension}' if extension else ''}"

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    from funding_forge import storage

    meta = await storage.save_file(
        content=contents,
        filename=stored_filename,
        mime_type=file.content_type,
    )

    document = await create_document(
        db,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_type=meta["storage_type"],
        storage_key=meta["key"],
        mime_type=meta["mime_type"],
        file_size=meta["size"],
        description=description or None,
        related_type=related_type or None,
        related_id=related_id if related_id else None,
        opportunity_id=opportunity_id if opportunity_id else None,
    )
    document = await get_document(db, document.id)
    return DocumentResponse.model_validate(document)


@api_router.get("/documents/{document_id}")
async def download_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """Download a stored document."""
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    from funding_forge import storage

    try:
        content = await storage.read_file(document.storage_type, document.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found in storage") from exc
    except RuntimeError as exc:
        logger.error("Storage download failed for document %s: %s", document_id, exc)
        raise HTTPException(status_code=503, detail="Storage unavailable") from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{document.original_filename}"',
    }
    return Response(
        content=content,
        media_type=document.mime_type or "application/octet-stream",
        headers=headers,
    )


@api_router.delete("/documents/{document_id}")
async def delete_document_endpoint(document_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a document and its stored file."""
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    from funding_forge import storage

    try:
        await storage.delete_file(document.storage_type, document.storage_key)
    except FileNotFoundError:
        pass
    except RuntimeError as exc:
        logger.error("Storage delete failed for document %s: %s", document_id, exc)

    await delete_document(db, document)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


@api_router.post("/seed")
async def seed_endpoint(db: AsyncSession = Depends(get_db)):
    """Reset and seed the suggested funding entity catalog."""
    result = await seed_suggested_entities(db)
    return {
        "ok": True,
        "funders_created": result["funders_created"],
        "contacts_created": result["contacts_created"],
        "seeded_at": _utcnow(),
    }
