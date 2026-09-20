# =============================================================================
# SSOT: app/core/vault_paths.py — CANONICAL VAULT PATH DEFINITIONS
# AI RULE: ALL vault folder paths come from this file ONLY.
# NEVER hardcode Semptify5.0/ paths anywhere else in the codebase.
# NEVER rename this file. NEVER duplicate these constants.
# =============================================================================
"""Canonical cloud vault paths (single source of truth).

Structure in user's cloud storage:
    Semptify5.0/                     ▸ user-visible root
    ├── Vault/                       ▸ user owns + sees this
    │   ├── documents/
    │   ├── certificates/
    │   ├── timeline/
    │   └── overlays/
    │       ├── documents/
    │       ├── queries/
    │       ├── forms/
    │       └── redactions/
    └── .semptify/                   ▸ hidden system config (dot-prefix hides from casual browsing)
        ├── auth/                    ▸ token.enc, device_keys.json, provisioning.json, rehome.json
        └── vault/                   ▸ manifest.json, README.md
"""

import logging

from app.core.path_utils import normalize_cloud_path

logger = logging.getLogger(__name__)

# ── Root folders ──────────────────────────────────────────────────────────────
SEMPTIFY_ROOT = normalize_cloud_path("Semptify5.0")
SYSTEM_FOLDER = normalize_cloud_path(f"{SEMPTIFY_ROOT}/.semptify")  # hidden system config root
AUTH_FOLDER = normalize_cloud_path(f"{SYSTEM_FOLDER}/auth")  # token + device keys
VAULT_FOLDER = normalize_cloud_path(f"{SYSTEM_FOLDER}/vault")  # manifest + README
VAULT_ROOT = normalize_cloud_path(f"{SEMPTIFY_ROOT}/Vault")  # user document store

# ── System files (hidden under .semptify/) ────────────────────────────────────
TOKEN_FILE = f"{AUTH_FOLDER}/token.enc"
TOKEN_BACKUP = f"{AUTH_FOLDER}/token.enc.backup"
DEVICE_KEYS_FILE = f"{AUTH_FOLDER}/device_keys.json"
PROVISIONING_FILE = f"{AUTH_FOLDER}/provisioning.json"
REHOME_FILE = f"{AUTH_FOLDER}/rehome.json"
README_FILE = f"{VAULT_FOLDER}/README.md"
VAULT_MANIFEST = f"{VAULT_FOLDER}/manifest.json"
EXPERIENCE_TOKEN_FILE = f"{VAULT_FOLDER}/experience_token.json"
# Per-tenant SQLite datastore — live reads/writes for journal, calendar/
# timeline, and composer/preview domains. Single file; WAL sidecars never
# leave the local temp dir it is opened in.
VAULT_DB_FILE = f"{SYSTEM_FOLDER}/vault.db"
# Vault-resident per-role configs installed by provisioning (prov-role-configs)
CONFIGS_FOLDER = normalize_cloud_path(f"{SYSTEM_FOLDER}/configs")
OCR_CONFIG_FILE = f"{CONFIGS_FOLDER}/ocr.json"
OVERLAY_CONFIG_FILE = f"{CONFIGS_FOLDER}/overlays.json"

# ── User document folders (under Vault/) ─────────────────────────────────────
VAULT_DOCUMENTS = normalize_cloud_path(f"{VAULT_ROOT}/documents")
VAULT_CERTIFICATES = normalize_cloud_path(f"{VAULT_ROOT}/certificates")

VAULT_TIMELINE = normalize_cloud_path(f"{VAULT_ROOT}/timeline")
VAULT_TIMELINE_EVENTS_FILENAME = "events.json"
VAULT_TIMELINE_EVENTS_FILE = normalize_cloud_path(f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}")

# =============================================================================
# Unified Overlay System Paths (single source of truth)
# =============================================================================

# Per-user scratchpad for sticky notes. Not a certified vault document; it
# provides the document_id/vault_path anchor required by UnifiedOverlay while
# the actual note content lives in NOTE/STICKY_NOTE overlays.
VAULT_SCRATCHPAD = normalize_cloud_path(f"{VAULT_ROOT}/scratchpad")
VAULT_SCRATCHPAD_FILE = normalize_cloud_path(f"{VAULT_SCRATCHPAD}/notepad.json")

# Per-user journal anchor for JOURNAL_ENTRY overlays. Not a certified vault
# document; it provides the document_id/vault_path anchor required by
# UnifiedOverlay while entry content lives in the overlays themselves.
VAULT_JOURNAL = normalize_cloud_path(f"{VAULT_ROOT}/journal")
VAULT_JOURNAL_FILE = normalize_cloud_path(f"{VAULT_JOURNAL}/journal.json")

# Per-user ledger anchor for RENT_LEDGER_ENTRY overlays (rent payments, fees,
# deposits, credits, charges with running balance).
VAULT_LEDGER = normalize_cloud_path(f"{VAULT_ROOT}/ledger")
VAULT_LEDGER_FILE = normalize_cloud_path(f"{VAULT_LEDGER}/ledger.json")

# Per-user calendar anchor for CALENDAR_EVENT overlays (deadlines, hearings,
# reminders, appointments — manual and auto-synced alike).
VAULT_CALENDAR = normalize_cloud_path(f"{VAULT_ROOT}/calendar")
VAULT_CALENDAR_FILE = normalize_cloud_path(f"{VAULT_CALENDAR}/calendar.json")

# Per-user contacts anchor for CONTACT + CONTACT_INTERACTION overlays
# (landlords, attorneys, witnesses, agencies + the interaction log).
VAULT_CONTACTS = normalize_cloud_path(f"{VAULT_ROOT}/contacts")
VAULT_CONTACTS_FILE = normalize_cloud_path(f"{VAULT_CONTACTS}/contacts.json")

# Per-user records anchor for tenant record overlays that don't warrant their
# own folder yet (complaint wizard drafts/filings first; witness statements,
# incidents, dispute records join this file in later migration slices).
VAULT_RECORDS = normalize_cloud_path(f"{VAULT_ROOT}/records")
VAULT_RECORDS_FILE = normalize_cloud_path(f"{VAULT_RECORDS}/records.json")

# Per-user derived-data anchor for computed tenant artifacts (pattern detection
# records first). Derived means regenerated from vault documents — still
# tenant-owned, so it lives in the user's cloud, not the server DB.
VAULT_DERIVED = normalize_cloud_path(f"{VAULT_ROOT}/derived")
VAULT_DERIVED_FILE = normalize_cloud_path(f"{VAULT_DERIVED}/derived.json")

# Per-user external-mappings anchor for EXTERNAL_MAPPING / COURT_CASE_MAPPING /
# PROPERTY_MAPPING / AGENCY_MAPPING overlays — bridges between the tenant's
# records and external system references (court cases, parcels, agencies).
VAULT_EXTERNAL = normalize_cloud_path(f"{VAULT_ROOT}/external")
VAULT_EXTERNAL_FILE = normalize_cloud_path(f"{VAULT_EXTERNAL}/mappings.json")

# =============================================================================
# Role-specific folders (direct children of Vault/)
# =============================================================================
# Canonical leaf names for per-role vault trees. role_configs/{role}.json
# folder_tree entries resolve through these constants only — never raw paths.
VAULT_CLIENT_FILES = normalize_cloud_path(f"{VAULT_ROOT}/client_files")
VAULT_CASE_NOTES = normalize_cloud_path(f"{VAULT_ROOT}/case_notes")
VAULT_LEGAL_FILINGS = normalize_cloud_path(f"{VAULT_ROOT}/legal_filings")
VAULT_COURT_EXHIBITS = normalize_cloud_path(f"{VAULT_ROOT}/court_exhibits")
VAULT_COURT_EXHIBITS_FILE = normalize_cloud_path(f"{VAULT_COURT_EXHIBITS}/packages.json")
VAULT_CASE_FILES = normalize_cloud_path(f"{VAULT_ROOT}/case_files")
VAULT_DISCOVERY = normalize_cloud_path(f"{VAULT_ROOT}/discovery")
VAULT_RESEARCH = normalize_cloud_path(f"{VAULT_ROOT}/research")
VAULT_DOSSIERS = normalize_cloud_path(f"{VAULT_ROOT}/dossiers")

VAULT_OVERLAYS = normalize_cloud_path(f"{VAULT_ROOT}/overlays")
VAULT_OVERLAY_REGISTRY = normalize_cloud_path(f"{VAULT_OVERLAYS}/registry.json")
VAULT_OVERLAY_DOCUMENTS = normalize_cloud_path(f"{VAULT_OVERLAYS}/documents")
VAULT_OVERLAY_QUERIES = normalize_cloud_path(f"{VAULT_OVERLAYS}/queries")
VAULT_OVERLAYS_FORMS = normalize_cloud_path(f"{VAULT_OVERLAYS}/forms")
VAULT_OVERLAY_REDACTIONS = normalize_cloud_path(f"{VAULT_OVERLAYS}/redactions")

# =============================================================================
# Filedored Post-Processing Structure (auto-sort + dedup + AI classification)
# =============================================================================
VAULT_FILEDORED = normalize_cloud_path(f"{VAULT_ROOT}/filedored")
VAULT_FILEDORED_PDF = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/PDF")
VAULT_FILEDORED_WORD = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Word")
VAULT_FILEDORED_TEXT = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Text")
VAULT_FILEDORED_SPREADS = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Spreadsheets")
VAULT_FILEDORED_PRESENTS = normalize_cloud_path(f"{VAULT_FILEDORED}/Documents/Presentations")
VAULT_FILEDORED_SCANS = normalize_cloud_path(f"{VAULT_FILEDORED}/Scans/Images")
VAULT_FILEDORED_DUPLICATES = normalize_cloud_path(f"{VAULT_FILEDORED}/__DUPLICATES__")
VAULT_FILEDORED_OTHER = normalize_cloud_path(f"{VAULT_FILEDORED}/__OTHER__")
VAULT_FILEDORED_AI = normalize_cloud_path(f"{VAULT_FILEDORED}/__AI_CLASSIFIED__")
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
