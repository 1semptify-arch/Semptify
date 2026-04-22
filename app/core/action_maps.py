"""
Action Maps — Quick Action to Route/Module Binding
====================================================

Maps quick actions (buttons, links) to their destinations.
Integrates with PageContracts and telemetry for consistent UX.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from enum import Enum, auto


class ActionType(Enum):
    """Types of actions available."""
    NAVIGATE = auto()      # Go to another page
    TRIGGER = auto()       # Trigger a workflow
    OPEN = auto()          # Open modal/panel
    DOWNLOAD = auto()      # Download file
    SHARE = auto()         # Share content
    EXTERNAL = auto()      # External link


@dataclass
class QuickAction:
    """
    Definition of a quick action button/link.
    
    Usage:
        action = QuickAction(
            action_id="view_deadlines",
            label="View Deadlines",
            icon="calendar",
            action_type=ActionType.NAVIGATE,
            target="/calendar",
            telemetry_event="quick_action_clicked",
        )
    """
    action_id: str
    label: str
    icon: Optional[str] = None
    action_type: ActionType = ActionType.NAVIGATE
    target: Optional[str] = None  # URL, route, or workflow ID
    target_params: Optional[Dict[str, Any]] = None
    telemetry_event: Optional[str] = None
    required_roles: Optional[List[str]] = None
    confirmation_prompt: Optional[str] = None  # If set, show confirmation
    disabled_states: Optional[List[str]] = None  # Page states where disabled


# =============================================================================
# DASHBOARD QUICK ACTIONS
# =============================================================================

DASHBOARD_QUICK_ACTIONS: Dict[str, QuickAction] = {
    "view_deadlines": QuickAction(
        action_id="view_deadlines",
        label="View Deadlines",
        icon="calendar",
        action_type=ActionType.NAVIGATE,
        target="/calendar",
        telemetry_event="quick_action_clicked",
    ),
    "view_documents": QuickAction(
        action_id="view_documents",
        label="My Documents",
        icon="folder",
        action_type=ActionType.NAVIGATE,
        target="/documents",
        telemetry_event="quick_action_clicked",
    ),
    "upload_document": QuickAction(
        action_id="upload_document",
        label="Upload Document",
        icon="upload",
        action_type=ActionType.NAVIGATE,
        target="/vault",
        target_params={"action": "upload"},
        telemetry_event="quick_action_clicked",
    ),
    "prepare_answer": QuickAction(
        action_id="prepare_answer",
        label="Prepare Answer",
        icon="file-text",
        action_type=ActionType.NAVIGATE,
        target="/eviction-answer",
        telemetry_event="quick_action_clicked",
        required_roles=["user", "advocate", "legal"],
    ),
    "view_timeline": QuickAction(
        action_id="view_timeline",
        label="Case Timeline",
        icon="clock",
        action_type=ActionType.NAVIGATE,
        target="/timeline",
        telemetry_event="quick_action_clicked",
    ),
    "court_prep": QuickAction(
        action_id="court_prep",
        label="Court Prep",
        icon="briefcase",
        action_type=ActionType.NAVIGATE,
        target="/court-packet",
        telemetry_event="quick_action_clicked",
        required_roles=["user", "advocate", "legal"],
    ),
    "hearing_prep": QuickAction(
        action_id="hearing_prep",
        label="Hearing Prep",
        icon="mic",
        action_type=ActionType.NAVIGATE,
        target="/hearing-prep",
        telemetry_event="quick_action_clicked",
        required_roles=["user", "advocate", "legal"],
    ),
    "get_help": QuickAction(
        action_id="get_help",
        label="Get Help",
        icon="help-circle",
        action_type=ActionType.NAVIGATE,
        target="/help",
        telemetry_event="quick_action_clicked",
    ),
    "emergency_crisis": QuickAction(
        action_id="emergency_crisis",
        label="Crisis Support",
        icon="alert-triangle",
        action_type=ActionType.NAVIGATE,
        target="/crisis-intake",
        telemetry_event="quick_action_clicked",
        confirmation_prompt="This will connect you with emergency housing resources. Continue?",
    ),
}


# =============================================================================
# VAULT DOCUMENT ACTIONS
# =============================================================================

VAULT_DOCUMENT_ACTIONS: Dict[str, QuickAction] = {
    "upload_new": QuickAction(
        action_id="upload_new",
        label="Upload New Document",
        icon="upload",
        action_type=ActionType.TRIGGER,
        target="vault_upload",
        telemetry_event="vault_upload_started",
    ),
    "view_overlay": QuickAction(
        action_id="view_overlay",
        label="View Certificate",
        icon="shield",
        action_type=ActionType.OPEN,
        target="unified_overlay",
        telemetry_event="overlay_viewed",
    ),
    "download": QuickAction(
        action_id="download",
        label="Download",
        icon="download",
        action_type=ActionType.DOWNLOAD,
        target="document_download",
        telemetry_event="document_downloaded",
    ),
    "share": QuickAction(
        action_id="share",
        label="Share",
        icon="share",
        action_type=ActionType.SHARE,
        target="document_share",
        telemetry_event="document_shared",
    ),
    "analyze": QuickAction(
        action_id="analyze",
        label="Analyze Document",
        icon="search",
        action_type=ActionType.TRIGGER,
        target="auto_document_analysis",
        telemetry_event="mesh_workflow_triggered",
    ),
}


# =============================================================================
# COURT PACKET ACTIONS
# =============================================================================

COURT_PACKET_ACTIONS: Dict[str, QuickAction] = {
    "add_form": QuickAction(
        action_id="add_form",
        label="Add Form",
        icon="file-plus",
        action_type=ActionType.NAVIGATE,
        target="/forms",
        telemetry_event="form_added_to_packet",
    ),
    "add_evidence": QuickAction(
        action_id="add_evidence",
        label="Add Evidence",
        icon="paperclip",
        action_type=ActionType.NAVIGATE,
        target="/vault",
        target_params={"select": "evidence"},
        telemetry_event="evidence_indexed",
    ),
    "generate_packet": QuickAction(
        action_id="generate_packet",
        label="Generate Packet",
        icon="package",
        action_type=ActionType.TRIGGER,
        target="court_packet_generate",
        telemetry_event="packet_generated",
    ),
    "download_packet": QuickAction(
        action_id="download_packet",
        label="Download Packet",
        icon="download",
        action_type=ActionType.DOWNLOAD,
        target="packet_download",
        telemetry_event="packet_downloaded",
    ),
}


# =============================================================================
# EVICTION ANSWER ACTIONS
# =============================================================================

EVICTION_ANSWER_ACTIONS: Dict[str, QuickAction] = {
    "select_defense": QuickAction(
        action_id="select_defense",
        label="Select Defenses",
        icon="shield",
        action_type=ActionType.OPEN,
        target="defense_selector",
        telemetry_event="defense_selected",
    ),
    "add_counterclaim": QuickAction(
        action_id="add_counterclaim",
        label="Add Counterclaim",
        icon="plus-circle",
        action_type=ActionType.OPEN,
        target="counterclaim_form",
        telemetry_event="counterclaim_added",
    ),
    "generate_answer": QuickAction(
        action_id="generate_answer",
        label="Generate Answer",
        icon="file-text",
        action_type=ActionType.TRIGGER,
        target="answer_form_generate",
        telemetry_event="answer_form_generated",
    ),
    "download_answer": QuickAction(
        action_id="download_answer",
        label="Download for Filing",
        icon="download",
        action_type=ActionType.DOWNLOAD,
        target="answer_download",
        telemetry_event="answer_downloaded",
    ),
}


# =============================================================================
# HEARING PREP ACTIONS
# =============================================================================

HEARING_PREP_ACTIONS: Dict[str, QuickAction] = {
    "generate_talking_points": QuickAction(
        action_id="generate_talking_points",
        label="Generate Talking Points",
        icon="message-square",
        action_type=ActionType.TRIGGER,
        target="talking_points_generate",
        telemetry_event="talking_points_generated",
    ),
    "check_evidence": QuickAction(
        action_id="check_evidence",
        label="Evidence Checklist",
        icon="check-square",
        action_type=ActionType.OPEN,
        target="evidence_checklist",
        telemetry_event="evidence_checklist_completed",
    ),
    "test_virtual": QuickAction(
        action_id="test_virtual",
        label="Test Audio/Video",
        icon="mic",
        action_type=ActionType.NAVIGATE,
        target="/zoom-court",
        target_params={"mode": "test"},
        telemetry_event="virtual_hearing_tested",
    ),
    "download_prep_guide": QuickAction(
        action_id="download_prep_guide",
        label="Download Prep Guide",
        icon="book",
        action_type=ActionType.DOWNLOAD,
        target="prep_guide_download",
        telemetry_event="prep_guide_downloaded",
    ),
}


# =============================================================================
# STORAGE SETUP ACTIONS
# =============================================================================

STORAGE_SETUP_ACTIONS: Dict[str, QuickAction] = {
    "connect_google": QuickAction(
        action_id="connect_google",
        label="Connect Google Drive",
        icon="google-drive",  # conceptual
        action_type=ActionType.TRIGGER,
        target="oauth_google",
        telemetry_event="provider_selected",
    ),
    "connect_onedrive": QuickAction(
        action_id="connect_onedrive",
        label="Connect OneDrive",
        icon="cloud",  # conceptual
        action_type=ActionType.TRIGGER,
        target="oauth_onedrive",
        telemetry_event="provider_selected",
    ),
    "connect_dropbox": QuickAction(
        action_id="connect_dropbox",
        label="Connect Dropbox",
        icon="box",  # conceptual
        action_type=ActionType.TRIGGER,
        target="oauth_dropbox",
        telemetry_event="provider_selected",
    ),
}


# =============================================================================
# CRISIS INTAKE ACTIONS
# =============================================================================

CRISIS_INTAKE_ACTIONS: Dict[str, QuickAction] = {
    "emergency_hotline": QuickAction(
        action_id="emergency_hotline",
        label="Emergency Hotline",
        icon="phone",
        action_type=ActionType.EXTERNAL,
        target="tel:+1-800-xxx-xxxx",  # Placeholder
        telemetry_event="hotline_connected",
    ),
    "legal_aid": QuickAction(
        action_id="legal_aid",
        label="Legal Aid Resources",
        icon="scale",
        action_type=ActionType.NAVIGATE,
        target="/help",
        telemetry_event="emergency_resource_accessed",
    ),
    "escalate_advocate": QuickAction(
        action_id="escalate_advocate",
        label="Request Advocate",
        icon="user-plus",
        action_type=ActionType.TRIGGER,
        target="advocate_escalation",
        telemetry_event="advocate_escalation",
    ),
}


# =============================================================================
# GLOBAL ACTION REGISTRY
# =============================================================================

ALL_ACTION_MAPS: Dict[str, Dict[str, QuickAction]] = {
    "dashboard": DASHBOARD_QUICK_ACTIONS,
    "vault": VAULT_DOCUMENT_ACTIONS,
    "documents": VAULT_DOCUMENT_ACTIONS,
    "court_packet": COURT_PACKET_ACTIONS,
    "eviction_answer": EVICTION_ANSWER_ACTIONS,
    "hearing_prep": HEARING_PREP_ACTIONS,
    "storage_setup": STORAGE_SETUP_ACTIONS,
    "crisis_intake": CRISIS_INTAKE_ACTIONS,
}


def get_page_actions(page_id: str) -> Dict[str, QuickAction]:
    """Get all actions defined for a page."""
    return ALL_ACTION_MAPS.get(page_id, {})


def get_action(page_id: str, action_id: str) -> Optional[QuickAction]:
    """Get a specific action by ID."""
    page_actions = get_page_actions(page_id)
    return page_actions.get(action_id)


def filter_actions_by_role(
    actions: Dict[str, QuickAction],
    user_roles: List[str],
) -> Dict[str, QuickAction]:
    """Filter actions to only those allowed for the user's roles."""
    filtered = {}
    for action_id, action in actions.items():
        if action.required_roles is None:
            filtered[action_id] = action
        elif any(r in action.required_roles for r in user_roles):
            filtered[action_id] = action
    return filtered


def render_action_button(action: QuickAction) -> Dict[str, Any]:
    """Render an action as a button configuration for frontend."""
    return {
        "id": action.action_id,
        "label": action.label,
        "icon": action.icon,
        "type": action.action_type.name.lower(),
        "target": action.target,
        "params": action.target_params or {},
        "confirmation": action.confirmation_prompt,
    }


# =============================================================================
# CLI / DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=== Action Maps System ===")
    print(f"Total pages with actions: {len(ALL_ACTION_MAPS)}")
    
    for page_id, actions in ALL_ACTION_MAPS.items():
        print(f"\n{page_id}:")
        for action_id, action in actions.items():
            roles = action.required_roles or ["all"]
            print(f"  - {action.label} ({action.action_type.name}, roles: {roles})")
    
    print(f"\n✅ Action maps ready for integration.")
