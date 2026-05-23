from fastapi import APIRouter
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/zoom-court-prep/status")
async def zoom_court_prep_status():
    return {"status": "disabled", "message": "Zoom court prep is not available in this deployment"}
