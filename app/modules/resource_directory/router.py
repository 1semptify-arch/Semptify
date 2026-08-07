"""Resource directory API for tenant housing-rights support listings.

Public endpoints list community resources. Admin endpoints (Tailscale-gated)
create, update, and bulk-import listings. Staleness tracking is surfaced
explicitly because an outdated phone number can actively harm someone in crisis.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select

from app.core.admin_gating import require_admin_network
from app.core.database import get_db_session
from app.core.id_gen import make_id
from app.core.utc import utc_now
from app.models.models import Resource as ResourceModel
from app.modules.resource_directory.schemas import (
    ResourceContactInfo,
    ResourceCreate,
    ResourceImportResponse,
    ResourceListResponse,
    ResourceRead,
    ResourceUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_STALE_DAYS = 365  # Resources older than this are flagged as stale


def _model_to_response(resource: ResourceModel) -> ResourceRead:
    """Convert a Resource DB model to the public response schema."""
    languages = resource.languages or []
    if isinstance(languages, str):
        languages = json.loads(languages) if languages else []
    contact = resource.contact_info or {}
    if isinstance(contact, str):
        contact = json.loads(contact) if contact else {}
    return ResourceRead(
        id=resource.id,
        name=resource.name,
        category=resource.category,
        service_area=resource.service_area,
        languages=languages,
        contact_info=ResourceContactInfo(**contact),
        source=resource.source,
        last_verified=resource.last_verified,
        is_active=resource.is_active,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


@router.get("/api/resources", response_model=ResourceListResponse)
async def list_resources(
    category: str | None = Query(None, description="Filter by resource category"),
    service_area: str | None = Query(None, description="Filter by geographic service area"),
    language: str | None = Query(None, description="Filter by offered language code (ISO-639-1)"),
    include_inactive: bool = Query(False, description="Include inactive listings (admin preview)"),
    stale_only: bool = Query(False, description="Only return stale (unverified) listings"),
):
    """List active community resources, optionally filtered."""
    async with get_db_session() as session:
        query = select(ResourceModel)

        if not include_inactive:
            query = query.where(ResourceModel.is_active == True)
        if category:
            query = query.where(func.lower(ResourceModel.category) == category.lower())
        if service_area:
            query = query.where(func.lower(ResourceModel.service_area) == service_area.lower())
        if stale_only:
            cutoff = utc_now() - timedelta(days=_STALE_DAYS)
            query = query.where((ResourceModel.last_verified == None) | (ResourceModel.last_verified < cutoff))

        result = await session.execute(query)
        resources = result.scalars().all()

    filtered = []
    for resource in resources:
        if language:
            langs = resource.languages or []
            if isinstance(langs, str):
                langs = json.loads(langs) if langs else []
            if language.lower() not in {lang.lower() for lang in langs}:
                continue
        filtered.append(_model_to_response(resource))

    return ResourceListResponse(resources=filtered, total=len(filtered))


@router.get("/api/resources/{resource_id}", response_model=ResourceRead)
async def get_resource(resource_id: str):
    """Get a single resource listing by ID."""
    async with get_db_session() as session:
        result = await session.execute(
            select(ResourceModel).where(ResourceModel.id == resource_id, ResourceModel.is_active == True)
        )
        resource = result.scalar_one_or_none()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return _model_to_response(resource)


@router.post(
    "/admin/resources",
    response_model=ResourceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_network)],
)
async def create_resource(data: ResourceCreate):
    """Create a single resource listing (admin network only)."""
    resource = ResourceModel(
        id=make_id("res"),
        name=data.name,
        category=data.category,
        service_area=data.service_area,
        languages=data.languages,
        contact_info=data.contact_info.model_dump() if data.contact_info else None,
        source=data.source,
        last_verified=data.last_verified or utc_now(),
        is_active=data.is_active,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    async with get_db_session() as session:
        session.add(resource)
        await session.commit()
        await session.refresh(resource)
    return _model_to_response(resource)


@router.put(
    "/admin/resources/{resource_id}", response_model=ResourceRead, dependencies=[Depends(require_admin_network)]
)
async def update_resource(resource_id: str, data: ResourceUpdate):
    """Update a resource listing (admin network only)."""
    async with get_db_session() as session:
        result = await session.execute(select(ResourceModel).where(ResourceModel.id == resource_id))
        resource = result.scalar_one_or_none()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "contact_info" and value is not None:
                value = ResourceContactInfo(**value).model_dump()
            setattr(resource, field, value)

        resource.updated_at = utc_now()
        await session.commit()
        await session.refresh(resource)
        return _model_to_response(resource)


@router.delete(
    "/admin/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_network)],
)
async def delete_resource(resource_id: str):
    """Soft-delete a resource listing (admin network only)."""
    async with get_db_session() as session:
        result = await session.execute(select(ResourceModel).where(ResourceModel.id == resource_id))
        resource = result.scalar_one_or_none()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        resource.is_active = False
        resource.updated_at = utc_now()
        await session.commit()
    return None


def _normalize_languages(raw: str | None) -> list[str]:
    """Parse a comma/semicolon separated language string into a clean list."""
    if not raw:
        return []
    return [lang.strip() for lang in raw.replace(";", ",").split(",") if lang.strip()]


def _parse_last_verified(raw: str | None) -> datetime | None:
    """Parse an ISO date/datetime string, returning None on failure."""
    if not raw:
        return utc_now()
    raw = raw.strip()
    if raw.lower() in ("", "now", "today"):
        return utc_now()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=0, minute=0, second=1)
            return parsed
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _row_contact(row: dict[str, str]) -> dict[str, Any]:
    """Build contact_info JSON from CSV row columns."""
    contact: dict[str, Any] = {}
    for key in ("phone", "email", "website", "address"):
        value = row.get(key, "").strip()
        if value:
            contact[key] = value
    return contact


async def _find_existing(session, name: str, category: str, service_area: str | None) -> ResourceModel | None:
    """Find an existing resource by name + category + service_area (case-insensitive)."""
    query = select(ResourceModel).where(
        func.lower(ResourceModel.name) == name.lower(),
        func.lower(ResourceModel.category) == category.lower(),
    )
    if service_area:
        query = query.where(func.lower(ResourceModel.service_area) == service_area.lower())
    else:
        query = query.where(ResourceModel.service_area == None)
    result = await session.execute(query)
    return result.scalar_one_or_none()


@router.post(
    "/admin/resources/import",
    response_model=ResourceImportResponse,
    dependencies=[Depends(require_admin_network)],
)
async def import_resources_csv(file: UploadFile = File(...)):
    """Bulk import resources from a CSV file (admin network only).

    Expected columns: name, category, service_area, languages, phone, email,
    website, address, source, last_verified. `name` and `category` are required.
    Existing rows (matched by name + category + service_area) are updated.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    imported = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode CSV as UTF-8: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row")

    async with get_db_session() as session:
        for idx, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            category = (row.get("category") or "").strip()
            if not name or not category:
                skipped += 1
                errors.append(f"Row {idx}: missing required 'name' or 'category'")
                continue

            service_area = (row.get("service_area") or "").strip() or None
            languages = _normalize_languages(row.get("languages"))
            contact_info = _row_contact(row)
            source = (row.get("source") or "").strip() or None
            last_verified = _parse_last_verified(row.get("last_verified"))
            if last_verified is None:
                skipped += 1
                errors.append(f"Row {idx}: invalid 'last_verified' date")
                continue

            existing = await _find_existing(session, name, category, service_area)
            if existing:
                existing.service_area = service_area
                existing.languages = languages
                existing.contact_info = contact_info
                existing.source = source
                existing.last_verified = last_verified
                existing.is_active = True
                existing.updated_at = utc_now()
                updated += 1
            else:
                resource = ResourceModel(
                    id=make_id("res"),
                    name=name,
                    category=category,
                    service_area=service_area,
                    languages=languages,
                    contact_info=contact_info,
                    source=source,
                    last_verified=last_verified,
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                session.add(resource)
                imported += 1

        await session.commit()

    return ResourceImportResponse(imported=imported, updated=updated, skipped=skipped, errors=errors)


@router.get(
    "/admin/resources/stale", response_model=ResourceListResponse, dependencies=[Depends(require_admin_network)]
)
async def list_stale_resources(days: int = Query(_STALE_DAYS, ge=1, description="Staleness threshold in days")):
    """List resources whose last_verified date is older than `days` (admin network only)."""
    cutoff = utc_now() - timedelta(days=days)
    async with get_db_session() as session:
        result = await session.execute(
            select(ResourceModel).where(
                ResourceModel.is_active == True,
                (ResourceModel.last_verified == None) | (ResourceModel.last_verified < cutoff),
            )
        )
        resources = result.scalars().all()
    return ResourceListResponse(
        resources=[_model_to_response(r) for r in resources],
        total=len(resources),
    )
