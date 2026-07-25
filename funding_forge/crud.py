"""Funding Forge CRUD operations."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from funding_forge.config import settings
from funding_forge.models import (
    Contact,
    Document,
    EmailMessage,
    Funder,
    Interaction,
    Opportunity,
    OpportunityStep,
    Setting,
    Task,
    utc_now,
)
from funding_forge.schemas import (
    ContactCreate,
    ContactUpdate,
    EmailMessageCreate,
    EmailMessageUpdate,
    FunderCreate,
    FunderUpdate,
    InteractionCreate,
    InteractionUpdate,
    OpportunityCreate,
    OpportunityStepCreate,
    OpportunityStepUpdate,
    OpportunityUpdate,
    TaskCreate,
    TaskUpdate,
)

SEED_PATH = Path(__file__).parent / "seed_data.json"
UPLOADS_PATH = Path(settings.uploads_dir)


def _model_copy_with_counts(funder: Funder) -> dict[str, Any]:
    """Return a FunderResponse-compatible dict with relationship counts."""
    return {
        **{c.name: getattr(funder, c.name) for c in funder.__table__.columns},
        "contact_count": len(funder.contacts),
        "opportunity_count": len(funder.opportunities),
    }


# ---------------------------------------------------------------------------
# Funder
# ---------------------------------------------------------------------------


async def create_funder(db: AsyncSession, data: FunderCreate) -> Funder:
    funder = Funder(**data.model_dump())
    db.add(funder)
    await db.commit()
    await db.refresh(funder)
    return funder


async def get_funder(db: AsyncSession, funder_id: int) -> Funder | None:
    result = await db.execute(
        select(Funder)
        .where(Funder.id == funder_id)
        .options(
            selectinload(Funder.contacts).selectinload(Contact.funder),
            selectinload(Funder.opportunities).selectinload(Opportunity.funder),
        )
    )
    return result.scalar_one_or_none()


async def list_funders(db: AsyncSession) -> list[Funder]:
    result = await db.execute(
        select(Funder).options(
            selectinload(Funder.contacts),
            selectinload(Funder.opportunities),
        )
    )
    return list(result.scalars().unique())


async def update_funder(db: AsyncSession, funder: Funder, data: FunderUpdate) -> Funder:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(funder, key, value)
    await db.commit()
    await db.refresh(funder)
    return funder


async def delete_funder(db: AsyncSession, funder: Funder) -> None:
    await db.delete(funder)
    await db.commit()


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------


async def create_contact(db: AsyncSession, data: ContactCreate) -> Contact:
    contact = Contact(**data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def get_contact(db: AsyncSession, contact_id: int) -> Contact | None:
    result = await db.execute(
        select(Contact)
        .where(Contact.id == contact_id)
        .options(
            selectinload(Contact.funder),
            selectinload(Contact.interactions).selectinload(Interaction.opportunity),
            selectinload(Contact.interactions).selectinload(Interaction.contact),
            selectinload(Contact.emails).selectinload(EmailMessage.opportunity),
        )
    )
    return result.scalar_one_or_none()


async def list_contacts(db: AsyncSession) -> list[Contact]:
    result = await db.execute(select(Contact).options(selectinload(Contact.funder)))
    return list(result.scalars().unique())


async def update_contact(db: AsyncSession, contact: Contact, data: ContactUpdate) -> Contact:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(db: AsyncSession, contact: Contact) -> None:
    await db.delete(contact)
    await db.commit()


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------


async def create_opportunity(db: AsyncSession, data: OpportunityCreate) -> Opportunity:
    opportunity = Opportunity(**data.model_dump())
    db.add(opportunity)
    await db.commit()
    await db.refresh(opportunity)
    return opportunity


async def get_opportunity(db: AsyncSession, opportunity_id: int) -> Opportunity | None:
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.id == opportunity_id)
        .options(
            selectinload(Opportunity.funder),
            selectinload(Opportunity.steps),
            selectinload(Opportunity.interactions).selectinload(Interaction.contact),
            selectinload(Opportunity.interactions).selectinload(Interaction.opportunity),
            selectinload(Opportunity.documents),
            selectinload(Opportunity.emails).selectinload(EmailMessage.contact),
        )
    )
    return result.scalar_one_or_none()


async def list_opportunities(db: AsyncSession) -> list[Opportunity]:
    result = await db.execute(select(Opportunity).options(selectinload(Opportunity.funder)))
    return list(result.scalars().unique())


async def update_opportunity(db: AsyncSession, opportunity: Opportunity, data: OpportunityUpdate) -> Opportunity:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(opportunity, key, value)
    await db.commit()
    await db.refresh(opportunity)
    return opportunity


async def delete_opportunity(db: AsyncSession, opportunity: Opportunity) -> None:
    await db.delete(opportunity)
    await db.commit()


# ---------------------------------------------------------------------------
# OpportunityStep
# ---------------------------------------------------------------------------


async def create_opportunity_step(
    db: AsyncSession, opportunity: Opportunity, data: OpportunityStepCreate
) -> OpportunityStep:
    step = OpportunityStep(opportunity_id=opportunity.id, **data.model_dump())
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def get_opportunity_step(db: AsyncSession, step_id: int) -> OpportunityStep | None:
    result = await db.execute(select(OpportunityStep).where(OpportunityStep.id == step_id))
    return result.scalar_one_or_none()


async def update_opportunity_step(
    db: AsyncSession, step: OpportunityStep, data: OpportunityStepUpdate
) -> OpportunityStep:
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "status":
            if value == "done" and not step.completed_at:
                step.completed_at = utc_now()
            elif value != "done":
                step.completed_at = None
        setattr(step, key, value)
    await db.commit()
    await db.refresh(step)
    return step


async def delete_opportunity_step(db: AsyncSession, step: OpportunityStep) -> None:
    await db.delete(step)
    await db.commit()


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------


async def create_interaction(db: AsyncSession, data: InteractionCreate) -> Interaction:
    interaction = Interaction(**data.model_dump())
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)
    return interaction


async def get_interaction(db: AsyncSession, interaction_id: int) -> Interaction | None:
    result = await db.execute(
        select(Interaction)
        .where(Interaction.id == interaction_id)
        .options(
            selectinload(Interaction.contact),
            selectinload(Interaction.opportunity),
        )
    )
    return result.scalar_one_or_none()


async def list_interactions(db: AsyncSession) -> list[Interaction]:
    result = await db.execute(
        select(Interaction).options(
            selectinload(Interaction.contact),
            selectinload(Interaction.opportunity),
        )
    )
    return list(result.scalars().unique())


async def update_interaction(db: AsyncSession, interaction: Interaction, data: InteractionUpdate) -> Interaction:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(interaction, key, value)
    await db.commit()
    await db.refresh(interaction)
    return interaction


async def delete_interaction(db: AsyncSession, interaction: Interaction) -> None:
    await db.delete(interaction)
    await db.commit()


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    task = Task(**data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def list_tasks(db: AsyncSession) -> list[Task]:
    result = await db.execute(select(Task).order_by(Task.due_date.asc_nulls_last()))
    return list(result.scalars().unique())


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data:
        if update_data["status"] == "done" and not task.completed_at:
            task.completed_at = utc_now()
        elif update_data["status"] != "done":
            task.completed_at = None
    for key, value in update_data.items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


async def create_document(
    db: AsyncSession,
    original_filename: str,
    stored_filename: str,
    storage_type: str,
    storage_key: str,
    mime_type: str | None,
    file_size: int,
    description: str | None,
    related_type: str | None,
    related_id: int | None,
    opportunity_id: int | None,
) -> Document:
    document = Document(
        filename=stored_filename,
        original_filename=original_filename,
        storage_type=storage_type,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size=file_size,
        description=description,
        related_type=related_type,
        related_id=related_id,
        opportunity_id=opportunity_id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def get_document(db: AsyncSession, document_id: int) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == document_id).options(selectinload(Document.opportunity))
    )
    return result.scalar_one_or_none()


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).options(selectinload(Document.opportunity)))
    return list(result.scalars().unique())


async def delete_document(db: AsyncSession, document: Document) -> None:
    await db.delete(document)
    await db.commit()


# ---------------------------------------------------------------------------
# Email messages
# ---------------------------------------------------------------------------


async def create_email(db: AsyncSession, data: EmailMessageCreate, send_result: dict[str, Any]) -> EmailMessage:
    email = EmailMessage(
        contact_id=data.contact_id,
        opportunity_id=data.opportunity_id,
        to_address=data.to_address,
        from_address=data.from_address or settings.from_email,
        reply_to=data.reply_to or settings.reply_to_email,
        subject=data.subject,
        body=data.body,
        html_body=data.html_body,
        status=send_result.get("status", "draft"),
        provider=send_result.get("provider", "none"),
        external_id=send_result.get("external_id"),
        error=send_result.get("error"),
        sent_at=send_result.get("sent_at"),
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return email


async def get_email(db: AsyncSession, email_id: int) -> EmailMessage | None:
    result = await db.execute(
        select(EmailMessage)
        .where(EmailMessage.id == email_id)
        .options(
            selectinload(EmailMessage.contact),
            selectinload(EmailMessage.opportunity),
        )
    )
    return result.scalar_one_or_none()


async def list_emails(
    db: AsyncSession,
    contact_id: int | None = None,
    opportunity_id: int | None = None,
) -> list[EmailMessage]:
    stmt = select(EmailMessage)
    if contact_id is not None:
        stmt = stmt.where(EmailMessage.contact_id == contact_id)
    if opportunity_id is not None:
        stmt = stmt.where(EmailMessage.opportunity_id == opportunity_id)
    result = await db.execute(
        stmt.order_by(EmailMessage.created_at.desc()).options(
            selectinload(EmailMessage.contact),
            selectinload(EmailMessage.opportunity),
        )
    )
    return list(result.scalars().unique())


async def update_email(db: AsyncSession, email: EmailMessage, data: EmailMessageUpdate) -> EmailMessage:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(email, key, value)
    await db.commit()
    await db.refresh(email)
    return email


async def delete_email(db: AsyncSession, email: EmailMessage) -> None:
    await db.delete(email)
    await db.commit()


# ---------------------------------------------------------------------------
# Dashboard / stats
# ---------------------------------------------------------------------------


async def get_dashboard_stats(db: AsyncSession) -> dict[str, int]:
    funder_count = (await db.execute(select(func.count(Funder.id)))).scalar() or 0
    contact_count = (await db.execute(select(func.count(Contact.id)))).scalar() or 0
    opportunity_count = (await db.execute(select(func.count(Opportunity.id)))).scalar() or 0
    open_task_count = (await db.execute(select(func.count(Task.id)).where(Task.status != "done"))).scalar() or 0
    upcoming_deadline_count = (
        await db.execute(select(func.count(Opportunity.id)).where(Opportunity.deadline.isnot(None)))
    ).scalar() or 0
    recent_interaction_count = (await db.execute(select(func.count(Interaction.id)))).scalar() or 0
    email_count = (await db.execute(select(func.count(EmailMessage.id)))).scalar() or 0
    return {
        "funder_count": funder_count,
        "contact_count": contact_count,
        "opportunity_count": opportunity_count,
        "open_task_count": open_task_count,
        "upcoming_deadline_count": upcoming_deadline_count,
        "recent_interaction_count": recent_interaction_count,
        "email_count": email_count,
    }


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------


async def seed_suggested_entities(db: AsyncSession) -> dict[str, int]:
    """Load the bundled catalog of suggested funding entities."""
    if not SEED_PATH.exists():
        return {"funders_created": 0, "contacts_created": 0}

    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    funders_created = 0
    contacts_created = 0

    for item in raw.get("funders", []):
        existing = (await db.execute(select(Funder).where(Funder.name == item["name"]))).scalar_one_or_none()
        if existing:
            funder = existing
        else:
            funder = Funder(
                name=item["name"],
                type=item.get("type", "other"),
                status=item.get("status", "researching"),
                website=item.get("website"),
                focus=item.get("focus"),
                location=item.get("location"),
                notes=item.get("notes"),
            )
            db.add(funder)
            await db.flush()
            funders_created += 1

        for contact_item in item.get("contacts", []):
            email = contact_item.get("email")
            if email:
                where_clause = [
                    Contact.funder_id == funder.id,
                    Contact.email == email,
                ]
            else:
                where_clause = [
                    Contact.funder_id == funder.id,
                    Contact.name == contact_item.get("name"),
                ]
            existing_contact = (await db.execute(select(Contact).where(*where_clause))).scalar_one_or_none()
            if not existing_contact:
                db.add(
                    Contact(
                        funder_id=funder.id,
                        name=contact_item.get("name", "Unknown"),
                        role=contact_item.get("role"),
                        email=email,
                        phone=contact_item.get("phone"),
                        status=contact_item.get("status", "active"),
                        notes=contact_item.get("notes"),
                    )
                )
                contacts_created += 1

    await db.commit()

    setting = (await db.execute(select(Setting).where(Setting.key == "seeded_at"))).scalar_one_or_none()
    if setting:
        setting.value = utc_now().isoformat()
    else:
        db.add(Setting(key="seeded_at", value=utc_now().isoformat()))
    await db.commit()

    return {"funders_created": funders_created, "contacts_created": contacts_created}


def ensure_uploads_dir() -> None:
    UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
