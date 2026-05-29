"""
Semptify Internal SDK - Single File for Module Integration
==========================================================

This is the ONE file internal modules need to integrate with Semptify.

It includes:
- Module registration and capabilities
- Product tier management
- Function group contracts
- Module hub for inter-module communication
- All enums and data structures

USAGE:
------
```python
from app.core.semptify_internal_sdk import (
    ModuleManifest,
    ModuleCapability,
    register_module,
    ProductTier,
    register_tier_modules,
    module_hub,
    InfoPack,
    PackType,
    ModuleType,
)

# Register a module
manifest = ModuleManifest(
    name="my_module",
    display_name="My Module",
    description="Does amazing things",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.my_module.router",
)
register_module(app, manifest)

# Use module hub for communication
await module_hub.route_document(
    user_id="user_123",
    document_id="doc_456",
    document_type="eviction_notice",
    extracted_data={"landlord_name": "John Doe"},
)
```
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from functools import wraps

from fastapi import FastAPI

from app.core.id_gen import make_id
from app.core.event_bus import event_bus, EventType as BusEventType

logger = logging.getLogger(__name__)


# =============================================================================
# PRODUCT TIERS
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
# MODULE CAPABILITIES
# =============================================================================

class ModuleCapability(str, Enum):
    """Capabilities a module can declare."""
    ROUTER = "router"           # Provides FastAPI routes
    CONTRACT = "contract"       # Declares function-group contracts
    MESH = "mesh"               # Integrates with Positronic Mesh
    DOCUMENT = "document"       # Handles document processing
    WIDGET = "widget"           # Provides UI widgets
    BACKGROUND = "background"   # Has background tasks


# =============================================================================
# MODULE TYPES (for Module Hub)
# =============================================================================

class ModuleType(str, Enum):
    """All registered module types"""
    EVICTION_DEFENSE = "eviction_defense"
    TIMELINE = "timeline"
    CALENDAR = "calendar"
    DOCUMENTS = "documents"
    VAULT = "vault"
    COPILOT = "copilot"
    FORMS = "forms"
    LAW_LIBRARY = "law_library"
    ZOOM_COURT = "zoom_court"
    CONTEXT_ENGINE = "context"
    ADAPTIVE_UI = "ui"
    COMPLAINT_WIZARD = "complaint_wizard"
    LOCATION = "location"
    HUD_FUNDING = "hud_funding"
    FRAUD_EXPOSURE = "fraud_exposure"
    PUBLIC_EXPOSURE = "public_exposure"
    RESEARCH = "research"
    LEGAL_TRAILS = "legal_trails"
    CUSTOM = "custom"


# =============================================================================
# DOCUMENT CATEGORIES
# =============================================================================

class DocumentCategory(str, Enum):
    """Document categories that trigger module routing"""
    EVICTION_NOTICE = "eviction_notice"
    LEASE = "lease"
    RENT_RECEIPT = "rent_receipt"
    REPAIR_REQUEST = "repair_request"
    COURT_SUMMONS = "court_summons"
    NOTICE_TO_QUIT = "notice_to_quit"
    PAY_OR_QUIT = "pay_or_quit"
    LEASE_VIOLATION = "lease_violation"
    COMMUNICATION = "communication"
    PHOTO_EVIDENCE = "photo_evidence"
    LEGAL_DOCUMENT = "legal_document"
    FINANCIAL = "financial"
    OTHER = "other"
    # SDK/backward-compatible aliases
    PAYMENT_RECORD = "payment_record"
    PHOTO = "photo"


# =============================================================================
# PACK TYPES
# =============================================================================

class PackType(str, Enum):
    """Types of info packs"""
    EVICTION_CASE = "eviction_case"
    LEASE_INFO = "lease_info"
    PAYMENT_HISTORY = "payment_history"
    REPAIR_ISSUE = "repair_issue"
    COURT_CASE = "court_case"
    TIMELINE_EVENTS = "timeline_events"
    CALENDAR_DEADLINES = "calendar_deadlines"
    DOCUMENT_ANALYSIS = "document_analysis"
    COMPLAINT_FILING = "complaint_filing"
    LOCATION_DATA = "location_data"
    HUD_FUNDING_INFO = "hud_funding_info"
    CASE_CONTEXT = "case_context"
    FRAUD_ANALYSIS = "fraud_analysis"
    # SDK/backward-compatible aliases
    EVICTION_DATA = "eviction_data"
    LEASE_DATA = "lease_data"
    CASE_DATA = "case_data"
    USER_DATA = "user_data"


# =============================================================================
# REQUEST TYPES
# =============================================================================

class RequestType(str, Enum):
    """Types of data requests modules can make"""
    GET_USER_DOCUMENTS = "get_user_documents"
    GET_DOCUMENT_BY_TYPE = "get_document_by_type"
    GET_TIMELINE_EVENTS = "get_timeline_events"
    GET_CALENDAR_DEADLINES = "get_calendar_deadlines"
    GET_CASE_INFO = "get_case_info"
    GET_LEASE_DATA = "get_lease_data"
    GET_PAYMENT_HISTORY = "get_payment_history"
    GET_LANDLORD_INFO = "get_landlord_info"
    GET_PROPERTY_INFO = "get_property_info"
    GET_APPLICABLE_LAWS = "get_applicable_laws"
    GET_USER_CONTEXT = "get_user_context"


# =============================================================================
# FUNCTION GROUP CONTRACTS
# =============================================================================

@dataclass(frozen=True)
class FunctionGroupContract:
    """Standard contract for a function-group within a module."""

    module: str
    group_name: str
    title: str
    description: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "group_name": self.group_name,
            "title": self.title,
            "description": self.description,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "dependencies": list(self.dependencies),
            "deterministic": self.deterministic,
        }


class ModuleContractRegistry:
    """In-memory registry for function-group contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, FunctionGroupContract] = {}

    @staticmethod
    def _make_key(module: str, group_name: str) -> str:
        return f"{module.strip().lower()}::{group_name.strip().lower()}"

    def register(self, contract: FunctionGroupContract) -> FunctionGroupContract:
        key = self._make_key(contract.module, contract.group_name)
        self._contracts[key] = contract
        return contract

    def list_contracts(self) -> list[FunctionGroupContract]:
        return list(self._contracts.values())

    def get(self, module: str, group_name: str) -> FunctionGroupContract | None:
        return self._contracts.get(self._make_key(module, group_name))

    def validate(self) -> dict[str, Any]:
        violations: list[dict[str, str]] = []

        for contract in self._contracts.values():
            if not contract.module.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "module must be non-empty",
                    }
                )
            if not contract.group_name.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "group_name must be non-empty",
                    }
                )
            if len(contract.outputs) == 0:
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "outputs must define at least one key",
                    }
                )

        return {
            "status": "pass" if not violations else "fail",
            "summary": {
                "total_contracts": len(self._contracts),
                "violations": len(violations),
            },
            "violations": violations,
        }


contract_registry = ModuleContractRegistry()


def register_function_group(contract: FunctionGroupContract) -> FunctionGroupContract:
    return contract_registry.register(contract)


# =============================================================================
# PRODUCT MANIFEST - MODULE ENTRY
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
# MANIFEST REGISTRY
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


# =============================================================================
# MODULE SDK - MANIFEST
# =============================================================================

@dataclass(frozen=True)
class ModuleManifest:
    """Immutable declaration of a Semptify module.

    This is the ONE thing module authors write to integrate.
    Everything else is derived or handled by ``register_module()``.
    """

    # Identity
    name: str
    display_name: str
    description: str
    version: str
    tier: ProductTier

    # Capabilities
    capabilities: Tuple[ModuleCapability, ...] = ()

    # Router configuration (only used when ModuleCapability.ROUTER present)
    router_module: Optional[str] = None
    router_attr: str = "router"
    tags: Tuple[str, ...] = ()
    prefix: str = ""

    # Contracts (only used when ModuleCapability.CONTRACT present)
    contracts: Tuple[FunctionGroupContract, ...] = ()

    # Mesh actions (only used when ModuleCapability.MESH present)
    mesh_actions: Tuple[str, ...] = ()

    # Registration behavior
    optional: bool = True

    def to_module_entry(self) -> Optional[ModuleEntry]:
        """Convert to a product-manifest ``ModuleEntry`` for router registration.

        Returns ``None`` if this module does not declare a router.
        """
        if ModuleCapability.ROUTER not in self.capabilities:
            return None
        if not self.router_module:
            return None
        return ModuleEntry(
            module_path=self.router_module,
            router_attr=self.router_attr,
            tags=self.tags,
            prefix=self.prefix,
            optional=self.optional,
            tier=self.tier,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (useful for /api/modules discovery)."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "tier": self.tier.value,
            "capabilities": [c.value for c in self.capabilities],
            "router_module": self.router_module,
            "prefix": self.prefix,
            "optional": self.optional,
        }


@dataclass
class InstalledModule:
    """Runtime representation of a module that has been registered."""
    manifest: ModuleManifest
    router: Any = None
    initialized: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.manifest.to_dict(),
            "initialized": self.initialized,
            "has_router": self.router is not None,
            "error": self.error,
        }


class ModuleRegistry:
    """Global singleton registry tracking all installed Semptify modules.

    Thread-safe for the normal read-heavy FastAPI async pattern.
    Writes happen once at startup, so no locking is needed.
    """

    _instance: Optional[ModuleRegistry] = None

    def __new__(cls) -> ModuleRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._modules: Dict[str, InstalledModule] = {}
        self._tier_index: Dict[ProductTier, List[str]] = {
            t: [] for t in ProductTier.all()
        }

    def install(self, module: InstalledModule) -> None:
        self._modules[module.manifest.name] = module
        self._tier_index[module.manifest.tier].append(module.manifest.name)
        logger.debug(
            "ModuleRegistry: installed %s (%s)",
            module.manifest.name,
            module.manifest.tier.value,
        )

    def get(self, name: str) -> Optional[InstalledModule]:
        return self._modules.get(name)

    def list_by_tier(self, tier: ProductTier) -> List[InstalledModule]:
        return [
            self._modules[n]
            for n in self._tier_index.get(tier, [])
            if n in self._modules
        ]

    def list_by_capability(self, capability: ModuleCapability) -> List[InstalledModule]:
        return [
            m for m in self._modules.values()
            if capability in m.manifest.capabilities
        ]

    def all(self) -> List[InstalledModule]:
        return list(self._modules.values())

    def validate(self) -> dict[str, Any]:
        """Validate the installed module set."""
        violations: List[dict[str, str]] = []
        for module in self._modules.values():
            m = module.manifest
            if ModuleCapability.ROUTER in m.capabilities and not m.router_module:
                violations.append({
                    "module": m.name,
                    "reason": "declares ROUTER but router_module is empty",
                })
            if ModuleCapability.CONTRACT in m.capabilities and not m.contracts:
                violations.append({
                    "module": m.name,
                    "reason": "declares CONTRACT but contracts is empty",
                })
        return {
            "valid": len(violations) == 0,
            "total": len(self._modules),
            "violations": violations,
        }


module_registry = ModuleRegistry()


def register_module(app: FastAPI, manifest: ModuleManifest) -> InstalledModule:
    """Register a single module with the Semptify platform.

    This is the **single entry point** for module authors.

    Steps:
    1. Registers the router via product manifest (if module declares ROUTER).
    2. Registers function-group contracts (if module declares CONTRACT).
    3. Tracks the module in the global ``ModuleRegistry``.

    Args:
        app: The FastAPI application instance.
        manifest: The module's declaration.

    Returns:
        The ``InstalledModule`` runtime record.
    """
    installed = InstalledModule(manifest=manifest)

    # 1. Router registration (delegated to product manifest)
    if ModuleCapability.ROUTER in manifest.capabilities and manifest.router_module:
        entry = manifest.to_module_entry()
        if entry is not None:
            try:
                router = _load_router(entry)
                if router is not None:
                    kwargs: Dict[str, Any] = {"tags": list(entry.tags)}
                    if entry.prefix:
                        kwargs["prefix"] = entry.prefix
                    app.include_router(router, **kwargs)
                    installed.router = router
                    logger.info(
                        "🔄 %s: router registered (%s)",
                        manifest.name,
                        entry.qualified_name,
                    )
                else:
                    installed.error = f"Router not found: {entry.qualified_name}"
                    if not entry.optional:
                        raise RuntimeError(installed.error)
                    logger.warning(
                        "ℹ️  %s: router skipped (optional, not found)",
                        manifest.name,
                    )
            except Exception as exc:
                installed.error = str(exc)
                if not entry.optional:
                    raise
                logger.warning("%s: router error (optional): %s", manifest.name, exc)

    # 2. Contract registration
    if ModuleCapability.CONTRACT in manifest.capabilities:
        for contract in manifest.contracts:
            contract_registry.register(contract)
            logger.info(
                "📋 %s: contract %s::%s registered",
                manifest.name,
                contract.module,
                contract.group_name,
            )

    # 3. Track in registry
    module_registry.install(installed)
    installed.initialized = True

    logger.info(
        "✅ Module installed: %s (%s) — capabilities=%s",
        manifest.name,
        manifest.tier.value,
        ", ".join(c.value for c in manifest.capabilities),
    )
    return installed


def register_tier_modules(app: FastAPI, *tiers: ProductTier) -> dict[str, Any]:
    """Batch-register all modules declared in the product manifest for the given tiers.

    Unlike ``register_tiers`` (which only registers *routers*), this also:
    - Installs each module into the ``ModuleRegistry``
    - Registers function-group contracts
    - Returns a full installation report

    Args:
        app: The FastAPI application instance.
        *tiers: One or more ``ProductTier`` values to enable.

    Returns:
        Installation report with ``installed``, ``skipped``, ``errors``, and
        ``modules`` keys.
    """
    if not tiers:
        raise ValueError("At least one ProductTier must be specified")

    entries = MANIFEST.by_tier(*tiers)
    installed_count = 0
    skipped_count = 0
    error_count = 0
    modules: List[InstalledModule] = []

    logger.info("=" * 60)
    logger.info("Registering modules for tiers: %s", ", ".join(t.value for t in tiers))
    logger.info("=" * 60)

    for entry in entries:
        manifest = ModuleManifest(
            name=entry.module_path.rsplit(".", 1)[-1],
            display_name=entry.tags[0] if entry.tags else entry.module_path,
            description="Auto-generated from product manifest",
            version="1.0.0",
            tier=entry.tier,
            capabilities=(ModuleCapability.ROUTER,),
            router_module=entry.module_path,
            router_attr=entry.router_attr,
            tags=entry.tags,
            prefix=entry.prefix,
            optional=entry.optional,
        )
        try:
            mod = register_module(app, manifest)
            modules.append(mod)
            if mod.router is not None:
                installed_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            error_count += 1
            logger.error("Failed to register %s: %s", manifest.name, exc)

    report = {
        "installed": installed_count,
        "skipped": skipped_count,
        "errors": error_count,
        "total": len(entries),
        "modules": [m.to_dict() for m in modules],
    }

    logger.info(
        "🚀 Module registration complete: %d installed, %d skipped, %d errors (of %d)",
        installed_count,
        skipped_count,
        error_count,
        len(entries),
    )
    return report


def get_module_status() -> dict[str, Any]:
    """Get the current status of all installed modules.

    Useful for a ``/api/modules`` health/status endpoint.
    """
    registry = ModuleRegistry()
    validation = registry.validate()
    return {
        "installed_modules": [m.to_dict() for m in registry.all()],
        "by_tier": {
            t.value: [m.manifest.name for m in registry.list_by_tier(t)]
            for t in ProductTier.all()
        },
        "by_capability": {
            c.value: [m.manifest.name for m in registry.list_by_capability(c)]
            for c in ModuleCapability
        },
        "validation": validation,
    }


# =============================================================================
# MODULE HUB - DATA STRUCTURES
# =============================================================================

@dataclass
class InfoPack:
    """
    An Info Pack - Pre-filled data bundle sent to modules.
    
    Created when document intake recognizes a document type
    and needs to initialize a module with relevant data.
    """
    id: str
    pack_type: PackType
    user_id: str
    source_document_id: Optional[str] = None
    target_module: Optional[ModuleType] = None
    
    # The actual data payload
    data: Dict[str, Any] = field(default_factory=dict)
    
    # What data is available vs what user needs to provide
    auto_filled: Dict[str, Any] = field(default_factory=dict)
    user_required: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    
    # Status tracking
    status: str = "pending"  # pending, sent, received, processed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    # Confidence scores for auto-filled data
    confidence: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pack_type": self.pack_type.value,
            "user_id": self.user_id,
            "source_document_id": self.source_document_id,
            "target_module": self.target_module.value if self.target_module else None,
            "data": self.data,
            "auto_filled": self.auto_filled,
            "user_required": self.user_required,
            "optional_fields": self.optional_fields,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "InfoPack":
        data["pack_type"] = PackType(data["pack_type"])
        if data.get("target_module"):
            data["target_module"] = ModuleType(data["target_module"])
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("processed_at") and isinstance(data["processed_at"], str):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        return cls(**data)


@dataclass
class DataRequest:
    """
    A data request from a module to the hub.
    
    Modules use this to request data they need from the central system.
    """
    id: str
    request_type: RequestType
    requesting_module: ModuleType
    user_id: str
    
    # Request parameters
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Response
    response_data: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_type": self.request_type.value,
            "requesting_module": self.requesting_module.value,
            "user_id": self.user_id,
            "params": self.params,
            "response_data": self.response_data,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ModuleUpdate:
    """
    An update from a module back to the hub.
    
    Modules send these when they have new data to share
    with other modules or the main application.
    """
    id: str
    source_module: ModuleType
    user_id: str
    update_type: str
    
    # The update data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Optional: which modules should receive this update
    target_modules: List[ModuleType] = field(default_factory=list)
    
    # Broadcast to all modules?
    broadcast: bool = False
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_module": self.source_module.value,
            "user_id": self.user_id,
            "update_type": self.update_type,
            "data": self.data,
            "target_modules": [m.value for m in self.target_modules],
            "broadcast": self.broadcast,
            "created_at": self.created_at.isoformat(),
        }


@dataclass 
class RegisteredModule:
    """A registered module in the hub"""
    module_type: ModuleType
    name: str
    description: str
    
    # What document types this module handles
    handles_documents: List[DocumentCategory] = field(default_factory=list)
    
    # What pack types this module accepts
    accepts_packs: List[PackType] = field(default_factory=list)
    
    # Callbacks
    on_pack_received: Optional[Callable] = None
    on_data_request: Optional[Callable] = None
    on_update_received: Optional[Callable] = None
    
    # Status
    active: bool = True
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# DOCUMENT ROUTING RULES
# =============================================================================

# Map document types to target modules and pack types
DOCUMENT_ROUTING = {
    DocumentCategory.EVICTION_NOTICE: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "critical",
        "auto_extract": [
            "landlord_name", "tenant_name", "property_address",
            "notice_date", "deadline_date", "reason", "amount_claimed"
        ],
        "user_required": [
            "county", "case_number"  # Often not on notice
        ],
    },
    DocumentCategory.COURT_SUMMONS: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.COURT_CASE,
        "priority": "critical",
        "auto_extract": [
            "case_number", "hearing_date", "hearing_time", "court_location",
            "judge_name", "plaintiff", "defendant"
        ],
        "user_required": [],
    },
    DocumentCategory.NOTICE_TO_QUIT: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "critical",
        "auto_extract": [
            "landlord_name", "notice_date", "quit_date", "reason"
        ],
        "user_required": ["property_address"],
    },
    DocumentCategory.PAY_OR_QUIT: {
        "target_module": ModuleType.EVICTION_DEFENSE,
        "pack_type": PackType.EVICTION_CASE,
        "priority": "high",
        "auto_extract": [
            "amount_due", "due_date", "landlord_name"
        ],
        "user_required": ["property_address"],
    },
    DocumentCategory.LEASE: {
        "target_module": ModuleType.DOCUMENTS,  # Goes to vault, but extracts lease info
        "pack_type": PackType.LEASE_INFO,
        "priority": "medium",
        "auto_extract": [
            "landlord_name", "tenant_name", "property_address",
            "lease_start", "lease_end", "rent_amount", "security_deposit"
        ],
        "user_required": [],
    },
    DocumentCategory.RENT_RECEIPT: {
        "target_module": ModuleType.TIMELINE,
        "pack_type": PackType.PAYMENT_HISTORY,
        "priority": "medium",
        "auto_extract": [
            "payment_date", "amount", "payment_method", "landlord_name"
        ],
        "user_required": [],
    },
    DocumentCategory.REPAIR_REQUEST: {
        "target_module": ModuleType.DOCUMENTS,
        "pack_type": PackType.REPAIR_ISSUE,
        "priority": "high",
        "auto_extract": [
            "request_date", "issue_description", "landlord_name"
        ],
        "user_required": [],
    },
}


# =============================================================================
# MODULE HUB - MAIN CLASS
# =============================================================================

class ModuleHub:
    """
    Module Hub - Bidirectional Communication System for All Modules

    This is the CENTRAL NERVOUS SYSTEM that connects all modules:
    - Document Intake → Creates Info Packs → Routes to appropriate modules
    - Modules can REQUEST data from the hub
    - Modules can SEND updates back to the hub
    - All communication is logged and traceable
    """

    def __init__(self):
        self._modules: Dict[ModuleType, RegisteredModule] = {}
        self._info_packs: Dict[str, InfoPack] = {}
        self._requests: List[DataRequest] = []
        self._updates: List[ModuleUpdate] = []
        self._user_stores: Dict[str, Dict[str, Any]] = {}  # user_id -> data store
        self._comm_log: List[Dict[str, Any]] = []

    # =========================================================================
    # MODULE REGISTRATION
    # =========================================================================

    def register_module(
        self,
        module_type: ModuleType,
        name: str,
        description: str,
        handles_documents: List[DocumentCategory] = None,
        accepts_packs: List[PackType] = None,
        on_pack_received: Callable = None,
        on_data_request: Callable = None,
        on_update_received: Callable = None,
    ):
        """Register a module with the hub"""
        module = RegisteredModule(
            module_type=module_type,
            name=name,
            description=description,
            handles_documents=handles_documents or [],
            accepts_packs=accepts_packs or [],
            on_pack_received=on_pack_received,
            on_data_request=on_data_request,
            on_update_received=on_update_received,
        )
        self._modules[module_type] = module
        logger.info(f"🔌 Module registered: {name} ({module_type.value})")

    # =========================================================================
    # INFO PACKS (Hub → Module)
    # =========================================================================

    def create_info_pack(
        self,
        source_module: str,
        pack_type: str,
        data: Dict[str, Any],
        user_id: str,
        target_module: Optional[str] = None,
    ) -> InfoPack:
        """Create an info pack (for external use)"""
        pack = InfoPack(
            id=make_id("pack"),
            pack_type=PackType(pack_type),
            user_id=user_id,
            source_document_id=None,
            target_module=ModuleType(target_module) if target_module else None,
            data=data,
        )
        self._info_packs[pack.id] = pack
        return pack

    async def route_document(
        self,
        user_id: str,
        document_id: str,
        document_type: str,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float] = None,
    ) -> Optional[InfoPack]:
        """
        Route a document to the appropriate module.
        
        Called by document pipeline after classification.
        Creates an Info Pack and sends it to the target module.
        """
        # Normalize document type
        try:
            doc_category = DocumentCategory(document_type.lower().replace(" ", "_"))
        except ValueError:
            doc_category = DocumentCategory.OTHER
        
        # Get routing rules
        routing = DOCUMENT_ROUTING.get(doc_category)
        if not routing:
            logger.info(f"No routing rule for document type: {doc_category}")
            return None
        
        # Create Info Pack
        pack = self._create_info_pack(
            user_id=user_id,
            document_id=document_id,
            doc_category=doc_category,
            routing=routing,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores or {},
        )
        
        # Store pack
        self._info_packs[pack.id] = pack
        
        # Send to target module
        await self._send_pack_to_module(pack)
        
        # Log
        self._log_comm(
            "route_document",
            routing["target_module"].value,
            {
                "document_id": document_id,
                "pack_id": pack.id,
                "pack_type": pack.pack_type.value,
            },
            user_id=user_id,
        )
        
        logger.info(
            f"📨 Document routed: {doc_category.value} → "
            f"{routing['target_module'].value} (pack: {pack.id})"
        )
        
        return pack

    def _create_info_pack(
        self,
        user_id: str,
        document_id: str,
        doc_category: DocumentCategory,
        routing: Dict,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float],
    ) -> InfoPack:
        """Create an Info Pack from extracted document data"""
        
        pack_id = make_id("pack")
        
        # Separate auto-filled from user-required
        auto_filled = {}
        for field in routing.get("auto_extract", []):
            if field in extracted_data:
                auto_filled[field] = extracted_data[field]
        
        # Get existing user data if available
        user_store = self._get_user_store(user_id)
        
        # Merge with existing data (don't overwrite if already have good data)
        for field, value in auto_filled.items():
            existing = user_store.get(field)
            existing_conf = user_store.get(f"{field}_confidence", 0)
            new_conf = confidence_scores.get(field, 0.5)
            
            if not existing or new_conf > existing_conf:
                user_store[field] = value
                user_store[f"{field}_confidence"] = new_conf
        
        # Build complete data package
        pack_data = {
            **auto_filled,
            "document_id": document_id,
            "document_type": doc_category.value,
            "priority": routing.get("priority", "medium"),
        }
        
        # Add any additional context from user store
        context_fields = [
            "landlord_name", "tenant_name", "property_address",
            "lease_start", "lease_end", "rent_amount"
        ]
        for field in context_fields:
            if field not in pack_data and field in user_store:
                pack_data[field] = user_store[field]
        
        return InfoPack(
            id=pack_id,
            pack_type=routing["pack_type"],
            user_id=user_id,
            source_document_id=document_id,
            target_module=routing["target_module"],
            data=pack_data,
            auto_filled=auto_filled,
            user_required=routing.get("user_required", []),
            optional_fields=routing.get("optional_fields", []),
            confidence=confidence_scores,
        )

    async def _send_pack_to_module(self, pack: InfoPack):
        """Send an Info Pack to its target module"""
        if not pack.target_module:
            return
        
        module = self._modules.get(pack.target_module)
        if not module:
            logger.warning(f"Target module not registered: {pack.target_module}")
            pack.status = "failed"
            return
        
        pack.status = "sent"
        
        # Call module's pack handler if registered
        if module.on_pack_received:
            try:
                if asyncio.iscoroutinefunction(module.on_pack_received):
                    await module.on_pack_received(pack)
                else:
                    module.on_pack_received(pack)
                pack.status = "received"
            except Exception as e:
                logger.error(f"Error sending pack to {pack.target_module}: {e}")
                pack.status = "failed"
        
        # Also publish to event bus
        await event_bus.publish(
            BusEventType.NOTIFICATION,
            {
                "type": "info_pack",
                "pack_id": pack.id,
                "pack_type": pack.pack_type.value,
                "target_module": pack.target_module.value,
                "priority": pack.data.get("priority", "medium"),
            },
            source="module_hub",
            user_id=pack.user_id,
        )

    # =========================================================================
    # DATA REQUESTS (Module → Hub)
    # =========================================================================

    async def request_data(
        self,
        requesting_module: ModuleType,
        request_type: RequestType,
        user_id: str,
        params: Dict[str, Any] = None,
    ) -> DataRequest:
        """
        Handle a data request from a module.
        
        Modules call this to get data they need from the hub.
        """
        request = DataRequest(
            id=make_id("req"),
            request_type=request_type,
            requesting_module=requesting_module,
            user_id=user_id,
            params=params or {},
        )
        
        self._requests.append(request)
        
        # Process the request
        try:
            request.status = "processing"
            response = await self._process_request(request)
            request.response_data = response
            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            request.status = "failed"
            request.error = str(e)
            logger.error(f"Request failed: {e}")
        
        self._log_comm(
            "data_request",
            requesting_module.value,
            {
                "request_type": request_type.value,
                "status": request.status,
            },
            user_id=user_id,
        )
        
        return request

    async def _process_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process a data request and return response data"""
        user_store = self._get_user_store(request.user_id)
        params = request.params
        
        handlers = {
            RequestType.GET_USER_DOCUMENTS: self._get_user_documents,
            RequestType.GET_DOCUMENT_BY_TYPE: self._get_document_by_type,
            RequestType.GET_TIMELINE_EVENTS: self._get_timeline_events,
            RequestType.GET_CALENDAR_DEADLINES: self._get_calendar_deadlines,
            RequestType.GET_CASE_INFO: self._get_case_info,
            RequestType.GET_LEASE_DATA: self._get_lease_data,
            RequestType.GET_PAYMENT_HISTORY: self._get_payment_history,
            RequestType.GET_LANDLORD_INFO: self._get_landlord_info,
            RequestType.GET_PROPERTY_INFO: self._get_property_info,
            RequestType.GET_APPLICABLE_LAWS: self._get_applicable_laws,
            RequestType.GET_USER_CONTEXT: self._get_user_context,
        }
        
        handler = handlers.get(request.request_type)
        if handler:
            return await handler(request.user_id, params)
        
        return {"error": f"Unknown request type: {request.request_type}"}

    async def _get_user_documents(self, user_id: str, params: Dict) -> Dict:
        """Get all documents for a user"""
        try:
            from app.services.document_pipeline import get_document_pipeline
            pipeline = get_document_pipeline()
            docs = pipeline.get_user_documents(user_id)
            return {
                "documents": [d.to_dict() for d in docs],
                "count": len(docs),
            }
        except Exception as e:
            return {"documents": [], "error": str(e)}

    async def _get_document_by_type(self, user_id: str, params: Dict) -> Dict:
        """Get documents filtered by type"""
        doc_type = params.get("type")
        try:
            from app.services.document_pipeline import get_document_pipeline
            from app.services.azure_ai import DocumentType
            pipeline = get_document_pipeline()
            docs = pipeline.get_user_documents_by_type(user_id, DocumentType(doc_type))
            return {
                "documents": [d.to_dict() for d in docs],
                "count": len(docs),
            }
        except Exception as e:
            return {"documents": [], "error": str(e)}

    async def _get_timeline_events(self, user_id: str, params: Dict) -> Dict:
        """Get timeline events for a user"""
        try:
            from app.services.document_pipeline import get_document_pipeline
            pipeline = get_document_pipeline()
            timeline = pipeline.get_timeline(user_id)
            return {
                "events": timeline,
                "count": len(timeline),
            }
        except Exception as e:
            return {"events": [], "error": str(e)}

    async def _get_calendar_deadlines(self, user_id: str, params: Dict) -> Dict:
        """Get calendar deadlines for a user"""
        user_store = self._get_user_store(user_id)
        deadlines = user_store.get("deadlines", [])
        return {
            "deadlines": deadlines,
            "count": len(deadlines),
        }

    async def _get_case_info(self, user_id: str, params: Dict) -> Dict:
        """Get eviction case info for a user"""
        user_store = self._get_user_store(user_id)
        case_fields = [
            "case_number", "hearing_date", "hearing_time", "court_location",
            "judge_name", "answer_deadline", "case_type", "filing_date"
        ]
        case_info = {k: user_store.get(k) for k in case_fields if k in user_store}
        return case_info

    async def _get_lease_data(self, user_id: str, params: Dict) -> Dict:
        """Get lease information for a user"""
        user_store = self._get_user_store(user_id)
        lease_fields = [
            "lease_start", "lease_end", "rent_amount", "security_deposit",
            "landlord_name", "property_address", "lease_terms"
        ]
        lease_data = {k: user_store.get(k) for k in lease_fields if k in user_store}
        return lease_data

    async def _get_payment_history(self, user_id: str, params: Dict) -> Dict:
        """Get payment history for a user"""
        user_store = self._get_user_store(user_id)
        return {
            "payments": user_store.get("payment_history", []),
        }

    async def _get_landlord_info(self, user_id: str, params: Dict) -> Dict:
        """Get landlord information"""
        user_store = self._get_user_store(user_id)
        landlord_fields = [
            "landlord_name", "landlord_address", "landlord_phone",
            "landlord_email", "property_manager"
        ]
        return {k: user_store.get(k) for k in landlord_fields if k in user_store}

    async def _get_property_info(self, user_id: str, params: Dict) -> Dict:
        """Get property information"""
        user_store = self._get_user_store(user_id)
        property_fields = [
            "property_address", "unit_number", "property_type",
            "move_in_date", "move_out_date"
        ]
        return {k: user_store.get(k) for k in property_fields if k in user_store}

    async def _get_applicable_laws(self, user_id: str, params: Dict) -> Dict:
        """Get applicable laws for user's situation"""
        user_store = self._get_user_store(user_id)
        try:
            from app.services.law_engine import get_law_engine
            law_engine = get_law_engine()
            return law_engine.get_applicable_laws(user_store)
        except Exception as e:
            return {"error": str(e)}

    async def _get_user_context(self, user_id: str, params: Dict) -> Dict:
        """Get full user context"""
        return self._get_user_store(user_id)

    # =========================================================================
    # MODULE UPDATES (Module → Hub)
    # =========================================================================

    async def send_update(
        self,
        source_module: ModuleType,
        user_id: str,
        update_type: str,
        data: Dict[str, Any],
        target_modules: List[ModuleType] = None,
        broadcast: bool = False,
    ) -> ModuleUpdate:
        """
        Send an update from a module to the hub.
        
        Modules call this when they have new data to share.
        """
        update = ModuleUpdate(
            id=make_id("update"),
            source_module=source_module,
            user_id=user_id,
            update_type=update_type,
            data=data,
            target_modules=target_modules or [],
            broadcast=broadcast,
        )
        
        self._updates.append(update)
        
        # Route to target modules
        if broadcast:
            for module in self._modules.values():
                if module.on_update_received:
                    try:
                        if asyncio.iscoroutinefunction(module.on_update_received):
                            await module.on_update_received(update)
                        else:
                            module.on_update_received(update)
                    except Exception as e:
                        logger.error(f"Error sending update to {module.module_type}: {e}")
        else:
            for target_type in target_modules:
                module = self._modules.get(target_type)
                if module and module.on_update_received:
                    try:
                        if asyncio.iscoroutinefunction(module.on_update_received):
                            await module.on_update_received(update)
                        else:
                            module.on_update_received(update)
                    except Exception as e:
                        logger.error(f"Error sending update to {target_type}: {e}")
        
        self._log_comm(
            "module_update",
            source_module.value,
            {
                "update_type": update_type,
                "target_count": len(target_modules or []),
                "broadcast": broadcast,
            },
            user_id=user_id,
        )
        
        return update

    # =========================================================================
    # USER DATA STORE
    # =========================================================================

    def _get_user_store(self, user_id: str) -> Dict[str, Any]:
        """Get or create a user's data store"""
        if user_id not in self._user_stores:
            self._user_stores[user_id] = {}
        return self._user_stores[user_id]

    def update_user_data(self, user_id: str, data: Dict[str, Any]):
        """Update a user's data store"""
        user_store = self._get_user_store(user_id)
        user_store.update(data)

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get a user's data store"""
        return self._get_user_store(user_id)

    # =========================================================================
    # COMMUNICATION LOGGING
    # =========================================================================

    def _log_comm(self, comm_type: str, module: str, details: Dict, user_id: str):
        """Log a communication event"""
        self._comm_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": comm_type,
            "module": module,
            "details": details,
            "user_id": user_id,
        })

    def get_comm_log(self, user_id: str = None, limit: int = 100) -> List[Dict]:
        """Get communication log"""
        if user_id:
            return [log for log in self._comm_log if log.get("user_id") == user_id][-limit:]
        return self._comm_log[-limit:]

    # =========================================================================
    # STATUS AND QUERIES
    # =========================================================================

    def get_hub_status(self) -> Dict[str, Any]:
        """Get the current status of the hub"""
        return {
            "modules_registered": len(self._modules),
            "modules": [
                {
                    "type": m.module_type.value,
                    "name": m.name,
                    "active": m.active,
                }
                for m in self._modules.values()
            ],
            "info_packs_created": len(self._info_packs),
            "requests_processed": len(self._requests),
            "updates_sent": len(self._updates),
            "user_stores": len(self._user_stores),
        }

    def get_module_info(self, module_type: ModuleType) -> Optional[Dict]:
        """Get information about a specific module"""
        module = self._modules.get(module_type)
        if not module:
            return None
        return {
            "type": module.module_type.value,
            "name": module.name,
            "description": module.description,
            "handles_documents": [d.value for d in module.handles_documents],
            "accepts_packs": [p.value for p in module.accepts_packs],
            "active": module.active,
            "registered_at": module.registered_at.isoformat(),
        }


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

module_hub = ModuleHub()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Product Tiers
    "ProductTier",
    
    # Module Capabilities
    "ModuleCapability",
    
    # Module Types
    "ModuleType",
    
    # Document Categories
    "DocumentCategory",
    
    # Pack Types
    "PackType",
    
    # Request Types
    "RequestType",
    
    # Contracts
    "FunctionGroupContract",
    "ModuleContractRegistry",
    "contract_registry",
    "register_function_group",
    
    # Product Manifest
    "ModuleEntry",
    "_ManifestRegistry",
    "MANIFEST",
    "_register",
    "_load_router",
    "register_tiers",
    "register_all_tiers",
    
    # Module SDK
    "ModuleManifest",
    "InstalledModule",
    "ModuleRegistry",
    "module_registry",
    "register_module",
    "register_tier_modules",
    "get_module_status",
    
    # Module Hub
    "InfoPack",
    "DataRequest",
    "ModuleUpdate",
    "RegisteredModule",
    "DOCUMENT_ROUTING",
    "ModuleHub",
    "module_hub",
]
