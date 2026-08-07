"""
State Laws API Router
Provides dynamic state law information with MN as the complete reference implementation.
"""
# Migrated from app/routers/state_laws.py into the state_laws SDK module.
# All imports remain absolute since state_laws is a CORE module.

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.core.capabilities import require_capability

router = APIRouter(
    prefix="/api/states",
    tags=["State Laws"],
    dependencies=[Depends(require_capability("app.modules.state_laws.router"))],
)

# Load state laws data
DATA_PATH = os.path.join(os.path.dirname(__file__), "../../static/data/state-laws.json")
_state_laws_cache = None


def _load_state_laws():
    """Load state laws from JSON file with caching."""
    global _state_laws_cache
    if _state_laws_cache is None:
        try:
            with open(DATA_PATH, encoding='utf-8') as f:
                _state_laws_cache = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="State laws data file not found")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid state laws data format")
    return _state_laws_cache


class StateBasic(BaseModel):
    """Basic state info for listing."""
    code: str = Field(..., description="Two-letter state code")
    name: str = Field(..., description="Full state name")
    status: str = Field(..., description="Data completeness: 'complete' or 'stub'")


class StateDetails(BaseModel):
    """Full state housing law details."""
    code: str
    name: str
    nickname: str | None = None
    status: str
    housing_laws: dict | None = None
    notice_requirements: dict | None = None
    security_deposit: dict | None = None
    rent_control: dict | None = None
    repairs: dict | None = None
    landlord_entry: dict | None = None
    eviction: dict | None = None
    discrimination: dict | None = None
    legal_aid: list | None = None
    government_resources: list | None = None
    forms_templates: list | None = None
    special_programs: dict | None = None
    stub_url: str | None = None
    notes: str | None = None


@router.get("/", response_model=dict)
async def list_states():
    """
    List all states with basic information.
    
    Returns:
        List of states with code, name, and data completeness status.
    """
    data = _load_state_laws()
    states = []
    for code, info in data.get("states", {}).items():
        states.append({
            "code": code,
            "name": info.get("name"),
            "status": info.get("status", "stub"),
            "has_complete_data": info.get("status") == "complete"
        })

    return {
        "count": len(states),
        "complete_count": sum(1 for s in states if s["has_complete_data"]),
        "stub_count": sum(1 for s in states if not s["has_complete_data"]),
        "states": sorted(states, key=lambda x: x["name"])
    }


@router.get("/{state_code}", response_model=StateDetails)
async def get_state(state_code: str):
    """
    Get detailed housing law information for a specific state.
    
    Args:
        state_code: Two-letter state code (e.g., 'MN', 'CA')
    
    Returns:
        Complete state housing law details or stub information.
    """
    data = _load_state_laws()
    state = data.get("states", {}).get(state_code.upper())

    if not state:
        raise HTTPException(status_code=404, detail=f"State '{state_code}' not found")

    return state


@router.get("/nearby/search")
async def find_nearby_states(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    limit: int = Query(5, ge=1, le=10, description="Number of nearby states to return")
):
    """
    Find states geographically nearest to the provided coordinates.
    
    This is a simplified implementation that returns likely nearby states
    based on US geography. For production, would use proper geocoding.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude  
        limit: Maximum states to return
    
    Returns:
        List of nearby state codes sorted by estimated proximity.
    """
    # Simplified US state centroid coordinates for rough proximity
    state_centroids = {
        "MN": {"lat": 46.4, "lon": -94.6, "name": "Minnesota"},
        "WI": {"lat": 44.7, "lon": -89.9, "name": "Wisconsin"},
        "IA": {"lat": 42.0, "lon": -93.2, "name": "Iowa"},
        "ND": {"lat": 47.5, "lon": -99.7, "name": "North Dakota"},
        "SD": {"lat": 44.5, "lon": -100.2, "name": "South Dakota"},
        "MI": {"lat": 44.3, "lon": -85.6, "name": "Michigan"},
        "IL": {"lat": 40.0, "lon": -89.1, "name": "Illinois"},
        "MO": {"lat": 38.3, "lon": -92.4, "name": "Missouri"},
        "CA": {"lat": 36.7, "lon": -119.4, "name": "California"},
        "NY": {"lat": 43.0, "lon": -75.0, "name": "New York"},
        "TX": {"lat": 31.0, "lon": -99.9, "name": "Texas"},
        "FL": {"lat": 27.9, "lon": -81.7, "name": "Florida"},
        "WA": {"lat": 47.4, "lon": -121.4, "name": "Washington"},
        "OR": {"lat": 43.9, "lon": -120.5, "name": "Oregon"},
        "CO": {"lat": 39.0, "lon": -105.5, "name": "Colorado"},
        "AZ": {"lat": 34.2, "lon": -111.6, "name": "Arizona"},
        "MA": {"lat": 42.4, "lon": -72.0, "name": "Massachusetts"},
        "PA": {"lat": 41.2, "lon": -77.8, "name": "Pennsylvania"},
        "OH": {"lat": 40.4, "lon": -82.7, "name": "Ohio"},
        "NC": {"lat": 35.7, "lon": -79.8, "name": "North Carolina"},
        "GA": {"lat": 32.6, "lon": -83.4, "name": "Georgia"},
        "VA": {"lat": 37.5, "lon": -78.8, "name": "Virginia"},
        "NJ": {"lat": 40.0, "lon": -74.7, "name": "New Jersey"},
    }

    # Calculate rough distances
    import math

    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate rough distance between two points."""
        R = 3959  # Earth's radius in miles
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    distances = []
    for code, centroid in state_centroids.items():
        dist = haversine_distance(lat, lon, centroid["lat"], centroid["lon"])
        distances.append({
            "code": code,
            "name": centroid["name"],
            "distance_miles": round(dist, 1)
        })

    distances.sort(key=lambda x: x["distance_miles"])

    return {
        "query": {"latitude": lat, "longitude": lon},
        "nearby_states": distances[:limit]
    }


@router.get("/detect/location")
async def detect_user_state(request: Request):
    """
    Detect user's likely state based on IP geolocation.
    
    Uses ip-api.com free service for IP geolocation.
    Falls back to MN if detection fails.
    
    Returns:
        Detected or default state information.
    """
    try:
        import httpx
        client_ip = request.client.host if request.client else "127.0.0.1"

        # Skip localhost for dev
        if client_ip in ("127.0.0.1", "localhost", "::1"):
            return {
                "method": "default",
                "detected_state": "MN",
                "state_name": "Minnesota",
                "confidence": "medium",
                "message": "Local development detected. Defaulting to Minnesota.",
                "manual_selection_url": "/library.html#state-selector"
            }

        async with httpx.AsyncClient(timeout=3.0) as http_client:
            response = await http_client.get(f"http://ip-api.com/json/{client_ip}")
            if response.status_code == 200:
                data = response.json()
                state_code = data.get("regionCode", "MN")
                state_name = data.get("region", "Minnesota")
                return {
                    "method": "ip_geolocation",
                    "detected_state": state_code,
                    "state_name": state_name,
                    "confidence": "high",
                    "message": "Detected location based on your IP address.",
                    "manual_selection_url": "/library.html#state-selector"
                }
    except Exception as e:
        logger.warning(f"IP geolocation failed: {e}")

    # Fallback to MN
    return {
        "method": "default",
        "detected_state": "MN",
        "state_name": "Minnesota",
        "confidence": "medium",
        "message": "Could not detect location. Defaulting to Minnesota.",
        "manual_selection_url": "/library.html#state-selector"
    }
