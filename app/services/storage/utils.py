from typing import Optional

async def download_prefer_id(storage, storage_path: str, provider_file_id: Optional[str] = None):
    """Try provider id download first (if given), otherwise fallback to path download.

    `storage` must implement `download_file(path_or_id)` and support an `id:` prefix for direct id downloads.
    """
    if provider_file_id:
        try:
            return await storage.download_file(f"id:{provider_file_id}")
        except Exception:
            # fall back to path download
            pass
    return await storage.download_file(storage_path)
