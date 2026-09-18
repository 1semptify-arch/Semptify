"""External mapping store — mapping overlays in the tenant's cloud vault.

External mappings (bridges between tenant records and external system
references) persist as overlays anchored to `document_id="mappings:{user_id}"`
at VAULT_EXTERNAL_FILE. Four record kinds share the anchor:

    EXTERNAL_MAPPING      — general-purpose mapping (any external system)
    COURT_CASE_MAPPING    — court case detail (parties, dates, status)
    PROPERTY_MAPPING      — parcel/address detail (county, tax id)
    AGENCY_MAPPING        — agency complaint detail (status, outcome)

Legacy rows from `external_mappings`, `court_case_mappings`,
`property_mappings`, `agency_mappings` migrate on first read per kind:
non-destructive, idempotent via `payload["legacy_id"]`, bounded 25 rows/call.

Integer PKs are preserved per record kind (`payload["record_id"]`, allocated
max+1 per user per kind) — `/mapping/{id}` paths keep resolving.

View contract: view objects carry each model's `to_dict()` response shape —
including the legacy `septify_*` key spelling — plus the ORM attribute
surface the router reads.
"""

import logging
from datetime import datetime
from types import SimpleNamespace

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.user_context import UserContext
from app.core.vault_paths import VAULT_EXTERNAL_FILE
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage import get_provider
from app.services.unified_overlay_manager import UnifiedOverlayManager, get_unified_overlay_manager

logger = logging.getLogger(__name__)


def _anchor(effective_id: str) -> str:
    return f"mappings:{effective_id}"


async def _get_manager(user: UserContext) -> UnifiedOverlayManager:
    storage = get_provider(user.provider.value, access_token=user.access_token)
    return await get_unified_overlay_manager(storage, user.get_effective_user_id())


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _next_id(overlays: list) -> int:
    ids = [o.payload.get("record_id") for o in overlays if isinstance(o.payload.get("record_id"), int)]
    return (max(ids) + 1) if ids else 1


async def _list_overlays(user: UserContext, overlay_type: OverlayType) -> list:
    manager = await _get_manager(user)
    effective_id = user.get_effective_user_id()
    response = await manager.get_overlays(document_id=_anchor(effective_id), overlay_type=overlay_type)
    if not response.success:
        logger.warning("Mapping overlay list failed for user %s: %s", user.user_id[:8], response.message)
        return []
    return [o for o in response.overlays if o.created_by == effective_id]


async def _create(user: UserContext, overlay_type: OverlayType, payload: dict, scope: str) -> object | None:
    effective_id = user.get_effective_user_id()
    manager = await _get_manager(user)
    response = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=overlay_type,
            document_id=_anchor(effective_id),
            vault_path=VAULT_EXTERNAL_FILE,
            payload=payload,
            metadata={"scope": scope},
        )
    )
    if not response.success or not response.overlay_id:
        logger.error("Failed to create %s for user %s: %s", scope, user.user_id[:8], response.message)
        return None
    return await manager.get_overlay(response.overlay_id)


# ── General external mappings ────────────────────────────────────────────────


class MappingView(SimpleNamespace):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mapping_type": self.mapping_type,
            "external_system": self.external_system,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "septify_entity_type": self.semptify_entity_type,
            "septify_entity_id": self.semptify_entity_id,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "verified": self.verified,
            "verification_source": self.verification_source,
        }


def _mapping_view(overlay, effective_id: str) -> MappingView:
    p = overlay.payload
    return MappingView(
        id=p.get("record_id"),
        user_id=effective_id,
        mapping_type=p.get("mapping_type"),
        external_system=p.get("external_system"),
        external_id=p.get("external_id"),
        external_url=p.get("external_url"),
        semptify_entity_type=p.get("semptify_entity_type"),
        semptify_entity_id=p.get("semptify_entity_id"),
        display_name=p.get("display_name"),
        description=p.get("description"),
        status=p.get("status") or "active",
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
        verified=bool(p.get("verified")),
        verification_source=p.get("verification_source"),
        overlay_id=overlay.overlay_id,
    )


async def create_mapping(user: UserContext, **fields) -> MappingView | None:
    """Create a general external mapping (companion rows included)."""
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.EXTERNAL_MAPPING)
    now = utc_now().isoformat()
    payload = {k: _to_iso(v) for k, v in fields.items()}
    payload.update(
        {
            "record_id": _next_id(overlays),
            "status": payload.get("status") or "active",
            "verified": bool(payload.get("verification_source")),
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }
    )
    overlay = await _create(user, OverlayType.EXTERNAL_MAPPING, payload, "external_mapping")
    return _mapping_view(overlay, user.get_effective_user_id()) if overlay else None


async def list_mappings(user: UserContext, mapping_type: str | None = None, status: str = "active") -> list[MappingView]:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.EXTERNAL_MAPPING)
    if status:
        overlays = [o for o in overlays if (o.payload.get("status") or "active") == status]
    if mapping_type:
        overlays = [o for o in overlays if o.payload.get("mapping_type") == mapping_type]
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_mapping_view(o, effective_id) for o in overlays]


async def get_mapping(user: UserContext, mapping_id) -> MappingView | None:
    await migrate_legacy_mappings(user)
    try:
        wanted = int(mapping_id)
    except (TypeError, ValueError):
        return None
    for o in await _list_overlays(user, OverlayType.EXTERNAL_MAPPING):
        if o.overlay_id == mapping_id or o.payload.get("record_id") == wanted:
            return _mapping_view(o, user.get_effective_user_id())
    return None


async def find_by_external_id(
    user: UserContext, external_system: str, external_id: str, mapping_type: str | None = None
) -> MappingView | None:
    """Find a mapping by external system + id (dedupe helper)."""
    await migrate_legacy_mappings(user)
    for o in await _list_overlays(user, OverlayType.EXTERNAL_MAPPING):
        p = o.payload
        if p.get("external_system") == external_system and p.get("external_id") == external_id:
            if mapping_type and p.get("mapping_type") != mapping_type:
                continue
            return _mapping_view(o, user.get_effective_user_id())
    return None


async def update_mapping_status(
    user: UserContext, mapping_id, status: str, verification_source: str | None = None
) -> MappingView | None:
    await migrate_legacy_mappings(user)
    try:
        wanted = int(mapping_id)
    except (TypeError, ValueError):
        return None
    for o in await _list_overlays(user, OverlayType.EXTERNAL_MAPPING):
        if o.overlay_id == mapping_id or o.payload.get("record_id") == wanted:
            o.payload["status"] = status
            o.payload["updated_at"] = utc_now().isoformat()
            if verification_source:
                o.payload["verified"] = True
                o.payload["verification_source"] = verification_source
            manager = await _get_manager(user)
            await manager.update_overlay(o.overlay_id, payload=o.payload)
            return _mapping_view(o, user.get_effective_user_id())
    return None


# ── Court case mappings ──────────────────────────────────────────────────────


class CourtCaseView(SimpleNamespace):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "court_system": self.court_system,
            "case_number": self.case_number,
            "case_type": self.case_type,
            "case_title": self.case_title,
            "court_name": self.court_name,
            "judge_name": self.judge_name,
            "division": self.division,
            "plaintiff": self.plaintiff,
            "defendant": self.defendant,
            "attorney_bar_numbers": self.attorney_bar_numbers,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "hearing_date": self.hearing_date.isoformat() if self.hearing_date else None,
            "trial_date": self.trial_date.isoformat() if self.trial_date else None,
            "case_status": self.case_status,
            "case_portal_url": self.case_portal_url,
            "document_filing_url": self.document_filing_url,
            "septify_complaint_id": self.semptify_complaint_id,
            "septify_timeline_event_ids": self.semptify_timeline_event_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def _court_view(overlay, effective_id: str) -> CourtCaseView:
    p = overlay.payload
    return CourtCaseView(
        id=p.get("record_id"),
        user_id=effective_id,
        court_system=p.get("court_system"),
        case_number=p.get("case_number"),
        case_type=p.get("case_type"),
        case_title=p.get("case_title"),
        court_name=p.get("court_name"),
        judge_name=p.get("judge_name"),
        division=p.get("division"),
        plaintiff=p.get("plaintiff"),
        defendant=p.get("defendant"),
        attorney_bar_numbers=p.get("attorney_bar_numbers"),
        filing_date=_parse_dt(p.get("filing_date")),
        hearing_date=_parse_dt(p.get("hearing_date")),
        trial_date=_parse_dt(p.get("trial_date")),
        case_status=p.get("case_status") or "pending",
        case_portal_url=p.get("case_portal_url"),
        document_filing_url=p.get("document_filing_url"),
        semptify_complaint_id=p.get("semptify_complaint_id"),
        semptify_timeline_event_ids=p.get("semptify_timeline_event_ids"),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
        overlay_id=overlay.overlay_id,
    )


async def find_court_case(user: UserContext, case_number: str, court_system: str) -> CourtCaseView | None:
    await migrate_legacy_mappings(user)
    for o in await _list_overlays(user, OverlayType.COURT_CASE_MAPPING):
        if o.payload.get("case_number") == case_number and o.payload.get("court_system") == court_system:
            return _court_view(o, user.get_effective_user_id())
    return None


async def create_court_case(user: UserContext, **fields) -> CourtCaseView | None:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.COURT_CASE_MAPPING)
    now = utc_now().isoformat()
    payload = {k: _to_iso(v) for k, v in fields.items()}
    payload.update(
        {
            "record_id": _next_id(overlays),
            "case_status": payload.get("case_status") or "pending",
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }
    )
    overlay = await _create(user, OverlayType.COURT_CASE_MAPPING, payload, "court_case_mapping")
    return _court_view(overlay, user.get_effective_user_id()) if overlay else None


async def list_court_cases(
    user: UserContext, case_type: str | None = None, case_status: str | None = None
) -> list[CourtCaseView]:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.COURT_CASE_MAPPING)
    if case_type:
        overlays = [o for o in overlays if o.payload.get("case_type") == case_type]
    if case_status:
        overlays = [o for o in overlays if o.payload.get("case_status") == case_status]
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_court_view(o, effective_id) for o in overlays]


# ── Property mappings ────────────────────────────────────────────────────────


class PropertyView(SimpleNamespace):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "parcel_id": self.parcel_id,
            "county": self.county,
            "municipality": self.municipality,
            "street_address": self.street_address,
            "unit": self.unit,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "property_type": self.property_type,
            "tax_id": self.tax_id,
            "county_assessor_url": self.county_assessor_url,
            "county_recorder_url": self.county_recorder_url,
            "gis_map_url": self.gis_map_url,
            "septify_lease_doc_id": self.semptify_lease_doc_id,
            "is_primary_residence": self.is_primary_residence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "verified": self.verified,
        }


def _property_view(overlay, effective_id: str) -> PropertyView:
    p = overlay.payload
    return PropertyView(
        id=p.get("record_id"),
        user_id=effective_id,
        parcel_id=p.get("parcel_id"),
        county=p.get("county"),
        municipality=p.get("municipality"),
        street_address=p.get("street_address"),
        unit=p.get("unit"),
        city=p.get("city"),
        state=p.get("state") or "MN",
        zip_code=p.get("zip_code"),
        property_type=p.get("property_type"),
        tax_id=p.get("tax_id"),
        county_assessor_url=p.get("county_assessor_url"),
        county_recorder_url=p.get("county_recorder_url"),
        gis_map_url=p.get("gis_map_url"),
        semptify_lease_doc_id=p.get("semptify_lease_doc_id"),
        is_primary_residence=p.get("is_primary_residence", True),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
        verified=bool(p.get("verified")),
        overlay_id=overlay.overlay_id,
    )


async def find_property(user: UserContext, parcel_id: str, county: str) -> PropertyView | None:
    await migrate_legacy_mappings(user)
    for o in await _list_overlays(user, OverlayType.PROPERTY_MAPPING):
        if o.payload.get("parcel_id") == parcel_id and o.payload.get("county") == county:
            return _property_view(o, user.get_effective_user_id())
    return None


async def create_property(user: UserContext, **fields) -> PropertyView | None:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.PROPERTY_MAPPING)
    now = utc_now().isoformat()
    payload = {k: _to_iso(v) for k, v in fields.items()}
    payload.update(
        {
            "record_id": _next_id(overlays),
            "state": payload.get("state") or "MN",
            "is_primary_residence": payload.get("is_primary_residence", True),
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }
    )
    overlay = await _create(user, OverlayType.PROPERTY_MAPPING, payload, "property_mapping")
    return _property_view(overlay, user.get_effective_user_id()) if overlay else None


async def list_properties(
    user: UserContext, county: str | None = None, is_primary: bool | None = None
) -> list[PropertyView]:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.PROPERTY_MAPPING)
    if county:
        overlays = [o for o in overlays if o.payload.get("county") == county]
    if is_primary is not None:
        overlays = [o for o in overlays if o.payload.get("is_primary_residence", True) == is_primary]
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_property_view(o, effective_id) for o in overlays]


# ── Agency mappings ──────────────────────────────────────────────────────────


class AgencyView(SimpleNamespace):
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agency_code": self.agency_code,
            "agency_name": self.agency_name,
            "complaint_number": self.complaint_number,
            "complaint_type": self.complaint_type,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "submission_method": self.submission_method,
            "complaint_status": self.complaint_status,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "resolution_outcome": self.resolution_outcome,
            "agency_portal_url": self.agency_portal_url,
            "tracking_url": self.tracking_url,
            "septify_complaint_id": self.semptify_complaint_id,
            "septify_document_ids": self.semptify_document_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def _agency_view(overlay, effective_id: str) -> AgencyView:
    p = overlay.payload
    return AgencyView(
        id=p.get("record_id"),
        user_id=effective_id,
        agency_code=p.get("agency_code"),
        agency_name=p.get("agency_name"),
        complaint_number=p.get("complaint_number"),
        complaint_type=p.get("complaint_type"),
        submission_date=_parse_dt(p.get("submission_date")),
        submission_method=p.get("submission_method"),
        complaint_status=p.get("complaint_status") or "submitted",
        resolution_date=_parse_dt(p.get("resolution_date")),
        resolution_outcome=p.get("resolution_outcome"),
        agency_portal_url=p.get("agency_portal_url"),
        tracking_url=p.get("tracking_url"),
        semptify_complaint_id=p.get("semptify_complaint_id"),
        semptify_document_ids=p.get("semptify_document_ids"),
        created_at=_parse_dt(p.get("created_at")) or overlay.created_at,
        updated_at=_parse_dt(p.get("updated_at")) or overlay.updated_at,
        overlay_id=overlay.overlay_id,
    )


async def find_agency_mapping(user: UserContext, agency_code: str, complaint_number: str) -> AgencyView | None:
    await migrate_legacy_mappings(user)
    for o in await _list_overlays(user, OverlayType.AGENCY_MAPPING):
        if o.payload.get("agency_code") == agency_code and o.payload.get("complaint_number") == complaint_number:
            return _agency_view(o, user.get_effective_user_id())
    return None


async def create_agency_mapping(user: UserContext, **fields) -> AgencyView | None:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.AGENCY_MAPPING)
    now = utc_now().isoformat()
    payload = {k: _to_iso(v) for k, v in fields.items()}
    payload.update(
        {
            "record_id": _next_id(overlays),
            "complaint_status": payload.get("complaint_status") or "submitted",
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }
    )
    overlay = await _create(user, OverlayType.AGENCY_MAPPING, payload, "agency_mapping")
    return _agency_view(overlay, user.get_effective_user_id()) if overlay else None


async def list_agency_mappings(
    user: UserContext, agency_code: str | None = None, complaint_type: str | None = None
) -> list[AgencyView]:
    await migrate_legacy_mappings(user)
    overlays = await _list_overlays(user, OverlayType.AGENCY_MAPPING)
    if agency_code:
        overlays = [o for o in overlays if o.payload.get("agency_code") == agency_code]
    if complaint_type:
        overlays = [o for o in overlays if o.payload.get("complaint_type") == complaint_type]
    overlays.sort(key=lambda o: o.payload.get("created_at") or "", reverse=True)
    effective_id = user.get_effective_user_id()
    return [_agency_view(o, effective_id) for o in overlays]


# ── Cross-kind search ────────────────────────────────────────────────────────


def _matches(payload: dict, fields: tuple[str, ...], needle: str) -> bool:
    return any(needle in str(payload.get(f) or "").lower() for f in fields)


async def search(user: UserContext, query: str, mapping_type: str | None = None) -> dict:
    """Case-insensitive substring search across all four mapping kinds —
    mirrors the legacy ilike('%q%') semantics in Python."""
    await migrate_legacy_mappings(user)
    needle = (query or "").lower()
    effective_id = user.get_effective_user_id()

    general = [
        o
        for o in await _list_overlays(user, OverlayType.EXTERNAL_MAPPING)
        if _matches(o.payload, ("external_id", "display_name", "description"), needle)
        and (not mapping_type or o.payload.get("mapping_type") == mapping_type)
    ]
    court = [
        o
        for o in await _list_overlays(user, OverlayType.COURT_CASE_MAPPING)
        if _matches(o.payload, ("case_number", "case_title", "plaintiff", "defendant"), needle)
    ]
    props = [
        o
        for o in await _list_overlays(user, OverlayType.PROPERTY_MAPPING)
        if _matches(o.payload, ("parcel_id", "street_address", "city"), needle)
    ]
    agencies = [
        o
        for o in await _list_overlays(user, OverlayType.AGENCY_MAPPING)
        if _matches(o.payload, ("complaint_number", "agency_name"), needle)
    ]

    return {
        "general_mappings": [_mapping_view(o, effective_id) for o in general],
        "court_cases": [_court_view(o, effective_id) for o in court],
        "properties": [_property_view(o, effective_id) for o in props],
        "agencies": [_agency_view(o, effective_id) for o in agencies],
    }


# ── Legacy migration ─────────────────────────────────────────────────────────


_MIGRATION_SPECS = (
    (
        OverlayType.EXTERNAL_MAPPING,
        "external_mappings",
        "app.models.external_mappings",
        "ExternalMapping",
        lambda row: {
            "record_id": row.id,
            "mapping_type": row.mapping_type,
            "external_system": row.external_system,
            "external_id": row.external_id,
            "external_url": row.external_url,
            "semptify_entity_type": row.semptify_entity_type,
            "semptify_entity_id": row.semptify_entity_id,
            "display_name": row.display_name,
            "description": row.description,
            "status": row.status,
            "verified": bool(row.verified),
            "verification_source": row.verification_source,
        },
    ),
    (
        OverlayType.COURT_CASE_MAPPING,
        "court_case_mappings",
        "app.models.external_mappings",
        "CourtCaseMapping",
        lambda row: {
            "record_id": row.id,
            "court_system": row.court_system,
            "case_number": row.case_number,
            "case_type": row.case_type,
            "case_title": row.case_title,
            "court_name": row.court_name,
            "judge_name": row.judge_name,
            "division": row.division,
            "plaintiff": row.plaintiff,
            "defendant": row.defendant,
            "attorney_bar_numbers": row.attorney_bar_numbers,
            "filing_date": row.filing_date.isoformat() if row.filing_date else None,
            "hearing_date": row.hearing_date.isoformat() if row.hearing_date else None,
            "trial_date": row.trial_date.isoformat() if row.trial_date else None,
            "case_status": row.case_status,
            "case_portal_url": row.case_portal_url,
            "document_filing_url": row.document_filing_url,
            "semptify_complaint_id": row.semptify_complaint_id,
            "semptify_timeline_event_ids": row.semptify_timeline_event_ids,
        },
    ),
    (
        OverlayType.PROPERTY_MAPPING,
        "property_mappings",
        "app.models.external_mappings",
        "PropertyMapping",
        lambda row: {
            "record_id": row.id,
            "parcel_id": row.parcel_id,
            "county": row.county,
            "municipality": row.municipality,
            "street_address": row.street_address,
            "unit": row.unit,
            "city": row.city,
            "state": row.state,
            "zip_code": row.zip_code,
            "property_type": row.property_type,
            "tax_id": row.tax_id,
            "county_assessor_url": row.county_assessor_url,
            "county_recorder_url": row.county_recorder_url,
            "gis_map_url": row.gis_map_url,
            "semptify_lease_doc_id": row.semptify_lease_doc_id,
            "is_primary_residence": row.is_primary_residence,
            "verified": bool(row.verified),
        },
    ),
    (
        OverlayType.AGENCY_MAPPING,
        "agency_mappings",
        "app.models.external_mappings",
        "AgencyMapping",
        lambda row: {
            "record_id": row.id,
            "agency_code": row.agency_code,
            "agency_name": row.agency_name,
            "complaint_number": row.complaint_number,
            "complaint_type": row.complaint_type,
            "submission_date": row.submission_date.isoformat() if row.submission_date else None,
            "submission_method": row.submission_method,
            "complaint_status": row.complaint_status,
            "resolution_date": row.resolution_date.isoformat() if row.resolution_date else None,
            "resolution_outcome": row.resolution_outcome,
            "agency_portal_url": row.agency_portal_url,
            "tracking_url": row.tracking_url,
            "semptify_complaint_id": row.semptify_complaint_id,
            "semptify_document_ids": row.semptify_document_ids,
        },
    ),
)


async def migrate_legacy_mappings(user: UserContext, limit: int = 25) -> int:
    """Bounded import of legacy mapping rows across all four tables.
    Non-destructive, idempotent via payload["legacy_id"] +
    payload["legacy_table"]; preserves integer PKs in payload["record_id"]."""
    try:
        import importlib

        from sqlalchemy import select

        from app.core.database import get_db_session
        models_mod = importlib.import_module("app.models.external_mappings")
    except Exception:
        return 0

    effective_id = user.get_effective_user_id()
    imported = 0
    try:
        manager = await _get_manager(user)
        async with get_db_session() as db:
            for overlay_type, table_name, _mod, class_name, to_payload in _MIGRATION_SPECS:
                if imported >= limit:
                    break
                model_cls = getattr(models_mod, class_name, None)
                if model_cls is None:
                    continue
                overlays = await _list_overlays(user, overlay_type)
                migrated_ids = {
                    o.payload.get("legacy_id") for o in overlays if o.payload.get("legacy_id") is not None
                }
                result = await db.execute(
                    select(model_cls).where(model_cls.user_id == user.user_id).order_by(model_cls.id).limit(limit)
                )
                for row in result.scalars().all():
                    if imported >= limit or row.id in migrated_ids:
                        continue
                    payload = to_payload(row)
                    payload.update(
                        {
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                            "legacy_id": row.id,
                            "legacy_table": table_name,
                            "migrated_from": table_name,
                        }
                    )
                    await manager.create_overlay(
                        CreateOverlayRequest(
                            overlay_type=overlay_type,
                            document_id=_anchor(effective_id),
                            vault_path=VAULT_EXTERNAL_FILE,
                            payload=payload,
                            metadata={"scope": table_name},
                        )
                    )
                    migrated_ids.add(row.id)
                    imported += 1
    except Exception:
        logger.exception("Legacy mapping migration failed for user %s", user.user_id[:8])
        return imported

    return imported
