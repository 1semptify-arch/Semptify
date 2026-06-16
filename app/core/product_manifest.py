"""
Semptify Product Manifest — Single Source of Truth for Module Registration
==========================================================================

Purpose:
- Declare which routers belong to which product tier (CORE, EXTENDED, etc.)
- Eliminate the 200-line commented router-import blocks in main.py
- Make product boundaries explicit, testable, and enforceable
- Enable/disable entire product tiers with one line

Usage (in main.py):
    from app.core.product_manifest import ProductTier, register_tiers

    # Register only the core tenant-rights platform
    register_tiers(fastapi_app, ProductTier.CORE, ProductTier.DEV)

    # Future: enable extended legal tools
    # register_tiers(fastapi_app, ProductTier.CORE, ProductTier.EXTENDED)

Design Rules:
1. Every router entry knows its tier, module path, and import strategy.
2. Optional routers fail silently (ImportError/AttributeError logged as warning).
3. Required routers raise on import failure — the app should not start without them.
4. No business logic here. This is a declaration layer, not an execution layer.

==========================================================================
CAPABILITY SYSTEM CONTRACT — READ BEFORE ADDING ANY MODULE
==========================================================================

Every NEW Feature Module must do THREE things in this file:

  1. Add its module_path to CAPABILITY_DEFAULTS for every role that gets it
     by default. Admin is automatic — do NOT add to admin list.

  2. Call _register() in the correct tier block below (CORE / EXTENDED /
     ADVOCATE / ADMIN / RESEARCH / DEV). The module_path in _register()
     MUST be identical to the string used in CAPABILITY_DEFAULTS and in
     the require_capability() call inside the router itself.

  3. In the router file, add require_capability() as a router-level
     dependency so the gate is enforced on every endpoint automatically:

        from app.core.capabilities import require_capability
        router = APIRouter(
            dependencies=[Depends(require_capability("app.modules.X.router"))]
        )

Pipeline modules (context_loop, positronic_brain, vault services) are
EXEMPT from the capability system. They are always-on, never added to
CAPABILITY_DEFAULTS, and never gated with require_capability().

The string "app.modules.your_module.router" is the capability key.
It must be IDENTICAL in all three locations or the gate will not work.
==========================================================================
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# =============================================================================
# Product Tiers
# =============================================================================

class ProductTier(str, Enum):
    """Semptify product tiers. Each tier is a bounded context."""

    CORE = "core"
    """Tenant-rights essentials. Always enabled."""

    EXTENDED = "extended"
    """Legal tools: eviction defense, court forms, case builder."""

    ADVOCATE = "advocate"
    """Advocate network: document delivery, collaboration, invite codes."""

    ADMIN = "admin"
    """Dashboards, analytics, batch ops, registry."""

    RESEARCH = "research"
    """AI intelligence: recognition, extraction, crawlers, dossiers."""

    DEV = "dev"
    """Internal: setup wizard, page editor, development tools."""

    @classmethod
    def all(cls) -> list[ProductTier]:
        return [cls.CORE, cls.EXTENDED, cls.ADVOCATE, cls.ADMIN, cls.RESEARCH, cls.DEV]


# =============================================================================
# Module Entry
# =============================================================================

@dataclass(frozen=True)
class ModuleEntry:
    """Immutable declaration of a FastAPI router module.

    Attributes:
        module_path: Dotted Python path, e.g. "app.routers.documents"
        router_attr: Attribute holding the APIRouter on the module (default "router")
        tags: OpenAPI tag(s) for docs organization
        prefix: URL prefix, e.g. "/api/vault"
        optional: If True, import failure is logged and skipped. If False, app startup fails.
        tier: Which product tier this module belongs to
        log_message: Optional message logged on successful registration
    """

    module_path: str
    router_attr: str = "router"
    tags: tuple[str, ...] = ()
    prefix: str = ""
    optional: bool = True
    tier: ProductTier = ProductTier.CORE
    log_message: str = ""

    def __post_init__(self) -> None:
        # Tags must be non-empty for OpenAPI discoverability
        if not self.tags:
            object.__setattr__(
                self, "tags", (self._default_tag(),)
            )

    def _default_tag(self) -> str:
        """Derive a tag from the module name if none provided."""
        parts = self.module_path.split(".")
        name = parts[-1] if parts else "unknown"
        return name.replace("_", " ").title()

    @property
    def qualified_name(self) -> str:
        """Fully-qualified reference for debugging."""
        return f"{self.module_path}:{self.router_attr}"


# =============================================================================
# Manifest Registry
# =============================================================================

class _ManifestRegistry:
    """In-memory registry of all declared module entries."""

    def __init__(self) -> None:
        self._entries: list[ModuleEntry] = []

    def add(self, *entries: ModuleEntry) -> None:
        """Register one or more entries."""
        for entry in entries:
            if not isinstance(entry, ModuleEntry):
                raise TypeError(f"Expected ModuleEntry, got {type(entry).__name__}")
            self._entries.append(entry)

    def by_tier(self, *tiers: ProductTier) -> list[ModuleEntry]:
        """Return entries matching the requested tiers (ordered by registration)."""
        tier_set = set(tiers)
        return [e for e in self._entries if e.tier in tier_set]

    def all(self) -> list[ModuleEntry]:
        return list(self._entries)

    def validate(self) -> dict:
        """Check for duplicate module_path+router_attr combinations."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for entry in self._entries:
            key = entry.qualified_name
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        return {
            "total": len(self._entries),
            "duplicates": duplicates,
            "valid": len(duplicates) == 0,
        }


# =============================================================================
# Global Manifest Instance
# =============================================================================

MANIFEST = _ManifestRegistry()


def _register(
    module_path: str,
    router_attr: str = "router",
    tags: tuple[str, ...] = (),
    prefix: str = "",
    optional: bool = True,
    tier: ProductTier = ProductTier.CORE,
    log_message: str = "",
) -> ModuleEntry:
    """Convenience helper to create and register a ModuleEntry in one call."""
    entry = ModuleEntry(
        module_path=module_path,
        router_attr=router_attr,
        tags=tags,
        prefix=prefix,
        optional=optional,
        tier=tier,
        log_message=log_message,
    )
    MANIFEST.add(entry)
    return entry


# =============================================================================
# CORE TIER — Tenant-Rights Essentials (Always Active)
# =============================================================================

# Health & system
_register("app.modules.health.router", tags=("Health",), optional=False, tier=ProductTier.CORE)
_register("app.core.versioning", router_attr="version_router", tags=("System",), tier=ProductTier.CORE)

# Entry points & routing
_register("app.modules.preamble.router", tags=("Preamble",), tier=ProductTier.CORE)
_register("app.modules.risc.router", tags=("RISC",), tier=ProductTier.CORE)
_register("app.modules.role_ui.router", tags=("Role UI",), tier=ProductTier.CORE)

# Storage & identity
_register("app.modules.storage.router", tags=("Storage Auth",), tier=ProductTier.CORE)
_register("app.modules.user.router", tags=("User",), tier=ProductTier.CORE,
          log_message="User router active — act-as impersonation endpoints enabled")
_register("app.modules.rent.router", prefix="/api/rent", tags=("Rent Ledger",), tier=ProductTier.CORE,
          log_message="Rent ledger router active — payment tracking endpoints enabled")
_register("app.modules.auth.router", tags=("Authentication",), tier=ProductTier.CORE,
          log_message="Auth status router active at /api/auth/me")
_register("app.modules.onboarding.reconnect", tags=("Onboarding", "Reconnect"), tier=ProductTier.CORE,
          log_message="Reconnect router active at /storage/reconnect (owned by onboarding module)")

# Document & vault system
_register("app.modules.documents.router", tags=("Documents",), tier=ProductTier.CORE)
_register("app.modules.vault.router", prefix="/api/vault", tags=("Document Vault",), tier=ProductTier.CORE)
_register("app.modules.vault_engine.router", tags=("Vault Engine"), tier=ProductTier.CORE)
_register("app.modules.timeline.router", prefix="/api/timeline", tags=("Unified Timeline",), tier=ProductTier.CORE)
_register("app.modules.briefcase.router", tags=("Briefcase",), tier=ProductTier.CORE)
_register("app.modules.workflow.router", tags=("Workflow",), tier=ProductTier.CORE)
_register("app.modules.workflow_validator.router", tags=("Admin",), tier=ProductTier.CORE)

# Rights & education
_register("app.modules.state_laws.router", tags=("State Laws",), tier=ProductTier.CORE)
_register("app.modules.law_library.router", tags=("Law Library",), tier=ProductTier.CORE)
_register("app.modules.law_library.router", router_attr="page_router", tags=("Law Library",), tier=ProductTier.CORE,
          log_message="Law Library page route active at /law-library")

# Core tools
_register("app.modules.contacts.router", tags=("Contact Manager",), tier=ProductTier.CORE)
_register("app.modules.public_forms.router", tags=("Public Forms",), tier=ProductTier.CORE)
_register("app.modules.search.router", prefix="/api/search", tags=("Global Search",), tier=ProductTier.CORE)
_register("app.modules.pdf_tools.router", tags=("PDF Tools",), tier=ProductTier.CORE)
_register("app.modules.preview.router", prefix="/api/preview", tags=("Document Preview",), tier=ProductTier.CORE,
          log_message="Document Preview router connected - Multi-format preview generation active")
_register("app.modules.document_converter.router", tags=("Document Converter",), tier=ProductTier.CORE)
_register("app.modules.legal_analysis.router", tags=("Legal Analysis",), tier=ProductTier.CORE)

# Real-time
_register("app.modules.websocket.router", prefix="/ws", tags=("WebSocket Events",), tier=ProductTier.CORE)

# Free APIs
_register("app.modules.free_api.router", tags=("Free APIs",), tier=ProductTier.CORE)

# Plugins
# _register("app.modules.plugins.router", tags=("Plugin System",), tier=ProductTier.CORE)  # INACTIVE: Marketplace not built

# Modular components & core infrastructure
# _register("app.modules.components.router", tags=("Modular Components",), tier=ProductTier.CORE,
#           log_message="Modular Components router connected - Component system integration active")  # INACTIVE: Dev scaffolding
_register("app.modules.core_system.router", router_attr="core_router", tags=("Core System",), tier=ProductTier.CORE)
_register("app.modules.security.router", prefix="/api/security", tags=("Advanced Security",), tier=ProductTier.CORE,
          log_message="Advanced Security router connected - 2FA and session management active")

# MNDES — Court Exhibit System (MN Supreme Court Order ADM09-8010 compliance)
_register("app.modules.mndes.router", tags=("MNDES",), optional=False, tier=ProductTier.CORE,
          log_message="MNDES router loaded — Court Exhibit System active")


# =============================================================================
# EXTENDED TIER — Legal Tools & Advanced Features (Disabled by Default)
# =============================================================================

# FEMS — Forensic Evidence Management System
_register(
    "app.modules.fems.router",
    tags=("FEMS",),
    prefix="",
    optional=True,
    tier=ProductTier.EXTENDED,
    log_message="FEMS router loaded — Forensic Evidence Management active at /api/fems",
)

_register("app.modules.eviction_defense.router", tags=("Eviction Defense Toolkit",), tier=ProductTier.EXTENDED)
_register("app.modules.zoom_court.router", tags=("Zoom Courtroom",), tier=ProductTier.EXTENDED)
_register("app.modules.zoom_court_prep.router", tags=("Zoom Court Prep",), tier=ProductTier.EXTENDED)
_register("app.modules.court_forms.router", tags=("Court Forms",), tier=ProductTier.EXTENDED)
_register("app.modules.court_packet.router", tags=("Court Packet",), tier=ProductTier.EXTENDED)
# _register("app.modules.legal_filing.router", tags=("Legal Filing",), tier=ProductTier.EXTENDED)  # INACTIVE: Not integrated with mesh/network
_register("app.modules.legal_trails.router", tags=("Legal Trails",), tier=ProductTier.EXTENDED)
_register("app.modules.tenant_defense", tags=("Tenant Defense",), tier=ProductTier.EXTENDED,
          log_message="Tenant Defense module loaded - Evidence, petitions, and screening disputes")

# Case management
_register("app.modules.intake.router", tags=("Document Intake",), tier=ProductTier.EXTENDED)
_register("app.modules.guided_intake.router", tags=("Guided Intake",), tier=ProductTier.EXTENDED)
_register("app.modules.case_builder.router", tags=("Case Builder",), tier=ProductTier.EXTENDED)
_register("app.modules.progress.router", tags=("Progress Tracker",), tier=ProductTier.EXTENDED)
_register("app.modules.actions.router", tags=("Smart Actions",), tier=ProductTier.EXTENDED)
_register("app.modules.plan_maker.router", tags=("Plan Maker",), tier=ProductTier.EXTENDED)
_register("app.modules.tools_api.router", tags=("Tools",), tier=ProductTier.EXTENDED)

# Complaints / accountability
_register("app.modules.complaints.router", tags=("Complaint Wizard",), tier=ProductTier.EXTENDED,
          log_message="Complaint Filing Wizard loaded - Regulatory accountability tools active")
_register("app.modules.housing_accountability.router", router_attr="accountability_router",
          tags=("Housing Accountability",), tier=ProductTier.EXTENDED)
_register("app.modules.housing_accountability.pattern_history", router_attr="pattern_history_router",
          tags=("Pattern History",), tier=ProductTier.EXTENDED)

# Role management
_register("app.modules.role_upgrade.router", tags=("Role Management",), tier=ProductTier.EXTENDED)


# =============================================================================
# ADVOCATE TIER — Collaboration & Document Delivery (Disabled by Default)
# =============================================================================

_register("app.modules.document_delivery.router", tags=("Document Delivery",), tier=ProductTier.ADVOCATE)
_register("app.modules.communication.router", tags=("Communications",), tier=ProductTier.ADVOCATE)
_register("app.modules.invite_codes.router", tags=("Invite Codes",), tier=ProductTier.ADVOCATE)


# =============================================================================
# ADMIN TIER — Dashboards, Analytics, Batch Ops (Disabled by Default)
# =============================================================================

_register("app.modules.analytics.router", prefix="/api/analytics", tags=("Analytics",), tier=ProductTier.ADMIN,
          log_message="Analytics router connected - Usage and performance tracking active")
_register("app.modules.dashboard.router", tags=("Unified Dashboard",), tier=ProductTier.ADMIN)
_register("app.modules.enterprise_dashboard.router", tags=("Enterprise Dashboard",), tier=ProductTier.ADMIN)
_register("app.modules.batch.router", prefix="/api/batch", tags=("Batch Operations",), tier=ProductTier.ADMIN,
          log_message="Batch Operations router connected - Bulk document management active")
_register("app.modules.registry.router", tags=("Document Registry",), tier=ProductTier.ADMIN)
_register("app.modules.tenancy_hub.router", tags=("Tenancy Hub",), tier=ProductTier.ADMIN)
_register("app.modules.capabilities.router", prefix="", tags=("Capabilities",), tier=ProductTier.ADMIN,
          log_message="Capabilities router active — user capability and overlay management enabled")


# =============================================================================
# RESEARCH TIER — AI Intelligence (Disabled by Default)
# =============================================================================

_register("app.modules.recognition.router", tags=("Document Recognition",), tier=ProductTier.RESEARCH)
_register("app.modules.extraction.router", tags=("Form Field Extraction",), tier=ProductTier.RESEARCH)
_register("app.modules.crawler.router", tags=("Crawler",), tier=ProductTier.RESEARCH)
_register("app.modules.research.router", tags=("Research Module",), tier=ProductTier.RESEARCH)
_register("app.modules.form_data.router", prefix="/api/form-data", tags=("Form Data Hub",), tier=ProductTier.RESEARCH)
_register("app.modules.overlays.router", tags=("Document Overlays",), tier=ProductTier.RESEARCH,
          log_message="Document Overlays router connected - Non-destructive annotation system active")
_register("app.modules.unified_overlays.router", tags=("Unified Overlays",), tier=ProductTier.RESEARCH)
_register("app.modules.vault_all_in_one.router", tags=("ALL-IN-ONE Vault",), tier=ProductTier.RESEARCH,
          log_message="ALL-IN-ONE Vault router connected - Unified evidence vault with three-timestamp model active")
_register("app.modules.cloud_sync.router", tags=("Cloud Sync",), tier=ProductTier.RESEARCH,
          log_message="Cloud Sync router connected - User-controlled data persistence active")

# AI infrastructure
_register("app.modules.brain.router", prefix="/brain", tags=("Positronic Brain",), tier=ProductTier.RESEARCH,
          log_message="Positronic Brain connected - Central intelligence hub active")
# _register("app.modules.auto_mode.router", tags=("Auto Mode",), tier=ProductTier.RESEARCH)  # INACTIVE: Not production-ready
_register("app.modules.emotion.router", tags=("Emotion Engine",), tier=ProductTier.RESEARCH)
_register("app.modules.positronic_mesh.router", prefix="/api", tags=("Positronic Mesh",), tier=ProductTier.RESEARCH)
_register("app.modules.mesh_network.router", prefix="/api", tags=("Mesh Network",), tier=ProductTier.RESEARCH)
_register("app.modules.module_hub.router", prefix="/api", tags=("Module Hub",), tier=ProductTier.RESEARCH)
_register("app.modules.functionx.router", tags=("FunctionX",), tier=ProductTier.RESEARCH)

# Funding / location
_register("app.modules.funding_search.router", tags=("Funding & Tax Credit Search",), tier=ProductTier.RESEARCH)
_register("app.modules.hud_funding.router", tags=("HUD Funding Guide",), tier=ProductTier.RESEARCH)
_register("app.modules.location.router", tags=("Location",), tier=ProductTier.RESEARCH)

# Campaign / public / fraud
_register("app.modules.campaign.router", tags=("Campaign Orchestration",), tier=ProductTier.RESEARCH)
_register("app.modules.public_exposure.router", tags=("Public Exposure",), tier=ProductTier.RESEARCH)
_register("app.modules.fraud_exposure.router", tags=("Fraud Exposure",), tier=ProductTier.RESEARCH)

# Litigation intelligence
_register("app.modules.litigation_intelligence.router", router_attr="lis_router",
          tags=("Litigation Intelligence",), tier=ProductTier.RESEARCH,
          log_message="Litigation Intelligence System router connected - Justice-grade legal intelligence active")


# =============================================================================
# DEV TIER — Internal Tools (Enabled in Development)
# =============================================================================

_register("app.modules.setup.router", prefix="/api/setup", tags=("Setup Wizard",), tier=ProductTier.DEV)
_register("app.modules.page_index.router", tags=("Page Index",), tier=ProductTier.DEV)
_register("app.modules.page_editor.router", tags=("Page Editor",), tier=ProductTier.DEV,
          log_message="Page Editor router connected - Interactive editor for static & Jinja2 templates")
_register("app.modules.development.router", tags=("Development Tools",), tier=ProductTier.DEV)
_register("app.modules.filedored.router", tags=("Filedored",), tier=ProductTier.DEV,
          log_message="Filedored router connected - Virtual document organization active")
_register("app.modules.data_freshness.router", tags=("Data Freshness",), tier=ProductTier.DEV,
          log_message="Data Freshness router connected - Automated data staleness prevention active")
_register("app.modules.inventory.router", tags=("Inventory Management",), tier=ProductTier.DEV,
          log_message="Inventory Management router connected - File rotation and dating system active")

# Phase 2 / internal utilities
_register("app.modules.export_import.router", prefix="/api/export-import", tags=("Data Export/Import",), tier=ProductTier.DEV,
          log_message="Data Export/Import router connected - GDPR-compliant data management active")
_register("app.modules.testing.router", prefix="/api/testing", tags=("Automated Testing",), tier=ProductTier.DEV,
          log_message="Automated Testing router connected - Comprehensive testing framework active")
_register("app.modules.documentation.router", prefix="/api/docs", tags=("API Documentation",), tier=ProductTier.DEV,
          log_message="API Documentation router connected - Developer portal active")


# =============================================================================
# Capability Defaults — Role-based Default Feature Module Sets
# =============================================================================
#
# These are the Feature Modules seeded into user_capabilities on first login.
# Keys match UserRole values: "tenant", "advocate", "manager", "admin".
# Values are module_path strings matching ModuleEntry.module_path.
#
# Rules:
# - Only Feature Modules go here. Pipeline modules are always-on, never listed.
# - Keep tenant defaults small — stressed users need clarity, not noise.
# - Advocate gets everything tenant gets plus collaboration tools.
# - Admin gets all tiers.
# - Adding a module here does NOT enable it for existing users — only new logins.
#   Use a migration or admin grant to backfill existing users.
# =============================================================================

CAPABILITY_DEFAULTS: dict[str, list[str]] = {
    "tenant": [
        "app.modules.vault.router",
        "app.modules.timeline.router",
        "app.modules.documents.router",
        "app.modules.state_laws.router",
        "app.modules.law_library.router",
        "app.modules.contacts.router",
        "app.modules.search.router",
    ],
    "advocate": [
        # Everything tenant gets
        "app.modules.vault.router",
        "app.modules.timeline.router",
        "app.modules.documents.router",
        "app.modules.state_laws.router",
        "app.modules.law_library.router",
        "app.modules.contacts.router",
        "app.modules.search.router",
        # Plus extended legal tools
        "app.modules.case_builder.router",
        "app.modules.eviction_defense.router",
        "app.modules.court_forms.router",
        "app.modules.legal_trails.router",
        "app.modules.intake.router",
        "app.modules.guided_intake.router",
        "app.modules.plan_maker.router",
        # Plus collaboration
        "app.modules.document_delivery.router",
        "app.modules.communication.router",
        "app.modules.invite_codes.router",
    ],
    "manager": [
        "app.modules.documents.router",
        "app.modules.timeline.router",
        "app.modules.contacts.router",
        "app.modules.state_laws.router",
        "app.modules.search.router",
    ],
    "admin": [
        # Admin gets all tiers — resolved at runtime from MANIFEST
        # This sentinel value triggers full-grant in seed_capability_defaults()
        "__all__",
    ],
}


# =============================================================================
# FUTURE: Role + Jurisdiction + Device Module Activation (NOT BUILT YET)
# =============================================================================
#
# ONRAMP PLAN — when ready to build:
#
# 1. Add optional fields to ModuleEntry:
#       requires_role: tuple[str, ...] = ()        # e.g. ("tenant", "advocate")
#       requires_jurisdiction: tuple[str, ...] = () # e.g. ("MN", "CA")
#       requires_gate: str = ""                     # e.g. "vault_initialized"
#
# 2. Build resolve_modules(role, jurisdiction, gates, device) → set[str]
#       Returns the set of module_paths the current user is allowed to use.
#       Lives in app/core/module_resolver.py
#
# 3. Add ModuleGateMiddleware — on each request check if the module is
#       in the user's resolved set. Return 403 if not.
#       No changes to startup — all routers stay mounted.
#       Enforcement is per-request, not per-startup.
#
# 4. True lazy loading (later, for mobile/low-resource devices):
#       Mount routers dynamically per session instead of at startup.
#
# DO NOT BUILD until basic system (CORE + EXTENDED) is stable and tested.
#
# =============================================================================

# =============================================================================
# Special / Dynamic Registrations (handled inline in main.py, not in manifest)
# =============================================================================
# These are imported dynamically inside create_app() and are NOT in the manifest
# because they require conditional logic beyond tier membership:
#
# - Dakota County eviction defense (conditional DAKOTA_AVAILABLE flag)
# - Any future feature-flagged modules that need runtime env checks
#
# Everything else is declared above and activated by tier membership.


# =============================================================================
# Registration API
# =============================================================================

def _load_router(entry: ModuleEntry):
    """Import a module and extract its router attribute.

    Returns the router object on success, None on failure (if optional).
    Raises ImportError/AttributeError if optional=False.
    """
    try:
        module = importlib.import_module(entry.module_path)
        return getattr(module, entry.router_attr)
    except (ImportError, AttributeError) as exc:
        if entry.optional:
            logger.warning(
                "Router import skipped (%s:%s): %s",
                entry.module_path,
                entry.router_attr,
                exc,
            )
            return None
        raise RuntimeError(
            f"Required router failed to load: {entry.qualified_name}"
        ) from exc


def register_tiers(app: FastAPI, *tiers: ProductTier) -> dict:
    """Register all module routers for the given product tiers.

    Args:
        app: The FastAPI application instance
        *tiers: One or more ProductTier values to enable

    Returns:
        Registration report: {"registered": int, "skipped": int, "errors": int}
    """
    if not tiers:
        raise ValueError("At least one ProductTier must be specified")

    entries = MANIFEST.by_tier(*tiers)
    registered = 0
    skipped = 0
    errors = 0

    logger.info("=" * 60)
    logger.info("Loading product tiers: %s", ", ".join(t.value for t in tiers))
    logger.info("=" * 60)

    for entry in entries:
        router = _load_router(entry)
        if router is None:
            skipped += 1
            continue

        kwargs: dict[str, object] = {"tags": list(entry.tags)}
        if entry.prefix:
            kwargs["prefix"] = entry.prefix

        try:
            app.include_router(router, **kwargs)
            registered += 1
            if entry.log_message:
                logger.info("   %s", entry.log_message)
        except Exception as exc:
            logger.error("Failed to include_router %s: %s", entry.qualified_name, exc)
            errors += 1

    logger.info("Modules: %d registered, %d skipped, %d errors", registered, skipped, errors)
    return {"registered": registered, "skipped": skipped, "errors": errors}


def register_all_tiers(app: FastAPI) -> dict:
    """Register every module in the manifest (all tiers). Useful for testing."""
    return register_tiers(app, *ProductTier.all())
