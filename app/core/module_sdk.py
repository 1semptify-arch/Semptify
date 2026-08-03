"""
Semptify Module SDK
===================

Defines how self-contained modules integrate with the Semptify platform.

A module is a self-contained feature unit that:
1. Declares its identity (name, tier, version)
2. Optionally provides a FastAPI router
3. Optionally declares function-group contracts
4. Optionally registers mesh actions
5. Optionally provides background tasks

Registration flow::

    from app.core.module_sdk import ModuleManifest, ModuleCapability, register_module

    manifest = ModuleManifest(
        name="tenant_defense",
        display_name="Tenant Defense",
        description="Evidence collection, sealing petitions, demand letters",
        version="1.0.0",
        tier=ProductTier.EXTENDED,
        capabilities=(ModuleCapability.ROUTER,),
        router_module="app.routers.tenant_defense",
        tags=("Tenant Defense",),
    )
    register_module(app, manifest)

Modules can also be batch-registered by tier::

    from app.core.module_sdk import register_tier_modules
    register_tier_modules(app, ProductTier.CORE)

The product manifest (``app.core.product_manifest``) is the authoritative
source for router declarations.  The module SDK sits *above* it, giving each
module a runtime identity, contract hooks, and registry tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI

from app.core.product_manifest import (
    ProductTier,
    ModuleEntry,
    MANIFEST,
    _load_router,
)
from app.core.module_contracts import (
    FunctionGroupContract,
    contract_registry,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Capabilities
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
# Manifest
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


# =============================================================================
# Installed Module (runtime)
# =============================================================================

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


# =============================================================================
# Registry
# =============================================================================

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

    # ------------------------------------------------------------------
    # Mutation (startup only)
    # ------------------------------------------------------------------

    def install(self, module: InstalledModule) -> None:
        self._modules[module.manifest.name] = module
        self._tier_index[module.manifest.tier].append(module.manifest.name)
        logger.debug(
            "ModuleRegistry: installed %s (%s)",
            module.manifest.name,
            module.manifest.tier.value,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

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


# =============================================================================
# Registration API
# =============================================================================

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
                        "▸ %s: router registered (%s)",
                        manifest.name,
                        entry.qualified_name,
                    )
                else:
                    installed.error = f"Router not found: {entry.qualified_name}"
                    if not entry.optional:
                        raise RuntimeError(installed.error)
                    logger.warning(
                        "ℹ  %s: router skipped (optional, not found)",
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
                "● %s: contract %s::%s registered",
                manifest.name,
                contract.module,
                contract.group_name,
            )

    # 3. Track in registry
    module_registry.install(installed)
    installed.initialized = True

    logger.info(
        "● Module installed: %s (%s) — capabilities=%s",
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
        "▸ Module registration complete: %d installed, %d skipped, %d errors (of %d)",
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
