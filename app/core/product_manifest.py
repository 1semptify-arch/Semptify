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

from app.core.upl_guardrails import UPLRiskTier

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

        --- Module Flag Overlay (Phase 2.1) ---
        lifecycle: Maturity stage. One of:
            "stable"        — production-ready, all roles per requires_role
            "beta"          — admin + users with beta_dashboard flag
            "experimental"  — admin + users with experimental_ui flag
            "dev_only"      — admin only, in active development
            "preview"       — admin only, not for active use (demo/placeholder)
            "internal"      — first-party, trusted (alias for stable + origin=internal)
        origin: "internal" (first-party) or "external" (third-party, sandboxed)
        requires_role: Tuple of roles allowed to use this module (empty = all roles)
        requires_jurisdiction: Tuple of jurisdictions (e.g. ("MN",)) (empty = all)
        requires_gate: Gate that must be set before module is usable (e.g. "vault_initialized")
        feature_flag: Optional Feature enum value that gates this module at runtime
        dev_notes: Developer notes for unfinished work, stubs, or pending decisions

        --- UPL Risk Tier ---
        upl_risk_tier: Unauthorized Practice of Law risk classification for this
            module's output. Defaults to LOW (safest). Every module MUST declare
            its tier — see app/core/upl_guardrails.py for the enum and enforcement
            rules. Modules at MEDIUM_HIGH+ must display the canonical disclaimer
            and referral block on output surfaces.

        --- External Module Fields (ignored for internal modules) ---
        external_repo: Git URL for external module source
        external_version: Pinned version string
        external_signature: Content hash (sha256:...) for integrity verification
        external_sandbox: If True, run in isolated sandbox with restricted permissions
    """

    module_path: str
    router_attr: str = "router"
    tags: tuple[str, ...] = ()
    prefix: str = ""
    optional: bool = True
    tier: ProductTier = ProductTier.CORE
    log_message: str = ""

    # Module Flag Overlay (Phase 2.1)
    lifecycle: str = "stable"
    origin: str = "internal"
    requires_role: tuple[str, ...] = ()
    requires_jurisdiction: tuple[str, ...] = ()
    requires_gate: str = ""
    feature_flag: str = ""
    dev_notes: str = ""

    # UPL risk tier — Unauthorized Practice of Law classification
    # Defaults to LOW (safest). Legal-adjacent modules MUST override.
    # See app/core/upl_guardrails.py for tier definitions and enforcement rules.
    upl_risk_tier: UPLRiskTier = UPLRiskTier.LOW

    # External module fields (ignored for internal)
    external_repo: str = ""
    external_version: str = ""
    external_signature: str = ""
    external_sandbox: bool = True

    def __post_init__(self) -> None:
        # Tags must be non-empty for OpenAPI discoverability
        if not self.tags:
            object.__setattr__(
                self, "tags", (self._default_tag(),)
            )
        # Validate lifecycle against allowed values
        allowed_lifecycles = ("stable", "beta", "experimental", "dev_only", "preview", "internal", "deprecated")
        if self.lifecycle not in allowed_lifecycles:
            raise ValueError(
                f"ModuleEntry {self.module_path}: lifecycle '{self.lifecycle}' "
                f"is invalid. Must be one of {allowed_lifecycles}"
            )
        # Validate origin
        if self.origin not in ("internal", "external"):
            raise ValueError(
                f"ModuleEntry {self.module_path}: origin '{self.origin}' "
                f"is invalid. Must be 'internal' or 'external'"
            )
        # External modules must have external_repo
        if self.origin == "external" and not self.external_repo:
            raise ValueError(
                f"ModuleEntry {self.module_path}: origin='external' requires "
                f"external_repo to be set"
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

    @property
    def is_external(self) -> bool:
        """True if this is a third-party module requiring sandboxed execution."""
        return self.origin == "external"

    @property
    def is_dev_only(self) -> bool:
        """True if this module is in active development and admin-only."""
        return self.lifecycle == "dev_only"

    @property
    def is_preview(self) -> bool:
        """True if this module is a placeholder/demo not for active use."""
        return self.lifecycle == "preview"

    @property
    def visibility_label(self) -> str:
        """Human-readable visibility for admin UI."""
        if self.lifecycle == "dev_only":
            return "Admin only (in development)"
        if self.lifecycle == "preview":
            return "Admin only (preview/placeholder)"
        if self.lifecycle == "experimental":
            return "Admin + experimental_ui flag"
        if self.lifecycle == "beta":
            return "Admin + beta_dashboard flag"
        if self.lifecycle in ("stable", "internal"):
            return "All roles per requires_role"
        return self.lifecycle


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

    def by_lifecycle(self, *lifecycles: str) -> list[ModuleEntry]:
        """Return entries matching the requested lifecycle stages."""
        lc_set = set(lifecycles)
        return [e for e in self._entries if e.lifecycle in lc_set]

    def by_origin(self, origin: str) -> list[ModuleEntry]:
        """Return entries matching the requested origin ('internal' or 'external')."""
        return [e for e in self._entries if e.origin == origin]

    def external(self) -> list[ModuleEntry]:
        """Return all external (third-party) entries."""
        return [e for e in self._entries if e.origin == "external"]

    def dev_only(self) -> list[ModuleEntry]:
        """Return all dev_only entries (admin-only, in active development)."""
        return [e for e in self._entries if e.lifecycle == "dev_only"]

    def preview(self) -> list[ModuleEntry]:
        """Return all preview entries (admin-only, placeholder/demo)."""
        return [e for e in self._entries if e.lifecycle == "preview"]

    def find(self, module_path: str) -> ModuleEntry | None:
        """Find an entry by module_path. Returns None if not found."""
        for e in self._entries:
            if e.module_path == module_path:
                return e
        return None

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

    def summary(self) -> dict:
        """Return a summary dict of the manifest for admin UI / diagnostics."""
        by_tier_count: dict[str, int] = {}
        by_lifecycle_count: dict[str, int] = {}
        by_origin_count: dict[str, int] = {}
        for e in self._entries:
            by_tier_count[e.tier.value] = by_tier_count.get(e.tier.value, 0) + 1
            by_lifecycle_count[e.lifecycle] = by_lifecycle_count.get(e.lifecycle, 0) + 1
            by_origin_count[e.origin] = by_origin_count.get(e.origin, 0) + 1
        return {
            "total": len(self._entries),
            "by_tier": by_tier_count,
            "by_lifecycle": by_lifecycle_count,
            "by_origin": by_origin_count,
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
    # Module Flag Overlay (Phase 2.1)
    lifecycle: str = "stable",
    origin: str = "internal",
    requires_role: tuple[str, ...] = (),
    requires_jurisdiction: tuple[str, ...] = (),
    requires_gate: str = "",
    feature_flag: str = "",
    dev_notes: str = "",
    upl_risk_tier: UPLRiskTier = UPLRiskTier.LOW,
    # External module fields
    external_repo: str = "",
    external_version: str = "",
    external_signature: str = "",
    external_sandbox: bool = True,
) -> ModuleEntry:
    """Convenience helper to create and register a ModuleEntry in one call.

    Accepts all Module Flag Overlay fields (Phase 2.1) in addition to the
    original registration fields. Existing callers do not need to change —
    new fields default to safe values (lifecycle='stable', origin='internal').
    """
    entry = ModuleEntry(
        module_path=module_path,
        router_attr=router_attr,
        tags=tags,
        prefix=prefix,
        optional=optional,
        tier=tier,
        log_message=log_message,
        lifecycle=lifecycle,
        origin=origin,
        requires_role=requires_role,
        requires_jurisdiction=requires_jurisdiction,
        requires_gate=requires_gate,
        feature_flag=feature_flag,
        dev_notes=dev_notes,
        upl_risk_tier=upl_risk_tier,
        external_repo=external_repo,
        external_version=external_version,
        external_signature=external_signature,
        external_sandbox=external_sandbox,
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
_register("app.modules.vault.router", prefix="/api/vault", tags=("Document Vault",), tier=ProductTier.CORE,
          dev_notes="Canonical document storage vault. Upload, certify, and serve documents from the user's cloud provider. UI uploads go through /api/intake/upload/auto.")
_register("app.modules.vault_engine.router", prefix="/api/vault-engine", tags=("Vault Engine", "Access Control"), tier=ProductTier.CORE,
          lifecycle="dev_only", requires_role=("admin",),
          dev_notes="Access-control engine for vault resources (permissions, sharing, audit). Distinct from document-storage vault. Not yet user-facing.")
_register("app.modules.timeline.router", prefix="/api/timeline", tags=("Unified Timeline",), tier=ProductTier.CORE)
_register("app.modules.briefcase.router", tags=("Briefcase",), tier=ProductTier.CORE)
_register("app.modules.workflow.router", tags=("Workflow",), tier=ProductTier.CORE)
_register("app.modules.workflow_validator.router", tags=("Admin",), tier=ProductTier.CORE)

# Rights & education
_register("app.modules.state_laws.router", tags=("State Laws",), tier=ProductTier.CORE,
          lifecycle="beta", upl_risk_tier=UPLRiskTier.LOW,
          dev_notes="6 states complete (MN, NY, CA, TX, FL, IL). 43 states remain stubs with external resource links only.")
_register("app.modules.law_library.router", tags=("Law Library",), tier=ProductTier.CORE,
          upl_risk_tier=UPLRiskTier.LOW)
_register("app.modules.law_library.router", router_attr="page_router", tags=("Law Library",), tier=ProductTier.CORE,
          log_message="Law Library page route active at /law-library",
          upl_risk_tier=UPLRiskTier.LOW)

# Core tools
_register("app.modules.contacts.router", tags=("Contact Manager",), tier=ProductTier.CORE)
_register("app.modules.public_forms.router", tags=("Public Forms",), tier=ProductTier.CORE)
_register("app.modules.search.router", prefix="/api/search", tags=("Global Search",), tier=ProductTier.CORE)
_register("app.modules.pdf_tools.router", tags=("PDF Tools",), tier=ProductTier.CORE)
_register("app.modules.preview.router", prefix="/api/preview", tags=("Document Preview",), tier=ProductTier.CORE,
          log_message="Document Preview router connected - Multi-format preview generation active")
_register("app.modules.document_converter.router", tags=("Document Converter",), tier=ProductTier.CORE,
          dev_notes="Canonical document converter module. Legacy app/modules/document_converter.py standalone file removed — it was shadowed by this package.")
_register("app.modules.legal_analysis.router", tags=("Legal Analysis",), tier=ProductTier.CORE,
          upl_risk_tier=UPLRiskTier.LOW_MEDIUM)
_register("app.modules.context_engine.router", tags=("Context Engine", "Facts", "Stories"), tier=ProductTier.CORE,
          dev_notes="Verified-facts + tenant-stories engine. Distinct from context_loop (runtime state/event loop).",
          log_message="Context Engine router connected — verified facts + tenant stories active")
_register("app.modules.page_composer.router", tags=("Page Composer", "Facts", "Stories", "Case"), tier=ProductTier.CORE,
          log_message="Page Composer router connected — unified page view (facts + stories + case)")

# Public portal — guest portal + services catalog for semptify.org
_register("app.modules.portal.router", tags=("Portal", "Public", "Services"), tier=ProductTier.CORE,
          log_message="Portal router connected — guest portal + services catalog active at /api/portal")
_register("app.modules.portal.router", router_attr="seo_router", tags=("Portal", "SEO"), tier=ProductTier.CORE,
          log_message="Portal SEO router connected — sitemap.xml + robots.txt active")

# UI Composer — self-assembling tenant GUI (Phase 1A)
_register("app.modules.ui_composer.router", tags=("UI Composer", "GUI"), tier=ProductTier.CORE,
          log_message="UI Composer router connected — /api/ui/page, /api/ui/fragment, /api/ui/process active")

# Tenant Feed Aggregator — RECORD pillar data source (Phase 1B)
_register("app.modules.tenant_feed.router", tags=("Tenant Feed", "RECORD"), tier=ProductTier.CORE,
          log_message="Tenant Feed router connected — /api/tenant/feed active (aggregated timeline)")

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
          lifecycle="beta",
          dev_notes="3 NotImplementedError pending external MN Supreme Court API. Contact EAST team.",
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

_register("app.modules.eviction_defense.router", tags=("Eviction Defense Toolkit",), tier=ProductTier.EXTENDED,
          upl_risk_tier=UPLRiskTier.HIGH,
          dev_notes="Canonical eviction-defense toolkit. Legacy app/modules/tenant_defense.py standalone file removed — it was shadowed by this router.")
_register("app.modules.zoom_court.router", tags=("Zoom Courtroom",), tier=ProductTier.EXTENDED)
_register("app.modules.zoom_court_prep.router", tags=("Zoom Court Prep",), tier=ProductTier.EXTENDED)
_register("app.modules.court_forms.router", tags=("Court Forms",), tier=ProductTier.EXTENDED,
          upl_risk_tier=UPLRiskTier.HIGH)
_register("app.modules.court_packet.router", tags=("Court Packet",), tier=ProductTier.EXTENDED,
          upl_risk_tier=UPLRiskTier.MEDIUM)
# _register("app.modules.legal_filing.router", tags=("Legal Filing",), tier=ProductTier.EXTENDED)  # INACTIVE: Not integrated with mesh/network
_register("app.modules.legal_trails.router", tags=("Legal Trails",), tier=ProductTier.EXTENDED)
_register("app.modules.legal.router", tags=("Legal", "Court Filing", "Discovery", "Exhibits", "Workspace"), tier=ProductTier.EXTENDED,
          upl_risk_tier=UPLRiskTier.MEDIUM_HIGH,
          log_message="Legal workspace router connected — matters, filings, discovery, exhibits active")

# Case management
_register("app.modules.intake.router", tags=("Document Intake",), tier=ProductTier.EXTENDED)
_register("app.modules.guided_intake.router", tags=("Guided Intake",), tier=ProductTier.EXTENDED)
_register("app.modules.case_builder.router", tags=("Case Builder",), tier=ProductTier.EXTENDED,
          upl_risk_tier=UPLRiskTier.MEDIUM,
          dev_notes="Canonical case-builder module. Legacy app/modules/case_builder.py standalone file removed — it was shadowed by this package.")
_register("app.modules.progress.router", tags=("Progress Tracker",), tier=ProductTier.EXTENDED)
_register("app.modules.actions.router", tags=("Smart Actions",), tier=ProductTier.EXTENDED)
_register("app.modules.plan_maker.router", tags=("Plan Maker",), tier=ProductTier.EXTENDED)
_register("app.modules.tools_api.router", tags=("Tools",), tier=ProductTier.EXTENDED)

# Complaints / accountability
_register("app.modules.complaints.router", tags=("Complaint Wizard",), tier=ProductTier.EXTENDED,
          log_message="Complaint Filing Wizard loaded - Regulatory accountability tools active",
          dev_notes="Canonical complaint-filing wizard. Legacy app/modules/complaint_wizard_module.py standalone (Mesh SDK, DISABLED in main.py) removed — shadowed by this router.")
_register("app.modules.housing_accountability.router", router_attr="accountability_router",
          tags=("Housing Accountability",), tier=ProductTier.EXTENDED,
          lifecycle="beta", dev_notes="detect_repeated_fees() fully implemented — groups by fee type, jurisdiction-aware legal basis, safe date parsing.")
_register("app.modules.housing_accountability.pattern_history", router_attr="pattern_history_router",
          tags=("Pattern History",), tier=ProductTier.EXTENDED,
          lifecycle="beta", dev_notes="Depends on housing_accountability pattern matching.")

# External system mappings (court cases, properties, agencies)
_register("app.modules.external_mappings.router", router_attr="mappings_router",
          tags=("External Mappings", "Court Cases", "Properties", "Agencies"), tier=ProductTier.EXTENDED,
          lifecycle="beta", dev_notes="Bridge between Semptify and external systems. CRUD for cross-system ID mappings.")

# Role management
_register("app.modules.role_upgrade.router", tags=("Role Management",), tier=ProductTier.EXTENDED)


# =============================================================================
# ADVOCATE TIER — Collaboration & Document Delivery (Disabled by Default)
# =============================================================================

_register("app.modules.document_delivery.router", tags=("Document Delivery",), tier=ProductTier.ADVOCATE)
_register("app.modules.communication.router", tags=("Communications",), tier=ProductTier.ADVOCATE)
_register("app.modules.invite_codes.router", tags=("Invite Codes",), tier=ProductTier.ADVOCATE)
_register("app.modules.advocate.router", tags=("Advocate", "Clients", "Case Management"), tier=ProductTier.ADVOCATE)


# =============================================================================
# ADMIN TIER — Dashboards, Analytics, Batch Ops (Disabled by Default)
# =============================================================================

_register("app.modules.admin_console.router", prefix="/admin-console", tags=("Admin Console",), tier=ProductTier.ADMIN,
          log_message="Admin Console router connected - System maintenance and diagnostics active")
_register("app.modules.admin_console.module_flags", tier=ProductTier.ADMIN,
          lifecycle="internal",
          requires_role=("admin",),
          dev_notes="Phase 2.4 — Module Flag Overlay admin UI. Provides /admin/api/module-flags endpoints for runtime lifecycle/feature_flag overrides.",
          log_message="Module Flag Overlay admin router active — /admin/api/module-flags")
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
_register("app.modules.manager.router", tags=("Manager", "Case Assignment", "Reporting", "Bulk Ops"), tier=ProductTier.ADMIN,
          log_message="Manager router connected — case assignment, reporting, bulk ops active")
_register("app.modules.funding_mgmt.router", tags=("Funding Management",), tier=ProductTier.ADMIN,
          lifecycle="beta", dev_notes="Admin-only funding dashboard and prospectus. Requires require_admin dependency.")


# =============================================================================
# RESEARCH TIER — AI Intelligence (Disabled by Default)
# =============================================================================

_register("app.modules.recognition.router", tags=("Document Recognition",), tier=ProductTier.RESEARCH)
_register("app.modules.extraction.router", tags=("Form Field Extraction",), tier=ProductTier.RESEARCH)
_register("app.modules.crawler.router", tags=("Crawler",), tier=ProductTier.RESEARCH)
_register("app.modules.research.router", tags=("Research Module",), tier=ProductTier.RESEARCH,
          dev_notes="Canonical landlord/property research router. Legacy app/modules/research_module.py standalone file removed — it was shadowed by this package.")
_register("app.modules.form_data.router", prefix="/api/form-data", tags=("Form Data Hub",), tier=ProductTier.RESEARCH)
# Old app.modules.overlays.router retired 2026-06-18 — superseded by unified_overlays.router (SSOT).
# 943-line legacy router removed from registration; no callers used /api/overlays/ paths.
_register("app.modules.unified_overlays.router", tags=("Unified Overlays",), tier=ProductTier.RESEARCH,
          log_message="Unified Overlays router connected - Non-destructive annotation system active")
_register("app.modules.cloud_sync.router", tags=("Cloud Sync",), tier=ProductTier.RESEARCH,
          log_message="Cloud Sync router connected - User-controlled data persistence active")

# AI infrastructure
# _register("app.modules.brain.router", prefix="/brain", tags=("Positronic Brain",), tier=ProductTier.RESEARCH,
#           lifecycle="experimental", feature_flag="experimental_ai_model",
#           dev_notes="Heavy service. Memory-optimized load. Guarded by ENABLE_HEAVY_SERVICES.",
#           log_message="Positronic Brain connected - Central intelligence hub active")
# _register("app.modules.auto_mode.router", tags=("Auto Mode",), tier=ProductTier.RESEARCH)  # INACTIVE: Not production-ready
# Tagged as preview in roadmap — not registered until production-ready
_register("app.modules.emotion.router", tags=("Emotion Engine",), tier=ProductTier.RESEARCH,
          lifecycle="experimental")
# _register("app.modules.positronic_mesh.router", prefix="/api", tags=("Positronic Mesh",), tier=ProductTier.RESEARCH,
#           lifecycle="experimental", feature_flag="experimental_ai_model",
#           dev_notes="Heavy service. Guarded by ENABLE_HEAVY_SERVICES.")
# _register("app.modules.mesh_network.router", prefix="/api", tags=("Mesh Network",), tier=ProductTier.RESEARCH,
#           lifecycle="experimental", feature_flag="beta_mesh_network")
_register("app.modules.module_hub.router", prefix="/api", tags=("Module Hub",), tier=ProductTier.RESEARCH,
          lifecycle="experimental", feature_flag="experimental_ui",
          dev_notes="Heavy service. Memory-optimized load.")
_register("app.modules.functionx.router", tags=("FunctionX",), tier=ProductTier.RESEARCH,
          lifecycle="dev_only", dev_notes="FunctionX concept — not yet defined.")

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
          dev_notes="17 live endpoints in lis_router. module_routes_list.txt route-count discrepancy resolved.",
          log_message="Litigation Intelligence System router connected - Justice-grade legal intelligence active")


# =============================================================================
# DEV TIER — Internal Tools (Enabled in Development)
# =============================================================================

_register("app.modules.setup.router", prefix="/api/setup", tags=("Setup Wizard",), tier=ProductTier.DEV)
_register("app.modules.page_index.router", tags=("Page Index",), tier=ProductTier.DEV)
_register("app.modules.page_editor.router", tags=("Page Editor",), tier=ProductTier.DEV,
          log_message="Page Editor router connected - Interactive editor for static & Jinja2 templates")
_register("app.modules.development.router", tags=("Development Tools",), tier=ProductTier.DEV)
_register("app.modules.dev_lab.router", prefix="/dev/lab", tags=("Dev Lab",), tier=ProductTier.DEV,
          lifecycle="dev_only", requires_role=("admin",),
          dev_notes="Phase 3.1a — Incubator hub for dev modules. Lists dev_only modules, runs tests, promotes lifecycle stages.",
          log_message="Dev Lab router active — /dev/lab (admin-only)")
_register("app.modules.agent_orchestrator.router", prefix="/api/agent-orchestrator", tags=("Agent Orchestrator",), tier=ProductTier.DEV,
          lifecycle="dev_only", requires_role=("admin",),
          dev_notes="Forge task queue for parallel agent work. v1 in-memory. Generates copy-paste prompts for the unlimited model fleet (GLM-5.2, SWE-1.6, SWE-1.7, Kimi 2.7) from workbook stub/duplicate rows.",
          log_message="Agent Orchestrator router active — /api/agent-orchestrator (admin-only)")
_register("app.modules.dev_lab.ideas", prefix="/dev/lab/ideas", tags=("Dev Ideas",), tier=ProductTier.DEV,
          lifecycle="dev_only", requires_role=("admin",),
          dev_notes="Phase 3.1b/3.6 — Idea submission pipeline. Submit/list/promote ideas to dev modules.",
          log_message="Dev Ideas router active — /dev/lab/ideas (admin-only)")
_register("app.modules.filedored.router", tags=("Filedored",), tier=ProductTier.DEV,
          log_message="Filedored router connected - Virtual document organization active")
_register("app.modules.data_freshness.router", tags=("Data Freshness",), tier=ProductTier.DEV,
          log_message="Data Freshness router connected - Automated data staleness prevention active")
_register("app.modules.inventory.router", tags=("Inventory Management",), tier=ProductTier.DEV,
          log_message="Inventory Management router connected - File rotation and dating system active")
_register("app.modules.judge.router", tags=("Judge", "Deprecated", "Merged Into Legal"), tier=ProductTier.DEV,
          lifecycle="deprecated", requires_role=("admin",),
          dev_notes="Judge role DEPRECATED 2026-06-23. Merged into Legal as sub_role='judge'. Stub for backward compat.",
          log_message="Judge module registered as deprecated (merged into Legal sub-role)")

# Calendar — Total Recollection Viewer (per user vision 2026-06-28)
_register("app.modules.calendar.router", prefix="/api/calendar", tags=("Calendar",), tier=ProductTier.DEV,
          lifecycle="beta",
          dev_notes="Total Recollection Viewer — appointments, ledger, court dates, contacts, communications, journal. Yearly→monthly→weekly→daily→hourly drill-down.")

# Tactics — Legal tactics development tools
_register("app.modules.tactics.router", tags=("Tactics",), tier=ProductTier.DEV,
          lifecycle="beta",
          dev_notes="Legal tactics recommendations, evidence checklist, pre-hearing timeline, retaliation/habitability checks.")

# Standalone module files (dev_only — not yet wired into main app flow)
_register("app.modules.example_payment_tracking", tags=("Payment Tracking",), tier=ProductTier.DEV,
          lifecycle="dev_only",
          dev_notes="Standalone payment tracking module with /payments router. Mesh SDK pattern.")
_register("app.modules.legal_filing_module", router_attr="legal_filing_router", tags=("Legal Filing",), tier=ProductTier.DEV,
          lifecycle="dev_only",
          dev_notes="Thin wrapper that mounts the legal_filing router from app.modules.legal_filing. 5 endpoints under /api/legal-filing.")
_register("app.modules.free_api_pack", tags=("Free API Pack",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          dev_notes="Free API registry — PropertyLookup, LandlordLookup, CourtScraper, Violations, Inspections, Statutes. No FastAPI router — utility classes only.")
_register("app.modules.vault_sync", tags=("Vault Sync",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          dev_notes=(
              "ON HOLD — user approved plan 2026-07-01, deferred until GUI Phase 1 ships. "
              "Live encrypted replica of Semptify metadata (journal, timeline, letters, deadlines, document pointers) "
              "streamed to user's own OAuth-connected cloud drive (Dropbox prototype first — true append API). "
              "AES-256-GCM chunk encryption with user-passphrase-derived key (server never stores plaintext). "
              "Background drain loop: batch flush every 3-5s OR 50 rows. Output: encrypted .jsonl on user's cloud. "
              "Open questions on revive: (1) Dropbox-only prototype — pending final OK, "
              "(2) passphrase model A per-session vs B persistent — user has not picked, "
              "(3) greenlight to scaffold — not yet. "
              "Files planned: __init__.py, register.py, router.py, sync_engine.py, providers/dropbox.py, "
              "crypto.py, sync_log.py + alembic migration for sync_log table. "
              "Does NOT touch documents (those already live in user's cloud). No PII, no OAuth tokens synced."
          ))

# =============================================================================
# UPL Matrix — Conceptual module registrations
# =============================================================================
# These modules are declared in the UPL risk matrix but do not yet have code.
# Registered here so their UPL tier is declared and ready for when they are
# built. All are dev_only, optional, no router — safe to import-fail.
# When a module is built, update its entry with the real module_path and
# move it to the appropriate tier block above.

_register("app.modules.eviction_notice_explainer", tags=("Eviction Notice Explainer",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          upl_risk_tier=UPLRiskTier.HIGH,
          dev_notes="Conceptual from UPL matrix. Explains eviction notices in plain language. HIGH tier — generates tailored legal analysis of a user's specific notice, requires attorney-review gate before output. No router yet.")
_register("app.modules.response_letter_generator", tags=("Response Letter Generator",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          upl_risk_tier=UPLRiskTier.HIGH,
          dev_notes="Conceptual from UPL matrix. Generates response letters (e.g. answer to complaint). HIGH tier — drafts documents intended to be filed, requires attorney-review gate. No router yet.")
_register("app.modules.eviction_defense_content", tags=("Eviction Defense Content",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          upl_risk_tier=UPLRiskTier.LOW,
          dev_notes="Conceptual from UPL matrix. Informational-only eviction defense content — plain-language facts and statutes, no filtering/selection flow, no tailored advice. LOW tier: pure facts and neutral listings. No router yet. DO NOT build a filtering or selection flow — that would move this to MEDIUM_HIGH+.")
_register("app.modules.ai_copilot", tags=("AI Copilot",), tier=ProductTier.DEV,
          lifecycle="dev_only", optional=True,
          upl_risk_tier=UPLRiskTier.LOW,
          dev_notes="Conceptual from UPL matrix. AI assistant for tenant questions. LOW tier per matrix — provides facts and organization, not legal advice. Banned-phrase checker in upl_guardrails.py is the safety net. No router yet.")

# Modules wired via main.py direct import (tracked here for manifest visibility)
_register("app.modules.context_loop.router", tags=("Context Loop",), tier=ProductTier.DEV,
          lifecycle="stable", optional=True,
          dev_notes="Runtime state/event loop (nervous system). Distinct from context_engine (verified-facts + tenant-stories engine). Wired via main.py subscribe_context_loop_events().")
_register("app.modules.vault_installer.routes", router_attr="router", tags=("Vault Installer",), tier=ProductTier.DEV,
          lifecycle="stable", optional=True,
          dev_notes="Simple vault installation endpoints. Wired via main.py register_vault_installer(). Uses routes.py not router.py.")

# Phase 2 / internal utilities
_register("app.modules.export_import.router", prefix="/api/export-import", tags=("Data Export/Import",), tier=ProductTier.DEV,
          log_message="Data Export/Import router connected - GDPR-compliant data management active")
_register("app.modules.testing.router", prefix="/api/testing", tags=("Automated Testing",), tier=ProductTier.DEV,
          log_message="Automated Testing router connected - Comprehensive testing framework active")
_register("app.modules.documentation.router", prefix="/api/docs", tags=("API Documentation",), tier=ProductTier.DEV,
          log_message="API Documentation router connected - Developer portal active")
_register("app.modules.document_center.router", prefix="/api/dc", tags=("Document Center",), tier=ProductTier.DEV,
          lifecycle="stable", requires_role=("admin",),
          dev_notes=(
              "Document Center — 3-pane GUI (left: vault list, center: viewer, right: overlays). "
              "✅ Slice 1: HTML shell. "
              "✅ Slice 2: real vault list from DB. "
              "✅ Slice 3: iframe/img/download viewer states + /view endpoint. "
              "✅ Slice 4: /overlays endpoint — synthesizes 6 progress items from VaultDocument metadata. "
              "✅ Slice 5: /type endpoint — DB persistence + DOCUMENT_CLASSIFICATION overlay + one-trip right-panel refresh. "
              "✅ Slice 6b: GET /api/dc/unlocks; renderUnlocks() async+cache; CSS extracted. "
              "✅ Slice 7: openOverlay() drill-down (items field + DOM toggle); "
              "_overlayDataByDoc cache; unlock invalidation on type save. "
              "✅ Slice 8: _formatExpandItems per-type formatting (pill, code, icons); "
              "OCR excerpt cap 200ch; items list cap 10. "
              "Forge: 28/28 smoke tests. 5 contracts. Promoted beta → stable 2026-06-28."
          ),
          log_message="Document Center router connected at /api/dc (stable — admin only)")


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
        "app.modules.legal.router",
        "app.modules.intake.router",
        "app.modules.guided_intake.router",
        "app.modules.plan_maker.router",
        # Plus collaboration
        "app.modules.document_delivery.router",
        "app.modules.communication.router",
        "app.modules.invite_codes.router",
        "app.modules.advocate.router",
    ],
    "manager": [
        "app.modules.documents.router",
        "app.modules.timeline.router",
        "app.modules.contacts.router",
        "app.modules.state_laws.router",
        "app.modules.search.router",
        "app.modules.manager.router",
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
