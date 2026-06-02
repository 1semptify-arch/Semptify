"""Canonical cloud vault paths (single source of truth).

Structure in user's cloud storage:
    Semptify5.0/                     ← user-visible root
    ├── Vault/                       ← user owns + sees this
    │   ├── documents/
    │   ├── certificates/
    │   ├── timeline/
    │   └── overlays/
    │       ├── documents/
    │       ├── queries/
    │       ├── forms/
    │       └── redactions/
    └── .semptify/                   ← hidden system config (dot-prefix hides from casual browsing)
        ├── auth/                    ← token.enc, device_keys.json, provisioning.json, rehome.json
        └── vault/                   ← manifest.json, README.md
"""

from app.core.path_utils import normalize_cloud_path
import logging
logger = logging.getLogger(__name__)

# ── Root folders ──────────────────────────────────────────────────────────────
SEMPTIFY_ROOT = normalize_cloud_path("Semptify5.0")
SYSTEM_FOLDER = normalize_cloud_path(f"{SEMPTIFY_ROOT}/.semptify")      # hidden system config root
AUTH_FOLDER   = normalize_cloud_path(f"{SYSTEM_FOLDER}/auth")           # token + device keys
VAULT_FOLDER  = normalize_cloud_path(f"{SYSTEM_FOLDER}/vault")          # manifest + README
VAULT_ROOT    = normalize_cloud_path(f"{SEMPTIFY_ROOT}/Vault")          # user document store

# ── System files (hidden under .semptify/) ────────────────────────────────────
TOKEN_FILE        = f"{AUTH_FOLDER}/token.enc"
TOKEN_BACKUP      = f"{AUTH_FOLDER}/token.enc.backup"
DEVICE_KEYS_FILE  = f"{AUTH_FOLDER}/device_keys.json"
PROVISIONING_FILE = f"{AUTH_FOLDER}/provisioning.json"
REHOME_FILE       = f"{AUTH_FOLDER}/rehome.json"
README_FILE       = f"{VAULT_FOLDER}/README.md"
VAULT_MANIFEST    = f"{VAULT_FOLDER}/manifest.json"

# ── User document folders (under Vault/) ─────────────────────────────────────
VAULT_DOCUMENTS   = normalize_cloud_path(f"{VAULT_ROOT}/documents")
VAULT_CERTIFICATES = normalize_cloud_path(f"{VAULT_ROOT}/certificates")

VAULT_TIMELINE                = normalize_cloud_path(f"{VAULT_ROOT}/timeline")
VAULT_TIMELINE_EVENTS_FILENAME = "events.json"
VAULT_TIMELINE_EVENTS_FILE    = normalize_cloud_path(f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}")

# =============================================================================
# Unified Overlay System Paths (single source of truth)
# =============================================================================

VAULT_OVERLAYS           = normalize_cloud_path(f"{VAULT_ROOT}/overlays")
VAULT_OVERLAY_REGISTRY   = normalize_cloud_path(f"{VAULT_OVERLAYS}/registry.json")
VAULT_OVERLAY_DOCUMENTS  = normalize_cloud_path(f"{VAULT_OVERLAYS}/documents")
VAULT_OVERLAY_QUERIES    = normalize_cloud_path(f"{VAULT_OVERLAYS}/queries")
VAULT_OVERLAYS_FORMS     = normalize_cloud_path(f"{VAULT_OVERLAYS}/forms")
VAULT_OVERLAY_REDACTIONS = normalize_cloud_path(f"{VAULT_OVERLAYS}/redactions")
CANONICAL_VAULT_FOLDERS = [
    SEMPTIFY_ROOT,
    VAULT_ROOT,
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
    VAULT_TIMELINE,
    VAULT_OVERLAYS,
    VAULT_OVERLAY_DOCUMENTS,
    VAULT_OVERLAY_QUERIES,
    VAULT_OVERLAYS_FORMS,
    VAULT_OVERLAY_REDACTIONS,
    SYSTEM_FOLDER,
    AUTH_FOLDER,
    VAULT_FOLDER,
]
