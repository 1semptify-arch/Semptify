"""
Contact Manager Router
======================
API endpoints for managing case-related contacts:
- Landlords, property managers
- Attorneys (opposing and legal aid)
- Witnesses
- Inspectors, agencies, courts
- Any person/organization involved in your case

Integrates with:
- Form Field Extraction (auto-populate from documents)
- Form Data Hub (use contacts in court forms)
- Timeline (log interactions)
"""

from datetime import datetime
from app.core.id_gen import make_id
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_user, StorageUser
from app.models.models import Contact, ContactInteraction
from app.core.event_bus import event_bus, EventType as BusEventType


router = APIRouter(prefix="/api/contacts", tags=["Contact Manager"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ContactCreate(BaseModel):
    """Create a new contact."""
    contact_type: str  # landlord, property_manager, attorney, witness, inspector, agency, court, legal_aid, tenant_org, other
    role: Optional[str] = None
    name: str
    organization: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    phone_alt: Optional[str] = None
    email: Optional[str] = None
    fax: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[str] = "manual"
    source_document_id: Optional[str] = None


class ContactUpdate(BaseModel):
    """Update an existing contact."""
    contact_type: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    phone_alt: Optional[str] = None
    email: Optional[str] = None
    fax: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    is_starred: Optional[bool] = None


class ContactResponse(BaseModel):
    """Contact response."""
    id: str
    contact_type: str
    role: Optional[str]
    name: str
    organization: Optional[str]
    title: Optional[str]
    phone: Optional[str]
    phone_alt: Optional[str]
    email: Optional[str]
    fax: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    website: Optional[str]
    notes: Optional[str]
    tags: Optional[str]
    source: Optional[str]
    last_contact_date: Optional[datetime]
    interaction_count: int
    is_active: bool
    is_starred: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    """Log an interaction with a contact."""
    interaction_type: str  # phone_call, email, letter, in_person, court_appearance, voicemail
    direction: str  # incoming, outgoing
    subject: Optional[str] = None
    summary: Optional[str] = None
    interaction_date: datetime
    duration_minutes: Optional[int] = None
    related_document_ids: Optional[List[str]] = None
    follow_up_needed: bool = False
    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None


class InteractionResponse(BaseModel):
    """Interaction response."""
    id: str
    contact_id: str
    interaction_type: str
    direction: str
    subject: Optional[str]
    summary: Optional[str]
    interaction_date: datetime
    duration_minutes: Optional[int]
    follow_up_needed: bool
    follow_up_date: Optional[datetime]
    follow_up_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ContactsListResponse(BaseModel):
    """List of contacts."""
    contacts: List[ContactResponse]
    total: int
    by_type: dict


class ExtractedContactsRequest(BaseModel):
    """Request to import contacts from extracted form data."""
    tenant_name: Optional[str] = None
    tenant_address: Optional[str] = None
    tenant_phone: Optional[str] = None
    tenant_email: Optional[str] = None
    landlord_name: Optional[str] = None
    landlord_address: Optional[str] = None
    landlord_phone: Optional[str] = None
    landlord_email: Optional[str] = None
    attorney_name: Optional[str] = None
    attorney_firm: Optional[str] = None
    attorney_address: Optional[str] = None
    attorney_phone: Optional[str] = None
    source_document_id: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def contact_to_response(contact: Contact) -> ContactResponse:
    """Convert Contact model to response."""
    return ContactResponse(
        id=contact.id,
        contact_type=contact.contact_type,
        role=contact.role,
        name=contact.name,
        organization=contact.organization,
        title=contact.title,
        phone=contact.phone,
        phone_alt=contact.phone_alt,
        email=contact.email,
        fax=contact.fax,
        address_line1=contact.address_line1,
        address_line2=contact.address_line2,
        city=contact.city,
        state=contact.state,
        zip_code=contact.zip_code,
        website=contact.website,
        notes=contact.notes,
        tags=contact.tags,
        source=contact.source,
        last_contact_date=contact.last_contact_date,
        interaction_count=contact.interaction_count,
        is_active=contact.is_active,
        is_starred=contact.is_starred,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


def parse_address(address: str) -> dict:
    """Parse a full address string into components."""
    # Simple parsing - can be enhanced with address parsing library
    parts = address.split(",") if address else []
    result = {
        "address_line1": None,
        "city": None,
        "state": None,
        "zip_code": None,
    }
    
    if len(parts) >= 1:
        result["address_line1"] = parts[0].strip()
    if len(parts) >= 2:
        result["city"] = parts[1].strip()
    if len(parts) >= 3:
        # Try to split "MN 55121" into state and zip
        state_zip = parts[2].strip().split()
        if len(state_zip) >= 1:
            result["state"] = state_zip[0]
        if len(state_zip) >= 2:
            result["zip_code"] = state_zip[1]
    
    return result


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get("/", response_model=ContactsListResponse)
async def list_contacts(
    contact_type: Optional[str] = Query(None, description="Filter by contact type"),
    role: Optional[str] = Query(None, description="Filter by role"),
    search: Optional[str] = Query(None, description="Search name/organization"),
    starred_only: bool = Query(False, description="Show only starred contacts"),
    active_only: bool = Query(True, description="Show only active contacts"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all contacts for the current user.
    
    Filter by type, role, or search by name/organization.
    """
    query = select(Contact).where(Contact.user_id == user.user_id)
    
    if contact_type:
        query = query.where(Contact.contact_type == contact_type)
    if role:
        query = query.where(Contact.role == role)
    if starred_only:
        query = query.where(Contact.is_starred == True)
    if active_only:
        query = query.where(Contact.is_active == True)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Contact.name.ilike(search_pattern),
                Contact.organization.ilike(search_pattern),
                Contact.email.ilike(search_pattern),
            )
        )
    
    query = query.order_by(Contact.is_starred.desc(), Contact.name)
    
    result = await db.execute(query)
    contacts = result.scalars().all()
    
    # Count by type
    type_counts = {}
    for c in contacts:
        type_counts[c.contact_type] = type_counts.get(c.contact_type, 0) + 1
    
    return ContactsListResponse(
        contacts=[contact_to_response(c) for c in contacts],
        total=len(contacts),
        by_type=type_counts,
    )


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contact."""
    contact = Contact(
        id=make_id("con"),
        user_id=user.user_id,
        contact_type=data.contact_type,
        role=data.role,
        name=data.name,
        organization=data.organization,
        title=data.title,
        phone=data.phone,
        phone_alt=data.phone_alt,
        email=data.email,
        fax=data.fax,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        website=data.website,
        notes=data.notes,
        tags=data.tags,
        source=data.source or "manual",
        source_document_id=data.source_document_id,
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return contact_to_response(contact)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific contact by ID."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return contact_to_response(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing contact."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    contact.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(contact)
    
    return contact_to_response(contact)


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a contact."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    await db.delete(contact)
    await db.commit()
    
    return {"status": "deleted", "id": contact_id}


@router.post("/{contact_id}/star")
async def toggle_star(
    contact_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle starred status for a contact."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    contact.is_starred = not contact.is_starred
    await db.commit()
    
    return {"status": "success", "is_starred": contact.is_starred}


# =============================================================================
# Interaction Logging
# =============================================================================

@router.get("/{contact_id}/interactions", response_model=List[InteractionResponse])
async def list_interactions(
    contact_id: str,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """List all interactions with a contact."""
    # Verify contact exists and belongs to user
    contact_result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    if not contact_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contact not found")
    
    result = await db.execute(
        select(ContactInteraction)
        .where(ContactInteraction.contact_id == contact_id)
        .order_by(ContactInteraction.interaction_date.desc())
    )
    interactions = result.scalars().all()
    
    return [
        InteractionResponse(
            id=i.id,
            contact_id=i.contact_id,
            interaction_type=i.interaction_type,
            direction=i.direction,
            subject=i.subject,
            summary=i.summary,
            interaction_date=i.interaction_date,
            duration_minutes=i.duration_minutes,
            follow_up_needed=i.follow_up_needed,
            follow_up_date=i.follow_up_date,
            follow_up_notes=i.follow_up_notes,
            created_at=i.created_at,
        )
        for i in interactions
    ]


@router.post("/{contact_id}/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def log_interaction(
    contact_id: str,
    data: InteractionCreate,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Log an interaction with a contact."""
    # Verify contact exists and belongs to user
    contact_result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.user_id,
        )
    )
    contact = contact_result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    import json
    
    interaction = ContactInteraction(
        id=make_id("con"),
        user_id=user.user_id,
        contact_id=contact_id,
        interaction_type=data.interaction_type,
        direction=data.direction,
        subject=data.subject,
        summary=data.summary,
        interaction_date=data.interaction_date,
        duration_minutes=data.duration_minutes,
        related_document_ids=json.dumps(data.related_document_ids) if data.related_document_ids else None,
        follow_up_needed=data.follow_up_needed,
        follow_up_date=data.follow_up_date,
        follow_up_notes=data.follow_up_notes,
    )
    
    db.add(interaction)
    
    # Update contact's last interaction date and count
    contact.last_contact_date = data.interaction_date
    contact.interaction_count += 1
    
    await db.commit()
    await db.refresh(interaction)
    
    return InteractionResponse(
        id=interaction.id,
        contact_id=interaction.contact_id,
        interaction_type=interaction.interaction_type,
        direction=interaction.direction,
        subject=interaction.subject,
        summary=interaction.summary,
        interaction_date=interaction.interaction_date,
        duration_minutes=interaction.duration_minutes,
        follow_up_needed=interaction.follow_up_needed,
        follow_up_date=interaction.follow_up_date,
        follow_up_notes=interaction.follow_up_notes,
        created_at=interaction.created_at,
    )


# =============================================================================
# Import from Extracted Data
# =============================================================================

@router.post("/import-from-extraction")
async def import_from_extraction(
    data: ExtractedContactsRequest,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import contacts from extracted form data.
    
    This is called by the extraction pipeline when contacts are
    found in uploaded documents (leases, summons, etc.).
    """
    created = []
    
    # Import landlord if provided
    if data.landlord_name:
        addr = parse_address(data.landlord_address) if data.landlord_address else {}
        
        landlord = Contact(
            id=make_id("con"),
            user_id=user.user_id,
            contact_type="landlord",
            role="opposing_party",
            name=data.landlord_name,
            phone=data.landlord_phone,
            email=data.landlord_email,
            address_line1=addr.get("address_line1"),
            city=addr.get("city"),
            state=addr.get("state"),
            zip_code=addr.get("zip_code"),
            source="extracted",
            source_document_id=data.source_document_id,
        )
        db.add(landlord)
        created.append({"type": "landlord", "name": data.landlord_name})
    
    # Import attorney if provided
    if data.attorney_name:
        addr = parse_address(data.attorney_address) if data.attorney_address else {}
        
        attorney = Contact(
            id=make_id("con"),
            user_id=user.user_id,
            contact_type="attorney",
            role="opposing_counsel",
            name=data.attorney_name,
            organization=data.attorney_firm,
            phone=data.attorney_phone,
            address_line1=addr.get("address_line1"),
            city=addr.get("city"),
            state=addr.get("state"),
            zip_code=addr.get("zip_code"),
            source="extracted",
            source_document_id=data.source_document_id,
        )
        db.add(attorney)
        created.append({"type": "attorney", "name": data.attorney_name})
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Imported {len(created)} contacts from document",
        "contacts_created": created,
    }


# =============================================================================
# Quick Add (Common Types)
# =============================================================================

@router.post("/quick-add/landlord", response_model=ContactResponse)
async def quick_add_landlord(
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    address: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick add a landlord contact."""
    addr = parse_address(address) if address else {}
    
    contact = Contact(
        id=make_id("con"),
        user_id=user.user_id,
        contact_type="landlord",
        role="opposing_party",
        name=name,
        phone=phone,
        email=email,
        address_line1=addr.get("address_line1"),
        city=addr.get("city"),
        state=addr.get("state"),
        zip_code=addr.get("zip_code"),
        source="manual",
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return contact_to_response(contact)


@router.post("/quick-add/witness", response_model=ContactResponse)
async def quick_add_witness(
    name: str,
    relationship: str,  # neighbor, family, friend, professional
    phone: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick add a witness contact."""
    contact = Contact(
        id=make_id("con"),
        user_id=user.user_id,
        contact_type="witness",
        role="my_witness",
        name=name,
        title=relationship,
        phone=phone,
        email=email,
        notes=notes,
        source="manual",
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return contact_to_response(contact)


# =============================================================================
# Form Data Integration
# =============================================================================

@router.get("/for-forms")
async def get_contacts_for_forms(
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get contacts formatted for form filling.
    
    Returns contacts in a structure that matches court form fields.
    """
    result = await db.execute(
        select(Contact).where(
            Contact.user_id == user.user_id,
            Contact.is_active == True,
        )
    )
    contacts = result.scalars().all()
    
    # Organize by role for form filling
    landlord = next((c for c in contacts if c.contact_type == "landlord"), None)
    attorney = next((c for c in contacts if c.contact_type == "attorney" and c.role == "opposing_counsel"), None)
    
    def format_contact(c):
        if not c:
            return None
        return {
            "name": c.name,
            "organization": c.organization,
            "address": f"{c.address_line1 or ''}, {c.city or ''}, {c.state or ''} {c.zip_code or ''}".strip(", "),
            "phone": c.phone,
            "email": c.email,
        }
    
    return {
        "landlord": format_contact(landlord),
        "opposing_counsel": format_contact(attorney),
        "witnesses": [
            {
                "name": c.name,
                "relationship": c.title,
                "contact": c.phone or c.email,
            }
            for c in contacts
            if c.contact_type == "witness"
        ],
        "all_contacts": [contact_to_response(c) for c in contacts],
    }


# =============================================================================
# Contact Types Reference
# =============================================================================

@router.get("/types")
async def get_contact_types():
    """Get available contact types and roles."""
    return {
        "contact_types": [
            {"value": "landlord", "label": "Landlord", "icon": "🏠"},
            {"value": "property_manager", "label": "Property Manager", "icon": "🏢"},
            {"value": "attorney", "label": "Attorney", "icon": "⚖️"},
            {"value": "witness", "label": "Witness", "icon": "👁️"},
            {"value": "inspector", "label": "Inspector", "icon": "🔍"},
            {"value": "agency", "label": "Government Agency", "icon": "🏛️"},
            {"value": "court", "label": "Court", "icon": "⚖️"},
            {"value": "legal_aid", "label": "Legal Aid", "icon": "🤝"},
            {"value": "tenant_org", "label": "Tenant Organization", "icon": "✊"},
            {"value": "other", "label": "Other", "icon": "📋"},
        ],
        "roles": [
            {"value": "opposing_party", "label": "Opposing Party"},
            {"value": "opposing_counsel", "label": "Opposing Counsel"},
            {"value": "my_witness", "label": "My Witness"},
            {"value": "their_witness", "label": "Their Witness"},
            {"value": "inspector", "label": "Inspector"},
            {"value": "caseworker", "label": "Caseworker"},
            {"value": "judge", "label": "Judge"},
            {"value": "mediator", "label": "Mediator"},
            {"value": "support", "label": "Support Contact"},
        ],
        "interaction_types": [
            {"value": "phone_call", "label": "Phone Call", "icon": "📞"},
            {"value": "email", "label": "Email", "icon": "📧"},
            {"value": "letter", "label": "Letter/Mail", "icon": "✉️"},
            {"value": "in_person", "label": "In Person", "icon": "🤝"},
            {"value": "court_appearance", "label": "Court Appearance", "icon": "⚖️"},
            {"value": "voicemail", "label": "Voicemail", "icon": "📱"},
        ],
    }
