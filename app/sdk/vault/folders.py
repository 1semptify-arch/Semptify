"""First-use folder creation — the lazy half of vault folder requirements.

Any service writing into a lazy-declared folder calls ensure before the
write; the folder materializes the first time it's actually needed instead
of at provisioning time. Provider create_folder() is idempotent — an
existing folder is a no-op, so callers never check first (one API call,
not two).

Dependency envelope matches db.py: stdlib + vault_paths. No FastAPI,
SQLAlchemy, or navigation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def ensure_vault_folders(storage, paths: list[str]) -> bool:
    """Create each path (and parents) if missing. Returns False on first
    failure — a False means the following write will fail too, so callers
    should surface it rather than continue.
    """
    for path in paths:
        try:
            created = await storage.create_folder(path)
            if created:
                logger.info("Vault folder created on first use: %s", path)
        except Exception as exc:  # provider adapters return False or raise
            logger.error("First-use folder creation failed for %s: %s", path, exc)
            return False
        if created is False:
            # Provider said no — distinguishable from an exception so the
            # caller can report which folder refused (KF: check every result).
            logger.error("create_folder returned False for %s", path)
            return False
    return True


async def ensure_parent_for_file(storage, file_path: str) -> bool:
    """Ensure the parent folder of a file path exists before writing it."""
    parent = file_path.rsplit("/", 1)[0] if "/" in file_path else file_path
    return await ensure_vault_folders(storage, [parent])
