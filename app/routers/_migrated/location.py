"""
📍 Location Router - API Endpoints
==================================
REST API for location detection and state-specific resources.
Integrated with Positronic Brain for cross-module awareness.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.services.location_service import (
    LocationService,
    get_location_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/location", tags=["Location"])


# =============================================================================
# SCHEMAS
# =============================================================================

class LocationUpdate(BaseModel):
    """Request to update user's location"""
    state_code: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    county: Optional[str] = Field(None, description="County name")
    city: Optional[str] = Field(None, description="City name")
    zip_code: Optional[str] = Field(None, pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")
    detection_method: str = Field("user_input", description="How location was determined")
    latitude: Optional[float] = Field(None, description="Latitude for geolocation")
    longitude: Optional[float] = Field(None, description="Longitude for geolocation")


class LocationResponse(BaseModel):
    """Location information response"""
    state_code: str
    state_name: str
    county: Optional[str]
    city: Optional[str]
    zip_code: Optional[str]
    support_level: str
    detection_method: str


class StateInfoResponse(BaseModel):
    """State information response"""
    code: str
    name: str
    support_level: str
    tenant_rights_url: Optional[str]
    legal_aid_phone: Optional[str]
    eviction_timeline_days: int
    late_fee_limit: Optional[str]
    security_deposit_limit: Optional[str]


# =============================================================================
# HELPER: Get User ID
# =============================================================================

def get_user_id(request: Request) -> str:
    """
    Get user ID from request.
    Falls back to session ID or generates temporary ID.
    """
    user_id = None

    # Try to get from session (safely check if session middleware is installed)
    try:
        if "session" in request.scope:
            user_id = request.session.get("user_id")
    except (AssertionError, KeyError):
        pass

    if not user_id:
        # Try cookie
        user_id = request.cookies.get("semptify_user_id")

    if not user_id:
        # Generate temporary ID based on client IP (for demo purposes)
        try:
            client_ip = request.client.host if request.client else "unknown"
        except (AttributeError, TypeError):
            client_ip = "unknown"
        user_id = f"temp_{hash(client_ip) % 100000:05d}"

    return user_id
# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/current", response_model=LocationResponse)
async def get_current_location(
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    📍 Get current user location.
    
    Returns the user's stored location or default (Minnesota).
    """
    user_id = get_user_id(request)
    location = service.get_user_location(user_id)
    
    return LocationResponse(
        state_code=location.state_code,
        state_name=location.state_name,
        county=location.county,
        city=location.city,
        zip_code=location.zip_code,
        support_level=location.support_level.value,
        detection_method=location.detection_method,
    )


@router.post("/update", response_model=LocationResponse)
async def update_location(
    location_data: LocationUpdate,
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    📍 Update user's location.
    
    This is called by the frontend location detection script
    or when user manually selects their state.
    """
    user_id = get_user_id(request)
    
    location = service.set_user_location(
        user_id=user_id,
        state_code=location_data.state_code.upper(),
        county=location_data.county,
        city=location_data.city,
        zip_code=location_data.zip_code,
        detection_method=location_data.detection_method,
        latitude=location_data.latitude,
        longitude=location_data.longitude,
    )
    
    logger.info("📍 Location updated for %s...: %s", user_id[:8], location.state_code)

    # Emit brain event for location change
    try:
        from app.services.positronic_brain import get_brain, BrainEvent, EventType, ModuleType
        brain = get_brain()
        await brain.emit(BrainEvent(
            event_type=EventType.LOCATION_CHANGED,
            source_module=ModuleType.LOCATION,
            data={
                "state_code": location.state_code,
                "state_name": location.state_name,
                "county": location.county,
                "city": location.city,
                "support_level": location.support_level.value,
            },
            user_id=user_id,
        ))
    except (ImportError, AttributeError, RuntimeError) as e:
        logger.debug("Could not emit brain event: %s", e)

    return LocationResponse(
        state_code=location.state_code,
        state_name=location.state_name,
        county=location.county,
        city=location.city,
        zip_code=location.zip_code,
        support_level=location.support_level.value,
        detection_method=location.detection_method,
    )


@router.delete("/clear")
async def clear_location(
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    🗑️ Clear saved location (resets to default Minnesota).
    """
    user_id = get_user_id(request)
    service.clear_user_location(user_id)
    
    return {"success": True, "message": "Location cleared, defaulting to Minnesota"}


@router.get("/states")
async def get_supported_states(
    service: LocationService = Depends(get_location_service),
):
    """
    📋 Get list of supported states.
    
    Returns all states with their support levels:
    - full: Complete tenant rights database
    - partial: Some resources available
    - minimal: Basic info, references MN resources
    """
    return {
        "states": service.get_supported_states(),
        "default": "MN",
        "primary": "MN",
    }


@router.get("/state/{state_code}", response_model=StateInfoResponse)
async def get_state_info(
    state_code: str,
    service: LocationService = Depends(get_location_service),
):
    """
    📊 Get detailed information about a specific state.
    """
    state_info = service.get_state_info(state_code.upper())
    
    if not state_info:
        raise HTTPException(status_code=404, detail=f"State '{state_code}' not found")
    
    return StateInfoResponse(
        code=state_info.code,
        name=state_info.name,
        support_level=state_info.support_level.value,
        tenant_rights_url=state_info.tenant_rights_url,
        legal_aid_phone=state_info.legal_aid_phone,
        eviction_timeline_days=state_info.eviction_timeline_days,
        late_fee_limit=state_info.late_fee_limit,
        security_deposit_limit=state_info.security_deposit_limit,
    )


@router.get("/resources")
async def get_legal_resources(
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    ⚖️ Get legal resources based on user's location.
    
    Returns:
    - State-specific tenant rights links
    - Legal aid hotlines
    - County court information (if Minnesota)
    - Minnesota resources (always included as reference)
    """
    user_id = get_user_id(request)
    return service.get_legal_resources(user_id)


@router.get("/eviction-timeline")
async def get_eviction_timeline(
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    ⏱️ Get eviction timeline rules for user's state.
    
    Returns:
    - Answer period (days to respond to eviction)
    - Late fee limits
    - Security deposit rules
    """
    user_id = get_user_id(request)
    return service.get_eviction_timeline(user_id)


@router.get("/counties/mn")
async def get_mn_counties(
    service: LocationService = Depends(get_location_service),
):
    """
    🏛️ Get Minnesota counties with housing court information.
    """
    return {
        "counties": service.get_mn_counties(),
        "state": "MN",
    }


@router.get("/county/{county}")
async def get_county_info(
    county: str,
    state_code: str = "MN",
    service: LocationService = Depends(get_location_service),
):
    """
    🏛️ Get county-specific information (housing court, etc).
    
    Currently only supports Minnesota counties.
    """
    county_info = service.get_county_info(county, state_code.upper())
    
    if not county_info:
        raise HTTPException(
            status_code=404,
            detail=f"County '{county}' not found for state '{state_code}'"
        )
    
    return {
        "county": county,
        "state": state_code.upper(),
        **county_info,
    }


@router.get("/context")
async def get_location_context(
    request: Request,
    service: LocationService = Depends(get_location_service),
):
    """
    🧠 Get full location context for brain/mesh integration.
    
    This endpoint provides complete location data for
    cross-module workflows and the Positronic Brain.
    """
    user_id = get_user_id(request)
    return service.get_location_context(user_id)
