"""Canonical cloud vault paths (single source of truth)."""

from app.core.path_utils import normalize_cloud_path

SEMPTIFY_ROOT = normalize_cloud_path("Semptify5.0")
AUTH_FOLDER = normalize_cloud_path(f".{SEMPTIFY_ROOT}/auth")
VAULT_FOLDER = normalize_cloud_path(f".{SEMPTIFY_ROOT}/vault")
VAULT_ROOT = normalize_cloud_path(f"{SEMPTIFY_ROOT}/Vault")

# Local auth files
TOKEN_FILE = f"{AUTH_FOLDER}/token.enc"
TOKEN_BACKUP = f"{AUTH_FOLDER}/token.enc.backup"
DEVICE_KEYS_FILE = f"{AUTH_FOLDER}/device_keys.json"
PROVISIONING_FILE = f"{AUTH_FOLDER}/provisioning.json"
REHOME_FILE = f"{AUTH_FOLDER}/rehome.json"
README_FILE = f"{VAULT_FOLDER}/README.md"
VAULT_MANIFEST = f"{VAULT_FOLDER}/manifest.json"

VAULT_DOCUMENTS = normalize_cloud_path(f"{VAULT_ROOT}/documents")
VAULT_CERTIFICATES = normalize_cloud_path(f"{VAULT_ROOT}/certificates")

VAULT_TIMELINE = normalize_cloud_path(f"{VAULT_ROOT}/timeline")
VAULT_TIMELINE_EVENTS_FILENAME = "events.json"
VAULT_TIMELINE_EVENTS_FILE = normalize_cloud_path(f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}")

# =============================================================================
# Unified Overlay System Paths (single source of truth)
# =============================================================================

VAULT_OVERLAYS = normalize_cloud_path(f"{VAULT_ROOT}/overlays")                          # All overlay types
VAULT_OVERLAY_REGISTRY = normalize_cloud_path(f"{VAULT_OVERLAYS}/registry.json")            # Master index
VAULT_OVERLAY_DOCUMENTS = normalize_cloud_path(f"{VAULT_OVERLAYS}/documents")              # Per-document overlays
VAULT_OVERLAY_QUERIES = normalize_cloud_path(f"{VAULT_OVERLAYS}/queries")                  # Query/output overlays
VAULT_OVERLAYS_FORMS = normalize_cloud_path(f"{VAULT_OVERLAYS}/forms")                      # Form-fill overlays
VAULT_OVERLAY_REDACTIONS = normalize_cloud_path(f"{VAULT_OVERLAYS}/redactions")            # Redaction overlays
