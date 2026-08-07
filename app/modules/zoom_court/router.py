import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/zoom-court/status")
async def zoom_court_status():
    return {"status": "enabled", "message": "Zoom court preparation tools available"}

@router.get("/api/zoom-court/tech-checklist")
async def tech_checklist():
    """Technical checklist for virtual court hearings."""
    return [
        {
            "item": "Stable internet connection",
            "description": "Test your connection speed before the hearing",
            "how_to_fix": "Use speedtest.net, connect via ethernet if possible",
            "critical": True
        },
        {
            "item": "Working camera and microphone",
            "description": "Test both in Zoom before the hearing starts",
            "how_to_fix": "Join Zoom test meeting at zoom.us/test",
            "critical": True
        },
        {
            "item": "Quiet, well-lit space",
            "description": "Ensure the judge can see and hear you clearly",
            "how_to_fix": "Find a private room, close windows, use lamp facing you",
            "critical": True
        },
        {
            "item": "Charged device or power cord",
            "description": "Your device must stay on for the entire hearing",
            "how_to_fix": "Plug in laptop or have charger nearby",
            "critical": True
        },
        {
            "item": "Zoom app installed and updated",
            "description": "Use the latest version for best compatibility",
            "how_to_fix": "Open Zoom, check for updates in settings",
            "critical": False
        },
        {
            "item": "Case documents ready",
            "description": "Have your documents open and accessible",
            "how_to_fix": "Open PDFs in separate window, print if needed",
            "critical": False
        },
        {
            "item": "Backup phone nearby",
            "description": "In case of technical failure",
            "how_to_fix": "Keep phone charged with court phone number saved",
            "critical": False
        },
        {
            "item": "Notebook and pen",
            "description": "Write down what the judge says",
            "how_to_fix": "Keep paper notes as backup to digital",
            "critical": False
        }
    ]

@router.get("/api/zoom-court/etiquette")
async def etiquette_rules():
    """Etiquette rules for virtual court hearings."""
    return [
        {
            "rule": "Dress as if appearing in person",
            "detail": "Court-appropriate attire shows respect for the process"
        },
        {
            "rule": "Mute microphone when not speaking",
            "detail": "Prevents background noise from disrupting the hearing"
        },
        {
            "rule": "Speak clearly and slowly",
            "detail": "Audio quality can be poor — enunciate and pace yourself"
        },
        {
            "rule": "Wait for your turn to speak",
            "detail": "The judge will indicate when you should respond"
        },
        {
            "rule": "Have your case number ready",
            "detail": "State your name and case number when asked"
        },
        {
            "rule": "Keep your camera on unless told otherwise",
            "detail": "Visual presence is expected in most hearings"
        },
        {
            "rule": "No eating or drinking during hearing",
            "detail": "Wait until the hearing is officially paused or concluded"
        },
        {
            "rule": "Be in a private space",
            "detail": "No children, pets, or other people in the background"
        },
        {
            "rule": "Address the judge as 'Your Honor'",
            "detail": "Standard courtroom courtesy applies virtually"
        },
        {
            "rule": "Take notes",
            "detail": "Write down deadlines, next hearing dates, and instructions"
        }
    ]
