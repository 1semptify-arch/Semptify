"""
Module Links — Page-to-Module Binding System
=============================================

Explicitly declares which backend modules each page connects to.
Used for dependency validation, mesh orchestration, and documentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum, auto


class ModuleType(Enum):
    """Types of backend modules."""
    DOCUMENT = auto()      # Document storage, vault, overlays
    CASE = auto()          # Case management, timelines
    CALENDAR = auto()      # Deadlines, hearings
    FORMS = auto()         # Form generation, PDF
    COURT = auto()         # Court integration, Zoom
    COPILOT = auto()       # AI assistance
    STORAGE = auto()       # OAuth, external storage
    NOTIFICATION = auto()  # Alerts, reminders
    IDENTITY = auto()      # Auth, user management
    RESEARCH = auto()      # Legal research, statutes


@dataclass
class ModuleLink:
    """
    Declares a page's connection to a backend module.
    
    Usage:
        link = ModuleLink(
            module_id="document_vault",
            module_type=ModuleType.DOCUMENT,
            connection_point="/api/v1/documents",
            required=True,
            fallback_behavior="show upload disabled message",
        )
    """
    module_id: str
    module_type: ModuleType
    connection_point: str  # API endpoint, event channel, etc.
    required: bool = True  # If True, page fails without this module
    fallback_behavior: Optional[str] = None  # What to do if module unavailable
    data_flow: str = "bidirectional"  # inbound, outbound, bidirectional


# =============================================================================
# DOCUMENT PAGES MODULE LINKS
# =============================================================================

VAULT_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="document_vault",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/vault",
        required=True,
        fallback_behavior="show 'storage unavailable' message",
        data_flow="bidirectional",
    ),
    ModuleLink(
        module_id="overlay_engine",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/overlays",
        required=False,
        fallback_behavior="show documents without overlays",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="certificate_generator",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/certificates",
        required=False,
        fallback_behavior="skip certificate generation",
        data_flow="outbound",
    ),
]

DOCUMENTS_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="document_index",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/documents/search",
        required=True,
        fallback_behavior="show empty document list",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="vault_connector",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/vault",
        required=True,
        fallback_behavior="disable upload/download",
        data_flow="bidirectional",
    ),
]

DOCUMENT_VIEWER_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="document_renderer",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/documents/{id}/render",
        required=True,
        fallback_behavior="show download-only view",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="annotation_store",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/documents/{id}/annotations",
        required=False,
        fallback_behavior="disable annotation features",
        data_flow="bidirectional",
    ),
]


# =============================================================================
# CASE MANAGEMENT MODULE LINKS
# =============================================================================

DASHBOARD_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="case_summary",
        module_type=ModuleType.CASE,
        connection_point="/api/v1/cases/summary",
        required=True,
        fallback_behavior="show welcome message instead",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="deadline_alerts",
        module_type=ModuleType.CALENDAR,
        connection_point="/api/v1/deadlines/upcoming",
        required=False,
        fallback_behavior="hide deadline section",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="quick_action_router",
        module_type=ModuleType.COPILOT,
        connection_point="/api/v1/actions",
        required=False,
        fallback_behavior="show static action list",
        data_flow="inbound",
    ),
]

TIMELINE_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="event_store",
        module_type=ModuleType.CASE,
        connection_point="/api/v1/cases/{id}/timeline",
        required=True,
        fallback_behavior="show 'timeline unavailable'",
        data_flow="bidirectional",
    ),
    ModuleLink(
        module_id="document_extractor",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/documents/extract-events",
        required=False,
        fallback_behavior="show only manual events",
        data_flow="outbound",
    ),
]

CALENDAR_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="deadline_engine",
        module_type=ModuleType.CALENDAR,
        connection_point="/api/v1/deadlines",
        required=True,
        fallback_behavior="show empty calendar",
        data_flow="bidirectional",
    ),
    ModuleLink(
        module_id="hearing_scheduler",
        module_type=ModuleType.COURT,
        connection_point="/api/v1/hearings",
        required=False,
        fallback_behavior="show deadlines only",
        data_flow="outbound",
    ),
]


# =============================================================================
# COURT / LEGAL MODULE LINKS
# =============================================================================

COURT_PACKET_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="form_assembly",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/forms/assemble",
        required=True,
        fallback_behavior="show 'forms unavailable'",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="evidence_indexer",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/evidence",
        required=False,
        fallback_behavior="packet without evidence index",
        data_flow="bidirectional",
    ),
    ModuleLink(
        module_id="packet_generator",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/packets/generate",
        required=True,
        fallback_behavior="show individual forms only",
        data_flow="outbound",
    ),
]

EVICTION_ANSWER_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="defense_selector",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/defenses",
        required=True,
        fallback_behavior="show free-form text entry",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="answer_generator",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/forms/eviction-answer",
        required=True,
        fallback_behavior="download blank form",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="counterclaim_builder",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/counterclaims",
        required=False,
        fallback_behavior="skip counterclaim section",
        data_flow="bidirectional",
    ),
]

HEARING_PREP_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="talking_points_generator",
        module_type=ModuleType.COPILOT,
        connection_point="/api/v1/copilot/talking-points",
        required=False,
        fallback_behavior="show generic talking points guide",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="evidence_checklist",
        module_type=ModuleType.CASE,
        connection_point="/api/v1/cases/{id}/evidence-checklist",
        required=False,
        fallback_behavior="show generic checklist",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="zoom_connector",
        module_type=ModuleType.COURT,
        connection_point="/api/v1/zoom/test",
        required=False,
        fallback_behavior="skip AV test, show instructions",
        data_flow="outbound",
    ),
]

ZOOM_COURT_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="zoom_integration",
        module_type=ModuleType.COURT,
        connection_point="/api/v1/zoom/join",
        required=True,
        fallback_behavior="show manual join instructions",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="hearing_documents",
        module_type=ModuleType.DOCUMENT,
        connection_point="/api/v1/hearings/{id}/documents",
        required=False,
        fallback_behavior="hearing without quick document access",
        data_flow="outbound",
    ),
]

MOTIONS_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="motion_templates",
        module_type=ModuleType.FORMS,
        connection_point="/api/v1/motions/templates",
        required=True,
        fallback_behavior="show blank motion form",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="motion_filer",
        module_type=ModuleType.COURT,
        connection_point="/api/v1/efile",
        required=False,
        fallback_behavior="download for manual filing",
        data_flow="outbound",
    ),
]

LEGAL_ANALYSIS_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="statute_lookup",
        module_type=ModuleType.RESEARCH,
        connection_point="/api/v1/research/statutes",
        required=True,
        fallback_behavior="show 'research unavailable'",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="precedent_search",
        module_type=ModuleType.RESEARCH,
        connection_point="/api/v1/research/precedents",
        required=False,
        fallback_behavior="skip precedent analysis",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="memo_generator",
        module_type=ModuleType.COPILOT,
        connection_point="/api/v1/copilot/memo",
        required=False,
        fallback_behavior="show raw analysis only",
        data_flow="outbound",
    ),
]


# =============================================================================
# STORAGE & SETUP MODULE LINKS
# =============================================================================

STORAGE_SETUP_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="oauth_manager",
        module_type=ModuleType.IDENTITY,
        connection_point="/api/v1/oauth",
        required=True,
        fallback_behavior="show 'connect unavailable'",
        data_flow="bidirectional",
    ),
    ModuleLink(
        module_id="storage_sync",
        module_type=ModuleType.STORAGE,
        connection_point="/api/v1/sync",
        required=False,
        fallback_behavior="manual upload only",
        data_flow="bidirectional",
    ),
]


# =============================================================================
# CRISIS MODULE LINKS
# =============================================================================

CRISIS_INTAKE_MODULE_LINKS: List[ModuleLink] = [
    ModuleLink(
        module_id="crisis_router",
        module_type=ModuleType.NOTIFICATION,
        connection_point="/api/v1/crisis/escalate",
        required=False,
        fallback_behavior="show static hotline numbers",
        data_flow="outbound",
    ),
    ModuleLink(
        module_id="advocate_alert",
        module_type=ModuleType.NOTIFICATION,
        connection_point="/api/v1/advocates/alert",
        required=False,
        fallback_behavior="show 'advocates unavailable'",
        data_flow="outbound",
    ),
]


# =============================================================================
# GLOBAL MODULE LINK REGISTRY
# =============================================================================

ALL_MODULE_LINKS: Dict[str, List[ModuleLink]] = {
    "dashboard": DASHBOARD_MODULE_LINKS,
    "vault": VAULT_MODULE_LINKS,
    "documents": DOCUMENTS_MODULE_LINKS,
    "document_viewer": DOCUMENT_VIEWER_MODULE_LINKS,
    "timeline": TIMELINE_MODULE_LINKS,
    "calendar": CALENDAR_MODULE_LINKS,
    "court_packet": COURT_PACKET_MODULE_LINKS,
    "eviction_answer": EVICTION_ANSWER_MODULE_LINKS,
    "hearing_prep": HEARING_PREP_MODULE_LINKS,
    "zoom_court": ZOOM_COURT_MODULE_LINKS,
    "motions": MOTIONS_MODULE_LINKS,
    "legal_analysis": LEGAL_ANALYSIS_MODULE_LINKS,
    "storage_setup": STORAGE_SETUP_MODULE_LINKS,
    "crisis_intake": CRISIS_INTAKE_MODULE_LINKS,
}


def get_page_modules(page_id: str) -> List[ModuleLink]:
    """Get all module links for a page."""
    return ALL_MODULE_LINKS.get(page_id, [])


def get_required_modules(page_id: str) -> List[ModuleLink]:
    """Get only required module links for a page."""
    return [m for m in get_page_modules(page_id) if m.required]


def get_modules_by_type(module_type: ModuleType) -> List[str]:
    """Get all page IDs that link to a specific module type."""
    pages = []
    for page_id, links in ALL_MODULE_LINKS.items():
        if any(link.module_type == module_type for link in links):
            pages.append(page_id)
    return pages


def check_page_dependencies(page_id: str, available_modules: Set[str]) -> Dict[str, str]:
    """
    Check if a page's dependencies are satisfied.
    
    Returns dict of {module_id: status} where status is:
        'ok', 'fallback', or 'blocked'
    """
    links = get_page_modules(page_id)
    results = {}
    
    for link in links:
        if link.module_id in available_modules:
            results[link.module_id] = 'ok'
        elif link.required:
            results[link.module_id] = 'blocked'
        else:
            results[link.module_id] = 'fallback'
    
    return results


# =============================================================================
# CLI / DEBUG
# =============================================================================

if __name__ == "__main__":
    print("=== Module Links System ===")
    print(f"Pages with module links: {len(ALL_MODULE_LINKS)}")
    
    # Count by module type
    type_counts: Dict[ModuleType, int] = {}
    for links in ALL_MODULE_LINKS.values():
        for link in links:
            type_counts[link.module_type] = type_counts.get(link.module_type, 0) + 1
    
    print("\nLinks by module type:")
    for mt, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {mt.name}: {count} links")
    
    # Show sample
    print("\nSample: dashboard modules")
    for link in DASHBOARD_MODULE_LINKS:
        req = "required" if link.required else "optional"
        print(f"  - {link.module_id} ({req}) → {link.connection_point}")
    
    print(f"\n✅ Module links ready for health checks.")
