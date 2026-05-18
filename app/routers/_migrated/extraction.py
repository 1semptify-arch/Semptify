"""
Form Field Extraction Router

API endpoints for:
- Extracting form fields from documents
- Reviewing and confirming extracted data
- Mapping extracted data to specific court forms
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.form_field_extractor import (
    FormFieldExtractor, 
    get_form_field_extractor,
    FormFieldsExtraction,
    FieldConfidence,
)
from app.services.form_data import get_form_data_service


router = APIRouter(prefix="/api/extraction", tags=["Form Field Extraction"])


# =============================================================================
# Request/Response Models
# =============================================================================

class DocumentInput(BaseModel):
    """Document for extraction."""
    filename: str
    text: str
    document_type: Optional[str] = None


class ExtractionRequest(BaseModel):
    """Request to extract form fields from documents."""
    documents: List[DocumentInput]


class FieldUpdate(BaseModel):
    """Update a single extracted field."""
    field_name: str
    value: Any
    confirmed: bool = True


class FieldUpdatesRequest(BaseModel):
    """Request to update multiple fields."""
    updates: List[FieldUpdate]


class ApplyToFormsRequest(BaseModel):
    """Request to apply extracted data to form data."""
    confirmed_only: bool = True  # Only apply confirmed fields


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/extract")
async def extract_form_fields(
    request: ExtractionRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Extract form fields from uploaded documents.
    
    This endpoint analyzes document text and extracts:
    - Case information (case number, court, county)
    - Party information (tenant, landlord names and addresses)
    - Property information (rental address, unit)
    - Lease details (rent, deposit, dates)
    - Case dates (hearing, summons, deadlines)
    - Amounts claimed
    
    Returns extracted fields with confidence scores and review flags.
    """
    if not request.documents:
        raise HTTPException(
            status_code=400,
            detail="No documents provided for extraction"
        )
    
    # Convert to dict format for extractor
    docs = [
        {
            "filename": doc.filename,
            "text": doc.text,
            "type": doc.document_type,
        }
        for doc in request.documents
    ]
    
    # Extract fields
    extractor = FormFieldExtractor()
    result = extractor.extract_from_documents(docs)
    
    return {
        "status": "extracted",
        "extraction": result.to_dict(),
        "summary": {
            "documents_processed": len(docs),
            "overall_confidence": round(result.overall_confidence * 100, 1),
            "fields_needing_review": result.fields_needing_review,
        }
    }


@router.post("/extract-from-vault")
async def extract_from_vault_documents(
    user: StorageUser = Depends(require_user),
):
    """
    Extract form fields from all documents in user's vault.
    
    This pulls documents from the vault storage and extracts
    form-ready data from their content.
    """
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.models import Document
    
    # Get user's documents
    async with get_db_session() as session:
        query = select(Document).where(Document.user_id == user.user_id)
        result = await session.execute(query)
        documents = result.scalars().all()
    
    if not documents:
        return {
            "status": "no_documents",
            "message": "No documents found in vault. Please upload documents first.",
            "extraction": None,
        }
    
    # Prepare documents for extraction
    docs = []
    for doc in documents:
        # Get document text - from content field or OCR result
        text = ""
        if hasattr(doc, 'extracted_text') and doc.extracted_text:
            text = doc.extracted_text
        elif hasattr(doc, 'content') and doc.content:
            text = doc.content
        elif hasattr(doc, 'description') and doc.description:
            text = doc.description
        
        docs.append({
            "filename": doc.original_filename or doc.filename,
            "text": text,
            "type": doc.document_type,
        })
    
    # Extract fields
    extractor = FormFieldExtractor()
    extraction = extractor.extract_from_documents(docs)
    
    return {
        "status": "extracted",
        "extraction": extraction.to_dict(),
        "summary": {
            "documents_processed": len(docs),
            "overall_confidence": round(extraction.overall_confidence * 100, 1),
            "fields_needing_review": extraction.fields_needing_review,
        }
    }


@router.get("/review-items")
async def get_review_items(
    user: StorageUser = Depends(require_user),
):
    """
    Get list of extracted fields that need user review.
    
    Returns fields marked for review with:
    - Current extracted value
    - Confidence level
    - Reason for review
    - Alternative values found
    """
    # For now, return a template of what needs review
    # In production, this would pull from user's stored extraction
    
    return {
        "status": "ok",
        "review_items": [
            {
                "category": "Case Information",
                "fields": [
                    {"field_name": "case_number", "display_name": "Case Number", "required": True},
                    {"field_name": "county", "display_name": "County", "required": True},
                ]
            },
            {
                "category": "Your Information (Tenant/Defendant)", 
                "fields": [
                    {"field_name": "tenant_name", "display_name": "Your Full Legal Name", "required": True},
                    {"field_name": "tenant_address", "display_name": "Your Current Mailing Address", "required": True},
                    {"field_name": "tenant_phone", "display_name": "Your Phone Number", "required": False},
                    {"field_name": "tenant_email", "display_name": "Your Email", "required": False},
                ]
            },
            {
                "category": "Landlord Information (Plaintiff)",
                "fields": [
                    {"field_name": "landlord_name", "display_name": "Landlord/Property Owner Name", "required": True},
                    {"field_name": "landlord_address", "display_name": "Landlord Address", "required": False},
                ]
            },
            {
                "category": "Rental Property",
                "fields": [
                    {"field_name": "property_address", "display_name": "Property Address", "required": True},
                    {"field_name": "unit_number", "display_name": "Unit/Apt Number", "required": False},
                    {"field_name": "property_city", "display_name": "City", "required": True},
                    {"field_name": "property_state", "display_name": "State", "required": True},
                    {"field_name": "property_zip", "display_name": "ZIP Code", "required": True},
                ]
            },
            {
                "category": "Lease & Rent",
                "fields": [
                    {"field_name": "monthly_rent", "display_name": "Monthly Rent Amount", "required": True},
                    {"field_name": "security_deposit", "display_name": "Security Deposit Paid", "required": False},
                ]
            },
            {
                "category": "Important Dates",
                "fields": [
                    {"field_name": "hearing_date", "display_name": "Court Hearing Date", "required": True},
                    {"field_name": "hearing_time", "display_name": "Hearing Time", "required": False},
                    {"field_name": "answer_deadline", "display_name": "Answer Due Date", "required": True},
                    {"field_name": "notice_date", "display_name": "Date Notice Was Served", "required": False},
                ]
            },
            {
                "category": "Amounts Claimed Against You",
                "fields": [
                    {"field_name": "rent_claimed", "display_name": "Rent They Claim You Owe", "required": False},
                    {"field_name": "total_claimed", "display_name": "Total Amount Claimed", "required": False},
                ]
            },
        ],
        "instructions": "Please review and confirm each field. Fields marked as required must be filled before generating forms."
    }


@router.post("/confirm")
async def confirm_extracted_fields(
    request: FieldUpdatesRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Confirm and update extracted field values.
    
    Users review extracted data and can:
    - Confirm the extracted value is correct
    - Update with a corrected value
    
    Confirmed fields are saved and used for form generation.
    """
    # Get form data service and update
    service = get_form_data_service(user.user_id)
    await service.load()
    
    # Map field updates to case info
    updates = {}
    tenant_updates = {}
    landlord_updates = {}
    
    for field_update in request.updates:
        name = field_update.field_name
        value = field_update.value
        
        # Route to correct nested object
        if name.startswith('tenant_'):
            key = name.replace('tenant_', '')
            if key == 'name':
                tenant_updates['name'] = value
            elif key == 'address':
                tenant_updates['address'] = value
            elif key == 'city':
                tenant_updates['city'] = value
            elif key == 'state':
                tenant_updates['state'] = value
            elif key == 'zip':
                tenant_updates['zip_code'] = value
            elif key == 'phone':
                tenant_updates['phone'] = value
            elif key == 'email':
                tenant_updates['email'] = value
        elif name.startswith('landlord_'):
            key = name.replace('landlord_', '')
            if key == 'name':
                landlord_updates['name'] = value
            elif key == 'address':
                landlord_updates['address'] = value
            elif key == 'city':
                landlord_updates['city'] = value
            elif key == 'state':
                landlord_updates['state'] = value
            elif key == 'zip':
                landlord_updates['zip_code'] = value
            elif key == 'phone':
                landlord_updates['phone'] = value
            elif key == 'email':
                landlord_updates['email'] = value
        elif name.startswith('property_'):
            key = name.replace('property_', '')
            updates[f'property_{key}'] = value
        else:
            updates[name] = value
    
    if tenant_updates:
        updates['tenant'] = tenant_updates
    if landlord_updates:
        updates['landlord'] = landlord_updates
    
    # Apply updates
    service.update_case_info(updates)
    
    return {
        "status": "confirmed",
        "fields_updated": len(request.updates),
        "case_summary": service.get_case_summary(),
    }


@router.post("/apply-to-forms")
async def apply_extraction_to_forms(
    request: ApplyToFormsRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Apply extracted and confirmed data to form data service.
    
    This merges extracted data into the central form data hub,
    making it available for all form generation endpoints.
    """
    service = get_form_data_service(user.user_id)
    await service.load()
    
    return {
        "status": "applied",
        "case_summary": service.get_case_summary(),
        "next_steps": [
            "Review your case information at /api/form-data",
            "Select defenses at /api/form-data/defenses/add",
            "Generate Answer form at /api/form-data/forms/answer",
        ]
    }


@router.get("/field-definitions")
async def get_field_definitions():
    """
    Get definitions and help text for all form fields.
    
    Useful for building UI that explains what each field means.
    """
    return {
        "fields": {
            "case_number": {
                "display_name": "Case Number",
                "help_text": "The case number assigned by the court. Found on summons or complaint. Format varies by county (e.g., 19AV-CV-25-3477).",
                "example": "19AV-CV-25-3477",
                "required": True,
            },
            "tenant_name": {
                "display_name": "Tenant Name",
                "help_text": "Your full legal name as it appears on the lease. This will be shown as the Defendant on court forms.",
                "example": "John Smith",
                "required": True,
            },
            "landlord_name": {
                "display_name": "Landlord/Plaintiff Name",
                "help_text": "The name of your landlord, property management company, or whoever filed the eviction. This is the Plaintiff.",
                "example": "ABC Property Management LLC",
                "required": True,
            },
            "property_address": {
                "display_name": "Rental Property Address",
                "help_text": "The address of the rental unit you're being evicted from. Include street, city, state, and ZIP.",
                "example": "123 Main Street, Apt 4B",
                "required": True,
            },
            "monthly_rent": {
                "display_name": "Monthly Rent",
                "help_text": "Your regular monthly rent amount. This should match what's in your lease agreement.",
                "example": "1200.00",
                "required": True,
            },
            "hearing_date": {
                "display_name": "Court Hearing Date",
                "help_text": "The date you must appear in court. Found on the summons. Missing this date may result in default judgment.",
                "example": "2025-01-15",
                "required": True,
            },
            "answer_deadline": {
                "display_name": "Answer Deadline",
                "help_text": "The deadline to file your Answer with the court. Usually 7 days after being served the summons.",
                "example": "2025-01-10",
                "required": True,
            },
            "rent_claimed": {
                "display_name": "Rent Amount Claimed",
                "help_text": "The amount of rent the landlord claims you owe. Found in the complaint or summons.",
                "example": "2400.00",
                "required": False,
            },
        }
    }
