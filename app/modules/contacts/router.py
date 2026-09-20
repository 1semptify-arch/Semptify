"""
Contact Manager Router
======================
API endpoints for managing case-related contacts:
- Landlords, property managers
- Attorneys (opposing and legal aid)
- Witnesses
- Inspectors, agencies, courts
- Any person/organization involved in your case

Migrated from app/routers/contacts.py into the contacts SDK module.
All imports remain absolute (pointing to app.core.*, app.models.*) since
contacts is a CORE module that depends on shared infrastructure.

Integrates with:
- Form Field Extraction (auto-populate from documents)
- Form Data Hub (use contacts in court forms)
- Timeline (log interactions)
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.core.capabilities import require_capability
from app.core.security import StorageUser, yellow_access
from app.models.unified_overlay_models import UnifiedOverlay
from app.modules.contacts import service
from app.services.calendar_sync import _parse_datetime as _parse_dt

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/contacts",
    tags=["Contact Manager"],
    dependencies=[Depends(require_capability("app.modules.contacts.router"))],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ContactCreate(BaseModel):
    """Create a new contact."""

    contact_type: (
        str  # landlord, property_manager, attorney, witness, inspector, agency, court, legal_aid, tenant_org, other
    )
    role: str | None = None
    name: str
    organization: str | None = None
    title: str | None = None
    phone: str | None = None
    phone_alt: str | None = None
    email: str | None = None
    fax: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    website: str | None = None
    notes: str | None = None
    tags: str | None = None
    source: str | None = "manual"
    source_document_id: str | None = None


class ContactUpdate(BaseModel):
    """Update an existing contact."""

    contact_type: str | None = None
    role: str | None = None
    name: str | None = None
    organization: str | None = None
    title: str | None = None
    phone: str | None = None
    phone_alt: str | None = None
    email: str | None = None
    fax: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    website: str | None = None
    notes: str | None = None
    tags: str | None = None
    is_active: bool | None = None
    is_starred: bool | None = None


class ContactResponse(BaseModel):
    """Contact response."""

    id: str
    contact_type: str
    role: str | None
    name: str
    organization: str | None
    title: str | None
    phone: str | None
    phone_alt: str | None
    email: str | None
    fax: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    website: str | None
    notes: str | None
    tags: str | None
    source: str | None
    last_contact_date: datetime | None
    interaction_count: int
    is_active: bool
    is_starred: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionCreate(BaseModel):
    """Log an interaction with a contact."""

    interaction_type: str  # phone_call, email, letter, in_person, court_appearance, voicemail
    direction: str  # incoming, outgoing
    subject: str | None = None
    summary: str | None = None
    interaction_date: datetime
    duration_minutes: int | None = None
    related_document_ids: list[str] | None = None
    follow_up_needed: bool = False
    follow_up_date: datetime | None = None
    follow_up_notes: str | None = None


class InteractionResponse(BaseModel):
    """Interaction response."""

    id: str
    contact_id: str
    interaction_type: str
    direction: str
    subject: str | None
    summary: str | None
    interaction_date: datetime
    duration_minutes: int | None
    follow_up_needed: bool
    follow_up_date: datetime | None
    follow_up_notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactsListResponse(BaseModel):
    """List of contacts."""

    contacts: list[ContactResponse]
    total: int
    by_type: dict


class ExtractedContactsRequest(BaseModel):
    """Request to import contacts from extracted form data."""

    tenant_name: str | None = None
    tenant_address: str | None = None
    tenant_phone: str | None = None
    tenant_email: str | None = None
    landlord_name: str | None = None
    landlord_address: str | None = None
    landlord_phone: str | None = None
    landlord_email: str | None = None
    attorney_name: str | None = None
    attorney_firm: str | None = None
    attorney_address: str | None = None
    attorney_phone: str | None = None
    source_document_id: str | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def contact_to_response(contact: UnifiedOverlay) -> ContactResponse:
    """Convert a CONTACT overlay to the response schema."""
    p = contact.payload
    return ContactResponse(
        id=contact.overlay_id,
        contact_type=p.get("contact_type") or "other",
        role=p.get("role"),
        name=p.get("name") or "",
        organization=p.get("organization"),
        title=p.get("title"),
        phone=p.get("phone"),
        phone_alt=p.get("phone_alt"),
        email=p.get("email"),
        fax=p.get("fax"),
        address_line1=p.get("address_line1"),
        address_line2=p.get("address_line2"),
        city=p.get("city"),
        state=p.get("state"),
        zip_code=p.get("zip_code"),
        website=p.get("website"),
        notes=p.get("notes"),
        tags=p.get("tags"),
        source=p.get("source"),
        last_contact_date=_parse_dt(p.get("last_contact_date")),
        interaction_count=int(p.get("interaction_count") or 0),
        is_active=bool(p.get("is_active")),
        is_starred=bool(p.get("is_starred")),
        created_at=_parse_dt(p.get("created_at")) or contact.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or contact.updated_at or contact.created_at,
    )


def _interaction_to_response(i: UnifiedOverlay) -> InteractionResponse:
    """Convert a CONTACT_INTERACTION overlay to the response schema."""
    p = i.payload
    return InteractionResponse(
        id=i.overlay_id,
        contact_id=p.get("contact_id") or "",
        interaction_type=p.get("interaction_type") or "note",
        direction=p.get("direction") or "outgoing",
        subject=p.get("subject"),
        summary=p.get("summary"),
        interaction_date=_parse_dt(p.get("interaction_date")) or i.created_at,
        duration_minutes=p.get("duration_minutes"),
        follow_up_needed=bool(p.get("follow_up_needed")),
        follow_up_date=_parse_dt(p.get("follow_up_date")),
        follow_up_notes=p.get("follow_up_notes"),
        created_at=i.created_at,
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
        # Try to split "MN 55001" into state and zip
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
    contact_type: str | None = Query(None, description="Filter by contact type"),
    role: str | None = Query(None, description="Filter by role"),
    search: str | None = Query(None, description="Search name/organization"),
    starred_only: bool = Query(False, description="Show only starred contacts"),
    active_only: bool = Query(True, description="Show only active contacts"),
    user: StorageUser = Depends(yellow_access),
):
    """
    List all contacts for the current user.

    Filter by type, role, or search by name/organization.
    """
    contacts, total = await service.list_contacts(
        user,
        contact_type=contact_type,
        role=role,
        starred_only=starred_only,
        active_only=active_only,
        search=search,
    )

    # Count by type
    type_counts = {}
    for c in contacts:
        ct = c.payload.get("contact_type") or "other"
        type_counts[ct] = type_counts.get(ct, 0) + 1

    return ContactsListResponse(
        contacts=[contact_to_response(c) for c in contacts],
        total=total,
        by_type=type_counts,
    )


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    user: StorageUser = Depends(yellow_access),
):
    """Create a new contact."""
    overlay = await service.create_contact(user, **data.model_dump())
    return contact_to_response(overlay)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Get a specific contact by ID."""
    overlay = await service.get_contact(user, contact_id)
    if overlay is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact_to_response(overlay)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    user: StorageUser = Depends(yellow_access),
):
    """Update an existing contact."""
    overlay = await service.update_contact(user, contact_id, data.model_dump(exclude_unset=True))
    if overlay is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact_to_response(overlay)


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Delete a contact."""
    if not await service.delete_contact(user, contact_id):
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": "deleted", "id": contact_id}


@router.post("/{contact_id}/star")
async def toggle_star(
    contact_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """Toggle starred status for a contact."""
    overlay = await service.get_contact(user, contact_id)
    if overlay is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    new_value = not overlay.payload.get("is_starred")
    updated = await service.update_contact(user, contact_id, {"is_starred": new_value})
    if updated is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": "success", "is_starred": new_value}


# =============================================================================
# Interaction Logging
# =============================================================================


@router.get("/{contact_id}/interactions", response_model=list[InteractionResponse])
async def list_interactions(
    contact_id: str,
    user: StorageUser = Depends(yellow_access),
):
    """List all interactions with a contact."""
    if await service.get_contact(user, contact_id) is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    interactions = await service.list_interactions(user, contact_id)
    return [_interaction_to_response(i) for i in interactions]


@router.post("/{contact_id}/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
async def log_interaction(
    contact_id: str,
    data: InteractionCreate,
    user: StorageUser = Depends(yellow_access),
):
    """Log an interaction with a contact."""
    import json

    overlay = await service.create_interaction(
        user,
        contact_id,
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
    if overlay is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return _interaction_to_response(overlay)


# =============================================================================
# Import from Extracted Data
# =============================================================================


@router.post("/import-from-extraction")
async def import_from_extraction(
    data: ExtractedContactsRequest,
    user: StorageUser = Depends(yellow_access),
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

        await service.create_contact(
            user,
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
        created.append({"type": "landlord", "name": data.landlord_name})

    # Import attorney if provided
    if data.attorney_name:
        addr = parse_address(data.attorney_address) if data.attorney_address else {}

        await service.create_contact(
            user,
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
        created.append({"type": "attorney", "name": data.attorney_name})

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
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    user: StorageUser = Depends(yellow_access),
):
    """Quick add a landlord contact."""
    addr = parse_address(address) if address else {}

    overlay = await service.create_contact(
        user,
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

    return contact_to_response(overlay)


@router.post("/quick-add/witness", response_model=ContactResponse)
async def quick_add_witness(
    name: str,
    relationship: str,  # neighbor, family, friend, professional
    phone: str | None = None,
    email: str | None = None,
    notes: str | None = None,
    user: StorageUser = Depends(yellow_access),
):
    """Quick add a witness contact."""
    overlay = await service.create_contact(
        user,
        contact_type="witness",
        role="my_witness",
        name=name,
        title=relationship,
        phone=phone,
        email=email,
        notes=notes,
        source="manual",
    )

    return contact_to_response(overlay)


# =============================================================================
# Form Data Integration
# =============================================================================


@router.get("/for-forms")
async def get_contacts_for_forms(
    user: StorageUser = Depends(yellow_access),
):
    """
    Get contacts formatted for form filling.

    Returns contacts in a structure that matches court form fields.
    """
    contacts, _total = await service.list_contacts(user, active_only=True)

    # Organize by role for form filling
    landlord = next((c for c in contacts if c.payload.get("contact_type") == "landlord"), None)
    attorney = next(
        (
            c
            for c in contacts
            if c.payload.get("contact_type") == "attorney" and c.payload.get("role") == "opposing_counsel"
        ),
        None,
    )

    def format_contact(c):
        if not c:
            return None
        p = c.payload
        return {
            "name": p.get("name"),
            "organization": p.get("organization"),
            "address": f"{p.get('address_line1') or ''}, {p.get('city') or ''}, {p.get('state') or ''} {p.get('zip_code') or ''}".strip(", "),
            "phone": p.get("phone"),
            "email": p.get("email"),
        }

    return {
        "landlord": format_contact(landlord),
        "opposing_counsel": format_contact(attorney),
        "witnesses": [
            {
                "name": c.payload.get("name"),
                "relationship": c.payload.get("title"),
                "contact": c.payload.get("phone") or c.payload.get("email"),
            }
            for c in contacts
            if c.payload.get("contact_type") == "witness"
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
            {"value": "landlord", "label": "Landlord", "icon": "○"},
            {"value": "property_manager", "label": "Property Manager", "icon": "○"},
            {"value": "attorney", "label": "Attorney", "icon": "▸"},
            {"value": "witness", "label": "Witness", "icon": "●"},
            {"value": "inspector", "label": "Inspector", "icon": "▸"},
            {"value": "agency", "label": "Government Agency", "icon": "▸"},
            {"value": "court", "label": "Court", "icon": "▸"},
            {"value": "legal_aid", "label": "Legal Aid", "icon": "▸"},
            {"value": "tenant_org", "label": "Tenant Organization", "icon": "○"},
            {"value": "elected_official", "label": "Elected Official", "icon": "▸"},
            {"value": "other", "label": "Other", "icon": "●"},
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
            {"value": "mayor", "label": "Mayor"},
            {"value": "council_member", "label": "City Council Member"},
            {"value": "county_commissioner", "label": "County Commissioner"},
            {"value": "state_legislator", "label": "State Legislator"},
            {"value": "city_staff", "label": "City Staff / Department"},
        ],
        "interaction_types": [
            {"value": "phone_call", "label": "Phone Call", "icon": "●"},
            {"value": "email", "label": "Email", "icon": "●"},
            {"value": "letter", "label": "Letter/Mail", "icon": "●"},
            {"value": "in_person", "label": "In Person", "icon": "▸"},
            {"value": "court_appearance", "label": "Court Appearance", "icon": "▸"},
            {"value": "voicemail", "label": "Voicemail", "icon": "○"},
        ],
    }
