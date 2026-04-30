"""
📍 Location Service - Integrated with Positronic Brain
======================================================
Manages user location context for state-specific tenant rights,
agencies, and legal resources.

Minnesota-focused with support for neighboring states.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# LOCATION DATA STRUCTURES
# =============================================================================

class SupportLevel(str, Enum):
    """Level of support available for a state"""
    FULL = "full"           # Full tenant rights database, all features
    PARTIAL = "partial"     # Some resources, may reference MN law
    MINIMAL = "minimal"     # Basic info only, defaults to MN resources


@dataclass
class StateInfo:
    """Information about a supported state"""
    code: str
    name: str
    support_level: SupportLevel
    tenant_rights_url: Optional[str] = None
    housing_court_info: Optional[str] = None
    legal_aid_phone: Optional[str] = None
    attorney_general_url: Optional[str] = None
    eviction_timeline_days: int = 14  # Default answer period
    late_fee_limit: Optional[str] = None
    security_deposit_limit: Optional[str] = None


@dataclass
class UserLocation:
    """User's location context"""
    state_code: str
    state_name: str
    county: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    support_level: SupportLevel = SupportLevel.MINIMAL
    detected_at: datetime = field(default_factory=datetime.utcnow)
    detection_method: str = "default"  # "geolocation", "user_input", "default"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_code": self.state_code,
            "state_name": self.state_name,
            "county": self.county,
            "city": self.city,
            "zip_code": self.zip_code,
            "support_level": self.support_level.value,
            "detected_at": self.detected_at.isoformat(),
            "detection_method": self.detection_method,
        }


# =============================================================================
# STATE DATABASE
# =============================================================================

STATES_INFO: Dict[str, StateInfo] = {
    # FULL SUPPORT - Minnesota (Primary)
    "MN": StateInfo(
        code="MN",
        name="Minnesota",
        support_level=SupportLevel.FULL,
        tenant_rights_url="https://www.ag.state.mn.us/consumer/handbooks/lt/default.asp",
        housing_court_info="Minnesota Housing Court - varies by county",
        legal_aid_phone="1-888-743-5327",  # Legal Aid MN
        attorney_general_url="https://www.ag.state.mn.us/",
        eviction_timeline_days=14,
        late_fee_limit="8% of rent or $12, whichever is greater (Minn. Stat. § 504B.177)",
        security_deposit_limit="No statutory limit, but interest required after 12 months",
    ),
    
    # PARTIAL SUPPORT - Neighboring states
    "WI": StateInfo(
        code="WI",
        name="Wisconsin",
        support_level=SupportLevel.PARTIAL,
        tenant_rights_url="https://datcp.wi.gov/Pages/Publications/LandlordTenantGuide.aspx",
        legal_aid_phone="1-855-947-2529",  # WI Legal Action
        eviction_timeline_days=5,  # Much shorter than MN!
        late_fee_limit="No statutory limit",
        security_deposit_limit="No limit if lease > 1 year",
    ),
    "IA": StateInfo(
        code="IA",
        name="Iowa",
        support_level=SupportLevel.PARTIAL,
        tenant_rights_url="https://www.iowalegalaid.org/resource/tenant-rights",
        legal_aid_phone="1-800-532-1275",  # Iowa Legal Aid
        eviction_timeline_days=3,  # Very short!
        late_fee_limit="No statutory limit, must be reasonable",
        security_deposit_limit="2 months rent",
    ),
    "SD": StateInfo(
        code="SD",
        name="South Dakota",
        support_level=SupportLevel.PARTIAL,
        tenant_rights_url="https://consumer.sd.gov/landlord-tenant.aspx",
        legal_aid_phone="1-800-658-2297",  # East River Legal
        eviction_timeline_days=3,
        late_fee_limit="No statutory limit",
        security_deposit_limit="1 month rent (unfurnished)",
    ),
    "ND": StateInfo(
        code="ND",
        name="North Dakota",
        support_level=SupportLevel.MINIMAL,
        tenant_rights_url="https://www.ag.nd.gov/consumer",
        legal_aid_phone="1-800-634-5263",  # Legal Services of ND
        eviction_timeline_days=3,
        late_fee_limit="No statutory limit",
        security_deposit_limit="1 month rent (unfurnished)",
    ),
}

# Minnesota counties with specific housing court info
MN_COUNTIES: Dict[str, Dict[str, str]] = {
    "Hennepin": {
        "court": "Hennepin County Housing Court",
        "address": "300 S 6th St, Minneapolis, MN 55487",
        "phone": "(612) 348-2040",
        "hours": "8:00 AM - 4:30 PM",
    },
    "Ramsey": {
        "court": "Ramsey County Housing Court",
        "address": "15 W Kellogg Blvd, St. Paul, MN 55102",
        "phone": "(651) 266-8265",
        "hours": "8:00 AM - 4:30 PM",
    },
    "Dakota": {
        "court": "Dakota County District Court",
        "address": "1560 Highway 55, Hastings, MN 55033",
        "phone": "(651) 438-4325",
        "hours": "8:00 AM - 4:30 PM",
        "notes": "Also serves Apple Valley, Burnsville, Eagan, Lakeville",
    },
    "Anoka": {
        "court": "Anoka County District Court",
        "address": "2100 3rd Ave, Anoka, MN 55303",
        "phone": "(763) 422-7300",
        "hours": "8:00 AM - 4:30 PM",
    },
    "Washington": {
        "court": "Washington County District Court",
        "address": "14949 62nd St N, Stillwater, MN 55082",
        "phone": "(651) 430-6300",
        "hours": "8:00 AM - 4:30 PM",
    },
    "Scott": {
        "court": "Scott County District Court",
        "address": "200 4th Ave W, Shakopee, MN 55379",
        "phone": "(952) 496-8200",
        "hours": "8:00 AM - 4:30 PM",
    },
    "Carver": {
        "court": "Carver County District Court",
        "address": "604 E 4th St, Chaska, MN 55318",
        "phone": "(952) 361-1420",
        "hours": "8:00 AM - 4:30 PM",
    },
}


# =============================================================================
# LOCATION SERVICE
# =============================================================================

class LocationService:
    """
    Location awareness service integrated with Positronic Brain.
    
    Provides:
    - User location detection and storage
    - State-specific tenant rights info
    - County-specific court information
    - Legal resource recommendations
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        
        # User location cache: user_id -> UserLocation
        self.user_locations: Dict[str, UserLocation] = {}
        
        # Default location (Minnesota)
        self.default_state = "MN"
        
        logger.info("📍 Location Service initialized - Minnesota-focused tenant rights")

    # =========================================================================
    # LOCATION MANAGEMENT
    # =========================================================================

    def set_user_location(
        self,
        user_id: str,
        state_code: str,
        county: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        detection_method: str = "user_input",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> UserLocation:
        """Set/update user's location"""
        
        state_info = self.get_state_info(state_code)
        
        location = UserLocation(
            state_code=state_code.upper(),
            state_name=state_info.name if state_info else state_code,
            county=county,
            city=city,
            zip_code=zip_code,
            support_level=state_info.support_level if state_info else SupportLevel.MINIMAL,
            detection_method=detection_method,
            latitude=latitude,
            longitude=longitude,
        )
        
        self.user_locations[user_id] = location

        logger.info("📍 Location set for user %s...: %s, %s", user_id[:8], state_code, county or 'no county')

        return location

    def get_user_location(self, user_id: str) -> UserLocation:
        """Get user's location (defaults to Minnesota)"""
        
        if user_id in self.user_locations:
            return self.user_locations[user_id]
        
        # Return default Minnesota location
        return UserLocation(
            state_code=self.default_state,
            state_name="Minnesota",
            support_level=SupportLevel.FULL,
            detection_method="default",
        )

    def clear_user_location(self, user_id: str):
        """Clear user's location (will default to MN)"""
        if user_id in self.user_locations:
            del self.user_locations[user_id]
            logger.info("📍 Location cleared for user %s...", user_id[:8])

    # =========================================================================
    # STATE INFORMATION
    # =========================================================================

    def get_state_info(self, state_code: str) -> Optional[StateInfo]:
        """Get information about a state"""
        return STATES_INFO.get(state_code.upper())

    def get_supported_states(self) -> List[Dict[str, Any]]:
        """Get list of all supported states"""
        return [
            {
                "code": info.code,
                "name": info.name,
                "support_level": info.support_level.value,
            }
            for info in STATES_INFO.values()
        ]

    def is_state_fully_supported(self, state_code: str) -> bool:
        """Check if state has full support"""
        info = self.get_state_info(state_code)
        return info is not None and info.support_level == SupportLevel.FULL

    # =========================================================================
    # COUNTY INFORMATION (Minnesota)
    # =========================================================================

    def get_county_info(self, county: str, state_code: str = "MN") -> Optional[Dict[str, str]]:
        """Get county-specific information (Minnesota only for now)"""
        if state_code.upper() != "MN":
            return None
        
        # Normalize county name
        county_normalized = county.replace(" County", "").strip().title()
        
        return MN_COUNTIES.get(county_normalized)

    def get_mn_counties(self) -> List[str]:
        """Get list of Minnesota counties with court info"""
        return list(MN_COUNTIES.keys())

    # =========================================================================
    # LEGAL RESOURCES BY LOCATION
    # =========================================================================

    def get_legal_resources(self, user_id: str) -> Dict[str, Any]:
        """Get legal resources based on user's location"""
        
        location = self.get_user_location(user_id)
        state_info = self.get_state_info(location.state_code)
        
        resources = {
            "state": location.state_code,
            "state_name": location.state_name,
            "support_level": location.support_level.value,
            "resources": [],
        }
        
        if state_info:
            if state_info.legal_aid_phone:
                resources["resources"].append({
                    "name": "Legal Aid Hotline",
                    "phone": state_info.legal_aid_phone,
                    "type": "phone",
                })
            
            if state_info.tenant_rights_url:
                resources["resources"].append({
                    "name": "Tenant Rights Guide",
                    "url": state_info.tenant_rights_url,
                    "type": "website",
                })
            
            if state_info.attorney_general_url:
                resources["resources"].append({
                    "name": "Attorney General Consumer Resources",
                    "url": state_info.attorney_general_url,
                    "type": "website",
                })
        
        # Add county-specific info if Minnesota
        if location.state_code == "MN" and location.county:
            county_info = self.get_county_info(location.county)
            if county_info:
                resources["county_court"] = county_info
        
        # Add Minnesota-specific resources (always helpful as reference)
        if location.state_code == "MN" or location.support_level != SupportLevel.FULL:
            resources["mn_resources"] = {
                "homeline": {
                    "name": "HOME Line Minnesota",
                    "phone": "612-728-5767",
                    "url": "https://homelinemn.org/",
                    "description": "Free tenant hotline and legal assistance",
                },
                "legal_aid_mn": {
                    "name": "Legal Aid Minnesota",
                    "phone": "1-888-743-5327",
                    "url": "https://www.mylegalaid.org/",
                    "description": "Free legal services for low-income Minnesotans",
                },
            }
        
        return resources

    def get_eviction_timeline(self, user_id: str) -> Dict[str, Any]:
        """Get eviction timeline based on user's state"""
        
        location = self.get_user_location(user_id)
        state_info = self.get_state_info(location.state_code) or STATES_INFO["MN"]
        
        return {
            "state": location.state_code,
            "answer_period_days": state_info.eviction_timeline_days,
            "late_fee_limit": state_info.late_fee_limit,
            "security_deposit_limit": state_info.security_deposit_limit,
            "note": f"Based on {state_info.name} law" if state_info else "Based on Minnesota law (default)",
        }

    # =========================================================================
    # BRAIN INTEGRATION
    # =========================================================================

    def get_location_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get full location context for brain/mesh integration.
        This is what gets passed to other modules.
        """
        location = self.get_user_location(user_id)
        state_info = self.get_state_info(location.state_code)
        
        return {
            "location": location.to_dict(),
            "state_info": {
                "code": state_info.code if state_info else "MN",
                "name": state_info.name if state_info else "Minnesota",
                "support_level": state_info.support_level.value if state_info else "minimal",
                "eviction_days": state_info.eviction_timeline_days if state_info else 14,
                "late_fee_limit": state_info.late_fee_limit if state_info else None,
            } if state_info else None,
            "is_primary_state": location.state_code == "MN",
            "legal_resources": self.get_legal_resources(user_id),
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

location_service = LocationService()


def get_location_service() -> LocationService:
    """Dependency injection for FastAPI"""
    return location_service


# =============================================================================
# BRAIN ACTION HANDLERS
# =============================================================================

async def handle_get_location(user_id: str, _params: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Brain action handler: Get user location"""
    return location_service.get_location_context(user_id)


async def handle_set_location(user_id: str, params: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Brain action handler: Set user location"""
    location = location_service.set_user_location(
        user_id=user_id,
        state_code=params.get("state_code", "MN"),
        county=params.get("county"),
        city=params.get("city"),
        zip_code=params.get("zip_code"),
        detection_method=params.get("detection_method", "brain_action"),
    )
    return {"location": location.to_dict(), "success": True}


async def handle_get_legal_resources(user_id: str, _params: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Brain action handler: Get legal resources for location"""
    return location_service.get_legal_resources(user_id)


async def handle_get_eviction_timeline(user_id: str, _params: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Brain action handler: Get eviction timeline for state"""
    return location_service.get_eviction_timeline(user_id)


# =============================================================================
# REGISTER WITH POSITRONIC MESH
# =============================================================================

def register_with_mesh():
    """Register location service actions with the Positronic Mesh"""
    try:
        from app.core.positronic_mesh import positronic_mesh
        
        positronic_mesh.register_action(
            module="location",
            action="get_location",
            handler=handle_get_location,
            description="Get user's location context",
            produces=["location", "state_info", "legal_resources"],
        )
        
        positronic_mesh.register_action(
            module="location",
            action="set_location",
            handler=handle_set_location,
            description="Set user's location",
            required_params=["state_code"],
            optional_params=["county", "city", "zip_code"],
            produces=["location"],
        )
        
        positronic_mesh.register_action(
            module="location",
            action="get_legal_resources",
            handler=handle_get_legal_resources,
            description="Get legal resources for user's location",
            produces=["legal_resources"],
        )
        
        positronic_mesh.register_action(
            module="location",
            action="get_eviction_timeline",
            handler=handle_get_eviction_timeline,
            description="Get eviction timeline rules for user's state",
            produces=["eviction_timeline"],
        )
        
        logger.info("📍 Location service registered with Positronic Mesh")
        
    except ImportError:
        logger.warning("Positronic Mesh not available, location service running standalone")


# Auto-register on import
register_with_mesh()
