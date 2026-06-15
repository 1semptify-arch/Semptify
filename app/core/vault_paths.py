# =============================================================================
# SSOT: app/core/vault_paths.py — CANONICAL VAULT PATH DEFINITIONS
# AI RULE: ALL vault folder paths come from this file ONLY.
# NEVER hardcode Semptify5.0/ paths anywhere else in the codebase.
# NEVER rename this file. NEVER duplicate these constants.
# =============================================================================
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

# =============================================================================
# Filedored Post-Processing Structure (auto-sort + dedup + AI classification)
# =============================================================================
VAULT_FILEDORED          = normalize_cloud_path(f"{VAULT_ROOT}/filedored")
VAULT_FILEDORED_PDF      = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/PDF")
VAULT_FILEDORED_WORD     = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Word")
VAULT_FILEDORED_TEXT     = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Text")
VAULT_FILEDORED_SPREADS  = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Spreadsheets")
VAULT_FILEDORED_PRESENTS = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Presentations")
VAULT_FILEDORED_SCANS    = normalize_cloud_path(f"{VAULT_FILEDORED}/Scans/Images")
VAULT_FILEDORED_DUPLICATES = normalize_cloud_path(f"{VAULT_FILEDORED}/__DUPLICATES__")
VAULT_FILEDORED_OTHER    = normalize_cloud_path(f"{VAULT_FILEDORED}/__OTHER__")
VAULT_FILEDORED_AI       = normalize_cloud_path(f"{VAULT_FILEDORED}/__AI_CLASSIFIED__")
VAULT_FILEDORED_AI_LEASE = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/lease")
VAULT_FILEDORED_AI_NOTICE = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/notice")
VAULT_FILEDORED_AI_EVIDENCE = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/evidence")
VAULT_FILEDORED_AI_PHOTO = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/photo")
VAULT_FILEDORED_AI_INVOICE = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/invoice")
VAULT_FILEDORED_AI_COMM = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/communication")
VAULT_FILEDORED_AI_UNKNOWN = normalize_cloud_path(f"{VAULT_FILEDORED_AI}/unknown")
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
    VAULT_FILEDORED,
    VAULT_FILEDORED_PDF,
    VAULT_FILEDORED_WORD,
    VAULT_FILEDORED_TEXT,
    VAULT_FILEDORED_SPREADS,
    VAULT_FILEDORED_PRESENTS,
    VAULT_FILEDORED_SCANS,
    VAULT_FILEDORED_DUPLICATES,
    VAULT_FILEDORED_OTHER,
    VAULT_FILEDORED_AI,
    VAULT_FILEDORED_AI_LEASE,
    VAULT_FILEDORED_AI_NOTICE,
    VAULT_FILEDORED_AI_EVIDENCE,
    VAULT_FILEDORED_AI_PHOTO,
    VAULT_FILEDORED_AI_INVOICE,
    VAULT_FILEDORED_AI_COMM,
    VAULT_FILEDORED_AI_UNKNOWN,
    SYSTEM_FOLDER,
    AUTH_FOLDER,
    VAULT_FOLDER,
]
