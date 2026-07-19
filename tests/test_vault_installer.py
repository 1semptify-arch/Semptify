from app.core.vault_paths import (
    VAULT_OVERLAY_DOCUMENTS,
    VAULT_OVERLAY_QUERIES,
    VAULT_OVERLAY_REDACTIONS,
    VAULT_OVERLAYS,
    VAULT_OVERLAYS_FORMS,
    VAULT_TIMELINE,
)
from app.modules.vault_installer.installer import VaultInstaller


def test_vault_installer_additional_folders_are_canonical():
    installer = VaultInstaller(provider_name="google_drive", access_token="tok", user_id="UID123")

    assert installer.additional_folders == [
        VAULT_TIMELINE,
        VAULT_OVERLAYS,
        VAULT_OVERLAY_DOCUMENTS,
        VAULT_OVERLAY_QUERIES,
        VAULT_OVERLAYS_FORMS,
        VAULT_OVERLAY_REDACTIONS,
    ]


def test_vault_installer_folder_spec_has_no_duplicate_folders():
    installer = VaultInstaller(provider_name="google_drive", access_token="tok", user_id="UID123")
    all_folders = installer.vault_client.folder_spec.all_folders

    assert len(set(all_folders)) == len(all_folders)
