from app.core.vault_paths import (
    VAULT_CERTIFICATES,
    VAULT_DOCUMENTS,
)
from app.modules.vault_installer.installer import VaultInstaller


def test_vault_installer_additional_folders_are_canonical():
    installer = VaultInstaller(provider_name="google_drive", access_token="tok", user_id="UID123")

    # The installer uses TENANT_VAULT folder spec. Only documents and certificates
    # are created at onboarding time; overlay, timeline, and filedored folders are
    # created on-demand when those features are first used.
    assert installer.vault_client.folder_spec.product_folders == (
        VAULT_DOCUMENTS,
        VAULT_CERTIFICATES,
    )


def test_vault_installer_folder_spec_has_no_duplicate_folders():
    installer = VaultInstaller(provider_name="google_drive", access_token="tok", user_id="UID123")
    all_folders = installer.vault_client.folder_spec.all_folders

    assert len(set(all_folders)) == len(all_folders)
