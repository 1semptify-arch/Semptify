"""
Semptify Vault Installer - Core Installation Logic

Direct vault creation using existing OAuth tokens.
No complex onboarding, just install and activate.

Uses Vault SDK for storage operations (SSOT for vault management).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.sdk.vault import VaultClient, TENANT_VAULT, VaultResult
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
    VAULT_ROOT,
)
from app.core.rehome import generate_rehome_html
from app.core.path_utils import normalize_cloud_path
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class VaultInstaller:
    """
    Standalone vault installer that creates the complete Semptify vault structure.
    
    Takes OAuth tokens and directly creates folders, files, and marks activation.
    No complex onboarding flow required.
    
    Uses Vault SDK for storage operations (SSOT for vault management).
    """

    def __init__(self, provider_name: str, access_token: str, user_id: str):
        self.provider_name = provider_name
        self.access_token = access_token
        self.user_id = user_id
        
        # Use Vault SDK for storage operations (SSOT)
        self.vault_client = VaultClient(
            provider=provider_name,
            access_token=access_token,
            user_id=user_id,
            folder_spec=TENANT_VAULT,
        )
        
        # Additional folders beyond base TENANT_VAULT spec
        self.additional_folders = [
            VAULT_TIMELINE,
            VAULT_OVERLAYS,
            normalize_cloud_path(f"{VAULT_OVERLAYS}/evidence"),
            normalize_cloud_path(f"{VAULT_OVERLAYS}/legal"),
            normalize_cloud_path(f"{VAULT_OVERLAYS}/timeline"),
            AUTH_FOLDER,
        ]
        
        # Register additional folders with SDK
        self.vault_client.register_folders(self.additional_folders)

    async def install_vault(self) -> Dict:
        """
        Install the complete vault structure using Vault SDK.
        
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
            logger.info("Step 1: Creating vault folders using SDK")
            # Step 1: Create all folders using Vault SDK
            vault_result = await self.vault_client.create_folders()
            if not vault_result.all_ok:
                results["errors"].extend([f"{f.path}: {f.detail}" for f in vault_result.failed])
                logger.error("Vault folder creation failed: %s", results["errors"])
                return results
            
            results["folders_created"] = [f.path for f in vault_result.succeeded]
            logger.info(f"Step 1 completed: Created {len(results['folders_created'])} vault folders via SDK")
            
            # Step 2: Create system files
            logger.info("Step 2: Creating system files")
            await self._create_system_files(results)
            logger.info("Step 2 completed: System files created")
            
            # Step 3: Create data files
            logger.info("Step 3: Creating data files")
            await self._create_data_files(results)
            logger.info("Step 3 completed: Data files created")
            
            # Step 4: Create encrypted token backup and device keys
            logger.info("Step 4: Creating token backup and device keys")
            await self._create_token_backup(results)
            logger.info("Step 4 completed: Token backup and device keys created")
            
            # Step 5: Verify installation using Vault SDK
            verification = await self._verify_installation()
            if not verification["ok"]:
                results["errors"].append(f"Verification failed: {verification['message']}")
                return results
            
            # Step 6: Generate activation code
            results["activation_code"] = self._generate_activation_code()
            results["success"] = True
            
            logger.info(f"Vault installed successfully for user {self.user_id[:6]}***")
            return results
            
        except Exception as e:
            logger.error(f"Vault installation failed: {e}")
            results["errors"].append(str(e))
            return results

    async def _create_system_files(self, results: Dict):
        """Create essential system files using Vault SDK."""
        system_files = {
            (normalize_cloud_path(SEMPTIFY_ROOT.replace(f"{VAULT_ROOT}/", "")), "README.txt"): self._readme_content(),
            (normalize_cloud_path(VAULT_FOLDER.replace(f"{VAULT_ROOT}/", "")), "manifest.json"): self._manifest_content(),
            (normalize_cloud_path(VAULT_FOLDER.replace(f"{VAULT_ROOT}/", "")), "vault_status.json"): self._status_content("installed"),
        }
        
        for (subfolder, filename), content in system_files.items():
            try:
                await self.vault_client.upload(
                    subfolder=subfolder,
                    filename=filename,
                    content=content.encode(),
                    mime_type="text/plain" if filename.endswith(".txt") else "application/json"
                )
                results["files_created"].append(f"{subfolder}/{filename}")
                logger.debug(f"Created system file: {subfolder}/{filename}")
            except Exception as e:
                results["errors"].append(f"Failed to create {subfolder}/{filename}: {str(e)}")

        # Rehome.html — written directly to SEMPTIFY_ROOT (not inside Vault/)
        # VaultClient.upload() prepends VAULT_ROOT so we use the storage provider directly.
        try:
            from app.core.config import get_settings
            settings = get_settings()
            base_url = (settings.public_base_url or "https://semptify.com").rstrip("/")
            rehome_html = generate_rehome_html(
                user_id=self.user_id,
                provider=self.provider_name,
                base_url=base_url,
            )
            storage = self.vault_client._get_storage()
            await storage.upload_file(
                file_content=rehome_html.encode(),
                destination_path=SEMPTIFY_ROOT,
                filename="Rehome.html",
                mime_type="text/html",
            )
            results["files_created"].append(f"{SEMPTIFY_ROOT}/Rehome.html")
            logger.debug("Created Rehome.html at %s/Rehome.html", SEMPTIFY_ROOT)
        except Exception as e:
            results["errors"].append(f"Failed to create Rehome.html: {str(e)}")

    async def _create_data_files(self, results: Dict):
        """Create initial data files using Vault SDK."""
        timeline_events = self._timeline_events_content()
        overlay_registry = self._overlay_registry_content()

        # Seed empty document index so read endpoints never 404 on first visit
        doc_index = {
            "version": "1.0",
            "created_by": self.user_id,
            "created_at": utc_now().isoformat(),
            "documents": [],
            "last_updated": utc_now().isoformat(),
        }
        try:
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(VAULT_DOCUMENTS.replace(f"{VAULT_ROOT}/", "")),
                filename="index.json",
                content=json.dumps(doc_index, indent=2).encode(),
                mime_type="application/json"
            )
            results["files_created"].append(normalize_cloud_path(f"{VAULT_DOCUMENTS}/index.json"))
        except Exception as e:
            results["errors"].append(f"Failed to create document index: {str(e)}")

        try:
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(VAULT_TIMELINE.replace(f"{VAULT_ROOT}/", "")),
                filename=VAULT_TIMELINE_EVENTS_FILENAME,
                content=json.dumps(timeline_events, indent=2).encode(),
                mime_type="application/json"
            )
            results["files_created"].append(normalize_cloud_path(f"{VAULT_TIMELINE}/{VAULT_TIMELINE_EVENTS_FILENAME}"))
        except Exception as e:
            results["errors"].append(f"Failed to create timeline events: {str(e)}")
        
        try:
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(VAULT_OVERLAYS.replace(f"{VAULT_ROOT}/", "")),
                filename="registry.json",
                content=json.dumps(overlay_registry, indent=2).encode(),
                mime_type="application/json"
            )
            results["files_created"].append(normalize_cloud_path(f"{VAULT_OVERLAYS}/registry.json"))
        except Exception as e:
            results["errors"].append(f"Failed to create overlay registry: {str(e)}")

    async def _verify_installation(self) -> Dict:
        """Comprehensive system test using Vault SDK - proves the vault is fully operational."""
        try:
            import secrets as _secrets
            details = []
            
            # 1. Use Vault SDK health check
            health = await self.vault_client.health_check()
            if not health.healthy:
                return {
                    "ok": False,
                    "message": f"Vault health check failed: {health.detail}",
                    "details": details,
                }
            details.append(f"health_check: {health.detail}")
            
            # 2. Write test using Vault SDK
            test_filename = f"_system_test_{_secrets.token_hex(4)}.txt"
            test_content = f"Semptify vault system test | user={self.user_id} | ts={utc_now().isoformat()}".encode()
            try:
                await self.vault_client.upload(
                    subfolder=normalize_cloud_path(VAULT_DOCUMENTS.replace(f"{VAULT_ROOT}/", "")),
                    filename=test_filename,
                    content=test_content,
                    mime_type="text/plain",
                )
                details.append(f"write_test: uploaded {test_filename}")
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Write test failed: {exc}",
                    "details": details,
                }
            
            # 3. Read test using Vault SDK
            try:
                read_back = await self.vault_client.download(
                    subfolder=normalize_cloud_path(VAULT_DOCUMENTS.replace(f"{VAULT_ROOT}/", "")),
                    filename=test_filename
                )
                if read_back != test_content:
                    raise ValueError("Content mismatch")
                details.append("read_test: content verified")
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Read test failed: {exc}",
                    "details": details,
                }
            
            # 4. Delete test using Vault SDK
            try:
                await self.vault_client.delete(
                    subfolder=normalize_cloud_path(VAULT_DOCUMENTS.replace(f"{VAULT_ROOT}/", "")),
                    filename=test_filename
                )
                details.append("delete_test: cleaned up")
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Delete test failed: {exc}",
                    "details": details,
                }
            
            # 5. System file integrity using Vault SDK
            system_files = {
                (normalize_cloud_path(SEMPTIFY_ROOT.replace(f"{VAULT_ROOT}/", "")), "README.txt"): "README",
                (normalize_cloud_path(VAULT_FOLDER.replace(f"{VAULT_ROOT}/", "")), "manifest.json"): "manifest",
                (normalize_cloud_path(VAULT_TIMELINE.replace(f"{VAULT_ROOT}/", "")), VAULT_TIMELINE_EVENTS_FILENAME): "timeline_events",
                (normalize_cloud_path(VAULT_OVERLAYS.replace(f"{VAULT_ROOT}/", "")), "registry.json"): "overlay_registry",
                (normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")), "token.enc"): "encrypted_token",
                (normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")), "device_keys.json"): "device_keys",
            }
            
            for (subfolder, filename), desc in system_files.items():
                try:
                    files = await self.vault_client.list_files(subfolder)
                    if files is None:
                        raise ValueError(f"{desc} folder not accessible")
                    file_names = [f.get("name", "") for f in files] if isinstance(files, list) else []
                    if filename not in file_names:
                        raise ValueError(f"{desc} file missing")
                    details.append(f"integrity_check: {desc} OK")
                except Exception as exc:
                    return {
                        "ok": False,
                        "message": f"System file check failed ({desc}): {exc}",
                        "details": details,
                    }
            
            return {
                "ok": True,
                "message": "Vault fully operational - all tests passed",
                "details": details,
            }
            
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
        """Generate vault manifest content using Vault SDK folder list."""
        manifest = {
            "semptify_version": "5.0",
            "vault_version": "1.0",
            "user_id": self.user_id,
            "provider": self.provider_name,
            "created_at": utc_now().isoformat(),
            "vault_status": "active",
            "installer": "vault_installer_v1.0_sdk",
            "folders": self.vault_client.list_expected_folders(),
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

    async def _create_token_backup(self, results: Dict):
        """Create encrypted token backup and device keys using Vault SDK encryption."""
        try:
            from app.sdk.vault.encryption import MasterToken, encrypt_token, decrypt_token
            from app.core.config import get_settings
            from app.core.vault_paths import TOKEN_FILE
            import secrets as _secrets

            # Get server secret key for encryption
            settings = get_settings()
            secret_key = getattr(settings, "SECRET_KEY", None) or getattr(settings, "secret_key", "")

            # Build master token with current OAuth credentials
            token = MasterToken(
                token_id=_secrets.token_urlsafe(32),
                user_id=self.user_id,
                created_at=utc_now().isoformat(),
                provider=self.provider_name,
                access_token=self.access_token,
            )

            encrypted = encrypt_token(token, self.user_id, secret_key)

            # Write primary using Vault SDK
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")),
                filename="token.enc",
                content=encrypted,
                mime_type="application/octet-stream",
            )
            results["files_created"].append(normalize_cloud_path(f"{AUTH_FOLDER}/token.enc"))
            
            # Write backup using Vault SDK
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")),
                filename="token.enc.backup",
                content=encrypted,
                mime_type="application/octet-stream",
            )
            results["files_created"].append(normalize_cloud_path(f"{AUTH_FOLDER}/token.enc.backup"))

            # Verify the primary can be read back and decrypted using Vault SDK
            read_back = await self.vault_client.download(
                subfolder=normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")),
                filename="token.enc"
            )
            decrypted = decrypt_token(read_back, self.user_id, secret_key)
            if decrypted.user_id != self.user_id:
                raise ValueError("Token backup read-back: user_id mismatch after decrypt")

            # Initialize empty device keys using Vault SDK
            device_keys = {"devices": [], "created_at": utc_now().isoformat()}
            await self.vault_client.upload(
                subfolder=normalize_cloud_path(AUTH_FOLDER.replace(f"{VAULT_ROOT}/", "")),
                filename="device_keys.json",
                content=json.dumps(device_keys, indent=2).encode(),
                mime_type="application/json",
            )
            results["files_created"].append(normalize_cloud_path(f"{AUTH_FOLDER}/device_keys.json"))

            logger.info("Encrypted token backup stored for user %s", self.user_id[:6] + "***")
            
        except Exception as e:
            results["errors"].append(f"Token backup failed: {str(e)}")
            raise


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


async def install_vault_folders_only(
    db: AsyncSession,
    user_id: str,
    provider_name: str,
    access_token: str,
    include_content: bool = True,
) -> Dict:
    """
    Install vault folders and essential content.
    
    This creates the folder structure and essential system files.
    Files are created quickly to stay within Cloudflare timeout.
    """
    installer = VaultInstaller(provider_name, access_token, user_id)
    
    results = {
        "success": False,
        "folders_created": [],
        "files_created": [],
        "errors": [],
        "activation_code": None,
    }
    
    try:
        logger.info("Creating vault folders for user %s", user_id[:6] + "***")
        
        # Step 1: Create all folders using Vault SDK
        vault_result = await installer.vault_client.create_folders()
        if not vault_result.all_ok:
            results["errors"].extend([f"{f.path}: {f.detail}" for f in vault_result.failed])
            logger.error("Vault folder creation failed: %s", results["errors"])
            return results
        
        results["folders_created"] = [f.path for f in vault_result.succeeded]
        logger.info(f"Created {len(results['folders_created'])} vault folders via SDK")
        
        # Step 2: Create essential system files (fast, small files)
        if include_content:
            logger.info("Creating essential system files...")
            await installer._create_system_files(results)
            logger.info(f"Created {len(results['files_created'])} system files")
            
            # Step 3: Create essential data files
            logger.info("Creating essential data files...")
            await installer._create_data_files(results)
            logger.info(f"Total files created: {len(results['files_created'])}")
        
        # Generate activation code
        results["activation_code"] = installer._generate_activation_code()
        results["success"] = True
        
        # Mark vault as initialized in database (CRITICAL: gate marking)
        from app.modules.onboarding.gates import mark_gate
        await mark_gate(db, user_id, "vault_initialized")
        logger.info(f"Vault gate marked as initialized for user {user_id[:6]}***")
        
        logger.info(f"Vault created successfully for user {user_id[:6]}*** with {len(results['files_created'])} files")
        
    except Exception as e:
        results["errors"].append(f"Vault creation failed: {str(e)}")
        logger.error("Vault creation error: %s", str(e))
    
    return results
