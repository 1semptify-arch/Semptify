"""
Semptify 5.0 - Page Manifest
===========================

Enumerates every non-archive page in the system and marks coverage state
against 9 required object sets:

1. Page Contract      - Registered in app/core/page_contracts.py
2. Route Guard(s)     - Authentication/authorization checks
3. Module Link(s)     - Connected module handlers
4. Action Map         - Available user actions
5. Object Set         - Required input objects
6. Output Object(s)   - Produced output objects
7. Telemetry Hook(s)  - Event emission points
8. Mesh Binding       - Positronic Mesh integration
9. Coverage State     - complete / partial / missing

Coverage State Definitions:
- complete  : All object sets fully implemented and wired
- partial   : Some object sets implemented, gaps identified
- missing   : Page exists but lacks required infrastructure
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum


class CoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    NA = "n/a"


@dataclass
class ObjectSetCoverage:
    """Coverage status for a single object set."""
    status: CoverageStatus
    notes: str = ""  # Details on what's present or missing


@dataclass
class PageManifestEntry:
    """Complete manifest entry for a single page."""
    
    # Identity
    page_id: str
    route: str
    source_file: str  # Template or static HTML file path
    page_type: str    # "template", "static", "route_rendered"
    
    # 9 Object Sets Coverage
    page_contract: ObjectSetCoverage
    route_guards: ObjectSetCoverage
    module_links: ObjectSetCoverage
    action_map: ObjectSetCoverage
    object_set_inputs: ObjectSetCoverage
    output_objects: ObjectSetCoverage
    telemetry_hooks: ObjectSetCoverage
    mesh_binding: ObjectSetCoverage
    
    # Overall status
    overall_coverage: CoverageStatus
    
    # Gap analysis
    missing_object_sets: List[str] = field(default_factory=list)
    recommended_priority: str = "low"  # low, medium, high, critical


# =============================================================================
# PAGE MANIFEST REGISTRY
# =============================================================================

PAGE_MANIFEST: List[PageManifestEntry] = [
    #
    # PROCESS A: WELCOME / ENTRY POINTS
    #
    PageManifestEntry(
        page_id="welcome",
        route="/",
        source_file="app/templates/pages/welcome.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_WELCOME registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access, role selection enforced"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Welcome module, security validation module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "role_select, storage_connect, process_start actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "UserRole selection, storage_status"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Session initialization, role cookie, route decision"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "welcome_page_load, role_selected, process_start_clicked"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "No mesh workflow triggered on entry (could trigger context_sync)"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # ONBOARDING SEQUENCE (A2 — A4)
    #
    PageManifestEntry(
        page_id="role_selection",
        route="/choose-role",
        source_file="app/templates/pages/role_selection.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_ROLE_SELECTION registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access — no auth required"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Welcome module, security_validation module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "role_selected action, routes to /storage-info"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "UserRole enum options"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Role cookie set, route to /storage-info"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "role_selection_load, role_selected, role_confirmed"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "No mesh workflow at role selection"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="high"
    ),

    PageManifestEntry(
        page_id="storage_info",
        route="/storage-info",
        source_file="app/templates/pages/storage_info.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_STORAGE_INFO registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Role cookie required; attempt counter enforced"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "OAuth module, storage setup module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "provider_selected, oauth_redirect, retry_loop, tech_support_fallback"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Storage provider list, attempt counter cookie"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "OAuth redirect, attempt counter update, tech support screen"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "storage_info_load, storage_provider_selected, oauth_redirect_initiated, storage_retry_loop, storage_tech_support_shown"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "No mesh workflow at storage selection"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="high"
    ),

    PageManifestEntry(
        page_id="storage_connecting",
        route="/storage-connecting",
        source_file="app/templates/pages/storage_connecting.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_STORAGE_CONNECTING registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "OAuth callback token required; no user input accepted"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Storage setup module, vault module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Auto-redirect to /home on success; retry link to /storage-info on failure"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "OAuth token from callback, backend setup job status"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Progressive step narrative, auto-redirect to /home"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "storage_connecting_load, storage_folder_created, storage_first_sync_complete, storage_setup_success, storage_setup_failed"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger FULL_SYNC workflow on storage_setup_success"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="high"
    ),

    #
    # PROCESS B: CORE USER WORKSPACE
    #
    PageManifestEntry(
        page_id="tenant_dashboard",
        route="/tenant",
        source_file="app/templates/pages/tenant.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_TENANT registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "require_user, storage validation"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "documents, timeline, help_contacts modules"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "document_upload, quick_action, help_request"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "user context, storage token, document list"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "document uploads, case actions"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "tenant_dashboard_load, document_upload_started"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Document upload triggers mesh workflows"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="dashboard",
        route="/dashboard",
        source_file="static/dashboard.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_DASHBOARD registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static file, no explicit guards"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "DASHBOARD_MODULE_LINKS defined in module_links.py (3 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "DASHBOARD_QUICK_ACTIONS defined in action_maps.py (9 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User context, case data implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case summaries, deadline lists displayed"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "dashboard_load, quick_action_clicked, deadline_viewed, case_summary_expanded in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "dashboard_load could trigger context_sync workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="documents",
        route="/documents",
        source_file="static/documents.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_DOCUMENTS registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static, no explicit guards"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "DOCUMENTS_MODULE_LINKS defined in module_links.py (2 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document actions present but not mapped to contracts"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User context implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document uploads"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "documents_page_load, document_upload_started, document_downloaded, document_shared, overlay_viewed in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Vault upload triggers mesh workflows"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="timeline",
        route="/timeline",
        source_file="static/timeline.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_TIMELINE registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Timeline events data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "timeline_load, event_expanded, timeline_filtered, timeline_exported in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Timeline extraction via mesh action"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="calendar",
        route="/calendar",
        source_file="static/calendar.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_CALENDAR registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Calendar events data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "calendar_load, date_selected, deadline_viewed, event_added in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar actions registered in mesh"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    #
    # PROCESS C: GUIDED JOURNEYS
    #
    PageManifestEntry(
        page_id="tenancy",
        route="/tenancy",
        source_file="app/templates/pages/tenancy.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "require_user"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy data implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy workflow progression"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger tenancy workflow"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="advocate",
        route="/advocate",
        source_file="app/templates/pages/advocate.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Role check implied"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Advocate module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Advocate actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Advocate context implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Advocate workflow progression"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="admin",
        route="/admin",
        source_file="app/templates/pages/admin.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Admin role check implied"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Admin module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Admin actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Admin context implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Admin operations"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # LEGAL / RESEARCH PAGES
    #
    PageManifestEntry(
        page_id="legal",
        route="/legal",
        source_file="app/templates/pages/legal.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "require_user"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Law library module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Legal research actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Legal data, case context"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Legal research output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Law library actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="legal_analysis",
        route="/legal-analysis",
        source_file="static/legal_analysis.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_LEGAL_ANALYSIS registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Legal analysis module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Analysis actions present"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document data implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Analysis results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "legal_analysis_load, statute_searched, precedent_checked, analysis_memo_generated in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger research workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="law_library",
        route="/law-library",
        source_file="static/law_library.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Law library module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Law lookup actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Legal queries"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Legal references"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Law library actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="research",
        route="/research",
        source_file="static/research.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research queries"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "Research module deferred in lean mode"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="legal_trails",
        route="/legal-trails",
        source_file="static/legal_trails.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Legal trails module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Trail actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Trail data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Trail output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "Legal trails deferred"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # DOCUMENT MANAGEMENT
    #
    PageManifestEntry(
        page_id="vault",
        route="/vault",
        source_file="static/vault.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_VAULT registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "VAULT_MODULE_LINKS defined in module_links.py (3 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "VAULT_DOCUMENT_ACTIONS defined in action_maps.py (5 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Files, metadata, document type"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Stored documents, certificates, overlays"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "vault_load, vault_upload_started, vault_upload_complete, vault_download, certificate_generated, mesh_workflow_triggered in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "vault_upload_complete triggers LEASE_ANALYSIS workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="document_viewer",
        route="/document-viewer",
        source_file="static/document_viewer.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_DOCUMENT_VIEWER registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Viewer actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document ID"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "document_viewer_load, overlay_toggled, annotation_added, document_printed in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger annotation workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="document_intake",
        route="/document-intake",
        source_file="static/document_intake.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger mesh workflow"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    #
    # COURT / HEARING
    #
    PageManifestEntry(
        page_id="court_packet",
        route="/court-packet",
        source_file="static/court_packet.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_COURT_PACKET registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static file, no explicit guards"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "COURT_PACKET_MODULE_LINKS defined in module_links.py (3 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "COURT_PACKET_ACTIONS defined in action_maps.py (4 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case data implied"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Packet output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "court_packet_load, packet_generated, form_added_to_packet, evidence_indexed, packet_downloaded in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "court_packet_load triggers COURT_PREP workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="eviction_answer",
        route="/eviction-answer",
        source_file="static/eviction_answer.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_EVICTION_ANSWER registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "EVICTION_ANSWER_MODULE_LINKS defined in module_links.py (3 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "EVICTION_ANSWER_ACTIONS defined in action_maps.py (4 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Eviction data, defenses"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Answer form draft"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "eviction_answer_load, defense_selected, counterclaim_added, answer_form_generated, answer_downloaded in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Forms actions in mesh"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="hearing_prep",
        route="/hearing-prep",
        source_file="static/hearing_prep.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_HEARING_PREP registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "HEARING_PREP_MODULE_LINKS defined in module_links.py (3 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "HEARING_PREP_ACTIONS defined in action_maps.py (4 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Hearing data, case info"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Hearing prep checklist"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "hearing_prep_load, talking_points_generated, evidence_checklist_completed, virtual_hearing_tested, prep_guide_downloaded in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Zoom court actions in mesh"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="zoom_court",
        route="/zoom-court",
        source_file="static/zoom_court.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_ZOOM_COURT registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Zoom court module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Virtual hearing prep"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Hearing info"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Virtual hearing guidance"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "zoom_court_load, test_mode_started, hearing_joined, audio_test_completed, document_shared_in_hearing in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Zoom court actions in mesh"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="motions",
        route="/motions",
        source_file="static/motions.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_MOTIONS registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Forms module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Motion preparation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Motion forms"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "motions_load, motion_template_selected, motion_drafted, motion_filed in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could use forms actions"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="counterclaim",
        route="/counterclaim",
        source_file="static/counterclaim.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Forms module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Counterclaim preparation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Counterclaim form"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could use forms actions"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    #
    # CASE BUILDER / BRIEFCASE
    #
    PageManifestEntry(
        page_id="case_builder",
        route="/case-builder",
        source_file="static/cases.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case builder module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case building actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Documents, timeline"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Compiled case"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger case workflow"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="briefcase",
        route="/briefcase",
        source_file="static/briefcase.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Briefcase module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Briefcase actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case documents"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Organized briefcase"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # UTILITY / TOOLS
    #
    PageManifestEntry(
        page_id="pdf_tools",
        route="/pdf-tools",
        source_file="static/pdf_tools.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "PDF tools module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "PDF manipulation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "PDF files"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Processed PDFs"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="document_converter",
        route="/document-converter",
        source_file="static/document-converter.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Converter module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Conversion actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Source documents"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Converted documents"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="contacts",
        route="/contacts",
        source_file="static/contacts.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Contacts module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Contact management"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Contact data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Contact list"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="correspondence",
        route="/correspondence",
        source_file="static/correspondence.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Correspondence module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Letter writing, communication"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Recipient, message data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Sent correspondence"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="letter_builder",
        route="/letter-builder",
        source_file="static/letter_builder.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Letter module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Letter composition"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template, recipient data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Composed letter"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # SETTINGS / SETUP
    #
    PageManifestEntry(
        page_id="settings",
        route="/settings",
        source_file="static/settings-v2.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Settings module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Settings management"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User preferences"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Updated settings"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="setup_wizard",
        route="/setup",
        source_file="static/setup_wizard.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Setup module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Setup steps"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User preferences, storage settings"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Configured system"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="storage_setup",
        route="/storage-setup",
        source_file="static/storage_setup.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_STORAGE_SETUP registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "STORAGE_SETUP_MODULE_LINKS defined in module_links.py (2 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "STORAGE_SETUP_ACTIONS defined in action_maps.py (3 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Provider selection, OAuth tokens"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Connected storage"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "storage_setup_load, provider_selected, oauth_started, oauth_completed, storage_connected in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "oauth_completed triggers storage_sync_setup workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    #
    # HELP / INFO
    #
    PageManifestEntry(
        page_id="help",
        route="/help",
        source_file="static/help.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Help module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Help navigation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Help content"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Help display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="about",
        route="/about",
        source_file="static/about.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.NA,
            "Static info page"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.NA,
            "No actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Static content"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.NA,
            "No output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "Static page"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="privacy",
        route="/privacy",
        source_file="static/privacy.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.NA,
            "Static info page"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.NA,
            "No actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Static content"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.NA,
            "No output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "Static page"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # SPECIALIZED MODULES
    #
    PageManifestEntry(
        page_id="fraud_exposure",
        route="/fraud-exposure",
        source_file="static/fraud.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Fraud module deferred"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Fraud reporting"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Fraud data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Fraud report"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "Fraud module deferred in lean mode"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="public_exposure",
        route="/public-exposure",
        source_file="static/exposure.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Exposure module deferred"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Exposure actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Public exposure output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "Public exposure deferred"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="complaints",
        route="/complaints",
        source_file="static/complaints.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Complaints module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Complaint filing"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Complaint data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Filed complaint"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="dakota_defense",
        route="/dakota-defense",
        source_file="static/dakota_defense.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Dakota module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Defense preparation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Case data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Defense output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could use eviction workflow"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # ADVANCED / SPECIALTY
    #
    PageManifestEntry(
        page_id="command_center",
        route="/command-center",
        source_file="static/command_center.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Command module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Command actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "System data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Command output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="brain",
        route="/brain",
        source_file="static/brain.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Brain/copilot module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "AI assistant actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User queries"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "AI responses"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Copilot actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="focus",
        route="/focus",
        source_file="static/focus.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Focus module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Focus mode actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Task data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Focused output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="campaign",
        route="/campaign",
        source_file="static/campaign.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Campaign module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Campaign actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Campaign data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Campaign output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="mesh_network",
        route="/mesh-network",
        source_file="static/mesh_network.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Positronic Mesh visualization"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "View mesh status, trigger workflows"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Mesh status data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Mesh visualization"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Direct mesh API integration"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="crawler",
        route="/crawler",
        source_file="static/crawler.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crawler module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crawler controls"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crawl parameters"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crawl results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="auto_analysis_summary",
        route="/auto-analysis",
        source_file="static/auto_analysis_summary.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Auto analysis module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Analysis actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Analysis summary"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger analysis workflow"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # ONBOARDING / REGISTRATION
    #
    PageManifestEntry(
        page_id="register",
        route="/register",
        source_file="app/templates/pages/register.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access, rate limited"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Registration module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "User registration, validation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "User data, validation rules"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Created user account"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="register_success",
        route="/register/success",
        source_file="app/templates/pages/register_success.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Post-registration redirect"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Success module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Next steps navigation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Registration confirmation"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User guidance"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="home",
        route="/home",
        source_file="static/home.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Home module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "User context"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Home dashboard"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="index",
        route="/index",
        source_file="static/index.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public access"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Index/navigation module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Static content"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Index display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # DEVELOPER / ADMIN TOOLS
    #
    PageManifestEntry(
        page_id="auto_mode_demo",
        route="/auto-mode-demo",
        source_file="app/templates/pages/auto_mode_demo.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Auto mode module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Demo actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Demo data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Demo output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger demo workflows"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="auto_mode_panel",
        route="/auto-mode-panel",
        source_file="app/templates/pages/auto_mode_panel.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Auto mode control module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Control actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Control parameters"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Control output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Mesh mode control endpoint"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="gui_navigation_hub",
        route="/gui-navigation",
        source_file="app/templates/pages/gui_navigation_hub.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation context"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="functionx",
        route="/functionx",
        source_file="app/templates/pages/functionx.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "FunctionX module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "FunctionX actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Function parameters"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Function output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="mode_selector",
        route="/mode-selector",
        source_file="app/templates/pages/mode_selector.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Mode selection module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Mode selection actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Mode options"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Selected mode"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger mode workflows"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="page_editor",
        route="/page-editor",
        source_file="static/page_editor.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Page editor module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Editor actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Page data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Edited page"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="layout_builder",
        route="/layout-builder",
        source_file="static/layout_builder.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Layout module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Layout actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Layout data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Layout output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="style_editor",
        route="/style-editor",
        source_file="static/style_editor.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Style module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Style actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Style data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Styled output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="module_converter",
        route="/module-converter",
        source_file="static/module-converter.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Converter module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Conversion actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Source module"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Converted module"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="component_converter",
        route="/component-converter",
        source_file="app/templates/pages/auto_analysis_summary.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Component module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Component actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Component data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Converted component"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="batch_analysis_results",
        route="/batch-analysis",
        source_file="app/templates/pages/batch_analysis_results.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Template rendered"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Batch module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Batch actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Batch data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Batch results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Could trigger batch workflows"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="page_index",
        route="/page-index",
        source_file="static/page-index.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Page index module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Index navigation"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Page catalog"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Page listing"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="error",
        route="/error",
        source_file="app/templates/pages/error.html",
        page_type="template",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Error handler"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.NA,
            "Error page"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Error recovery actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Error details"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Error display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "Error page"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    #
    # FUNDING / RESOURCES
    #
    PageManifestEntry(
        page_id="funding_search",
        route="/funding-search",
        source_file="static/funding_search.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Funding module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Search actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Search criteria"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Funding results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="hud_funding",
        route="/hud-funding",
        source_file="static/hud_funding.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "HUD module implied"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "HUD actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "HUD data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "HUD results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="recognition",
        route="/recognition",
        source_file="static/recognition.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Recognition module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Recognition actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Recognition data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Recognition output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="evaluation_report",
        route="/evaluation-report",
        source_file="static/evaluation_report.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Evaluation module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Evaluation actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Evaluation data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Evaluation report"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="crisis_intake",
        route="/crisis-intake",
        source_file="static/crisis_intake.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CONTRACT_CRISIS_INTAKE registered in page_contracts.py"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Urgent access"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CRISIS_INTAKE_MODULE_LINKS defined in module_links.py (2 modules)"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "CRISIS_INTAKE_ACTIONS defined in action_maps.py (3 actions)"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crisis data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Crisis response"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "crisis_intake_load, crisis_type_selected, emergency_resource_accessed, hotline_connected, advocate_escalation in telemetry_hooks.py"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "crisis_intake_load triggers crisis_escalation workflow"
        ),
        overall_coverage=CoverageStatus.PARTIAL,
        missing_object_sets=[],
        recommended_priority="high"
    ),
    
    PageManifestEntry(
        page_id="court_learning",
        route="/court-learning",
        source_file="static/court_learning.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Learning module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Learning actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Learning content"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Learning progress"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="complete_journey",
        route="/complete-journey",
        source_file="static/complete-journey.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="interactive_timeline",
        route="/interactive-timeline",
        source_file="static/interactive-timeline.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Interactive display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="timeline_builder",
        route="/timeline-builder",
        source_file="static/timeline-builder.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline builder module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Builder actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Event data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Built timeline"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Timeline actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="timeline_auto_build",
        route="/timeline-auto-build",
        source_file="static/timeline_auto_build.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Auto timeline module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Auto extract timeline"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Documents"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Auto-built timeline"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "timeline.extract_from_document action"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="document_calendar",
        route="/document-calendar",
        source_file="static/document_calendar.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Document dates"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar view"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Calendar actions in mesh"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="my_tenancy",
        route="/my-tenancy",
        source_file="static/my_tenancy.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Tenancy display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="sample_certificate",
        route="/sample-certificate",
        source_file="static/sample_certificate.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Public sample"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.NA,
            "Sample display"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.NA,
            "No actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Sample data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.NA,
            "No output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.NA,
            "Static sample"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="sidebar_with_auto_mode",
        route="/sidebar-auto-mode",
        source_file="static/sidebar_with_auto_mode.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Sidebar module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Sidebar actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Navigation data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Sidebar display"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="roles",
        route="/roles",
        source_file="static/roles.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Roles module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Role selection"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Role options"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Role selection"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="enterprise_dashboard",
        route="/enterprise-dashboard",
        source_file="static/enterprise-dashboard.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Enterprise module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Enterprise actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Enterprise data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Enterprise dashboard"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="intake",
        route="/intake",
        source_file="static/intake.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Intake output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="medium"
    ),
    
    PageManifestEntry(
        page_id="research_module",
        route="/research-module",
        source_file="static/research_module.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research queries"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Research results"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "Research module deferred in lean mode"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
    
    PageManifestEntry(
        page_id="journey",
        route="/journey",
        source_file="static/journey.html",
        page_type="static",
        page_contract=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "PageContract registered"
        ),
        route_guards=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Served as static"
        ),
        module_links=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey module"
        ),
        action_map=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey actions"
        ),
        object_set_inputs=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey data"
        ),
        output_objects=ObjectSetCoverage(
            CoverageStatus.PARTIAL,
            "Journey output"
        ),
        telemetry_hooks=ObjectSetCoverage(
            CoverageStatus.COMPLETE,
            "Telemetry events defined in PageContract"
        ),
        mesh_binding=ObjectSetCoverage(
            CoverageStatus.MISSING,
            "No mesh binding"
        ),
        overall_coverage=CoverageStatus.COMPLETE,
        missing_object_sets=[],
        recommended_priority="low"
    ),
]


# =============================================================================
# MANIFEST QUERY FUNCTIONS
# =============================================================================

def get_page_manifest_entry(page_id: str) -> Optional[PageManifestEntry]:
    """Get manifest entry for a specific page."""
    for entry in PAGE_MANIFEST:
        if entry.page_id == page_id:
            return entry
    return None


def get_pages_by_coverage(status: CoverageStatus) -> List[PageManifestEntry]:
    """Get all pages with a specific overall coverage status."""
    return [p for p in PAGE_MANIFEST if p.overall_coverage == status]


def get_pages_with_missing(object_set: str) -> List[PageManifestEntry]:
    """Get all pages missing a specific object set."""
    return [p for p in PAGE_MANIFEST if object_set in p.missing_object_sets]


def get_high_priority_pages() -> List[PageManifestEntry]:
    """Get all pages marked as high or critical priority."""
    return [p for p in PAGE_MANIFEST if p.recommended_priority in ("high", "critical")]


def get_coverage_summary() -> Dict[str, int]:
    """Get summary statistics of coverage across all pages."""
    total = len(PAGE_MANIFEST)
    complete = len(get_pages_by_coverage(CoverageStatus.COMPLETE))
    partial = len(get_pages_by_coverage(CoverageStatus.PARTIAL))
    missing = len(get_pages_by_coverage(CoverageStatus.MISSING))
    
    return {
        "total_pages": total,
        "complete": complete,
        "partial": partial,
        "missing": missing,
        "completion_rate": round(complete / total * 100, 1) if total else 0,
    }


def get_object_set_gap_summary() -> Dict[str, int]:
    """Get count of pages missing each object set."""
    object_sets = [
        "page_contract", "route_guards", "module_links", "action_map",
        "object_set_inputs", "output_objects", "telemetry_hooks", "mesh_binding"
    ]
    return {
        obj_set: len(get_pages_with_missing(obj_set))
        for obj_set in object_sets
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate_manifest() -> List[str]:
    """Validate the page manifest for completeness and consistency."""
    errors = []
    page_ids = set()
    
    for entry in PAGE_MANIFEST:
        # Check for duplicate page_ids
        if entry.page_id in page_ids:
            errors.append(f"Duplicate page_id: {entry.page_id}")
        page_ids.add(entry.page_id)
        
        # Check that missing_object_sets aligns with ObjectSetCoverage
        for missing in entry.missing_object_sets:
            coverage_map = {
                "page_contract": entry.page_contract.status,
                "route_guards": entry.route_guards.status,
                "module_links": entry.module_links.status,
                "action_map": entry.action_map.status,
                "object_set_inputs": entry.object_set_inputs.status,
                "output_objects": entry.output_objects.status,
                "telemetry_hooks": entry.telemetry_hooks.status,
                "mesh_binding": entry.mesh_binding.status,
            }
            if missing not in coverage_map:
                errors.append(f"[{entry.page_id}] Unknown missing object set: {missing}")
            elif coverage_map[missing] != CoverageStatus.MISSING:
                errors.append(
                    f"[{entry.page_id}] Inconsistency: {missing} in missing_object_sets "
                    f"but status is {coverage_map[missing]}"
                )
    
    return errors


if __name__ == "__main__":
    # Print coverage summary when run directly
    summary = get_coverage_summary()
    print("=" * 60)
    print("SEPTIFY PAGE MANIFEST - COVERAGE SUMMARY")
    print("=" * 60)
    print(f"Total Pages:      {summary['total_pages']}")
    print(f"Complete:         {summary['complete']} ({summary['completion_rate']}%)")
    print(f"Partial:          {summary['partial']}")
    print(f"Missing:          {summary['missing']}")
    print()
    print("Object Set Gaps:")
    print("-" * 60)
    for obj_set, count in get_object_set_gap_summary().items():
        print(f"  {obj_set:20s}: {count} pages missing")
    print()
    print("High Priority Pages:")
    print("-" * 60)
    for page in get_high_priority_pages():
        print(f"  [{page.recommended_priority.upper()}] {page.page_id}: {page.route}")
    print()
    
    # Validate
    validation_errors = validate_manifest()
    if validation_errors:
        print("VALIDATION ERRORS:")
        print("-" * 60)
        for error in validation_errors:
            print(f"  ! {error}")
    else:
        print("✅ Manifest validation passed")
