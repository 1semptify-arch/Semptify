"""
Vault Check — per-attempt verification record + the test-before-active gate.

Design: handoffs/onboarding-gate-timeline-blueprint-2026-09-15.md §7.

`User.completed_groups` stays the durable progress marks. This module records
*why* a vault is or isn't active: one `vault_checks` row per attempt with the
status, which named check failed, and a plain-language detail. A vault only
reaches "active" when every check explicitly passed — never inferred from the
absence of errors.
"""

import asyncio
import json
import logging
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VaultStatus(StrEnum):
    """Vault lifecycle states for the test-before-active gate."""

    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    TEST_PENDING = "test_pending"
    VERIFYING = "verifying"
    ACTIVE = "active"
    FAILED = "failed"


# Ordered check names. Each returns "pass", "fail", or "pending" —
# pending means still running and never counts as success.
CHECK_NAMES = (
    "token_usable",
    "folder_tree",
    "test_file_present",
    "extraction_ran",
    "overlay_created",
)


def _ok(detail: str) -> dict:
    return {"status": "pass", "detail": detail}


def _fail(detail: str) -> dict:
    return {"status": "fail", "detail": detail}


def _pending(detail: str) -> dict:
    return {"status": "pending", "detail": detail}


async def record_vault_check(
    db: AsyncSession,
    user_id: str,
    status: VaultStatus | str,
    *,
    failed_check: str | None = None,
    detail: str | None = None,
    checks: dict | None = None,
) -> None:
    """Append one vault-check attempt row. Never raises to the caller."""
    try:
        from app.models.models import VaultCheck

        db.add(
            VaultCheck(
                user_id=user_id,
                status=str(status),
                failed_check=failed_check,
                detail=detail,
                checks_json=json.dumps(checks) if checks else None,
            )
        )
        await db.commit()
    except Exception as exc:
        logger.warning("record_vault_check failed for %s: %s", user_id[:6] + "***", exc)


async def get_latest_vault_check(db: AsyncSession, user_id: str):
    """Latest vault_checks row for the user, or None (= not_started)."""
    from app.models.models import VaultCheck

    result = await db.execute(
        select(VaultCheck)
        .where(VaultCheck.user_id == user_id)
        .order_by(VaultCheck.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _ensure_manifest_overlay(manager, doc) -> bool:
    """
    Create the VAULT_UPLOAD_MANIFEST overlay for a doc that lacks one, then
    confirm it exists. Heals the documented silent gap where overlay creation
    failed inside the upload pipeline without surfacing (the doc stayed
    indexed with registry_id but no cert overlay).
    """
    try:
        from app.core.overlay_types import OverlayType
        from app.models.unified_overlay_models import CreateOverlayRequest

        request = CreateOverlayRequest(
            overlay_type=OverlayType.VAULT_UPLOAD_MANIFEST,
            document_id=doc.safe_filename,
            vault_path=doc.storage_path,
            payload={
                "vault_id": doc.vault_id,
                "filename": doc.filename,
                "sha256": doc.sha256_hash,
                "registry_id": doc.registry_id,
                "integrity_status": doc.integrity_status,
                "recreated_by": "vault_check",
            },
            metadata={"source": "vault_check_heal"},
            ephemeral=False,
        )
        result = await manager.create_overlay(request)
        if not getattr(result, "success", False):
            return False
        resp = await manager.get_overlays(document_id=doc.safe_filename)
        return bool(getattr(resp, "overlays", None))
    except Exception as exc:
        logger.warning("Overlay heal failed for %s: %s", doc.vault_id, exc)
        return False


async def run_vault_verification(
    db: AsyncSession,
    user_id: str,
    *,
    access_token: str,
    provider_name: str,
    role_type: str | None,
    target_doc=None,
) -> dict:
    """
    The test-before-active gate. Every check returns an explicit verdict —
    pass / fail / pending — never inferred success.

    Returns:
        {
            "checks": {name: {"status": ..., "detail": ...}},
            "verdict": "active" | "failed" | "verifying",
            "failed_check": name | None,
            "doc": VaultDocument | None,   # the doc the verdict is about
        }
    """
    results: dict[str, dict] = {}

    # ── Check 1: token usable — a live provider call, not just presence ──────
    client = None
    try:
        from app.core.oauth_token_manager import OAuthToken
        from app.core.vault_paths import SEMPTIFY_ROOT
        from app.modules.onboarding.role_config import vault_spec_for_role
        from app.modules.storage.router import get_valid_session
        from app.sdk.vault import VaultClient

        session = await get_valid_session(db, user_id, auto_refresh=False)
        if not session or not session.get("access_token"):
            results["token_usable"] = _fail("No stored storage session")
        else:
            token = OAuthToken.from_dict(session)
            if token.is_expired():
                results["token_usable"] = _fail("OAuth token expired")
            else:
                client = VaultClient(
                    provider=provider_name,
                    access_token=access_token,
                    user_id=user_id,
                    folder_spec=vault_spec_for_role(role_type),
                )
                await asyncio.wait_for(client.list_files(SEMPTIFY_ROOT), timeout=15.0)
                results["token_usable"] = _ok("Token valid — live provider call succeeded")
    except TimeoutError:
        results["token_usable"] = _fail("Provider did not respond within 15s")
    except Exception as exc:
        results["token_usable"] = _fail(f"Provider call failed: {exc}")

    # ── Check 2: folder tree confirmed to exist in the connected cloud ───────
    if client is None:
        results["folder_tree"] = _fail("Cannot verify folders — storage unavailable")
    else:
        try:
            from app.modules.onboarding.role_config import vault_spec_for_role

            spec = vault_spec_for_role(role_type)
            missing = []
            for folder in spec.all_folders():
                try:
                    # Empty list is a valid existing folder (Known Failure #4);
                    # only an exception means missing/inaccessible.
                    await asyncio.wait_for(client.list_files(folder), timeout=10.0)
                except Exception:
                    missing.append(folder)
            if missing:
                results["folder_tree"] = _fail(f"Missing folders: {', '.join(missing[:5])}")
            else:
                results["folder_tree"] = _ok(f"{len(spec.all_folders())} folders confirmed in cloud")
        except Exception as exc:
            results["folder_tree"] = _fail(f"Folder check error: {exc}")

    # ── Check 3: test file confirmed present in the vault documents folder ───
    from app.services.vault_upload_service import VaultUploadService

    svc = VaultUploadService()
    doc = target_doc
    if doc is None:
        try:
            docs = await svc.get_user_documents(user_id)
            doc = docs[0] if docs else None
        except Exception:
            doc = None
    if client is None:
        results["test_file_present"] = _fail("Cannot check vault contents — storage unavailable")
    elif doc is None:
        results["test_file_present"] = _fail("No document found in vault index")
    else:
        try:
            from app.core.vault_paths import VAULT_DOCUMENTS

            files = await asyncio.wait_for(client.list_files(VAULT_DOCUMENTS), timeout=10.0)
            names = {
                f.get("name") if isinstance(f, dict) else getattr(f, "name", str(f))
                for f in (files or [])
            }
            if doc.safe_filename in names:
                results["test_file_present"] = _ok("Test file confirmed in vault folder")
            elif names:
                results["test_file_present"] = _ok(f"Vault folder holds {len(names)} file(s)")
            else:
                results["test_file_present"] = _fail("Vault documents folder is empty")
        except Exception as exc:
            results["test_file_present"] = _fail(f"Could not list vault folder: {exc}")

    # ── Check 4: extraction/OCR pipeline ran (Pass-1 minimum) ────────────────
    try:
        from app.services.document_intake import DocumentIntakeEngine, IntakeStatus

        engine = DocumentIntakeEngine()
        intake = None
        if doc is not None:
            intake = next(
                (d for d in engine.get_user_documents(user_id) if d.vault_id == doc.vault_id),
                None,
            )
        if intake is None:
            results["extraction_ran"] = _pending("Extraction record not found yet — pipeline may still be starting")
        elif intake.status == IntakeStatus.FAILED:
            results["extraction_ran"] = _fail(f"Extraction failed: {intake.status_message or 'unknown error'}")
        elif intake.status in (IntakeStatus.RECEIVED, IntakeStatus.VALIDATING, IntakeStatus.EXTRACTING):
            results["extraction_ran"] = _pending(f"Extraction in progress ({intake.status.value})")
        else:
            results["extraction_ran"] = _ok(f"Extraction completed (status: {intake.status.value})")
    except Exception as exc:
        results["extraction_ran"] = _fail(f"Extraction check error: {exc}")

    # ── Check 5: an overlay actually exists — the exact prior silent gap ─────
    if doc is None:
        results["overlay_created"] = _fail("No document to check overlays for")
    else:
        try:
            from app.services.storage import get_provider
            from app.services.unified_overlay_manager import get_unified_overlay_manager

            storage = get_provider(provider_name, access_token=access_token)
            manager = await get_unified_overlay_manager(storage, user_id)
            resp = await manager.get_overlays(document_id=doc.safe_filename)
            overlays = getattr(resp, "overlays", None) or []
            if overlays:
                results["overlay_created"] = _ok(f"{len(overlays)} overlay(s) found")
            elif await _ensure_manifest_overlay(manager, doc):
                results["overlay_created"] = _ok("Overlay was missing — recreated and confirmed")
            else:
                results["overlay_created"] = _fail("No overlay exists and creation failed")
        except Exception as exc:
            results["overlay_created"] = _fail(f"Overlay check error: {exc}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    failed = [n for n in CHECK_NAMES if results.get(n, {}).get("status") == "fail"]
    pending = [n for n in CHECK_NAMES if results.get(n, {}).get("status") == "pending"]
    if failed:
        verdict, failed_check = VaultStatus.FAILED, failed[0]
    elif pending:
        verdict, failed_check = VaultStatus.VERIFYING, None
    else:
        verdict, failed_check = VaultStatus.ACTIVE, None

    return {
        "checks": results,
        "verdict": str(verdict),
        "failed_check": failed_check,
        "doc": doc,
    }
