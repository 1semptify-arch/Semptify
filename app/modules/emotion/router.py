"""
Emotion Engine API Router
=========================
Endpoints to track emotional state and get adaptive UI configurations.
"""

from fastapi import APIRouter, Request, Query
from typing import Dict, Any, Optional, List
import logging

from app.services.emotion_engine import (
    emotion_engine,
    EmotionalTrigger,
    get_user_emotional_state,
    process_user_trigger,
    get_adaptive_dashboard,
    get_ui_adaptation
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/emotion", tags=["Emotion Engine"])


@router.get("/state")
async def get_emotional_state(request: Request) -> Dict[str, Any]:
    """
    Get current emotional state for user.
    
    Returns 7-dimensional emotional state plus composite scores.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    state = get_user_emotional_state(user_id)
    return {
        "success": True,
        "user_id": user_id,
        "emotional_state": state
    }


@router.post("/trigger")
async def record_trigger(
    request: Request,
    trigger: str = Query(..., description="Trigger event name"),
    days_until_deadline: Optional[int] = Query(None),
    days_until_court: Optional[int] = Query(None)
) -> Dict[str, Any]:
    """
    Record an emotional trigger event.
    
    Triggers:
    - task_completed, evidence_uploaded, violation_found
    - deadline_approaching, deadline_missed, confusion_detected
    - rapid_page_switching, long_inactivity, error_encountered
    - court_date_near, repeated_help_clicks, abandoned_task
    - session_start, feature_explored, document_viewed
    - win_milestone, support_connected, deadline_met, document_organized
    - help_accessed
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    context = {}
    if days_until_deadline is not None:
        context['days_until_deadline'] = days_until_deadline
    if days_until_court is not None:
        context['days_until_court'] = days_until_court
    
    result = process_user_trigger(user_id, trigger, context)
    
    if 'error' in result:
        return {"success": False, "error": result['error']}
    
    return {
        "success": True,
        "trigger": trigger,
        "new_state": result
    }


@router.get("/dashboard-config")
async def get_dashboard_configuration(request: Request) -> Dict[str, Any]:
    """
    Get full adaptive dashboard configuration.
    
    Returns:
    - emotional_state: 7 dimensions + composites
    - ui_adaptation: How to adjust the UI
    - messages: Personalized greeting, encouragement, prompts
    - dashboard_mode: crisis|focused|guided|flow|power
    - visible_sections: Which sections to show
    - color_scheme: Emotionally-appropriate colors
    - animation_config: Animation settings
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    config = get_adaptive_dashboard(user_id)
    return {
        "success": True,
        "user_id": user_id,
        "config": config
    }


@router.get("/ui-adaptation")
async def get_ui_settings(request: Request) -> Dict[str, Any]:
    """
    Get UI adaptation settings only.
    
    Returns settings for content density, visual presentation,
    interaction style, tone, navigation, and actions.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    adaptation = get_ui_adaptation(user_id)
    return {
        "success": True,
        "adaptation": adaptation
    }


@router.get("/suggested-action")
async def get_suggested_action(request: Request) -> Dict[str, Any]:
    """
    Get the emotionally-appropriate next action for user.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    
    # Get available actions (would come from case context in real app)
    # For now, return mock suggestion based on state
    state = emotion_engine.get_state(user_id)
    messages = emotion_engine.get_personalized_message(user_id)
    adaptation = emotion_engine.calculate_ui_adaptation(user_id)
    
    return {
        "success": True,
        "dominant_emotion": state.dominant_emotion,
        "crisis_level": round(state.crisis_level, 2),
        "suggested_action": adaptation.suggested_action,
        "action_prompt": messages['action_prompt'],
        "encouragement": messages['encouragement']
    }


@router.get("/triggers")
async def list_available_triggers() -> Dict[str, Any]:
    """
    List all available emotional triggers.
    """
    triggers = {
        "positive": [
            {"name": "task_completed", "description": "User completed a task"},
            {"name": "evidence_uploaded", "description": "User uploaded evidence"},
            {"name": "violation_found", "description": "AI found a violation in their favor"},
            {"name": "deadline_met", "description": "User met a deadline"},
            {"name": "document_organized", "description": "User organized documents"},
            {"name": "help_accessed", "description": "User accessed help"},
            {"name": "win_milestone", "description": "Major win or milestone"},
            {"name": "support_connected", "description": "Connected with support resource"}
        ],
        "negative": [
            {"name": "deadline_approaching", "description": "Deadline coming soon"},
            {"name": "deadline_missed", "description": "User missed a deadline"},
            {"name": "confusion_detected", "description": "User appears confused"},
            {"name": "rapid_page_switching", "description": "User switching pages rapidly"},
            {"name": "long_inactivity", "description": "User inactive for extended period"},
            {"name": "error_encountered", "description": "User hit an error"},
            {"name": "court_date_near", "description": "Court date approaching"},
            {"name": "repeated_help_clicks", "description": "User clicking help repeatedly"},
            {"name": "abandoned_task", "description": "User abandoned a task"}
        ],
        "neutral": [
            {"name": "session_start", "description": "User started a session"},
            {"name": "feature_explored", "description": "User explored a feature"},
            {"name": "document_viewed", "description": "User viewed a document"}
        ]
    }
    return {
        "success": True,
        "triggers": triggers
    }


@router.post("/simulate-scenario")
async def simulate_emotional_scenario(
    request: Request,
    scenario: str = Query(..., description="Scenario to simulate: crisis|hopeful|overwhelmed|determined|confused")
) -> Dict[str, Any]:
    """
    Simulate an emotional scenario for testing/demo.
    Sets user's emotional state to match scenario.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    state = emotion_engine.get_state(user_id)
    
    scenarios = {
        "crisis": {
            "intensity": 0.15,    # Panicking
            "clarity": 0.25,      # Confused
            "confidence": 0.2,    # Hopeless
            "momentum": 0.2,      # Stuck
            "overwhelm": 0.15,    # Drowning
            "trust": 0.4,         # Somewhat trusting
            "resolve": 0.35       # Wavering
        },
        "hopeful": {
            "intensity": 0.6,
            "clarity": 0.65,
            "confidence": 0.7,
            "momentum": 0.65,
            "overwhelm": 0.6,
            "trust": 0.7,
            "resolve": 0.75
        },
        "overwhelmed": {
            "intensity": 0.3,
            "clarity": 0.4,
            "confidence": 0.45,
            "momentum": 0.35,
            "overwhelm": 0.2,     # Very overwhelmed
            "trust": 0.5,
            "resolve": 0.5
        },
        "determined": {
            "intensity": 0.5,
            "clarity": 0.7,
            "confidence": 0.65,
            "momentum": 0.6,
            "overwhelm": 0.6,
            "trust": 0.7,
            "resolve": 0.9       # Very determined
        },
        "confused": {
            "intensity": 0.45,
            "clarity": 0.15,     # Very confused
            "confidence": 0.35,
            "momentum": 0.3,
            "overwhelm": 0.35,
            "trust": 0.4,
            "resolve": 0.5
        },
        "winning": {
            "intensity": 0.8,
            "clarity": 0.85,
            "confidence": 0.9,
            "momentum": 0.9,
            "overwhelm": 0.85,
            "trust": 0.85,
            "resolve": 0.95
        }
    }
    
    if scenario not in scenarios:
        return {
            "success": False,
            "error": f"Unknown scenario. Available: {list(scenarios.keys())}"
        }
    
    # Apply scenario
    for dim, value in scenarios[scenario].items():
        setattr(state, dim, value)
    
    # Return full config
    config = emotion_engine.get_dashboard_config(user_id)
    
    return {
        "success": True,
        "scenario": scenario,
        "config": config
    }


@router.get("/history")
async def get_emotional_history(
    request: Request,
    limit: int = Query(20, le=100)
) -> Dict[str, Any]:
    """
    Get recent emotional trigger history for user.
    """
    user_id = request.cookies.get("semptify_uid", "anonymous")
    history = emotion_engine.user_history.get(user_id, [])
    
    return {
        "success": True,
        "user_id": user_id,
        "history": history[-limit:] if history else [],
        "total_events": len(history)
    }
