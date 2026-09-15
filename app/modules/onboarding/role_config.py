"""Role-based vault configuration loader.

Resolution order:
  1. Check the existing specs in app/sdk/vault/folder_spec.py (the SSOT).
     Roles with a built-in spec (tenant, advocate, legal, research, admin)
     return that spec directly — no JSON needed.
  2. Fall back to JSON role configs under role_configs/ for roles without
     a built-in spec (donor_supporter, etc.). Each JSON leaf name resolves
     through app/core/vault_paths.py constants.
  3. Unknown roles fall back to tenant.

This keeps folder_spec.py as the SSOT for roles that already have specs,
and uses JSON only for roles that don't — avoiding duplication.
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
    "research": RESEARCH_VAULT,
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


def vault_spec_for_role(role_type: str | None) -> VaultFolderSpec:
    """Return a VaultFolderSpec for the given role.

    Resolution order:
      1. Built-in specs in folder_spec.py (tenant, advocate, legal, research, admin).
      2. JSON config under role_configs/ for roles without a built-in spec.
      3. Tenant fallback for unknown roles.

    A corrupt JSON config or an unresolvable folder_tree leaf raises a
    clear error.
    """
    normalized = (role_type or "tenant").lower().strip()

    # 1. Check built-in specs first (the SSOT in folder_spec.py).
    if normalized in _BUILTIN_SPECS:
        return _BUILTIN_SPECS[normalized]

    # 2. Fall back to JSON config for roles without a built-in spec.
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


__all__ = ["vault_spec_for_role"]
