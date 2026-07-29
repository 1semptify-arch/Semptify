"""Contract Loader — imports all module register.py files at startup.

This module is the single place where all FunctionGroupContract registrations
are triggered. Each module's register.py file calls register_function_group()
at import time. This loader imports them all so their contracts are in the
registry before the app serves requests.

Usage (in main.py):
    from app.core.contract_loader import load_all_contracts
    load_all_contracts()
"""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

# Modules with register.py files that contain FunctionGroupContract registrations.
# Add new modules here as they get contracts.
_MODULES_WITH_CONTRACTS: tuple[str, ...] = (
    # RECORD pillar
    "app.modules.vault.register",
    "app.modules.documents.register",
    "app.modules.timeline.register",
    "app.modules.intake.register",
    "app.modules.contacts.register",
    "app.modules.calendar.register",
    "app.modules.search.register",
    "app.modules.journal.register",
    # KNOW pillar
    "app.modules.state_laws.register",
    "app.modules.location.register",
    "app.modules.law_library.register",
    "app.modules.housing_accountability.register",
    "app.modules.eviction_defense.register",
    "app.modules.complaints.register",
    "app.modules.context_engine.register",
    # Infrastructure
    "app.modules.onboarding.register_contracts",
    "app.modules.auth.register",
    "app.modules.storage.register",
    "app.modules.communication.register",
    "app.modules.health.register",
    "app.modules.security.register",
    "app.modules.dashboard.register",
    "app.modules.role_ui.register",
    "app.modules.analytics.register",
    "app.modules.documentation.register",
    "app.modules.page_editor.register",
    # Secondary (already had contracts)
    "app.modules.advocate.register",
    "app.modules.manager.register",
    "app.modules.legal.register",
    "app.modules.admin_console.module_admin_console",
    "app.modules.rent.register",
    "app.modules.court_forms.register",
    "app.modules.dev_lab.router",
    "app.modules.dev_lab.ideas",
    "app.modules.user.register",
    # Tertiary (newly added)
    "app.modules.preview.register",
    "app.modules.pdf_tools.register",
    "app.modules.document_converter.register",
    "app.modules.legal_analysis.register",
    "app.modules.free_api.register",
    "app.modules.invite_codes.register",
    "app.modules.document_delivery.register",
    "app.modules.court_packet.register",
    "app.modules.legal_trails.register",
    "app.modules.capabilities.register",
    "app.modules.tenancy_hub.register",
    "app.modules.case_builder.register",
    "app.modules.packet_builder.register",
    "app.modules.plan_maker.register",
    "app.modules.dispute_tracker.register",
    "app.modules.public_forms.register",
    "app.modules.guided_intake.register",
    # Phase 1d: Remaining modules (auto-generated)
    "app.modules.actions.register",
    "app.modules.auto_mode.register",
    "app.modules.batch.register",
    "app.modules.brain.register",
    "app.modules.briefcase.register",
    "app.modules.campaign.register",
    "app.modules.cloud_sync.register",
    "app.modules.components.register",
    "app.modules.context_loop.register",
    "app.modules.crawler.register",
    "app.modules.data_freshness.register",
    "app.modules.development.register",
    "app.modules.emotion.register",
    "app.modules.enterprise_dashboard.register",
    "app.modules.export_import.register",
    "app.modules.extraction.register",
    "app.modules.fems.register",
    "app.modules.filedored.register",
    "app.modules.form_data.register",
    "app.modules.fraud_exposure.register",
    "app.modules.functionx.register",
    "app.modules.funding_mgmt.register",
    "app.modules.funding_search.register",
    "app.modules.hud_funding.register",
    "app.modules.inventory.register",
    "app.modules.legal_filing.register",
    "app.modules.mesh_network.register",
    "app.modules.mndes.register",
    "app.modules.module_hub.register",
    "app.modules.page_index.register",
    "app.modules.plugins.register",
    "app.modules.positronic_mesh.register",
    "app.modules.preamble.register",
    "app.modules.progress.register",
    "app.modules.public_exposure.register",
    "app.modules.recognition.register",
    "app.modules.registry.register",
    "app.modules.research.register",
    "app.modules.risc.register",
    "app.modules.role_upgrade.register",
    "app.modules.setup.register",
    "app.modules.tactics.register",
    "app.modules.testing.register",
    "app.modules.tools_api.register",
    "app.modules.unified_overlays.register",
    "app.modules.vault_engine.register",
    "app.modules.websocket.register",
    "app.modules.workflow.register",
    "app.modules.workflow_validator.register",
    "app.modules.zoom_court.register",
    "app.modules.zoom_court_prep.register",
    "app.modules.dev_lab.register",
    # Phase 1e: Manually written (non-standard router names)
    "app.modules.core_system.register",
    "app.modules.external_mappings.register",
    # Phase 1A/1B: UI Composer + Tenant Feed (Hybrid Contextual GUI)
    "app.modules.ui_composer.register",
    "app.modules.tenant_feed.register",
    # NOTE: litigation_intelligence.register excluded — module is INACTIVE in manifest
    # and has a pre-existing SyntaxError in router.py (non-default arg after default arg).
    # Services with contracts
    "app.services.unified_overlay_manager",
    "app.services.communication_service",
    "app.services.document_delivery_service",
    "app.services.vault_upload_service",
    "app.services.duplicate_detection_service",
    "app.services.filedored_service",
    "app.services.timeline_chronology",
    "app.services.vault_ingestion",
    "app.services.vault_search",
    "app.core.semptify_internal_sdk",
)


def load_all_contracts() -> dict[str, int]:
    """Import all module register.py files to trigger contract registration.

    Returns a dict with 'loaded' and 'failed' counts. Failures are logged
    but do not raise — contracts are non-fatal to app startup.
    """
    loaded = 0
    failed = 0

    for module_path in _MODULES_WITH_CONTRACTS:
        try:
            importlib.import_module(module_path)
            loaded += 1
        except Exception as e:
            logger.warning(f"Contract load failed for {module_path}: {e}")
            failed += 1

    from app.core.module_contracts import contract_registry

    total = len(contract_registry.list_contracts())
    logger.info(f"Contract registry loaded: {total} contracts ({loaded} modules ok, {failed} failed)")

    return {"loaded": loaded, "failed": failed, "total_contracts": total}
