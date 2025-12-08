"""
Public Exposure Router - API Endpoints for Press Releases & Media
=================================================================

Provides API access to press release generation and media campaign tools.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.core.security import require_user, StorageUser
from app.services.public_exposure import (
    get_public_exposure_service,
    MediaOutlet,
    ReleaseType,
)

router = APIRouter(prefix="/api/exposure", tags=["Public Exposure"])


# Request Models
class GeneratePressReleaseRequest(BaseModel):
    """Request to generate a press release"""
    property_address: str
    violations: List[str]
    contact_info: Dict[str, str]
    bundle_link: Optional[str] = None
    language: str = "en"
    landlord_name: Optional[str] = None
    tenant_count: Optional[int] = None
    fraud_findings: Optional[List[Dict[str, Any]]] = None
    quotes: Optional[List[Dict[str, str]]] = None


class GenerateMediaKitRequest(BaseModel):
    """Request to generate a media kit"""
    press_release_id: str
    timeline_events: List[Dict[str, str]]
    evidence_docs: List[str]
    target_outlets: Optional[List[str]] = None


# Response Models
class PressReleaseResponse(BaseModel):
    """Press release response"""
    id: str
    headline: str
    subheadline: Optional[str]
    lede: str
    body: List[str]
    quotes: List[Dict[str, str]]
    call_to_action: str
    boilerplate: str
    contact_info: Dict[str, str]
    bundle_link: Optional[str]
    created_at: str
    language: str


class MediaKitResponse(BaseModel):
    """Media kit response"""
    id: str
    press_release: Dict[str, Any]
    fact_sheet: Dict[str, Any]
    timeline: List[Dict[str, str]]
    evidence_summary: List[str]
    suggested_angles: List[str]
    media_targets: List[Dict[str, str]]
    social_media_posts: List[Dict[str, str]]
    created_at: str


@router.get("/health")
async def exposure_health_check():
    """Health check for public exposure service"""
    return {"status": "healthy", "service": "public_exposure"}


@router.post("/press-release", response_model=PressReleaseResponse)
async def generate_press_release(
    request: GeneratePressReleaseRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Generate a professional press release for tenant rights violations.
    
    Supports multiple languages:
    - en: English
    - es: Spanish
    - hmn: Hmong
    - so: Somali
    """
    service = get_public_exposure_service()
    
    try:
        release = await service.generate_press_release(
            property_address=request.property_address,
            violations=request.violations,
            contact_info=request.contact_info,
            bundle_link=request.bundle_link,
            language=request.language,
            landlord_name=request.landlord_name,
            tenant_count=request.tenant_count,
            fraud_findings=request.fraud_findings,
            quotes=request.quotes,
        )
        return release.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Press release generation failed: {str(e)}")


@router.get("/press-release/{release_id}")
async def get_press_release(
    release_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a press release by ID"""
    service = get_public_exposure_service()
    release = service.get_press_release(release_id)
    
    if not release:
        raise HTTPException(status_code=404, detail="Press release not found")
    
    return release.to_dict()


@router.get("/press-release/{release_id}/text")
async def get_press_release_text(
    release_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a press release as formatted text (ready to send)"""
    service = get_public_exposure_service()
    release = service.get_press_release(release_id)
    
    if not release:
        raise HTTPException(status_code=404, detail="Press release not found")
    
    return {"text": release.to_text(), "id": release_id}


@router.post("/media-kit", response_model=MediaKitResponse)
async def generate_media_kit(
    request: GenerateMediaKitRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Generate a complete media kit for a campaign.
    
    Includes:
    - Press release
    - Fact sheet
    - Timeline
    - Evidence summary
    - Suggested story angles
    - Media targets
    - Social media posts
    """
    service = get_public_exposure_service()
    
    # Get the press release
    release = service.get_press_release(request.press_release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Press release not found")
    
    try:
        kit = await service.generate_media_kit(
            press_release=release,
            timeline_events=request.timeline_events,
            evidence_docs=request.evidence_docs,
            target_outlets=request.target_outlets,
        )
        return kit.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Media kit generation failed: {str(e)}")


@router.get("/media-kit/{kit_id}")
async def get_media_kit(
    kit_id: str,
    user: StorageUser = Depends(require_user)
):
    """Get a media kit by ID"""
    service = get_public_exposure_service()
    kit = service.get_media_kit(kit_id)
    
    if not kit:
        raise HTTPException(status_code=404, detail="Media kit not found")
    
    return kit.to_dict()


@router.get("/media-outlets")
async def list_media_outlets(
    outlet_type: Optional[str] = Query(None, description="Filter by outlet type"),
    user: StorageUser = Depends(require_user)
):
    """
    List Minnesota media outlets for outreach.
    
    Outlet types:
    - local_news
    - investigative
    - community_paper
    - radio
    - online
    - social_media
    """
    service = get_public_exposure_service()
    
    if outlet_type:
        try:
            media_type = MediaOutlet(outlet_type)
            outlets = service.get_mn_media_outlets(media_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid outlet type: {outlet_type}. Valid types: {[t.value for t in MediaOutlet]}"
            )
    else:
        outlets = service.get_mn_media_outlets()
    
    return {"outlets": outlets, "count": len(outlets)}


@router.get("/languages")
async def list_supported_languages(
    user: StorageUser = Depends(require_user)
):
    """List supported languages for press releases"""
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish (Español)"},
            {"code": "hmn", "name": "Hmong"},
            {"code": "so", "name": "Somali (Soomaali)"},
        ]
    }


@router.get("/release-types")
async def list_release_types(
    user: StorageUser = Depends(require_user)
):
    """List available press release types"""
    return {
        "types": [
            {"type": rt.value, "name": rt.name.replace("_", " ").title()}
            for rt in ReleaseType
        ]
    }


@router.post("/generate-social-posts")
async def generate_social_posts(
    headline: str = Query(..., description="The headline or main topic"),
    link: Optional[str] = Query(None, description="Link to include"),
    hashtags: Optional[List[str]] = Query(default=["TenantRights", "HousingJustice"]),
    user: StorageUser = Depends(require_user)
):
    """Generate social media posts for different platforms"""
    hashtag_str = " ".join(f"#{h}" for h in hashtags) if hashtags else ""
    
    return {
        "posts": [
            {
                "platform": "Twitter/X",
                "post": f"🏠 {headline} {link or ''} {hashtag_str}".strip(),
                "character_count": len(f"🏠 {headline} {link or ''} {hashtag_str}".strip()),
            },
            {
                "platform": "Facebook",
                "post": f"{headline}\n\nLearn more and support tenant rights. {link or ''}\n\n{hashtag_str}".strip(),
            },
            {
                "platform": "Instagram",
                "post": f"🏠 {headline}\n\nTenants deserve safe housing.\n\n{hashtag_str}".strip(),
            },
            {
                "platform": "LinkedIn",
                "post": f"{headline}\n\nHousing advocacy and tenant rights matter. {link or ''}".strip(),
            },
        ]
    }
