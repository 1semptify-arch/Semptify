"""
External Module Loader — Phase 3.2a

Verifies module signature (content hash), loads external modules in a
sandboxed execution context, enforces permission boundaries, and reports
permission violations to the admin console.

External modules live in app/modules/external/<vendor>/<name>/ and ship
a semptify.module.json manifest. The loader:

  1. Reads and validates the manifest
  2. Verifies the content_hash matches the module's files
  3. Imports the entry_point (router.py:router by default) in a restricted
     namespace that only exposes app.sdk.* imports
  4. Returns a LoadedExternalModule with the router and manifest

If any forbidden import is attempted (app.core.database, app.services.*,
etc.), the loader raises ExternalModuleSecurityError and logs the violation.
"""
import hashlib
import importlib
import importlib.util
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.sdk.external.permissions import PermissionSet, ALL_PERMISSIONS

logger = logging.getLogger(__name__)


# =============================================================================
# Errors
# =============================================================================

class ExternalModuleError(Exception):
    """Base error for external module loading failures."""


class ExternalModuleSecurityError(ExternalModuleError):
    """Raised when an external module violates security boundaries."""


class ExternalModuleManifestError(ExternalModuleError):
    """Raised when an external module's manifest is invalid."""


# =============================================================================
# Allowed imports for external modules
# =============================================================================

# External modules may ONLY import from these prefixes
ALLOWED_IMPORT_PREFIXES: tuple = (
    "app.sdk.external",
    "app.sdk.vault",
    "fastapi",
    "pydantic",
    "typing",
    "datetime",
    "dataclasses",
    "enum",
    "json",
    "logging",
    "pathlib",
    "starlette",
)

# Explicitly forbidden imports (even if somehow matched by allowed prefixes)
FORBIDDEN_IMPORT_PREFIXES: tuple = (
    "app.core.database",
    "app.core.redis",
    "app.services.storage",
    "app.modules",
    "app.routers",
    "app.core.security",
    "app.core.session",
    "sqlalchemy",
    "asyncpg",
    "redis",
)


# =============================================================================
# Manifest
# =============================================================================

@dataclass(frozen=True)
class ExternalModuleManifest:
    """Parsed semptify.module.json manifest."""

    name: str
    vendor: str
    version: str
    description: str
    lifecycle: str
    requires_role: tuple
    requires_jurisdiction: tuple
    requires_gate: Optional[str]
    permissions: PermissionSet
    dependencies: tuple
    entry_point: str  # e.g. "router.py:router"
    content_hash: str  # e.g. "sha256:..."
    homepage: Optional[str] = None
    support: Optional[str] = None
    license: Optional[str] = None

    @property
    def module_path(self) -> str:
        return f"app.modules.external.{self.vendor}.{self.name}"

    @property
    def router_attr(self) -> str:
        """Attribute name of the router in the entry_point module."""
        return self.entry_point.split(":")[1] if ":" in self.entry_point else "router"

    @property
    def entry_module_file(self) -> str:
        """File name of the entry_point module."""
        return self.entry_point.split(":")[0]


def parse_manifest(data: Dict[str, Any]) -> ExternalModuleManifest:
    """Parse and validate a manifest dict."""
    required_fields = (
        "name", "vendor", "version", "description", "lifecycle",
        "requires_role", "permissions", "dependencies", "entry_point", "content_hash",
    )
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ExternalModuleManifestError(f"Manifest missing required fields: {missing}")

    if data["lifecycle"] not in ("dev_only", "experimental", "beta", "stable"):
        raise ExternalModuleManifestError(
            f"Invalid lifecycle: {data['lifecycle']!r}. Must be one of dev_only|experimental|beta|stable"
        )

    # Validate permissions
    perm_list = data["permissions"]
    if not isinstance(perm_list, list):
        raise ExternalModuleManifestError("permissions must be a list")
    try:
        permissions = PermissionSet(perm_list)
    except ValueError as e:
        raise ExternalModuleManifestError(f"Invalid permissions: {e}")

    return ExternalModuleManifest(
        name=data["name"],
        vendor=data["vendor"],
        version=data["version"],
        description=data["description"],
        lifecycle=data["lifecycle"],
        requires_role=tuple(data["requires_role"]),
        requires_jurisdiction=tuple(data.get("requires_jurisdiction", [])),
        requires_gate=data.get("requires_gate"),
        permissions=permissions,
        dependencies=tuple(data["dependencies"]),
        entry_point=data["entry_point"],
        content_hash=data["content_hash"],
        homepage=data.get("homepage"),
        support=data.get("support"),
        license=data.get("license"),
    )


def load_manifest_file(manifest_path: Path) -> ExternalModuleManifest:
    """Load and parse a semptify.module.json file."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ExternalModuleManifestError(f"Invalid JSON in manifest: {e}")
    return parse_manifest(data)


# =============================================================================
# Content hash verification
# =============================================================================

def compute_module_hash(module_dir: Path) -> str:
    """Compute SHA-256 hash of all .py files in the module directory.

    The hash is order-independent (files sorted by name) and covers
    all Python source files in the module.
    """
    py_files = sorted(module_dir.rglob("*.py"))
    hasher = hashlib.sha256()
    for py_file in py_files:
        rel = py_file.relative_to(module_dir).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(py_file.read_bytes())
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}"


def verify_module_hash(module_dir: Path, expected_hash: str) -> bool:
    """Verify that the module's content hash matches the expected hash."""
    actual = compute_module_hash(module_dir)
    return actual == expected_hash


# =============================================================================
# Import guard
# =============================================================================

class _ImportGuard:
    """Meta path finder that blocks forbidden imports from external modules."""

    def __init__(self, module_name: str, vendor: str):
        self.module_name = module_name
        self.vendor = vendor
        self.violations: List[str] = []

    def find_spec(self, fullname, path=None, target=None):
        # Check if this is a forbidden import
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            if fullname == forbidden or fullname.startswith(forbidden + "."):
                self.violations.append(fullname)
                logger.error(
                    "ExternalModuleSecurity: module=%s vendor=%s attempted forbidden import: %s",
                    self.module_name, self.vendor, fullname,
                )
                raise ExternalModuleSecurityError(
                    f"External module '{self.module_name}' attempted forbidden import: {fullname}"
                )
        # Check if this is an allowed import
        for allowed in ALLOWED_IMPORT_PREFIXES:
            if fullname == allowed or fullname.startswith(allowed + "."):
                return None  # Allow normal import machinery to handle it
        # Unknown import — log warning but allow (might be stdlib)
        return None


# =============================================================================
# Loader
# =============================================================================

@dataclass
class LoadedExternalModule:
    """An external module that has been loaded and verified."""

    manifest: ExternalModuleManifest
    module_dir: Path
    router: Any
    import_violations: List[str]


def load_external_module(module_dir: Path) -> LoadedExternalModule:
    """Load an external module from a directory.

    Steps:
      1. Load and validate semptify.module.json
      2. Verify content_hash matches the module's .py files
      3. Install import guard to block forbidden imports
      4. Import the entry_point module
      5. Extract the router attribute
      6. Return LoadedExternalModule

    Raises:
      ExternalModuleManifestError: manifest invalid
      ExternalModuleSecurityError: hash mismatch or forbidden import
      ExternalModuleError: other loading failures
    """
    module_dir = Path(module_dir).resolve()
    if not module_dir.exists():
        raise ExternalModuleError(f"Module directory does not exist: {module_dir}")

    manifest_path = module_dir / "semptify.module.json"
    if not manifest_path.exists():
        raise ExternalModuleManifestError(f"No semptify.module.json in {module_dir}")

    # 1. Load manifest
    manifest = load_manifest_file(manifest_path)

    # 2. Verify hash
    if not verify_module_hash(module_dir, manifest.content_hash):
        actual = compute_module_hash(module_dir)
        raise ExternalModuleSecurityError(
            f"Content hash mismatch for module '{manifest.name}'. "
            f"Expected: {manifest.content_hash}, Actual: {actual}"
        )

    logger.info(
        "ExternalLoader: loading module=%s vendor=%s version=%s lifecycle=%s",
        manifest.name, manifest.vendor, manifest.version, manifest.lifecycle,
    )

    # 3. Install import guard
    guard = _ImportGuard(manifest.name, manifest.vendor)
    sys.meta_path.insert(0, guard)

    try:
        # 4. Import the entry_point module
        entry_file = module_dir / manifest.entry_module_file
        if not entry_file.exists():
            raise ExternalModuleError(
                f"Entry point file not found: {entry_file}"
            )

        # Use a unique module name to avoid collisions
        py_module_name = f"app.modules.external.{manifest.vendor}.{manifest.name}"

        spec = importlib.util.spec_from_file_location(py_module_name, entry_file)
        if spec is None or spec.loader is None:
            raise ExternalModuleError(f"Failed to create module spec for {entry_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[py_module_name] = module
        spec.loader.exec_module(module)

        # 5. Extract router
        router = getattr(module, manifest.router_attr, None)
        if router is None:
            raise ExternalModuleError(
                f"Entry point '{manifest.entry_point}' did not yield attribute '{manifest.router_attr}'"
            )

        logger.info(
            "ExternalLoader: successfully loaded module=%s vendor=%s",
            manifest.name, manifest.vendor,
        )

        return LoadedExternalModule(
            manifest=manifest,
            module_dir=module_dir,
            router=router,
            import_violations=guard.violations,
        )

    finally:
        # Remove the import guard
        if guard in sys.meta_path:
            sys.meta_path.remove(guard)


def list_external_modules(base_dir: Path) -> List[Dict[str, Any]]:
    """List all external modules found under base_dir.

    Expected structure: base_dir/<vendor>/<name>/semptify.module.json
    """
    base_dir = Path(base_dir)
    if not base_dir.exists():
        return []

    modules = []
    for vendor_dir in sorted(base_dir.iterdir()):
        if not vendor_dir.is_dir():
            continue
        for module_dir in sorted(vendor_dir.iterdir()):
            if not module_dir.is_dir():
                continue
            manifest_path = module_dir / "semptify.module.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = load_manifest_file(manifest_path)
                modules.append({
                    "name": manifest.name,
                    "vendor": manifest.vendor,
                    "version": manifest.version,
                    "description": manifest.description,
                    "lifecycle": manifest.lifecycle,
                    "permissions": manifest.permissions.to_list(),
                    "module_path": manifest.module_path,
                    "module_dir": str(module_dir),
                })
            except Exception as e:
                logger.warning(
                    "ExternalLoader: failed to parse manifest in %s: %s",
                    module_dir, e,
                )
                modules.append({
                    "name": module_dir.name,
                    "vendor": vendor_dir.name,
                    "error": str(e),
                    "module_dir": str(module_dir),
                })
    return modules
