import logging

logger = logging.getLogger(__name__)


async def download_prefer_id(storage, storage_path: str, provider_file_id: str | None = None):
    """Try provider id download first (if given), otherwise fallback to path download.

    `storage` must implement `download_file(path_or_id)` and support an `id:` prefix for direct id downloads.
    """
    if provider_file_id:
        try:
            return await storage.download_file(f"id:{provider_file_id}")
        except Exception as exc:
            logger.debug("ID-based download failed for %s, falling back to path: %s", provider_file_id, exc)
    return await storage.download_file(storage_path)
