"""
Central compliance metadata and validation for Semptify modules and startup behavior.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from app.core.config import Settings
from app.core.security_config import get_security_settings

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = ROOT_DIR / "app"
MODULES_DIR = APP_DIR / "modules"
ROUTERS_DIR = APP_DIR / "routers"
SERVICES_DIR = APP_DIR / "services"


@dataclass(frozen=True)
class ModuleCompliance:
    name: str
    file_path: str
    status: str
    privacy_scope: str
    evidence_role: str
    security_notes: str
    next_action: str


def _normalize_name(path: Path, base_dir: Path, prefix: str) -> str:
    rel = path.with_suffix("").relative_to(base_dir)
    parts = [prefix] + [p for p in rel.parts if p != ""]
    return "_".join(parts)


def _describe_component(path: Path, category: str) -> ModuleCompliance:
    rel_path = path.relative_to(ROOT_DIR)
    display = rel_path.with_suffix("").as_posix()
    item = path.with_suffix("").relative_to(APP_DIR).as_posix()
    if category == "router":
        privacy_scope = (
            f"Handles HTTP routing for {display}. Must enforce auth, validate input, and avoid exposing unauthorized PII."
        )
        evidence_role = (
            f"Serves API endpoints for {item}, which support the application workflows and evidence flows."
        )
        security_notes = (
            "Require authorization, request validation, and logging for all exposed routes."
        )
        next_action = (
            f"Verify router {display} enforces access control and logs sensitive actions."
        )
    else:
        privacy_scope = (
            f"Implements service logic for {display}. Must isolate sensitive data, limit retention, and avoid unnecessary PII processing."
        )
        evidence_role = (
            f"Provides backend capabilities used by modules and routers, such as document processing or legal analysis."
        )
        security_notes = (
            "Validate inputs, handle secrets safely, and ensure service outputs do not leak sensitive state."
        )
        next_action = (
            f"Review service {display} for data handling, audit logging, and access restrictions."
        )

    return ModuleCompliance(
        name=_normalize_name(path, APP_DIR, category),
        file_path=str(rel_path.as_posix()),
        status="Implemented",
        privacy_scope=privacy_scope,
        evidence_role=evidence_role,
        security_notes=security_notes,
        next_action=next_action,
    )


def _discover_components(base_dir: Path, category: str) -> List[ModuleCompliance]:
    if not base_dir.exists():
        return []

    components: List[ModuleCompliance] = []
    for path in sorted(base_dir.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        components.append(_describe_component(path, category))
    return components


MODULE_COMPLIANCE_INVENTORY: List[ModuleCompliance] = [
    ModuleCompliance(
        name="tenant_defense",
        file_path="app/modules/tenant_defense.py",
        status="Implemented",
        privacy_scope="Handles tenant defense information and case narrative. Should avoid unnecessary PII beyond case context.",
        evidence_role="Builds defense arguments and stores case-related evidence references for court filings.",
        security_notes="Must route through module hub to preserve traceability and audit metadata.",
        next_action="Review hooks for module_hub updates and ensure audit logging on case state changes.",
    ),
    ModuleCompliance(
        name="research_module",
        file_path="app/modules/research_module.py",
        status="Implemented",
        privacy_scope="Research data is non-sensitive external legal information, but case-linked queries must not leak user identifiers.",
        evidence_role="Provides statute and case-law support for tenant claims.",
        security_notes="Ensure external research queries do not store private case details in logs or analytics.",
        next_action="Validate that AI/legal research requests sanitize case context before search.",
    ),
    ModuleCompliance(
        name="case_builder",
        file_path="app/modules/case_builder.py",
        status="Implemented",
        privacy_scope="Constructs the user’s case package; must preserve evidence chain and document provenance.",
        evidence_role="Assembles court-ready packets and links documents to timeline events.",
        security_notes="Case builder output should be generated only after storage OAuth and session validation.",
        next_action="Confirm case_builder does not duplicate raw document content outside the vault or storage service.",
    ),
    ModuleCompliance(
        name="complaint_wizard_module",
        file_path="app/modules/complaint_wizard_module.py",
        status="Implemented",
        privacy_scope="Supports multi-agency complaints; should limit sensitive fields to only required complaint data.",
        evidence_role="Guides users through complaint filing while preserving agency deadlines and document attachments.",
        security_notes="Complaint wizard flows should honor storage access and not persist sensitive user documents in app DB.",
        next_action="Audit complaint flow for any temporary data retention beyond session lifetime.",
    ),
    ModuleCompliance(
        name="document_converter",
        file_path="app/modules/document_converter.py",
        status="Implemented",
        privacy_scope="Converts documents between formats; must maintain original document integrity and avoid data loss.",
        evidence_role="Supports court-ready export and document preservation for filings.",
        security_notes="Conversion artifacts should not remain cached beyond the active request.",
        next_action="Review document_converter handling of sensitive files and cleanup of temporary files.",
    ),
    ModuleCompliance(
        name="legal_filing_module",
        file_path="app/modules/legal_filing_module.py",
        status="Implemented (integration wrapper)",
        privacy_scope="Integrates legal filing router logic; should not introduce new storage or PII handling.",
        evidence_role="Connects filing workflows to the legal_filing router and compliance pipeline.",
        security_notes="The router must rely on storage OAuth and existing access controls, not bypass them.",
        next_action="Confirm the router’s file access is authorized and that module_hub routing is logged.",
    ),
    ModuleCompliance(
        name="example_payment_tracking",
        file_path="app/modules/example_payment_tracking.py",
        status="Implemented (example/sample module)",
        privacy_scope="Example payment tracking is a sample module; should be treated as non-production support.",
        evidence_role="Demonstrates module structure for financial tracking without core evidence reliance.",
        security_notes="Keep this module isolated from production compliance logic unless promoted to active feature.",
        next_action="Document its sample status clearly and avoid using it for essential tenant evidence flows.",
    ),
] + _discover_components(ROUTERS_DIR, "router") + _discover_components(SERVICES_DIR, "service")


def get_module_compliance_map() -> Dict[str, ModuleCompliance]:
    return {module.name: module for module in MODULE_COMPLIANCE_INVENTORY}


def validate_app_compliance(settings: Settings) -> None:
    """Validate startup compliance and module inventory at app initialization."""
    if settings.security_mode != "enforced":
        logger.warning(
            "Semptify started in SECURITY_MODE=%s. Set SECURITY_MODE=enforced for production deployments.",
            settings.security_mode,
        )

    if settings.security_mode == "enforced":
        security_settings = get_security_settings()
        security_settings.validate_production()
        logger.info("Production security validation passed.")

    missing_files = [
        module.file_path
        for module in MODULE_COMPLIANCE_INVENTORY
        if not (ROOT_DIR / module.file_path).exists()
    ]
    if missing_files:
        logger.warning(
            "Module compliance inventory contains missing files: %s",
            ", ".join(missing_files),
        )

    logger.debug(
        "Module compliance inventory loaded: %s",
        ", ".join(sorted(get_module_compliance_map().keys())),
    )
