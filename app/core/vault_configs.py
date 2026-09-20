"""Vault-resident per-role config payloads (prov-role-configs, Step 1d).

Provisioning installs these as JSON inside the tenant's own vault under
``.semptify/configs/``:

- ``ocr.json`` — drives the OCR-first intake pass: which doc types the role
  ingests, the required fields the per-field confirm loop asks about, the
  text-layer-first rule (native PDF/DOCX skip OCR), and the ADR-0007 engine
  routing (client-side WASM/ONNX primary, ephemeral in-memory server
  fallback, zero content logging).
- ``overlays.json`` — which overlay categories the role may create
  (categories from ``app.core.overlay_types``) plus typed seed slots.

v1 minimal by design — the task notes say iterate later. Content lives
here (core, product policy); transport lives in ``app.sdk.vault.configs``.
Nothing here reads ``app/modules/onboarding/`` — that tree is NO-TOUCH;
the role arrives via ``get_role_from_user_id``.
"""

from __future__ import annotations

from app.core.document_types import DOCUMENT_TYPES
from app.core.vault_paths import OCR_CONFIG_FILE, OVERLAY_CONFIG_FILE

OCR_CONFIG_VERSION = 2
OVERLAY_CONFIG_VERSION = 1

# Required-field catalog — sourced from the shipping SSOT
# (app/core/document_types.py) so the vault-resident config can never drift
# from the checklists the confirm loop actually renders.
DOC_TYPE_FIELDS: dict[str, list[str]] = {
    key: [f["name"] for f in defn["fields"] if f["required"]]
    for key, defn in DOCUMENT_TYPES.items()
}

# Roles that put documents through the OCR-first intake pipeline get the
# full catalog; everyone else gets an empty doc_types map (they don't
# intake tenant documents at all in v1).
_DOC_INTAKE_ROLES = {
    "tenant",
    "advocate",
    "multi_client_advocate",
    "legal",
    "manager",
    "agency",
}

# Overlay categories a role may create — names match the category groups
# in app.core.overlay_types (get_overlay_category). "identity" is the
# view-as/impersonation adapter — only roles that can view tenant records.
_OVERLAY_CATEGORIES_BY_ROLE: dict[str, list[str]] = {
    "tenant": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "record",
    ],
    "advocate": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "record", "case", "identity",
    ],
    "multi_client_advocate": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "record", "case", "identity",
    ],
    "legal": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "record", "case", "identity",
    ],
    "manager": [
        "upload", "processing", "annotation", "query", "record", "identity",
    ],
    "agency": ["annotation", "query", "record"],
    "researcher": ["processing", "annotation", "query"],
    "judge": ["query"],
    "admin": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "identity", "case", "record",
    ],
    "developer": [
        "upload", "processing", "annotation", "form", "query",
        "redaction", "identity", "case", "record",
    ],
    "donor_supporter": [],
}

# ADR-0007 (BETA): client-side OCR + embeddings on the tenant's device;
# ephemeral in-memory server fallback; zero structural content logging.
_OCR_ENGINE = {
    "primary": "client_wasm_onnx",
    "embedding_model": "all-MiniLM-L6-v2",
    "fallback": "server_ephemeral",
    "fallback_persistence": "memory_only",
    "content_logging": "none",
}

# Intake confirm flow (document_center handoff): per-field sequential
# confirm — yes / no / edit; all-yes -> verified, edits -> in_review.
_CONFIRM_FLOW = {
    "per_field": True,
    "controls": ["yes", "no", "edit"],
    "all_confirmed_state": "verified",
    "edited_state": "in_review",
}


def _normalize_role(role: str | None) -> str:
    role = (role or "").strip().lower()
    return role if role in _OVERLAY_CATEGORIES_BY_ROLE or role in _DOC_INTAKE_ROLES else "unknown"


def ocr_config_for_role(role: str | None) -> dict:
    """OCR intake config for one role. Non-intake roles get empty doc_types."""
    role = _normalize_role(role)
    return {
        "version": OCR_CONFIG_VERSION,
        "role": role,
        "text_layer_first": True,
        "engine": dict(_OCR_ENGINE),
        "confirm_flow": dict(_CONFIRM_FLOW),
        "doc_types": (
            {key: dict(defn) for key, defn in DOCUMENT_TYPES.items()}
            if role in _DOC_INTAKE_ROLES
            else {}
        ),
    }


def overlay_config_for_role(role: str | None) -> dict:
    """Overlay permissions config for one role. ``seeds`` is the slot for
    typed overlay seeds — empty in v1; consumers iterate later."""
    role = _normalize_role(role)
    return {
        "version": OVERLAY_CONFIG_VERSION,
        "role": role,
        "allowed_categories": list(_OVERLAY_CATEGORIES_BY_ROLE.get(role, [])),
        "seeds": [],
    }


def configs_for_role(role: str | None) -> dict[str, dict]:
    """All vault-resident config payloads for a role, keyed by remote path."""
    return {
        OCR_CONFIG_FILE: ocr_config_for_role(role),
        OVERLAY_CONFIG_FILE: overlay_config_for_role(role),
    }
