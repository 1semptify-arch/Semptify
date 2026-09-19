"""
Post-onboarding vault provisioning engine.

Runs AFTER onboarding FINALE (document_uploaded) when the user reaches their
role home — never inside onboarding, which stays untouched. Chunked,
idempotent, resumable: each step is a single short API call behind
Cloudflare (KF#5 — never more than ~20s of work per call).

Steps, in order:
    folders   — verify/create the full working-set folder tree
    vault_db  — per-tenant SQLite datastore + embedded migrations
                (queued: prov-vault-sqlite)
    configs   — per-role OCR + overlay config files
                (queued: prov-role-configs)

Progress state lives in User.completed_groups via the generic gate helpers
(``check_gate``/``mark_gate``) — Neon holds structure and pointers only,
never tenant content (SYSTEM_MANIFEST PII boundary). Step markers are
namespaced ``prov_*`` so they can never collide with onboarding gates.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import vault_paths as vp
from app.core.user_context import UserContext
from app.core.user_id import get_role_from_user_id
from app.modules.onboarding.gates import check_gate, mark_gate
from app.sdk.vault import VaultClient
from app.sdk.vault.folder_spec import BASE_VAULT, VaultFolderSpec

logger = logging.getLogger(__name__)

# FINALE gate from onboarding — provisioning may only run past it.
FINALE_GATE = "document_uploaded"
PROVISIONED_GATE = "vault_provisioned"

# Steps not yet implemented report "pending" and do not block the
# provisioned marker — they flip to done as their queued tasks land.
_STEP_GATES = {
    "folders": "prov_folders",
    "vault_db": "prov_vault_db",
    "configs": "prov_configs",
}
_PENDING_STEPS = {"vault_db", "configs"}
PROVISION_STEPS = tuple(_STEP_GATES)

# Full working set: canonical folder tree + the data-anchor directories
# every anchor file needs (journal.json lives in journal/, etc.). Onboarding
# creates only its own spec's subset; this superset is provisioned here —
# the role_configs/*.json onboarding specs stay untouched.
_WORKING_SET_FOLDERS = [
    vp.VAULT_DOCUMENTS,
    vp.VAULT_CERTIFICATES,
    vp.VAULT_TIMELINE,
    vp.VAULT_JOURNAL,
    vp.VAULT_LEDGER,
    vp.VAULT_CALENDAR,
    vp.VAULT_CONTACTS,
    vp.VAULT_RECORDS,
    vp.VAULT_DERIVED,
    vp.VAULT_EXTERNAL,
    vp.VAULT_SCRATCHPAD,
    vp.VAULT_OVERLAYS,
    vp.VAULT_OVERLAY_DOCUMENTS,
    vp.VAULT_OVERLAY_QUERIES,
    vp.VAULT_OVERLAYS_FORMS,
    vp.VAULT_OVERLAY_REDACTIONS,
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
]


def _provisioning_folder_spec(role_type: str | None) -> VaultFolderSpec:
    """Full working set + the role's own product folders (deduped)."""
    from app.modules.onboarding.role_config import vault_spec_for_role

    role_spec = vault_spec_for_role(role_type or "tenant")
    merged: list[str] = []
    seen: set[str] = set()
    for path in _WORKING_SET_FOLDERS + list(role_spec.product_folders):
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return BASE_VAULT.extend(merged)


async def status(db: AsyncSession, user_id: str) -> dict:
    """Provisioning status for a user. Cheap — gate flags only, no cloud call."""
    if not await check_gate(db, user_id, FINALE_GATE):
        return {"applicable": False}
    steps: dict[str, str] = {}
    next_step = None
    for name in PROVISION_STEPS:
        if await check_gate(db, user_id, _STEP_GATES[name]):
            steps[name] = "done"
        elif name in _PENDING_STEPS:
            steps[name] = "pending"
        else:
            steps[name] = "todo"
            if next_step is None:
                next_step = name
    # "provisioned" means every step is genuinely done — pending steps keep
    # it false so the narrative resumes when their tasks land. The banner's
    # question is narrower: is there a runnable step right now?
    provisioned = all(s == "done" for s in steps.values())
    if provisioned:
        await mark_gate(db, user_id, PROVISIONED_GATE)
    return {
        "applicable": True,
        "provisioned": provisioned,
        "steps": steps,
        "next_step": next_step,
    }


async def needs_run(db: AsyncSession, user_id: str | None) -> bool:
    """True when FINALE passed and a runnable step remains (state == todo).

    Pending steps do NOT count — the banner settles when nothing runnable
    is left and reappears on its own when a pending step gets implemented
    (its gate is unset, so it reads todo). Never raises.
    """
    if not user_id:
        return False
    try:
        s = await status(db, user_id)
        return bool(s.get("applicable") and s.get("next_step"))
    except Exception:  # pylint: disable=broad-exception-caught
        return False


async def run_step(db: AsyncSession, user: UserContext, step: str) -> dict:
    """Run one provisioning step. Idempotent — safe to call repeatedly."""
    if step not in _STEP_GATES:
        return {"success": False, "error": "unknown_step", "step": step}
    if step in _PENDING_STEPS:
        return {"success": True, "step": step, "state": "pending"}
    if await check_gate(db, user.user_id, _STEP_GATES[step]):
        return {"success": True, "step": step, "state": "done", "skipped": True}
    if step == "folders":
        return await _run_folders(db, user)
    return {"success": False, "error": "unhandled_step", "step": step}


async def _maybe_mark_provisioned(db: AsyncSession, user_id: str) -> None:
    """Mark vault_provisioned once every step — pending included — is done."""
    for name, gate in _STEP_GATES.items():
        if not await check_gate(db, user_id, gate):
            return
    await mark_gate(db, user_id, PROVISIONED_GATE)


async def _run_folders(db: AsyncSession, user: UserContext) -> dict:
    """Step 1: create the full working-set folder tree via the Vault SDK."""
    provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
    role_type = get_role_from_user_id(user.user_id)
    spec = _provisioning_folder_spec(role_type)
    client = VaultClient(provider_name, user.access_token, user.user_id, folder_spec=spec)
    try:
        result = await asyncio.wait_for(client.create_folders(), timeout=25.0)
    except TimeoutError:
        logger.error("Provisioning folders timed out for user %s", user.user_id[:6] + "***")
        return {"success": False, "step": "folders", "error": "Timed out creating folders — retrying is safe"}
    except Exception as e:
        logger.error("Provisioning folders failed for user %s: %s", user.user_id[:6] + "***", e)
        return {"success": False, "step": "folders", "error": str(e)}
    if not result.all_ok:
        return {
            "success": False,
            "step": "folders",
            "errors": [f"{f.path}: {f.detail}" for f in result.failed],
        }
    await mark_gate(db, user.user_id, _STEP_GATES["folders"])
    await _maybe_mark_provisioned(db, user.user_id)
    return {
        "success": True,
        "step": "folders",
        "state": "done",
        "folders_created": [f.path for f in result.succeeded],
    }
