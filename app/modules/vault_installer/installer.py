"""
Semptify Vault Installer - Core Installation Logic

Direct vault creation using existing OAuth tokens.
No complex onboarding, just install and activate.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.storage import get_provider
from app.core.vault_paths import (
    SEMPTIFY_ROOT,
    VAULT_FOLDER,
    AUTH_FOLDER,
    VAULT_DOCUMENTS,
    VAULT_CERTIFICATES,
    VAULT_TIMELINE,
    VAULT_OVERLAYS,
    VAULT_TIMELINE_EVENTS_FILENAME,
    VAULT_OVERLAY_REGISTRY,
)
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class VaultInstaller:
    """
    Standalone vault installer that creates the complete Semptify vault structure.
    
    Takes OAuth tokens and directly creates folders, files, and marks activation.
    No complex onboarding flow required.
    """

    def __init__(self, provider_name: str, access_token: str, user_id: str):
        self.provider_name = provider_name
        self.access_token = access_token
        self.user_id = user_id
        self.storage = get_provider(provider_name, access_token=access_token)
        
        # Complete folder structure to install
        self.vault_structure = {
            SEMPTIFY_ROOT: "Semptify root directory",
            VAULT_FOLDER: "Main vault storage",
            VAULT_DOCUMENTS: "Document storage",
            VAULT_CERTIFICATES: "Certificate storage", 
            VAULT_TIMELINE: "Timeline events",
            VAULT_OVERLAYS: "Analysis overlays",
            f"{VAULT_OVERLAYS}/evidence": "Evidence overlays",
            f"{VAULT_OVERLAYS}/legal": "Legal analysis overlays",
            f"{VAULT_OVERLAYS}/timeline": "Timeline overlays",
            AUTH_FOLDER: "Authentication and backups",
        }

    async def install_vault(self) -> Dict:
        """
        Install the complete vault structure.
        
        Returns:
            Dict with installation status and details.
        """
        results = {
            "success": False,
            "folders_created": [],
            "files_created": [],
            "errors": [],
            "activation_code": None,
        }

        try:
            # Step 1: Create all folders
            await self._create_folder_structure(results)
            
            # Step 2: Create system files
            await self._create_system_files(results)
            
            # Step 3: Create data files
            await self._create_data_files(results)
            
            # Step 4: Verify installation
            verification = await self._verify_installation()
            if not verification["ok"]:
                results["errors"].append(f"Verification failed: {verification['message']}")
                return results
            
            # Step 5: Generate activation code
            results["activation_code"] = self._generate_activation_code()
            results["success"] = True
            
            logger.info(f"Vault installed successfully for user {self.user_id[:6]}***")
            return results
            
        except Exception as e:
            logger.error(f"Vault installation failed: {e}")
            results["errors"].append(str(e))
            return results

    async def _create_folder_structure(self, results: Dict):
        """Create the complete folder hierarchy."""
        for folder_path, description in self.vault_structure.items():
            try:
                success = await self.storage.create_folder(folder_path)
                if success:
                    results["folders_created"].append(folder_path)
                    logger.debug(f"Created folder: {folder_path}")
                else:
                    results["errors"].append(f"Failed to create folder: {folder_path}")
            except Exception as e:
                results["errors"].append(f"Error creating {folder_path}: {str(e)}")

    async def _create_system_files(self, results: Dict):
        """Create essential system files."""
        system_files = {
            f"{SEMPTIFY_ROOT}/README.txt": self._readme_content(),
            f"{VAULT_FOLDER}/manifest.json": self._manifest_content(),
            f"{VAULT_FOLDER}/vault_status.json": self._status_content("installed"),
        }
        
        for file_path, content in system_files.items():
            try:
                folder, filename = file_path.rsplit("/", 1)
                await self.storage.upload_file(
                    file_content=content.encode(),
                    destination_path=folder,
                    filename=filename,
                    mime_type="text/plain" if filename.endswith(".txt") else "application/json"
                )
                results["files_created"].append(file_path)
            except Exception as e:
                results["errors"].append(f"Failed to create {file_path}: {str(e)}")

    async def _create_data_files(self, results: Dict):
        """Create initial data files."""
        data_files = {
            f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}": self._timeline_events_content(),
            f"{VAULT_OVERLAYS}/registry.json": self._overlay_registry_content(),
        }
        
        for file_path, content in data_files.items():
            try:
                folder, filename = file_path.rsplit("/", 1)
                await self.storage.upload_file(
                    file_content=json.dumps(content, indent=2).encode(),
                    destination_path=folder,
                    filename=filename,
                    mime_type="application/json"
                )
                results["files_created"].append(file_path)
            except Exception as e:
                results["errors"].append(f"Failed to create {file_path}: {str(e)}")

    async def _verify_installation(self) -> Dict:
        """Verify the vault was installed correctly."""
        try:
            # Check root folder exists
            root_files = await self.storage.list_files(SEMPTIFY_ROOT)
            if not root_files:
                return {"ok": False, "message": "Root folder not accessible"}
            
            # Check manifest exists
            manifest_files = await self.storage.list_files(VAULT_FOLDER)
            if "manifest.json" not in [f.get("name", "") for f in manifest_files]:
                return {"ok": False, "message": "Manifest file missing"}
            
            return {"ok": True, "message": "Installation verified"}
        except Exception as e:
            return {"ok": False, "message": f"Verification error: {str(e)}"}

    def _generate_activation_code(self) -> str:
        """Generate a unique activation code."""
        import secrets
        return f"SV-{secrets.token_hex(4).upper()}-{utc_now().strftime('%Y%m%d')}"

    def _readme_content(self) -> str:
        """Generate README.txt content."""
        return f"""Semptify Vault - Installed {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This vault contains your protected housing documents and evidence.

📁 Folders:
• documents/ - Your uploaded documents
• certificates/ - Official certificates and filings  
• timeline/ - Event timeline and journal
• overlays/ - Analysis and evidence overlays

🔐 Security:
• Vault is encrypted at rest in your {self.provider_name} account
• Only you have access through your Semptify account
• All timestamps use UTC timezone

📞 Support:
• For help: https://semptify.com/help
• Privacy policy: https://semptify.com/privacy

Generated by Semptify Vault Installer v1.0
"""

    def _manifest_content(self) -> str:
        """Generate vault manifest content."""
        manifest = {
            "semptify_version": "5.0",
            "vault_version": "1.0",
            "user_id": self.user_id,
            "provider": self.provider_name,
            "created_at": utc_now().isoformat(),
            "vault_status": "active",
            "installer": "vault_installer_v1.0",
            "folders": list(self.vault_structure.keys()),
        }
        return json.dumps(manifest, indent=2)

    def _status_content(self, status: str) -> str:
        """Generate vault status content."""
        status_data = {
            "status": status,
            "last_updated": utc_now().isoformat(),
            "installer_version": "1.0",
        }
        return json.dumps(status_data, indent=2)

    def _timeline_events_content(self) -> Dict:
        """Generate initial timeline events structure."""
        return {
            "version": "1.0",
            "created_by": self.user_id,
            "created_at": utc_now().isoformat(),
            "events": [],
            "metadata": {
                "total_events": 0,
                "date_range": None,
                "categories": ["housing", "documents", "communications", "legal"],
            },
        }

    def _overlay_registry_content(self) -> Dict:
        """Generate overlay registry structure."""
        return {
            "version": "1.0",
            "created_by": self.user_id,
            "created_at": utc_now().isoformat(),
            "overlays": {},
            "metadata": {
                "total_overlays": 0,
                "available_types": ["evidence", "legal", "timeline"],
            },
        }


async def install_vault_for_user(
    db: AsyncSession,
    user_id: str,
    provider_name: str,
    access_token: str,
) -> Dict:
    """
    Install vault for a user with existing OAuth tokens.
    
    This is the main entry point - use existing tokens, install vault, mark active.
    """
    installer = VaultInstaller(provider_name, access_token, user_id)
    result = await installer.install_vault()
    
    if result["success"]:
        # Mark vault as active in database
        from app.modules.onboarding.gates import mark_gate
        await mark_gate(db, user_id, "vault_initialized")
        logger.info(f"Vault installed and activated for user {user_id[:6]}***")
    
    return result
