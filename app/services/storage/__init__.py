# Storage services - OAuth2 cloud storage providers
import logging

from app.services.storage.base import StorageFile, StorageProvider, StorageToken
from app.services.storage.dropbox import DropboxProvider
from app.services.storage.google_drive import GoogleDriveProvider
from app.services.storage.onedrive import OneDriveProvider
from app.services.storage.r2 import R2Provider

logger = logging.getLogger(__name__)


def get_provider(provider_name: str, **kwargs) -> StorageProvider:
    """
    Factory function to get a storage provider by name.

    Args:
        provider_name: One of 'google_drive', 'dropbox', 'onedrive', 'r2'
        **kwargs: Provider-specific configuration

    Returns:
        StorageProvider instance
    """
    # Dev god-mode: the seeded dev token maps every provider call to local
    # disk so the app is fully usable without OAuth. Never a real user's path.
    from app.services.storage.local_disk import DEV_TOKEN, LocalDiskProvider

    if kwargs.get("access_token") == DEV_TOKEN:
        return LocalDiskProvider()

    providers = {
        "google_drive": GoogleDriveProvider,
        "googledrive": GoogleDriveProvider,
        "gdrive": GoogleDriveProvider,
        "dropbox": DropboxProvider,
        "onedrive": OneDriveProvider,
        "r2": R2Provider,
        "cloudflare_r2": R2Provider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown storage provider: {provider_name}")

    return provider_class(**kwargs)


__all__ = [
    "StorageProvider",
    "StorageFile",
    "StorageToken",
    "GoogleDriveProvider",
    "DropboxProvider",
    "OneDriveProvider",
    "R2Provider",
    "get_provider",
]
