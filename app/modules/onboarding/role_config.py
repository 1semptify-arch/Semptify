"""Role-based vault configuration loader.

Resolution order (per handoffs/onboarding-full-rebuild-spec-2026-09-16.md —
the JSON role configs are the driver, not a hardcoded tree):
  1. `role_configs/{role_type}.json` — the authoritative per-role config.
     Each folder_tree leaf name resolves through app/core/vault_paths.py
     constants.
  2. Built-in specs in app/sdk/vault/folder_spec.py — fallback ONLY for
     roles with no JSON file (e.g. advocate until advocate.json exists).
  3. tenant.json — final fallback for unknown roles.

This makes the per-role JSON configs the single point of change: adding or
reshaping a role's vault requires editing JSON, never Python.
"""

import inspect
import json
import logging
from pathlib import Path

from app.core.path_utils import get_cloud_basename, get_cloud_parent, normalize_cloud_path
from app.core.vault_paths import VAULT_ROOT
from app.sdk.vault.folder_spec import (
    ADVOCATE_VAULT,
    BASE_VAULT,
    LEGAL_VAULT,
    RESEARCH_VAULT,
    TENANT_VAULT,
    VaultFolderSpec,
)

logger = logging.getLogger(__name__)

# Directory containing role JSON configs, next to this module.
_CONFIG_DIR = Path(__file__).resolve().parent / "role_configs"

# Cache for parsed JSON configs.
_CONFIG_CACHE: dict[str, dict] = {}

# Built-in specs from folder_spec.py — the SSOT for roles that have them.
# Roles not in this map fall back to JSON configs.
_BUILTIN_SPECS: dict[str, VaultFolderSpec] = {
    "tenant": TENANT_VAULT,
    "advocate": ADVOCATE_VAULT,
    "multi_client_advocate": ADVOCATE_VAULT,
    "legal": LEGAL_VAULT,
    "judge": LEGAL_VAULT,  # deprecated role merged into legal (sub_role='judge')
    "research": RESEARCH_VAULT,  # legacy key — canonical config is researcher.json
}

# Build a leaf-name -> full canonical path mapping for every direct child of
# VAULT_ROOT that is declared in vault_paths.py. This keeps the JSON data free
# of absolute paths while still resolving through the canonical SSOT.
_LEAF_TO_VAULT_PATH: dict[str, str] = {}
from app.core import vault_paths as _vault_paths

for _name, _value in inspect.getmembers(_vault_paths, lambda v: isinstance(v, str)):
    if _name.startswith("_"):
        continue
    _norm = normalize_cloud_path(_value)
    if get_cloud_parent(_norm) == VAULT_ROOT:
        _leaf = get_cloud_basename(_norm)
        _LEAF_TO_VAULT_PATH[_leaf] = _norm


def _resolve_leaf(leaf: str) -> str:
    """Map a leaf name to a canonical vault path constant."""
    if leaf in _LEAF_TO_VAULT_PATH:
        return _LEAF_TO_VAULT_PATH[leaf]
    raise ValueError(
        f"folder_tree leaf {leaf!r} is not a known direct subfolder of "
        f"VAULT_ROOT under vault_paths.py. Known leaves: "
        f"{sorted(_LEAF_TO_VAULT_PATH)}"
    )


def _load_json_config(role_type: str) -> dict:
    """Load a role JSON config, falling back to tenant.json for unknown roles."""
    role_type = (role_type or "tenant").lower().strip()
    if role_type in _CONFIG_CACHE:
        return _CONFIG_CACHE[role_type]

    config_path = _CONFIG_DIR / f"{role_type}.json"
    if not config_path.is_file():
        logger.warning("Role config %s not found; falling back to tenant.json", role_type)
        config_path = _CONFIG_DIR / "tenant.json"

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupt role config file {config_path}: {exc}") from exc

    _CONFIG_CACHE[role_type] = config
    return config


def _spec_from_config(normalized: str) -> VaultFolderSpec:
    """Build a VaultFolderSpec from a role JSON config's folder_tree."""
    config = _load_json_config(normalized)
    declared_role = config.get("role_type", normalized)

    folder_tree = config.get("folder_tree")
    if not isinstance(folder_tree, list):
        raise ValueError(
            f"Role config {declared_role!r} has invalid folder_tree (must be a list)"
        )

    resolved: list[str] = []
    for leaf in folder_tree:
        if not isinstance(leaf, str):
            raise ValueError(
                f"Role config {declared_role!r} folder_tree contains non-string {leaf!r}"
            )
        try:
            resolved.append(_resolve_leaf(leaf))
        except ValueError as exc:
            raise ValueError(
                f"Role config {declared_role!r}: {exc}"
            ) from exc

    return BASE_VAULT.extend(resolved)


def vault_spec_for_role(role_type: str | None) -> VaultFolderSpec:
    """Return a VaultFolderSpec for the given role.

    Resolution order:
      1. role_configs/{role}.json — the driver (per-role config, no code edit).
      2. Built-in spec in folder_spec.py — only for roles with no JSON file.
      3. tenant.json — final fallback for unknown roles.

    A corrupt JSON config or an unresolvable folder_tree leaf raises a
    clear error.
    """
    normalized = (role_type or "tenant").lower().strip()

    # 1. JSON config is authoritative when it exists.
    if (_CONFIG_DIR / f"{normalized}.json").is_file():
        return _spec_from_config(normalized)

    # 2. Built-in spec fallback — only for roles that never got a JSON config.
    if normalized in _BUILTIN_SPECS:
        logger.info(
            "No role_configs/%s.json — using built-in folder_spec fallback", normalized
        )
        return _BUILTIN_SPECS[normalized]

    # 3. Unknown role — tenant.json fallback (inside _load_json_config too,
    #    but explicit here keeps intent obvious).
    logger.warning("Role %r has no JSON config or built-in spec; using tenant", normalized)
    return _spec_from_config("tenant")


# Default ordered gate list — used when a role config has no "gates" field.
# Extensible per role: role_configs/{role}.json may declare its own "gates"
# list (spec: handoffs/onboarding-full-rebuild-spec-2026-09-16.md).
DEFAULT_GATES = ["storage_connected", "vault_initialized", "document_uploaded"]


def gates_for_role(role_type: str | None) -> list[str]:
    """Ordered onboarding gate list for the role.

    Reads role_configs/{role}.json "gates" when present; otherwise returns
    the default three gates. A corrupt config falls back to the defaults —
    gate routing must never crash on a config error.
    """
    normalized = (role_type or "tenant").lower().strip()
    try:
        config = _load_json_config(normalized)
    except ValueError:
        return list(DEFAULT_GATES)
    gates = config.get("gates")
    if isinstance(gates, list) and gates and all(isinstance(g, str) for g in gates):
        return gates
    return list(DEFAULT_GATES)


__all__ = ["vault_spec_for_role", "gates_for_role", "DEFAULT_GATES"]
