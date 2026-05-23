from fastapi import APIRouter
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/zoom-court/status")
async def zoom_court_status():
    return {"status": "disabled", "message": "Zoom court integration is not available in this deployment"}
