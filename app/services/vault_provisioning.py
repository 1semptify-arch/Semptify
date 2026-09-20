"""
Post-onboarding vault provisioning engine.

Runs AFTER onboarding FINALE (document_uploaded) when the user reaches their
role home — never inside onboarding, which stays untouched. Chunked,
idempotent, resumable: each step is a single short API call behind
Cloudflare (KF#5 — never more than ~20s of work per call).

Steps, in order:
    folders   — verify/create the full working-set folder tree
    vault_db  — per-tenant SQLite datastore + embedded migrations
                (app/services/vault_db.py → .semptify/vault/vault.db)
    configs   — per-role OCR + overlay config files into .semptify/configs/
                (prov-role-configs: sdk/vault/configs.py + core/vault_configs.py)

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
from app.sdk.vault.configs import ensure_configs_remote
from app.sdk.vault.db import ensure_remote
from app.sdk.vault.folder_spec import BASE_VAULT, VaultFolderSpec
from app.services.storage import get_provider

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
_PENDING_STEPS: set[str] = set()  # all current steps implemented
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
        if step == "folders":
            # Vaults provisioned before Rehome was part of this step still
            # get it — every folders-step run verifies the file exists.
            provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
            client = VaultClient(provider_name, user.access_token, user.user_id, folder_spec=BASE_VAULT)
            rehome_error = await _ensure_rehome_file(client, user, provider_name)
            if rehome_error:
                return {"success": False, "step": step, "error": rehome_error}
        return {"success": True, "step": step, "state": "done", "skipped": True}
    if step == "folders":
        return await _run_folders(db, user)
    if step == "vault_db":
        return await _run_vault_db(db, user)
    if step == "configs":
        return await _run_configs(db, user)
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
    rehome_error = await _ensure_rehome_file(client, user, provider_name)
    if rehome_error:
        return {"success": False, "step": "folders", "error": rehome_error}
    await mark_gate(db, user.user_id, _STEP_GATES["folders"])
    await _maybe_mark_provisioned(db, user.user_id)
    return {
        "success": True,
        "step": "folders",
        "state": "done",
        "folders_created": [f.path for f in result.succeeded],
    }


async def _ensure_rehome_file(client: VaultClient, user: UserContext, provider_name: str) -> str | None:
    """Write Rehome.html at Semptify5.0/ if it isn't already there.

    The folder tree and the reconnection file belong together — a vault
    without Rehome.html can't sync a new device. Onboarding's installer
    writes it; this covers any vault whose tree came up another way
    (partial install, older spec). Idempotent: never overwrites an
    existing file. Returns an error string or None.
    """
    from app.core.rehome import generate_rehome_html

    storage = client._get_storage()  # system files live outside Vault/ — same pattern as vault_installer
    try:
        if await asyncio.wait_for(storage.file_exists(vp.REHOME_HTML_FILE), timeout=25.0):
            return None
        from app.core.config import get_settings

        base_url = (get_settings().public_base_url or "https://semptify.org").rstrip("/")
        await asyncio.wait_for(
            storage.upload_file(
                file_content=generate_rehome_html(user.user_id, provider_name, base_url).encode(),
                destination_path=vp.SEMPTIFY_ROOT,
                filename="Rehome.html",
                mime_type="text/html",
            ),
            timeout=25.0,
        )
        return None
    except TimeoutError:
        logger.error("Rehome.html write timed out for user %s", user.user_id[:6] + "***")
        return "Timed out writing Rehome.html — retrying is safe"
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Rehome.html write failed for user %s: %s", user.user_id[:6] + "***", e)
        return f"Rehome.html: {e}"


async def _run_vault_db(db: AsyncSession, user: UserContext) -> dict:
    """Step 2: create (or verify+migrate) the per-tenant vault SQLite file.

    ensure_remote is idempotent: a missing file is created at the current
    schema version; an existing file is downloaded, pending embedded
    migrations applied, and re-uploaded only when its version advanced.
    """
    provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
    storage = get_provider(provider_name, access_token=user.access_token)
    try:
        result = await asyncio.wait_for(ensure_remote(storage), timeout=25.0)
    except TimeoutError:
        logger.error("Provisioning vault_db timed out for user %s", user.user_id[:6] + "***")
        return {"success": False, "step": "vault_db", "error": "Timed out preparing vault database — retrying is safe"}
    except Exception as e:
        logger.error("Provisioning vault_db failed for user %s: %s", user.user_id[:6] + "***", e)
        return {"success": False, "step": "vault_db", "error": str(e)}
    await mark_gate(db, user.user_id, _STEP_GATES["vault_db"])
    await _maybe_mark_provisioned(db, user.user_id)
    return {"success": True, "step": "vault_db", "state": "done", **result}


async def _run_configs(db: AsyncSession, user: UserContext) -> dict:
    """Step 3: install per-role OCR + overlay configs into .semptify/configs/.

    Idempotent: missing files are uploaded, same-version files verified in
    place, stale/unparseable files refreshed, newer files never downgraded.
    """
    provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
    role_type = get_role_from_user_id(user.user_id)
    storage = get_provider(provider_name, access_token=user.access_token)
    try:
        result = await asyncio.wait_for(ensure_configs_remote(storage, role_type), timeout=25.0)
    except TimeoutError:
        logger.error("Provisioning configs timed out for user %s", user.user_id[:6] + "***")
        return {"success": False, "step": "configs", "error": "Timed out installing configs — retrying is safe"}
    except Exception as e:
        logger.error("Provisioning configs failed for user %s: %s", user.user_id[:6] + "***", e)
        return {"success": False, "step": "configs", "error": str(e)}
    await mark_gate(db, user.user_id, _STEP_GATES["configs"])
    await _maybe_mark_provisioned(db, user.user_id)
    return {"success": True, "step": "configs", "state": "done", **result}
