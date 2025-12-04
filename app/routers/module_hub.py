"""
Module Hub API Router
====================

API endpoints for the Module Hub - the central communication system.

Endpoints:
- GET /hub/status - Get hub status
- GET /hub/modules - List registered modules
- GET /hub/packs - Get info packs for user
- POST /hub/packs/{pack_id}/complete - Complete an info pack
- GET /hub/data/{user_id} - Get user's centralized data
- POST /hub/request - Make a data request
- GET /hub/log - Get communication log
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Cookie
from pydantic import BaseModel

from app.core.user_id import COOKIE_USER_ID
from app.core.module_hub import (
    module_hub,
    ModuleType,
    RequestType,
    PackType,
    InfoPack,
)

router = APIRouter(prefix="/hub", tags=["Module Hub"])


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def get_user_id_from_request(semptify_uid: Optional[str] = None) -> str:
    """Extract user ID from cookie or generate anonymous one"""
    if semptify_uid:
        return semptify_uid
    # Return anonymous user ID for unauthenticated requests
    return "anonymous"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DataRequestBody(BaseModel):
    """Request body for data requests"""
    request_type: str
    requesting_module: str
    params: Optional[Dict[str, Any]] = None


class CompletePackBody(BaseModel):
    """Request body for completing an info pack"""
    user_provided_data: Dict[str, Any]


class ModuleInfo(BaseModel):
    """Module information response"""
    type: str
    name: str
    active: bool
    handles_documents: List[str]
    accepts_packs: List[str]


class HubStatus(BaseModel):
    """Hub status response"""
    modules_registered: int
    modules: List[ModuleInfo]
    users_tracked: int
    info_packs_total: int
    info_packs_pending: int
    requests_total: int
    updates_total: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_hub_status():
    """Get the status of the module hub"""
    return module_hub.get_hub_status()


@router.get("/modules")
async def list_modules():
    """List all registered modules"""
    return {
        "modules": module_hub.list_modules(),
        "count": len(module_hub.list_modules()),
    }


@router.get("/packs")
async def get_user_packs(
    semptify_uid: Optional[str] = Cookie(None),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get all info packs for the current user"""
    user_id = get_user_id_from_request(semptify_uid)
    packs = module_hub.get_user_packs(user_id)

    if status:
        packs = [p for p in packs if p.status == status]

    return {
        "packs": [p.to_dict() for p in packs],
        "count": len(packs),
    }


@router.get("/packs/pending")
async def get_pending_packs(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get pending info packs that require user input"""
    user_id = get_user_id_from_request(semptify_uid)
    packs = module_hub.get_pending_packs(user_id)

    return {
        "packs": [p.to_dict() for p in packs],
        "count": len(packs),
        "message": f"You have {len(packs)} pack(s) requiring your input" if packs else "No pending packs",
    }


@router.get("/packs/{pack_id}")
async def get_pack(
    pack_id: str,
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get a specific info pack"""
    pack = module_hub.get_info_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")

    user_id = get_user_id_from_request(semptify_uid)
    if pack.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return pack.to_dict()


@router.post("/packs/{pack_id}/complete")
async def complete_pack(
    pack_id: str,
    body: CompletePackBody,
    semptify_uid: Optional[str] = Cookie(None),
):
    """Complete an info pack with user-provided data"""
    pack = module_hub.get_info_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")

    user_id = get_user_id_from_request(semptify_uid)
    if pack.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    completed_pack = await module_hub.complete_pack(pack_id, body.user_provided_data)
    if not completed_pack:
        raise HTTPException(status_code=500, detail="Failed to complete pack")

    return {
        "success": True,
        "pack": completed_pack.to_dict(),
        "message": "Info pack completed and sent to module",
    }


@router.get("/data")
async def get_user_data(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get centralized data for the current user"""
    user_id = get_user_id_from_request(semptify_uid)
    data = module_hub.get_user_data(user_id)

    return {
        "user_id": user_id,
        "data": data,
        "fields_count": len(data),
    }


@router.post("/request")
async def make_data_request(
    body: DataRequestBody,
    semptify_uid: Optional[str] = Cookie(None),
):
    """Make a data request from a module"""
    user_id = get_user_id_from_request(semptify_uid)

    try:
        request_type = RequestType(body.request_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request type. Valid types: {[r.value for r in RequestType]}"
        )

    try:
        module_type = ModuleType(body.requesting_module)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid module type. Valid types: {[m.value for m in ModuleType]}"
        )

    request = await module_hub.request_data(
        requesting_module=module_type,
        request_type=request_type,
        user_id=user_id,
        params=body.params or {},
    )

    return {
        "request_id": request.id,
        "status": request.status,
        "data": request.response_data,
        "error": request.error,
    }


@router.get("/log")
async def get_comm_log(
    semptify_uid: Optional[str] = Cookie(None),
    module: Optional[str] = Query(None, description="Filter by module"),
    limit: int = Query(100, ge=1, le=500, description="Max entries to return"),
):
    """Get communication log for debugging"""
    user_id = get_user_id_from_request(semptify_uid)

    log = module_hub.get_comm_log(
        user_id=user_id,
        module=module,
        limit=limit,
    )

    return {
        "log": log,
        "count": len(log),
    }


# =============================================================================
# CONVENIENCE ENDPOINTS FOR SPECIFIC DATA TYPES
# =============================================================================

@router.get("/case-info")
async def get_case_info(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get eviction case information for current user"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.EVICTION_DEFENSE,
        request_type=RequestType.GET_CASE_INFO,
        user_id=user_id,
    )

    return request.response_data or {}


@router.get("/lease-data")
async def get_lease_data(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get lease information for current user"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.DOCUMENTS,
        request_type=RequestType.GET_LEASE_DATA,
        user_id=user_id,
    )

    return request.response_data or {}


@router.get("/landlord-info")
async def get_landlord_info(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get landlord information for current user"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.DOCUMENTS,
        request_type=RequestType.GET_LANDLORD_INFO,
        user_id=user_id,
    )

    return request.response_data or {}


@router.get("/property-info")
async def get_property_info(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get property information for current user"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.DOCUMENTS,
        request_type=RequestType.GET_PROPERTY_INFO,
        user_id=user_id,
    )

    return request.response_data or {}


@router.get("/deadlines")
async def get_deadlines(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get calendar deadlines for current user"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.CALENDAR,
        request_type=RequestType.GET_CALENDAR_DEADLINES,
        user_id=user_id,
    )

    return request.response_data or {}


@router.get("/context")
async def get_user_context(
    semptify_uid: Optional[str] = Cookie(None),
):
    """Get full user context from context loop"""
    user_id = get_user_id_from_request(semptify_uid)

    request = await module_hub.request_data(
        requesting_module=ModuleType.CONTEXT_ENGINE,
        request_type=RequestType.GET_USER_CONTEXT,
        user_id=user_id,
    )

    return request.response_data or {}
