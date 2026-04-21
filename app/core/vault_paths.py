"""Canonical cloud vault paths (single source of truth)."""

SEMPTIFY_ROOT = "Semptify5.0"
VAULT_ROOT = f"{SEMPTIFY_ROOT}/Vault"

VAULT_DOCUMENTS = f"{VAULT_ROOT}/documents"
VAULT_CERTIFICATES = f"{VAULT_ROOT}/certificates"

VAULT_OVERLAY = f"{VAULT_ROOT}/.overlay"
VAULT_OVERLAY_REGISTRY = f"{VAULT_OVERLAY}/registry.json"

VAULT_TIMELINE = f"{VAULT_ROOT}/timeline"
VAULT_TIMELINE_EVENTS_FILENAME = "events.json"
VAULT_TIMELINE_EVENTS_FILE = f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}"

# =============================================================================
# Unified Overlay System Paths (single source of truth)
# =============================================================================

VAULT_OVERLAYS = f"{VAULT_ROOT}/overlays"                          # All overlay types
VAULT_OVERLAY_REGISTRY = f"{VAULT_OVERLAYS}/registry.json"            # Master index
VAULT_OVERLAY_DOCUMENTS = f"{VAULT_OVERLAYS}/documents"              # Per-document overlays
VAULT_OVERLAY_QUERIES = f"{VAULT_OVERLAYS}/queries"                  # Query/output overlays
VAULT_OVERLAYS_FORMS = f"{VAULT_OVERLAYS}/forms"                      # Form-fill overlays
VAULT_OVERLAY_REDACTIONS = f"{VAULT_OVERLAYS}/redactions"            # Redaction overlays
