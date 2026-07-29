"""Filedored Vault Post-Processing Service — overlay-based sorting, dedup, AI classification."""

import logging

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.vault_paths import (
    VAULT_FILEDORED,
    VAULT_FILEDORED_AI,
    VAULT_FILEDORED_AI_COMM,
    VAULT_FILEDORED_AI_EVIDENCE,
    VAULT_FILEDORED_AI_INVOICE,
    VAULT_FILEDORED_AI_LEASE,
    VAULT_FILEDORED_AI_NOTICE,
    VAULT_FILEDORED_AI_PHOTO,
    VAULT_FILEDORED_AI_UNKNOWN,
    VAULT_FILEDORED_DUPLICATES,
    VAULT_FILEDORED_OTHER,
    VAULT_FILEDORED_PDF,
    VAULT_FILEDORED_PRESENTS,
    VAULT_FILEDORED_SCANS,
    VAULT_FILEDORED_SPREADS,
    VAULT_FILEDORED_TEXT,
    VAULT_FILEDORED_WORD,
)
from app.models.unified_overlay_models import CreateOverlayRequest

logger = logging.getLogger(__name__)

# Base folders — created upfront when filedored is first used
BASE_FILEDORED_FOLDERS = [
    VAULT_FILEDORED,
    VAULT_FILEDORED_PDF,
    VAULT_FILEDORED_WORD,
    VAULT_FILEDORED_TEXT,
    VAULT_FILEDORED_SPREADS,
    VAULT_FILEDORED_PRESENTS,
    VAULT_FILEDORED_SCANS,
    VAULT_FILEDORED_DUPLICATES,
    VAULT_FILEDORED_OTHER,
]

# AI subdirectories — created on-demand when first AI-classified document arrives
AI_FILEDORED_FOLDERS = [
    VAULT_FILEDORED_AI,
    VAULT_FILEDORED_AI_LEASE,
    VAULT_FILEDORED_AI_NOTICE,
    VAULT_FILEDORED_AI_EVIDENCE,
    VAULT_FILEDORED_AI_PHOTO,
    VAULT_FILEDORED_AI_INVOICE,
    VAULT_FILEDORED_AI_COMM,
    VAULT_FILEDORED_AI_UNKNOWN,
]

DOCUMENT_EXTENSIONS = {
    "pdf": VAULT_FILEDORED_PDF,
    "doc": VAULT_FILEDORED_WORD,
    "docx": VAULT_FILEDORED_WORD,
    "txt": VAULT_FILEDORED_TEXT,
    "rtf": VAULT_FILEDORED_TEXT,
    "xls": VAULT_FILEDORED_SPREADS,
    "xlsx": VAULT_FILEDORED_SPREADS,
    "ppt": VAULT_FILEDORED_PRESENTS,
    "pptx": VAULT_FILEDORED_PRESENTS,
    "jpg": VAULT_FILEDORED_SCANS,
    "jpeg": VAULT_FILEDORED_SCANS,
    "png": VAULT_FILEDORED_SCANS,
}

AI_CLASSIFICATION_MAP = {
    "lease": VAULT_FILEDORED_AI_LEASE,
    "notice": VAULT_FILEDORED_AI_NOTICE,
    "evidence": VAULT_FILEDORED_AI_EVIDENCE,
    "photo": VAULT_FILEDORED_AI_PHOTO,
    "invoice": VAULT_FILEDORED_AI_INVOICE,
    "communication": VAULT_FILEDORED_AI_COMM,
    "unknown": VAULT_FILEDORED_AI_UNKNOWN,
}


def ai_classify_document(vault_id: str, content: bytes, filename: str) -> str:
    """
    AI classification hook.
    Expected return values: lease, notice, evidence, photo, invoice, communication, unknown

    Integration points:
    - SWE 1.6: Replace this function with SWE 1.6 API call
    - Local model: Uses the deterministic keyword/filename classifier in
      ``app.services.local_classifier`` (default). The classifier now also
      returns a confidence score via ``predict_with_confidence()``, which
      ``process_uploaded_document()`` stores in the overlay payload.
    - External API: Replace with external classification service
    """
    try:
        from app.services.local_classifier import predict

        return predict(content, filename)
    except Exception as exc:
        logger.warning("AI classification failed for %s: %s", vault_id, exc)
        return "unknown"


async def process_uploaded_document(
    vault_id: str,
    user_id: str,
    filename: str,
    content: bytes,
    sha256_hash: str,
    enable_ai: bool = False,
    overlay_manager=None,
) -> dict:
    """
    Post-process an uploaded document through filedored system using overlays.

    Instead of moving files, creates overlay references that organize documents
    into the filedored folder structure virtually.

    Returns dict with:
        - status: "sorted", "ai_classified", "skipped", "error"
        - overlay_path: virtual path in filedored structure
        - ai_label: if AI classification was used
    """
    if overlay_manager is None:
        raise RuntimeError(
            "overlay_manager is required by process_uploaded_document; "
            "caller must pass a constructed UnifiedOverlayManager"
        )

    try:
        # AI classification (optional)
        if enable_ai:
            try:
                from app.services.local_classifier import predict_with_confidence

                label, confidence = predict_with_confidence(content, filename)
            except Exception as exc:
                logger.warning("AI classification failed for %s: %s", vault_id, exc)
                label = "unknown"
                confidence = 0.0

            if label != "unknown":
                target_path = AI_CLASSIFICATION_MAP.get(label, VAULT_FILEDORED_AI_UNKNOWN)

                # Lazy-create the AI subdirectory on first use
                if hasattr(overlay_manager, "storage"):
                    await ensure_filedored_folder(overlay_manager.storage, target_path)

                overlay_payload = {
                    "original_vault_id": vault_id,
                    "original_filename": filename,
                    "filedored_category": label,
                    "filedored_path": target_path,
                    "classification_method": "ai",
                    "ai_confidence": confidence,
                    "classified_at": utc_now().isoformat(),
                }

                overlay_req = CreateOverlayRequest(
                    overlay_type=OverlayType.FILEDORED,
                    document_id=vault_id,
                    vault_path=target_path,
                    payload=overlay_payload,
                    metadata={"stage": "ai_classification", "filename": filename},
                )

                await overlay_manager.create_overlay(overlay_req)

                return {
                    "status": "ai_classified",
                    "overlay_path": target_path,
                    "ai_label": label,
                    "ai_confidence": confidence,
                }

        # Extension-based routing
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        target_path = DOCUMENT_EXTENSIONS.get(ext, VAULT_FILEDORED_OTHER)

        overlay_payload = {
            "original_vault_id": vault_id,
            "original_filename": filename,
            "filedored_category": "extension_based",
            "filedored_path": target_path,
            "file_extension": ext,
            "sorted_at": utc_now().isoformat(),
        }

        overlay_req = CreateOverlayRequest(
            overlay_type=OverlayType.FILEDORED,
            document_id=vault_id,
            vault_path=target_path,
            payload=overlay_payload,
            metadata={"stage": "extension_sort", "filename": filename},
        )

        await overlay_manager.create_overlay(overlay_req)

        return {
            "status": "sorted",
            "overlay_path": target_path,
            "extension": ext,
        }

    except Exception as e:
        logger.error("Filedored processing failed for %s: %s", vault_id, e)
        return {
            "status": "error",
            "error": str(e),
        }


_FILEDORED_FLAG_PREFIX = "semptify:filedored_ready:"
_FILEDORED_FLAG_TTL = 60 * 60 * 24 * 30  # 30 days


async def _filedored_flag_key(user_id: str) -> str:
    return f"{_FILEDORED_FLAG_PREFIX}{user_id}"


async def ensure_filedored_folders(vault_client) -> dict:
    """
    Ensure base filedored folders exist in the vault.
    Called on-demand before the first filedored overlay is written.
    Returns dict with folder creation status.
    Skips API calls if a Redis flag confirms folders already exist.

    NOTE: AI subdirectories are NOT created here — they are lazy-created
    on first AI-classified document via ensure_filedored_folder().
    """
    user_id = getattr(vault_client, "user_id", None)
    if user_id:
        try:
            from app.core.redis_client import get_redis

            redis = await get_redis()
            if redis is not None:
                flag = await redis.get(await _filedored_flag_key(user_id))
                if flag:
                    return {"status": "already_ready", "folders_created": [], "folders_failed": []}
        except Exception as _re:
            logger.debug("Filedored Redis flag check skipped: %s", _re)

    from app.sdk.vault.folder_spec import BASE_VAULT

    filedored_spec = BASE_VAULT.extend(BASE_FILEDORED_FOLDERS)
    vault_client._folder_spec = filedored_spec
    result = await vault_client.create_folders()

    if result.all_ok and user_id:
        try:
            from app.core.redis_client import get_redis

            redis = await get_redis()
            if redis is not None:
                await redis.set(await _filedored_flag_key(user_id), "1", ex=_FILEDORED_FLAG_TTL)
        except Exception as _re:
            logger.debug("Filedored Redis flag set skipped: %s", _re)

    return {
        "status": "complete" if result.all_ok else "partial",
        "folders_created": [f.path for f in result.folders if f.status == "ok"],
        "folders_failed": [f.path for f in result.failed],
    }


async def ensure_filedored_folder(storage_provider, folder_path: str) -> bool:
    """
    Lazily create a single filedored folder (and its parents) on demand.
    Used for AI subdirectories that are only created when first needed.

    Args:
        storage_provider: Cloud storage adapter with create_folder method
        folder_path: Path to create

    Returns True if the folder exists or was created successfully.
    """
    try:
        created = await storage_provider.create_folder(folder_path)
        if created:
            logger.info("Filedored folder created on-demand: %s", folder_path)
        return created
    except Exception as exc:
        logger.error("Failed to create filedored folder %s: %s", folder_path, exc)
        return False


# =============================================================================
# Module Contracts — SSOT signatures, visible in admin contract browser
# =============================================================================

try:
    from app.core.module_contracts import FunctionGroupContract, register_function_group

    register_function_group(
        FunctionGroupContract(
            module="filedored",
            group_name="document_process",
            title="Filedored Document Processing (SSOT)",
            description=(
                "CANONICAL document sorting/classification via process_uploaded_document(). "
                "Creates FILEDORED overlay with filedored_path in payload. "
                "Caller MUST pass a constructed UnifiedOverlayManager (no lazy init). "
                "AI classification is optional (enable_ai flag). "
                "FORBIDDEN: vault_id/user_id/overlay_path/overlay_data on CreateOverlayRequest."
            ),
            inputs=("vault_id", "user_id", "filename", "content", "sha256_hash", "enable_ai", "overlay_manager"),
            outputs=("status", "overlay_path", "ai_label?"),
            dependencies=(
                "app.services.filedored_service.process_uploaded_document",
                "app.services.unified_overlay_manager.UnifiedOverlayManager",
                "app.core.overlay_types.OverlayType.FILEDORED",
            ),
            deterministic=True,
        )
    )

    register_function_group(
        FunctionGroupContract(
            module="filedored",
            group_name="folders_ensure",
            title="Filedored Folders Ensure (SSOT)",
            description=(
                "CANONICAL folder creation via ensure_filedored_folders() and ensure_filedored_folder(). "
                "Base folders created upfront; AI subdirectories lazy-created on demand. "
                "Redis flag (30-day TTL) prevents redundant API calls."
            ),
            inputs=("vault_client", "storage_provider", "folder_path?"),
            outputs=("status", "folders_created", "folders_failed"),
            dependencies=(
                "app.services.filedored_service.ensure_filedored_folders",
                "app.services.filedored_service.ensure_filedored_folder",
                "app.core.vault_paths.VAULT_FILEDORED",
            ),
            deterministic=True,
        )
    )

except Exception as _e:
    logger.debug("Filedored contract registration skipped: %s", _e)
