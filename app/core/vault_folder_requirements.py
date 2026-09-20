"""Vault folder requirements — the SSOT for which feature needs which folders.

Each feature declares its anchor folders and whether they are:

  eager — created by post-FINALE provisioning (the folders step). These are
          the skeleton the system needs to exist before any feature writes:
          roots, the documents store, timeline, the overlays tree, and the
          hidden .semptify system folders.

  lazy  — created on first use by the feature's own write path. The
          mechanism already exists: filedored sort-dirs self-create via
          ensure_filedored_folder() when the first AI-classified document
          lands, and ensure_vault_folders() in the vault SDK generalizes
          the same pattern for any writer. A folder may only be marked
          lazy when every path that writes into it calls an ensure helper
          first — otherwise the first write fails.

Growth rule: adding a feature means adding an entry here, not hunting
through provisioning code. tools/folder_balance.py reports drift between
this map, the canonical tree, and which lazy-eligible folders still lack
an ensure hook.
"""

from __future__ import annotations

from app.core import vault_paths as vp

# ---------------------------------------------------------------------------
# Eager skeleton — provisioned at folder-creation time, needed before any
# feature can write. Keep this small: every entry here is an API call during
# provisioning.
# ---------------------------------------------------------------------------

FOLDER_REQUIREMENTS: dict[str, dict] = {
    "vault_skeleton": {
        "eager": True,
        "why": "Roots + document store — everything else hangs off these.",
        "folders": [
            vp.SEMPTIFY_ROOT,
            vp.VAULT_ROOT,
            vp.VAULT_DOCUMENTS,
            vp.VAULT_CERTIFICATES,
            vp.VAULT_TIMELINE,
        ],
    },
    "system_config": {
        "eager": True,
        "why": ".semptify system tree — tokens, manifest, vault.db, role configs.",
        "folders": [
            vp.SYSTEM_FOLDER,
            vp.AUTH_FOLDER,
            vp.VAULT_FOLDER,
            vp.CONFIGS_FOLDER,
        ],
    },
    "overlays": {
        "eager": True,
        "why": "Overlay tree is written at document intake — must exist immediately.",
        "folders": [
            vp.VAULT_OVERLAYS,
            vp.VAULT_OVERLAY_DOCUMENTS,
            vp.VAULT_OVERLAY_QUERIES,
            vp.VAULT_OVERLAYS_FORMS,
            vp.VAULT_OVERLAY_REDACTIONS,
        ],
    },
    # -----------------------------------------------------------------------
    # Lazy — first-use folders. Each entry names the ensure hook that creates
    # it; a folder flips eager->lazy only when that hook is wired on the write
    # path. tools/folder_balance.py reports anchors still missing a hook.
    # -----------------------------------------------------------------------
    "filedored": {
        "eager": False,
        "ensure_hook": "app.services.filedored_service.ensure_filedored_folder",
        "why": "AI sort dirs — only needed once a document is classified.",
        "folders": [
            vp.VAULT_FILEDORED,
            vp.VAULT_FILEDORED_PDF,
            vp.VAULT_FILEDORED_WORD,
            vp.VAULT_FILEDORED_TEXT,
            vp.VAULT_FILEDORED_SPREADS,
            vp.VAULT_FILEDORED_PRESENTS,
            vp.VAULT_FILEDORED_SCANS,
            vp.VAULT_FILEDORED_DUPLICATES,
            vp.VAULT_FILEDORED_OTHER,
            vp.VAULT_FILEDORED_AI,
            vp.VAULT_FILEDORED_AI_LEASE,
            vp.VAULT_FILEDORED_AI_NOTICE,
            vp.VAULT_FILEDORED_AI_EVIDENCE,
            vp.VAULT_FILEDORED_AI_PHOTO,
            vp.VAULT_FILEDORED_AI_INVOICE,
            vp.VAULT_FILEDORED_AI_COMM,
            vp.VAULT_FILEDORED_AI_UNKNOWN,
        ],
    },
    # Data anchors — write paths don't ensure yet, so these stay eager until
    # each service calls ensure_vault_folders() before its first write.
    # ensure_hook=None is what folder_balance reports as "not yet lazy-able".
    "journal": {
        "eager": True,
        "ensure_hook": None,
        "why": "journal.json anchor — flip to lazy once journal service ensures.",
        "folders": [vp.VAULT_JOURNAL],
    },
    "ledger": {
        "eager": True,
        "ensure_hook": None,
        "why": "ledger.json anchor — flip to lazy once rent service ensures.",
        "folders": [vp.VAULT_LEDGER],
    },
    "calendar": {
        "eager": True,
        "ensure_hook": None,
        "why": "calendar.json anchor — flip to lazy once calendar service ensures.",
        "folders": [vp.VAULT_CALENDAR],
    },
    "contacts": {
        "eager": True,
        "ensure_hook": None,
        "why": "contacts.json anchor — flip to lazy once contacts store ensures.",
        "folders": [vp.VAULT_CONTACTS],
    },
    "records": {
        "eager": True,
        "ensure_hook": None,
        "why": "records.json anchor — flip to lazy once record stores ensure.",
        "folders": [vp.VAULT_RECORDS],
    },
    "derived": {
        "eager": True,
        "ensure_hook": None,
        "why": "Derived data anchor — flip to lazy once writers ensure.",
        "folders": [vp.VAULT_DERIVED],
    },
    "external": {
        "eager": True,
        "ensure_hook": None,
        "why": "External mappings anchor — flip to lazy once mapping store ensures.",
        "folders": [vp.VAULT_EXTERNAL],
    },
    "scratchpad": {
        "eager": True,
        "ensure_hook": None,
        "why": "notepad.json anchor — flip to lazy once sticky-notes service ensures.",
        "folders": [vp.VAULT_SCRATCHPAD],
    },
}


def eager_folders() -> list[str]:
    """Folders provisioned at folder-creation time (order preserved, deduped)."""
    out: list[str] = []
    for entry in FOLDER_REQUIREMENTS.values():
        if entry.get("eager"):
            for path in entry["folders"]:
                if path not in out:
                    out.append(path)
    return out


def lazy_folders() -> list[str]:
    """Folders created on first use by their ensure hook."""
    out: list[str] = []
    for entry in FOLDER_REQUIREMENTS.values():
        if not entry.get("eager"):
            out.extend(entry["folders"])
    return out


def folders_for(feature: str) -> list[str]:
    """All folders a feature declares — for first-use ensure calls."""
    entry = FOLDER_REQUIREMENTS.get(feature)
    return list(entry["folders"]) if entry else []


def lazy_without_hook() -> dict[str, list[str]]:
    """Features that declare an ensure hook slot but haven't wired it —
    the flip-to-lazy roadmap. Skeleton entries don't declare the slot at
    all (they must exist before anything can write), so they're excluded.
    """
    return {
        name: entry["folders"]
        for name, entry in FOLDER_REQUIREMENTS.items()
        if entry.get("eager") and "ensure_hook" in entry and entry["ensure_hook"] is None
    }
