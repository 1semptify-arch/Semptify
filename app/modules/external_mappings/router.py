"""
External Mappings API - Manage connections to external systems

Provides endpoints to create, read, update, and manage mappings between
Semptify internal IDs and external system references (court cases, properties, agencies).

Mappings live in the tenant's own cloud vault (mapping overlays under
Vault/external/) via app.services.external_mapping_store — not the server DB.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.security import get_current_user
from app.services import external_mapping_store as store

logger = logging.getLogger(__name__)

# Initialize router
mappings_router = APIRouter(prefix="/api/external-mappings", tags=["External Mappings"])


# Pydantic models for requests/responses
from pydantic import BaseModel, Field


class MappingCreate(BaseModel):
    """Request to create a new external mapping."""

    mapping_type: str = Field(..., description="Type: court_case, property, agency, attorney")
    external_system: str = Field(..., description="External system name")
    external_id: str = Field(..., description="External system ID")
    display_name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="Description of the mapping")
    external_url: str | None = Field(None, description="Link to external system")
    semptify_entity_type: str | None = Field(None, description="Semptify entity type")
    semptify_entity_id: str | None = Field(None, description="Semptify entity ID")
    verification_source: str | None = Field(None, description="Source of verification")


class CourtCaseCreate(BaseModel):
    """Request to create a court case mapping."""

    court_system: str = Field(..., description="Court system: mn_state, hennepin_county, federal")
    case_number: str = Field(..., description="Official case number")
    case_type: str = Field(..., description="Case type: eviction, housing, small_claims")
    case_title: str | None = Field(None, description="Case title")
    court_name: str | None = Field(None, description="Court name")
    judge_name: str | None = Field(None, description="Judge name")
    division: str | None = Field(None, description="Court division")
    plaintiff: str | None = Field(None, description="Plaintiff name")
    defendant: str | None = Field(None, description="Defendant name")
    attorney_bar_numbers: str | None = Field(None, description="JSON array of attorney bar numbers")
    filing_date: datetime | None = Field(None, description="Filing date")
    hearing_date: datetime | None = Field(None, description="Hearing date")
    trial_date: datetime | None = Field(None, description="Trial date")
    case_portal_url: str | None = Field(None, description="Court portal URL")
    document_filing_url: str | None = Field(None, description="Document filing URL")
    semptify_complaint_id: str | None = Field(None, description="Linked Semptify complaint ID")
    semptify_timeline_event_ids: str | None = Field(None, description="JSON array of timeline event IDs")


class PropertyCreate(BaseModel):
    """Request to create a property mapping."""

    parcel_id: str = Field(..., description="Property parcel ID")
    county: str = Field(..., description="County: hennepin, ramsey, dakota")
    municipality: str | None = Field(None, description="City/municipality")
    street_address: str = Field(..., description="Street address")
    unit: str | None = Field(None, description="Unit/apartment number")
    city: str = Field(..., description="City")
    state: str = Field("MN", description="State")
    zip_code: str = Field(..., description="ZIP code")
    property_type: str | None = Field(None, description="Property type")
    tax_id: str | None = Field(None, description="Tax parcel ID")
    county_assessor_url: str | None = Field(None, description="Assessor portal URL")
    county_recorder_url: str | None = Field(None, description="Recorder portal URL")
    gis_map_url: str | None = Field(None, description="GIS map URL")
    semptify_lease_doc_id: str | None = Field(None, description="Lease document ID")
    is_primary_residence: bool = Field(True, description="Primary residence flag")


class AgencyCreate(BaseModel):
    """Request to create an agency mapping."""

    agency_code: str = Field(..., description="Agency code")
    agency_name: str = Field(..., description="Agency name")
    complaint_number: str = Field(..., description="Complaint number")
    complaint_type: str = Field(..., description="Complaint type")
    submission_date: datetime | None = Field(None, description="Submission date")
    submission_method: str | None = Field(None, description="Submission method")
    agency_portal_url: str | None = Field(None, description="Agency portal URL")
    tracking_url: str | None = Field(None, description="Tracking URL")
    semptify_complaint_id: str = Field(..., description="Semptify complaint ID")
    semptify_document_ids: str | None = Field(None, description="JSON array of document IDs")


# ============================================================================
# General Mapping Endpoints
# ============================================================================


@mappings_router.post("/mapping")
async def create_external_mapping(mapping: MappingCreate, current_user=Depends(get_current_user)):
    """Create a new external mapping."""
    try:
        # Check for duplicates
        existing = await store.find_by_external_id(
            current_user, mapping.external_system, mapping.external_id, mapping.mapping_type
        )
        if existing:
            raise HTTPException(status_code=409, detail="Mapping already exists for this external ID")

        # Create mapping
        new_mapping = await store.create_mapping(
            current_user,
            mapping_type=mapping.mapping_type,
            external_system=mapping.external_system,
            external_id=mapping.external_id,
            semptify_entity_type=mapping.septify_entity_type,
            semptify_entity_id=mapping.septify_entity_id,
            display_name=mapping.display_name,
            description=mapping.description,
            external_url=mapping.external_url,
            verification_source=mapping.verification_source,
        )

        return JSONResponse(content={"success": True, "mapping": new_mapping.to_dict()}, status_code=201)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create mapping")
        raise HTTPException(status_code=500, detail="Failed to create mapping")


@mappings_router.get("/mappings")
async def list_user_mappings(
    mapping_type: str | None = Query(None, description="Filter by mapping type"),
    status: str = Query("active", description="Filter by status"),
    current_user=Depends(get_current_user),
):
    """List all mappings for the current user."""
    try:
        mappings = await store.list_mappings(current_user, mapping_type, status)

        return JSONResponse(
            content={
                "success": True,
                "mappings": [m.to_dict() for m in mappings],
                "total_count": len(mappings),
                "filter_type": mapping_type,
                "filter_status": status,
            }
        )

    except Exception:
        logger.exception("Failed to retrieve mappings")
        raise HTTPException(status_code=500, detail="Failed to retrieve mappings")


@mappings_router.get("/mapping/{mapping_id}")
async def get_mapping_detail(mapping_id: int, current_user=Depends(get_current_user)):
    """Get detailed information about a specific mapping."""
    try:
        mapping = await store.get_mapping(current_user, mapping_id)

        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        return JSONResponse(content={"success": True, "mapping": mapping.to_dict()})

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to retrieve mapping")
        raise HTTPException(status_code=500, detail="Failed to retrieve mapping")


@mappings_router.put("/mapping/{mapping_id}/status")
async def update_mapping(
    mapping_id: int,
    status: str = Body(..., embed=True),
    verification_source: str | None = Body(None, embed=True),
    current_user=Depends(get_current_user),
):
    """Update mapping status and verification."""
    try:
        updated_mapping = await store.update_mapping_status(current_user, mapping_id, status, verification_source)

        if not updated_mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")

        return JSONResponse(
            content={
                "success": True,
                "message": f"Mapping status updated to {status}",
                "mapping": updated_mapping.to_dict(),
            }
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update mapping")
        raise HTTPException(status_code=500, detail="Failed to update mapping")


# ============================================================================
# Court Case Mappings
# ============================================================================


@mappings_router.post("/court-case")
async def create_court_case_mapping(case: CourtCaseCreate, current_user=Depends(get_current_user)):
    """Create a court case mapping with detailed legal information."""
    try:
        # Check for duplicates
        if await store.find_court_case(current_user, case.case_number, case.court_system):
            raise HTTPException(status_code=409, detail="Court case mapping already exists")

        # Create court case mapping
        court_case = await store.create_court_case(
            current_user,
            court_system=case.court_system,
            case_number=case.case_number,
            case_type=case.case_type,
            case_title=case.case_title,
            court_name=case.court_name,
            judge_name=case.judge_name,
            division=case.division,
            plaintiff=case.plaintiff,
            defendant=case.defendant,
            attorney_bar_numbers=case.attorney_bar_numbers,
            filing_date=case.filing_date,
            hearing_date=case.hearing_date,
            trial_date=case.trial_date,
            case_portal_url=case.case_portal_url,
            document_filing_url=case.document_filing_url,
            semptify_complaint_id=case.septify_complaint_id,
            semptify_timeline_event_ids=case.septify_timeline_event_ids,
        )

        # Also create a general mapping
        await store.create_mapping(
            current_user,
            mapping_type="court_case",
            external_system=case.court_system,
            external_id=case.case_number,
            semptify_entity_type="complaint",
            semptify_entity_id=case.septify_complaint_id,
            display_name=f"{case.case_type.title()} Case {case.case_number}",
            description=f"Case in {case.court_system.replace('_', ' ').title()}",
            external_url=case.case_portal_url,
            verification_source="user_input",
        )

        return JSONResponse(content={"success": True, "court_case": court_case.to_dict()}, status_code=201)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create court case mapping")
        raise HTTPException(status_code=500, detail="Failed to create court case mapping")


@mappings_router.get("/court-cases")
async def list_court_cases(
    case_type: str | None = Query(None, description="Filter by case type"),
    case_status: str | None = Query(None, description="Filter by case status"),
    current_user=Depends(get_current_user),
):
    """List court case mappings for the current user."""
    try:
        cases = await store.list_court_cases(current_user, case_type, case_status)

        return JSONResponse(
            content={
                "success": True,
                "court_cases": [c.to_dict() for c in cases],
                "total_count": len(cases),
                "filter_case_type": case_type,
                "filter_case_status": case_status,
            }
        )

    except Exception:
        logger.exception("Failed to retrieve court cases")
        raise HTTPException(status_code=500, detail="Failed to retrieve court cases")


# ============================================================================
# Property Mappings
# ============================================================================


@mappings_router.post("/property")
async def create_property_mapping(property: PropertyCreate, current_user=Depends(get_current_user)):
    """Create a property mapping with parcel and address details."""
    try:
        # Check for duplicates
        if await store.find_property(current_user, property.parcel_id, property.county):
            raise HTTPException(status_code=409, detail="Property mapping already exists")

        # Create property mapping
        prop_mapping = await store.create_property(
            current_user,
            parcel_id=property.parcel_id,
            county=property.county,
            municipality=property.municipality,
            street_address=property.street_address,
            unit=property.unit,
            city=property.city,
            state=property.state,
            zip_code=property.zip_code,
            property_type=property.property_type,
            tax_id=property.tax_id,
            county_assessor_url=property.county_assessor_url,
            county_recorder_url=property.county_recorder_url,
            gis_map_url=property.gis_map_url,
            semptify_lease_doc_id=property.septify_lease_doc_id,
            is_primary_residence=property.is_primary_residence,
        )

        # Also create a general mapping
        await store.create_mapping(
            current_user,
            mapping_type="property",
            external_system=f"{property.county}_county",
            external_id=property.parcel_id,
            semptify_entity_type="document",
            semptify_entity_id=property.septify_lease_doc_id,
            display_name=property.street_address,
            description=f"Property in {property.city}, {property.state}",
            external_url=property.county_assessor_url,
            verification_source="user_input",
        )

        return JSONResponse(content={"success": True, "property": prop_mapping.to_dict()}, status_code=201)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create property mapping")
        raise HTTPException(status_code=500, detail="Failed to create property mapping")


@mappings_router.get("/properties")
async def list_properties(
    county: str | None = Query(None, description="Filter by county"),
    is_primary: bool | None = Query(None, description="Filter by primary residence"),
    current_user=Depends(get_current_user),
):
    """List property mappings for the current user."""
    try:
        properties = await store.list_properties(current_user, county, is_primary)

        return JSONResponse(
            content={
                "success": True,
                "properties": [p.to_dict() for p in properties],
                "total_count": len(properties),
                "filter_county": county,
                "filter_is_primary": is_primary,
            }
        )

    except Exception:
        logger.exception("Failed to retrieve properties")
        raise HTTPException(status_code=500, detail="Failed to retrieve properties")


# ============================================================================
# Agency Mappings
# ============================================================================


@mappings_router.post("/agency")
async def create_agency_mapping(agency: AgencyCreate, current_user=Depends(get_current_user)):
    """Create an agency complaint mapping."""
    try:
        # Check for duplicates
        if await store.find_agency_mapping(current_user, agency.agency_code, agency.complaint_number):
            raise HTTPException(status_code=409, detail="Agency mapping already exists")

        # Create agency mapping
        agency_mapping = await store.create_agency_mapping(
            current_user,
            agency_code=agency.agency_code,
            agency_name=agency.agency_name,
            complaint_number=agency.complaint_number,
            complaint_type=agency.complaint_type,
            submission_date=agency.submission_date,
            submission_method=agency.submission_method,
            agency_portal_url=agency.agency_portal_url,
            tracking_url=agency.tracking_url,
            semptify_complaint_id=agency.septify_complaint_id,
            semptify_document_ids=agency.septify_document_ids,
        )

        # Also create a general mapping
        await store.create_mapping(
            current_user,
            mapping_type="agency",
            external_system=agency.agency_code,
            external_id=agency.complaint_number,
            semptify_entity_type="complaint",
            semptify_entity_id=agency.septify_complaint_id,
            display_name=f"{agency.agency_name} Complaint {agency.complaint_number}",
            description=f"{agency.complaint_type.title()} complaint filed with {agency.agency_name}",
            external_url=agency.tracking_url,
            verification_source="user_input",
        )

        return JSONResponse(content={"success": True, "agency": agency_mapping.to_dict()}, status_code=201)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create agency mapping")
        raise HTTPException(status_code=500, detail="Failed to create agency mapping")


@mappings_router.get("/agencies")
async def list_agency_mappings(
    agency_code: str | None = Query(None, description="Filter by agency code"),
    complaint_type: str | None = Query(None, description="Filter by complaint type"),
    current_user=Depends(get_current_user),
):
    """List agency mappings for the current user."""
    try:
        agencies = await store.list_agency_mappings(current_user, agency_code, complaint_type)

        return JSONResponse(
            content={
                "success": True,
                "agencies": [a.to_dict() for a in agencies],
                "total_count": len(agencies),
                "filter_agency_code": agency_code,
                "filter_complaint_type": complaint_type,
            }
        )

    except Exception:
        logger.exception("Failed to retrieve agency mappings")
        raise HTTPException(status_code=500, detail="Failed to retrieve agency mappings")


# ============================================================================
# Search and Lookup
# ============================================================================


@mappings_router.get("/search")
async def search_mappings(
    query: str = Query(..., description="Search query"),
    mapping_type: str | None = Query(None, description="Filter by mapping type"),
    current_user=Depends(get_current_user),
):
    """Search mappings by external ID, display name, or description."""
    try:
        results = await store.search(current_user, query, mapping_type)
        total = sum(len(v) for v in results.values())

        return JSONResponse(
            content={
                "success": True,
                "results": {kind: [v.to_dict() for v in views] for kind, views in results.items()},
                "total_matches": total,
                "search_query": query,
                "filter_type": mapping_type,
            }
        )

    except Exception:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail="Search failed")
