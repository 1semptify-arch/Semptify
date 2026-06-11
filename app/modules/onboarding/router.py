"""
Onboarding Router — all page and API routes for the onboarding flow.

Routes:
  GET  {prefix}/                     → entry point (role selection)
  GET  {prefix}/providers            → storage provider selection
  GET  {prefix}/auth/{provider}      → initiate OAuth (onboarding-specific)
  GET  {prefix}/callback/{provider}  → OAuth callback (onboarding-specific)
  GET  {prefix}/vault-setup          → vault setup page (step 1: build folders)
  GET  {prefix}/vault-setup/security → vault security page (step 2: token backup)
  GET  {prefix}/vault-setup/inspect  → vault inspect page (step 3: final check)
  POST {prefix}/api/vault/init       → create vault folders
  POST {prefix}/api/vault/security   → write token backup
  POST {prefix}/api/vault/verify     → live probe + document upload → marks both final gates
  GET  {prefix}/api/vault/status     → check user auth status
  GET  {prefix}/complete             → route to product home
  GET  {prefix}/status               → gate status check page
"""

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cookie_auth import clear_auth_cookie, verify_user_id, set_auth_cookie
from app.core.security import require_user, StorageUser, green_access
from app.core.workflow_engine import route_user
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding import gates as gate_ops
from app.modules.onboarding import oauth as oauth_ops
from app.modules.onboarding import vault as vault_ops

logger = logging.getLogger(__name__)


def create_router(config: OnboardingConfig) -> APIRouter:
    """
    Factory function — creates an APIRouter wired to the given config.
    Called by register_onboarding().
    """
    router = APIRouter(prefix=config.route_prefix, tags=["onboarding"])

    # ------------------------------------------------------------------
    # Root redirect — prevents trailing-slash redirect loop
    # ------------------------------------------------------------------
    @router.get("/")
    async def onboarding_root():
        """Redirect bare /onboarding/ to the real entry point."""
        return RedirectResponse(url=f"{config.route_prefix}/start", status_code=302)

    # ------------------------------------------------------------------
    # Test Route - Debug
    # ------------------------------------------------------------------
    @router.get("/test")
    async def test_onboarding():
        """Test route to verify onboarding module is accessible."""
        return {"status": "ok", "message": "Onboarding module is working"}

    # ------------------------------------------------------------------
    # Page: Role Selection (entry point)
    # ------------------------------------------------------------------
    @router.get("/role-select", response_class=HTMLResponse)
    async def role_select_static(request: Request, fresh: Optional[str] = Query(None)):
        """Serve the role selection page (static)."""
        # If fresh=true, clear the auth cookie to force new registration
        if fresh == "true":
            response = FileResponse(str(BASE_PATH / "static" / "onboarding" / "role-select.html"))
            clear_auth_cookie(response)
            return response
        
        role_select_path = BASE_PATH / "static" / "onboarding" / "role-select.html"
        if not role_select_path.exists():
            raise HTTPException(status_code=404, detail="Role selection page not found")
        return FileResponse(str(role_select_path))

    @router.get("/select-role.html", response_class=HTMLResponse)
    async def role_selection_page():
        """Show role selection page (Jinja2 template)."""
        return HTMLResponse(content=_render_role_selection_page(config))

    @router.get("/start")
    async def onboarding_start(
        semptify_uid: Optional[str] = Cookie(None),
    ):
        """Smart entry: returning user → reconnect, new user → role select."""
        if semptify_uid:
            raw_uid = verify_user_id(semptify_uid)
            if raw_uid:
                return ssot_redirect(navigation.get_reconnect_flow(), context="onboarding_start reconnect")
        role_stage = navigation.get_stage("role_select")
        return ssot_redirect(role_stage.path, context="onboarding_start new_user")

    # ------------------------------------------------------------------
    # Page: Provider Selection
    # ------------------------------------------------------------------
    @router.get("/providers", response_class=HTMLResponse)
    async def providers_page(
        role: Optional[str] = Query("tenant"),
        semptify_uid: Optional[str] = Cookie(None),
    ):
        """Show storage provider selection. Config-driven provider list.

        Returning users (have valid cookie) are redirected to reconnect flow
        to skip role/provider selection and go straight to OAuth refresh.
        """
        if semptify_uid:
            raw_uid = verify_user_id(semptify_uid)
            if raw_uid:
                # Returning user detected — send to reconnect, skip new user flow
                return ssot_redirect(navigation.get_reconnect_flow(), context="providers_page reconnect")
        return HTMLResponse(content=_render_providers_page(config))

    # ------------------------------------------------------------------
    # OAuth: Initiate (onboarding-specific callback URL)
    # ------------------------------------------------------------------
    @router.get("/auth/{provider}")
    async def onboarding_oauth_start(
        provider: str,
        role: str = Query("tenant"),
        force_fresh: bool = Query(False),
        db: AsyncSession = Depends(get_db),
        request: Request = None,
    ):
        """Initiate OAuth for onboarding. Uses onboarding callback URL."""
        logger.info("=== OAUTH REQUEST RECEIVED ===")
        logger.info("onboarding_oauth_start: provider=%s role=%s force_fresh=%s", provider, role, force_fresh)
        logger.info("Request URL: %s", str(request.url) if request else "No request")
        logger.info("Request headers: %s", dict(request.headers) if request else "No headers")
        
        if provider not in config.allowed_providers:
            logger.error("onboarding_oauth_start: provider '%s' not in allowed_providers: %s", provider, config.allowed_providers)
            raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")
        allowed_roles = getattr(gate_ops, 'ALLOWED_ROLES', {"tenant"})
        if role not in allowed_roles:
            role = "tenant"

        # Build callback URL — resolve the real public URL (Render proxy-aware)
        from app.core.config import get_settings as _get_settings
        _settings = _get_settings()
        if _settings.public_base_url:
            base_url = _settings.public_base_url.rstrip("/")
        else:
            # Render sets X-Forwarded-Host + X-Forwarded-Proto on every request
            fwd_host = request.headers.get("x-forwarded-host")
            fwd_proto = request.headers.get("x-forwarded-proto", "https")
            if fwd_host:
                base_url = f"{fwd_proto}://{fwd_host}"
            else:
                base_url = str(request.base_url).rstrip("/")
        callback_url = f"{base_url}{config.route_prefix}/callback/{provider}"

        try:
            state = await oauth_ops.create_oauth_state(db, provider, role, callback_url, force_fresh)
            auth_url = oauth_ops.build_oauth_url(config, provider, state, callback_url, force_fresh)
        except Exception as exc:
            logger.exception("OAuth initiation failed: provider=%s role=%s error=%s", provider, role, exc)
            raise HTTPException(status_code=500, detail="OAuth initiation failed") from exc

        logger.info("Onboarding OAuth initiated: provider=%s role=%s callback=%s headers_host=%s headers_proto=%s",
                    provider, role, callback_url,
                    request.headers.get("x-forwarded-host", "NONE"),
                    request.headers.get("x-forwarded-proto", "NONE"))
        # OAuth is external - use direct redirect
        return RedirectResponse(url=auth_url, status_code=302)

    # ------------------------------------------------------------------
    # OAuth: Callback (onboarding-specific)
    # ------------------------------------------------------------------
    @router.get("/callback/{provider}")
    async def onboarding_oauth_callback(
        provider: str,
        code: str = Query(...),
        state: str = Query(...),
        request: Request = None,
        db: AsyncSession = Depends(get_db),
    ):
        """
        Handle OAuth callback for onboarding. This callback:
        1. Exchanges code for tokens
        2. Creates or finds user
        3. Saves session + caches token
        4. Marks storage_connected gate
        5. ALWAYS routes to vault-setup (onboarding callback = vault needed)
        """
        try:
            logger.info("OAuth callback started: provider=%s state=%s", provider, state[:8] + "***")
            
            from app.core.config import get_settings as _get_settings
            _settings = _get_settings()
            if _settings.public_base_url:
                base_url = _settings.public_base_url.rstrip("/")
            else:
                fwd_host = request.headers.get("x-forwarded-host")
                fwd_proto = request.headers.get("x-forwarded-proto", "https")
                if fwd_host:
                    base_url = f"{fwd_proto}://{fwd_host}"
                else:
                    base_url = str(request.base_url).rstrip("/")
            callback_url = f"{base_url}{config.route_prefix}/callback/{provider}"
            
            logger.info("OAuth callback: built callback_url=%s", callback_url)

            result = await oauth_ops.handle_onboarding_callback(
                db=db,
                provider=provider,
                code=code,
                state=state,
                callback_url=callback_url,
                config=config,
            )
            
            logger.info("OAuth callback: handle_onboarding_callback completed")

            user_id = result["user_id"]
            vault_initialized = result["vault_initialized"]
            
            logger.info("OAuth callback: user_id=%s vault_initialized=%s", user_id[:6] + "***", vault_initialized)

            # Determine landing — always route to selected role's home page
            if vault_initialized:
                landing = await route_user(user_id)
            else:
                landing = f"{config.route_prefix}/vault-setup"

            logger.info(
                "Onboarding callback complete: user=%s vault=%s → %s",
                user_id[:6] + "***", vault_initialized, landing,
            )

            # Use SSOT-compliant redirect
            from app.core.ssot_guard import ssot_redirect
            response = ssot_redirect(landing, context="onboarding_oauth_callback")
            
            logger.info("OAuth callback: about to set cookie for user=%s", user_id[:6] + "***")
            set_auth_cookie(response, user_id, secure=request.url.scheme == "https")
            logger.info("OAuth callback: cookie set successfully")
            
            return response
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error("OAuth callback failed: %s\n%s", str(e), tb)
            return HTMLResponse(
                content=f"""<pre style="font-family:monospace;padding:2rem;background:#1e1e1e;color:#f44;max-width:100%;overflow:auto">
<b>OAuth Callback Error (debug mode)</b>

{str(e)}

{tb}
</pre>""",
                status_code=500,
            )

    # ------------------------------------------------------------------
    # Page: Vault Setup — Step 1: Build Folders
    # ------------------------------------------------------------------
    @router.get("/vault-setup", response_class=HTMLResponse)
    async def vault_setup_page(semptify_uid: Optional[str] = Cookie(None)):
        """Step 1: Create vault folders."""
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="vault_setup no cookie")
        return HTMLResponse(content=_render_vault_step1(config))

    # ------------------------------------------------------------------
    # Page: Vault Setup — Step 2: Security Wiring
    # ------------------------------------------------------------------
    @router.get("/vault-setup/security", response_class=HTMLResponse)
    async def vault_security_page(semptify_uid: Optional[str] = Cookie(None)):
        """Step 2: Write token backup and security files."""
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="vault_security no cookie")
        return HTMLResponse(content=_render_vault_step2(config))

    # ------------------------------------------------------------------
    # Page: Vault Setup — Step 3: Final Inspection
    # ------------------------------------------------------------------
    @router.get("/vault-setup/inspect", response_class=HTMLResponse)
    async def vault_inspect_page(semptify_uid: Optional[str] = Cookie(None)):
        """Step 3: Verify vault is fully operational."""
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="vault_inspect no cookie")
        return HTMLResponse(content=_render_vault_step3(config))

    # ------------------------------------------------------------------
    # API: Vault Status — single source, used by vault_status_poll.js
    # ------------------------------------------------------------------
    @router.get("/api/vault/status")
    async def vault_status(
        user: StorageUser = Depends(green_access),
        db: AsyncSession = Depends(get_db),
    ):
        """Return vault gate state for UI polling.

        Returns vault_initialized, document_uploaded, and document_count.
        vault_status_poll.js watches both gates before redirecting to /complete.
        """
        try:
            from app.modules.onboarding.gates import check_gate
            from app.services.vault_upload_service import VaultUploadService

            vault_initialized = await check_gate(db, user.user_id, "vault_initialized")
            document_uploaded = await check_gate(db, user.user_id, "document_uploaded")

            svc = VaultUploadService()
            docs = await svc.get_user_documents(user.user_id)
            document_count = len(docs) if docs is not None else 0

            return {
                "vault_initialized": bool(vault_initialized),
                "document_uploaded": bool(document_uploaded),
                "document_count": document_count,
                "storage_connected": True,
                "provider": user.provider.value if hasattr(user.provider, "value") else str(user.provider),
            }
        except Exception as e:
            logger.warning("vault_status error for user %s: %s", user.user_id[:6] + "***", str(e))
            return {"vault_initialized": False, "document_uploaded": False, "document_count": 0}

    # ------------------------------------------------------------------
    # API: Initialize Vault — Step 1: Folders + seed files only
    # ------------------------------------------------------------------
    @router.post("/api/vault/init")
    async def vault_init(
        user: StorageUser = Depends(green_access),
        db: AsyncSession = Depends(get_db),
    ):
        """Step 1: Create vault folder structure and seed files only."""
        from app.modules.vault_installer.installer import VaultInstaller
        from app.modules.onboarding.gates import check_gate
        import asyncio

        provider_name = user.provider.value if hasattr(user.provider, 'value') else str(user.provider)

        if await check_gate(db, user.user_id, "vault_initialized"):
            logger.info("Vault init skipped: already initialized for user %s", user.user_id[:6] + "***")
            return {"success": True, "message": "Vault already initialized", "folders_created": []}

        installer = VaultInstaller(provider_name, user.access_token, user.user_id)

        results = {"success": False, "folders_created": [], "files_created": [], "errors": []}
        try:
            logger.info("Step 1: Creating vault folders for user %s", user.user_id[:6] + "***")
            vault_result = await asyncio.wait_for(
                installer.vault_client.create_folders(), timeout=25.0
            )
            if not vault_result.all_ok:
                results["errors"] = [f"{f.path}: {f.detail}" for f in vault_result.failed]
                return results
            results["folders_created"] = [f.path for f in vault_result.succeeded]
            results["success"] = True
            logger.info("Step 1 complete: %d folders", len(results["folders_created"]))
            return results
        except asyncio.TimeoutError:
            logger.error("Vault init timed out for user %s", user.user_id[:6] + "***")
            return {"success": False, "error": "Timed out creating folders — please retry", "folders_created": [], "files_created": [], "errors": ["timeout"]}
        except Exception as e:
            logger.error("Vault init error for user %s: %s", user.user_id[:6] + "***", str(e))
            return {"success": False, "error": str(e), "folders_created": [], "files_created": [], "errors": [str(e)]}

    # ------------------------------------------------------------------
    # API: Vault Security — Step 2: Token backup
    # ------------------------------------------------------------------
    @router.post("/api/vault/security")
    async def vault_security(
        user: StorageUser = Depends(green_access),
        db: AsyncSession = Depends(get_db),
    ):
        """Step 2: Write encrypted token backup and device keys."""
        from app.modules.vault_installer.installer import VaultInstaller
        import asyncio

        provider_name = user.provider.value if hasattr(user.provider, 'value') else str(user.provider)
        installer = VaultInstaller(provider_name, user.access_token, user.user_id)

        results = {"success": False, "files_created": [], "errors": []}
        try:
            logger.info("Step 2: Writing token backup + system files for user %s", user.user_id[:6] + "***")
            # Write the critical token backup synchronously (short timeout) so
            # the probe and subsequent steps can rely on it being present.
            try:
                await asyncio.wait_for(installer._create_token_backup(results), timeout=20.0)
            except asyncio.TimeoutError:
                logger.error("Token backup timed out for user %s", user.user_id[:6] + "***")
                return {"success": False, "error": "Timed out writing token backup — please retry", "files_created": [], "errors": ["timeout"]}

            if results["errors"]:
                raise Exception("Token backup failed: " + ", ".join(results["errors"]))

            # Schedule system and data files in background to avoid exceeding
            # upstream gateway time limits (Cloudflare ~30s). These are not
            # strictly required to be present synchronously for onboarding to
            # continue, so run them asynchronously and log any failures.
            async def _create_noncritical_files(res):
                try:
                    await installer._create_system_files(res)
                    await installer._create_data_files(res)
                except Exception as bg_err:
                    logger.warning("Background vault files creation failed for user %s: %s", user.user_id[:6] + "***", bg_err)

            # Fire-and-forget background task
            _task = asyncio.create_task(_create_noncritical_files(results))

            results["success"] = True
            logger.info("Step 2 scheduled background file writes for user %s", user.user_id[:6] + "***")
            return results
        except Exception as e:
            logger.error("Vault security error for user %s: %s", user.user_id[:6] + "***", str(e))
            return {"success": False, "error": str(e), "files_created": [], "errors": [str(e)]}

    # ------------------------------------------------------------------
    # API: Verify Vault
    # ------------------------------------------------------------------
    @router.post("/api/vault/verify")
    async def vault_verify(
        request: Request,
        user: StorageUser = Depends(green_access),
        db: AsyncSession = Depends(get_db),
    ):
        """
        Step 3 final gate.

        1. Live write/read-back probe — proves the vault is writable.
        2. Routes the uploaded document through VaultUploadService (the canonical
           full pipeline): certificate → registry → overlay → timeline extraction
           → event bus → positronic mesh workflows.
        3. Marks the document_uploaded gate only after the pipeline succeeds.

        A document is REQUIRED — there is no skip path.
        """
        import asyncio
        import secrets as _secrets
        from app.core.utc import utc_now
        from app.sdk.vault import VaultClient, TENANT_VAULT
        from app.core.vault_paths import VAULT_ROOT, VAULT_DOCUMENTS
        from app.core.path_utils import normalize_cloud_path

        provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)

        # ── 1. Require a real file upload ─────────────────────────────────────
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type:
            return {"ok": False, "accessible": False, "error": "A document is required to complete setup"}

        form = await request.form()
        upload = form.get("file")
        if not upload or not hasattr(upload, "filename") or not upload.filename:
            return {"ok": False, "accessible": False, "error": "Please select a document to upload"}

        file_bytes = await upload.read()
        if not file_bytes:
            return {"ok": False, "accessible": False, "error": "The selected file appears to be empty"}

        # ── 2. Live probe — write a temp file, read it back, delete it ────────
        try:
            client = VaultClient(
                provider=provider_name,
                access_token=user.access_token,
                user_id=user.user_id,
                folder_spec=TENANT_VAULT,
            )
            # SDK expects relative path to VAULT_ROOT. Strip prefix.
            subfolder = VAULT_DOCUMENTS.replace(f"{VAULT_ROOT}/", "")
            probe_name = f"_vault_probe_{_secrets.token_hex(4)}.txt"
            probe_bytes = (
                f"Semptify vault probe | user={user.user_id} | ts={utc_now().isoformat()}"
            ).encode()
            await asyncio.wait_for(
                client.upload(subfolder=subfolder, filename=probe_name,
                              content=probe_bytes, mime_type="text/plain"),
                timeout=25.0,
            )
            read_back = await asyncio.wait_for(
                client.download(subfolder=subfolder, filename=probe_name),
                timeout=25.0,
            )
            if read_back != probe_bytes:
                raise ValueError("Read-back mismatch — vault storage is unreliable")
            await client.delete(subfolder=subfolder, filename=probe_name)
        except asyncio.TimeoutError:
            logger.error("Vault probe timed out for user %s", user.user_id[:6] + "***")
            return {"ok": False, "accessible": False, "error": "Vault probe timed out — please retry"}
        except Exception as e:
            logger.error("Vault probe failed for user %s: %s", user.user_id[:6] + "***", str(e))
            return {"ok": False, "accessible": False, "error": f"Vault probe failed: {str(e)}"}

        # ── 3. Full pipeline via VaultUploadService ────────────────────────────
        #   certificate → registry → overlay → timeline → event bus → mesh
        try:
            from app.services.vault_upload_service import VaultUploadService

            mime_type = upload.content_type or "application/octet-stream"
            original_name = upload.filename

            vault_service = VaultUploadService()
            vault_doc = await asyncio.wait_for(
                vault_service.upload(
                    user_id=user.user_id,
                    filename=original_name,
                    content=file_bytes,
                    mime_type=mime_type,
                    document_type=None,         # classifier will determine type
                    description="First document — uploaded during vault setup",
                    tags=["onboarding", "first_document"],
                    source_module="onboarding",
                    access_token=user.access_token,
                    storage_provider=provider_name,
                ),
                timeout=55.0,
            )

            # Verify the uploaded document can be retrieved from the vault storage.
            # This ensures stage 3 only passes when the uploaded file is actually present.
            stored_bytes = await asyncio.wait_for(
                vault_service.get_document_content(vault_doc.vault_id, access_token=user.access_token),
                timeout=40.0,
            )
            if stored_bytes is None:
                raise ValueError("Uploaded document could not be retrieved from vault storage")
            if stored_bytes != file_bytes:
                raise ValueError("Uploaded document contents do not match vault storage")

            if not vault_doc.registry_id or vault_doc.integrity_status != "verified":
                raise ValueError(
                    "Document was stored but did not receive a registry document ID."
                    " Please retry or contact support."
                )

            user_documents = await vault_service.get_user_documents(user.user_id)
            document_count = len(user_documents)

            # Kick off intake + flow orchestration in the background
            # (non-blocking — onboarding completes regardless)
            async def _run_pipeline(vault_id: str, uid: str) -> None:
                try:
                    from app.services.document_intake import DocumentIntakeEngine
                    from app.services.document_flow_orchestrator import DocumentFlowOrchestrator
                    engine = DocumentIntakeEngine()
                    intake_doc = await engine.intake_document(
                        user_id=uid,
                        file_content=file_bytes,
                        filename=original_name,
                        mime_type=mime_type,
                        vault_id=vault_id,
                    )
                    await engine.process_document(intake_doc.id)
                    orchestrator = DocumentFlowOrchestrator()
                    await orchestrator.process_document_complete(
                        doc_id=intake_doc.id, user_id=uid, db_session=db
                    )
                except Exception as pipeline_err:
                    logger.warning(
                        "Background pipeline error for vault_doc %s: %s", vault_id, pipeline_err
                    )

            import asyncio as _asyncio
            _asyncio.create_task(_run_pipeline(vault_doc.vault_id, user.user_id))

        except asyncio.TimeoutError:
            logger.error("VaultUploadService timed out for user %s", user.user_id[:6] + "***")
            return {"ok": False, "accessible": True, "error": "Upload timed out — please try again"}
        except Exception as e:
            logger.error("VaultUploadService failed for user %s: %s", user.user_id[:6] + "***", str(e))
            return {"ok": False, "accessible": True, "error": str(e)}

        # ── 4. Mark the final onboarding gates ────────────────────────────────
        # vault_initialized is only marked HERE — after folders, files, token
        # backup, live write/read probe, and document pipeline all pass.
        # Marking it earlier (e.g. after step 1) would give a false green.
        from app.modules.onboarding.gates import mark_gate
        await mark_gate(db, user.user_id, "vault_initialized")
        await mark_gate(db, user.user_id, "document_uploaded")

        logger.info(
            "Final gate passed — '%s' seeded all systems for user %s",
            original_name, user.user_id[:6] + "***",
        )
        return {
            "ok": True,
            "accessible": True,
            "document_saved": True,
            "document_name": original_name,
            "vault_id": vault_doc.vault_id,
            "document_id": vault_doc.registry_id,
            "certified": vault_doc.is_certified,
            "document_count": document_count,
        }



    # ------------------------------------------------------------------
    # API: System Verification — Final health check before completion
    # ------------------------------------------------------------------
    @router.post("/api/vault/system-check")
    async def system_check(
        user: StorageUser = Depends(require_user),
        db: AsyncSession = Depends(get_db),
    ):
        """
        Comprehensive system verification before marking onboarding complete.
        
        Checks all critical systems:
        1. Database connection and user record
        2. OAuth tokens valid and not expired
        3. Vault folders accessible via provider API
        4. User ID cookie signature valid
        5. All required modules loaded
        6. Pipeline services ready
        
        Returns detailed status for each system.
        """
        from app.core.cookie_auth import verify_user_id
        from app.sdk.vault import VaultClient, TENANT_VAULT
        from app.core.vault_paths import VAULT_DOCUMENTS
        from app.core.path_utils import normalize_cloud_path
        import asyncio

        provider_name = user.provider.value if hasattr(user.provider, "value") else str(user.provider)
        results = {
            "all_systems_go": False,
            "checks": {},
            "errors": []
        }

        # Check 1: Database connection and user record
        try:
            from sqlalchemy import select
            from app.models.models import User
            stmt = select(User).where(User.id == user.user_id)
            result = await db.execute(stmt)
            db_user = result.scalar_one_or_none()
            results["checks"]["database"] = {
                "status": "ok" if db_user else "failed",
                "detail": "User record found" if db_user else "User record missing"
            }
            if not db_user:
                results["errors"].append("Database: User record not found")
        except Exception as e:
            results["checks"]["database"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Database error: {str(e)}")

        # Check 2: OAuth tokens valid
        try:
            from app.core.oauth_token_manager import OAuthToken
            from app.modules.storage.router import get_valid_session
            session = await get_valid_session(db, user.user_id, auto_refresh=False)
            if session and session.get("access_token"):
                token = OAuthToken.from_dict(session)
                if not token.is_expired():
                    results["checks"]["oauth_tokens"] = {
                        "status": "ok",
                        "detail": f"Token valid, expires in {token.expires_in_seconds()}s"
                    }
                else:
                    results["checks"]["oauth_tokens"] = {
                        "status": "expired",
                        "detail": "OAuth token expired"
                    }
                    results["errors"].append("OAuth: Token expired")
            else:
                results["checks"]["oauth_tokens"] = {
                    "status": "failed",
                    "detail": "No valid session found"
                }
                results["errors"].append("OAuth: No valid session")
        except Exception as e:
            results["checks"]["oauth_tokens"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"OAuth error: {str(e)}")

        # Check 3: Vault folders accessible
        try:
            client = VaultClient(
                provider=provider_name,
                access_token=user.access_token,
                user_id=user.user_id,
                folder_spec=TENANT_VAULT
            )
            # Try to list documents folder as a health check
            docs_path = normalize_cloud_path(VAULT_DOCUMENTS)
            files = await asyncio.wait_for(
                client.list_files(docs_path),
                timeout=10.0
            )
            results["checks"]["vault_access"] = {
                "status": "ok",
                "detail": f"Vault accessible, {len(files)} files in documents folder"
            }
        except asyncio.TimeoutError:
            results["checks"]["vault_access"] = {"status": "timeout", "detail": "Vault access timed out"}
            results["errors"].append("Vault: Access timeout")
        except Exception as e:
            results["checks"]["vault_access"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Vault error: {str(e)}")

        # Check 4: Vault gate consistency
        try:
            from app.modules.onboarding.gates import check_gate
            vault_initialized = await check_gate(db, user.user_id, "vault_initialized")
            results["checks"]["vault_gate_consistency"] = {
                "status": "ok" if vault_initialized else "pending",
                "detail": "vault_initialized gate is set" if vault_initialized else "vault_initialized gate not yet set"
            }
            if vault_initialized and results["checks"]["vault_access"]["status"] != "ok":
                results["checks"]["vault_gate_consistency"] = {
                    "status": "warning",
                    "detail": "vault_initialized gate set but vault storage access failed"
                }
                results["errors"].append("Inconsistent state: vault_initialized gate set but storage access failed")
        except Exception as e:
            results["checks"]["vault_gate_consistency"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Vault gate consistency error: {str(e)}")

        # Check 5: User ID format valid
        try:
            from app.core.user_id import parse_user_id
            provider_code, role_code, unique_part = parse_user_id(user.user_id)
            valid_uid = bool(provider_code and role_code and unique_part)
            results["checks"]["user_id"] = {
                "status": "ok" if valid_uid else "failed",
                "detail": "User ID format valid" if valid_uid else "Invalid user ID format"
            }
            if not valid_uid:
                results["errors"].append("User ID: invalid format")
        except Exception as e:
            results["checks"]["user_id"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"User ID error: {str(e)}")

        # Check 5: Required modules loaded
        try:
            from app.services.document_intake import DocumentIntakeEngine
            from app.services.document_registry import DocumentRegistry
            results["checks"]["modules"] = {
                "status": "ok",
                "detail": "DocumentIntakeEngine and DocumentRegistry loaded"
            }
        except Exception as e:
            results["checks"]["modules"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Modules error: {str(e)}")

        # Check 6: Pipeline services ready
        try:
            from app.services.storage.vault_upload_service import VaultUploadService
            results["checks"]["pipeline"] = {
                "status": "ok",
                "detail": "VaultUploadService loaded"
            }
        except Exception as e:
            results["checks"]["pipeline"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Pipeline error: {str(e)}")

        # Final determination
        results["all_systems_go"] = (
            results["checks"].get("database", {}).get("status") == "ok" and
            results["checks"].get("oauth_tokens", {}).get("status") == "ok" and
            results["checks"].get("vault_access", {}).get("status") == "ok" and
            results["checks"].get("user_id", {}).get("status") == "ok" and
            results["checks"].get("modules", {}).get("status") == "ok" and
            results["checks"].get("pipeline", {}).get("status") == "ok"
        )

        return results

    # ------------------------------------------------------------------
    # Page: Complete
    # ------------------------------------------------------------------
    @router.get("/complete")
    async def onboarding_complete(
        semptify_uid: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db)
    ):
        """Validate onboarding completion and route to product home page."""
        from app.modules.onboarding.gates import check_gate
        
        if not semptify_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="onboarding_complete no cookie")
        
        raw_uid = verify_user_id(semptify_uid)
        if not raw_uid:
            role_stage = navigation.get_stage("role_select")
            return ssot_redirect(role_stage.path, context="onboarding_complete bad cookie")
        
        # All 3 gates must be passed in order
        storage_connected  = await check_gate(db, raw_uid, "storage_connected")
        vault_initialized  = await check_gate(db, raw_uid, "vault_initialized")
        document_uploaded  = await check_gate(db, raw_uid, "document_uploaded")

        if not storage_connected:
            return ssot_redirect(f"{config.route_prefix}/providers", context="onboarding_complete storage_missing")

        if not vault_initialized:
            return ssot_redirect(f"{config.route_prefix}/vault-setup", context="onboarding_complete vault_missing")

        if not document_uploaded:
            return ssot_redirect(f"{config.route_prefix}/vault-setup/inspect", context="onboarding_complete document_missing")

        # All gates passed - route to role-specific homepage
        destination = await route_user(raw_uid)
        logger.info("Onboarding completed successfully for user %s → %s", raw_uid[:6] + "***", destination)
        return ssot_redirect(destination, context="onboarding_complete success")

    # ------------------------------------------------------------------
    # Page: Gate Status
    # ------------------------------------------------------------------
    @router.get("/status", response_class=HTMLResponse)
    async def onboarding_status(
        semptify_uid: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db),
    ):
        """Check current gate status and show appropriate page."""
        if not semptify_uid:
            return ssot_redirect(f"{config.route_prefix}/", context="status no cookie")

        raw_uid = verify_user_id(semptify_uid)
        if not raw_uid:
            return ssot_redirect(f"{config.route_prefix}/", context="status bad cookie")

        incomplete = await gate_ops.get_first_incomplete_gate(db, raw_uid, config.gates)
        if incomplete is None:
            # Role-based redirect after onboarding completion
            from app.core.user_id import parse_user_id
            _, role, _ = parse_user_id(raw_uid)
            if role == "admin":
                return ssot_redirect("/admin/dashboard", context="status all gates done admin")
            return ssot_redirect(config.on_complete_redirect, context="status all gates done")

        return HTMLResponse(content=_render_status_page(config, incomplete))

    # ------------------------------------------------------------------
    # SSOT Navigation API
    # ------------------------------------------------------------------
    @router.get("/ssot-navigation")
    async def ssot_navigation():
        """Export navigation state for static files."""
        return navigation.to_dict()

    return router


# ============================================================================
# Page Renderers (minimal — these generate the HTML that JS drives)
# ============================================================================

def _render_role_selection_page(config: OnboardingConfig) -> str:
    """Render role selection page — all 5 roles, non-tenant marked Coming Soon."""
    providers_path = f"{config.route_prefix}/providers"

    roles = [
        ("tenant",  "🏠", "Tenant",             "I'm renting a home and need to protect my rights", True),
        ("manager", "�", "Worker / Manager",    "I work with multiple clients across housing cases", False),
        ("advocate","⚖️", "Housing Advocate",    "I help tenants navigate housing law", False),
        ("legal",   "📋", "Legal Professional",  "I'm an attorney or paralegal working housing cases", False),
        ("admin",   "🛡️", "Administrator",       "Platform administration and oversight", False),
    ]

    role_cards = ""
    for role_id, icon, name, desc, active in roles:
        if active:
            dest = f"{providers_path}?role={role_id}"
            role_cards += f"""
<a class="role-option active" href="{dest}">
  <div class="role-icon">{icon}</div>
  <div class="role-info">
    <div class="role-name">{name}</div>
    <div class="role-desc">{desc}</div>
  </div>
</a>"""
        else:
            role_cards += f"""
<div class="role-option coming-soon" title="Coming soon">
  <div class="role-icon">{icon}</div>
  <div class="role-info">
    <div class="role-name">{name} <span class="badge">Coming Soon</span></div>
    <div class="role-desc">{desc}</div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Select Your Role — {config.product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; padding: 2.5rem 2rem; text-align: center; }}
.header h1 {{ font-size: 2rem; font-weight: 400; letter-spacing: -0.02em; }}
.header .sub {{ font-size: 0.95rem; opacity: 0.8; margin-top: 0.4rem; font-style: italic; }}
.container {{ max-width: 560px; margin: 2rem auto; padding: 0 1.5rem 3rem; }}
.role-option {{ border: 2px solid #e2e8f0; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; background: white; display: flex; align-items: center; gap: 1rem; transition: all 0.2s; }}
.role-option.active {{ cursor: pointer; text-decoration: none; color: inherit; }}
.role-option.active:hover {{ border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.15); transform: translateY(-2px); }}
.role-option.coming-soon {{ opacity: 0.55; cursor: not-allowed; background: #f8fafc; }}
.role-icon {{ font-size: 2rem; flex-shrink: 0; width: 2.5rem; text-align: center; }}
.role-name {{ font-size: 1.05rem; font-weight: 600; color: #1e3a5f; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem; }}
.role-desc {{ font-size: 0.875rem; color: #64748b; line-height: 1.4; }}
.badge {{ font-size: 0.65rem; font-weight: 600; background: #f1f5f9; color: #94a3b8; border: 1px solid #e2e8f0; padding: 0.15rem 0.5rem; border-radius: 99px; letter-spacing: 0.04em; text-transform: uppercase; }}
</style>
</head><body>
<div class="header">
  <h1>Who are you?</h1>
  <div class="sub">Select your role to get started with {config.product_name}</div>
</div>
<div class="container">
{role_cards}
</div>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""

def _render_providers_page(config: OnboardingConfig) -> str:
    """Render storage provider selection page."""
    provider_cards = ""
    provider_info = {
        "google_drive": ("Google Drive", "🟢", "Free 15 GB • Fast sync"),
        "dropbox": ("Dropbox", "🔵", "Free 2 GB • Reliable sync"),
        "onedrive": ("OneDrive", "🟠", "Free 5 GB • Microsoft integration"),
    }
    for p in config.allowed_providers:
        name, icon, desc = provider_info.get(p, (p, "📁", "Cloud storage"))
        provider_cards += f"""
        <button class="provider-card" onclick="selectProvider('{p}')">
            <span class="provider-icon">{icon}</span>
            <span class="provider-name">{name}</span>
            <span class="provider-desc">{desc}</span>
        </button>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Connect Storage — {config.product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1e3a5f, #2d5a87); color: white; padding: 2.5rem 2rem; text-align: center; }}
.header h1 {{ font-size: 1.8rem; font-weight: 400; }}
.header .sub {{ font-size: 0.95rem; opacity: 0.85; font-style: italic; margin-top: 0.25rem; }}
.container {{ max-width: 600px; margin: 2rem auto; padding: 0 1.5rem; }}
.provider-grid {{ display: grid; gap: 1rem; }}
.provider-card {{ border: 2px solid #e2e8f0; border-radius: 12px; padding: 1.25rem; background: white; cursor: pointer; transition: all 0.2s; text-align: left; display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; gap: 0.25rem 0.75rem; font-family: inherit; }}
.provider-card:hover {{ border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59,130,246,0.12); transform: translateY(-2px); }}
.provider-icon {{ font-size: 1.75rem; grid-row: 1/3; align-self: center; }}
.provider-name {{ font-size: 1.05rem; font-weight: 600; color: #1e3a5f; }}
.provider-desc {{ font-size: 0.85rem; color: #64748b; }}
.trust {{ margin-top: 2rem; padding: 1.25rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; font-size: 0.9rem; color: #166534; }}
</style></head><body>
<div class="header">
    <h1>Connect Your Storage</h1>
    <div class="sub">Your documents stay in YOUR cloud — we never store them on our servers</div>
</div>
<div class="container">
    <div class="provider-grid">{provider_cards}</div>
    <div class="trust">
        <strong>Your privacy is protected.</strong> {config.product_name} stores documents in your personal
        cloud storage. We never have access to your files. You can disconnect at any time.
    </div>
</div>
<script>
function selectProvider(provider) {{
    const role = new URLSearchParams(window.location.search).get('role') || 'tenant';
    window.location.href = '{config.route_prefix}/auth/' + provider + '?role=' + role;
}}
</script>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""


_VAULT_FACTS = [
    "Minnesota has one of the strongest tenant protection laws in the U.S., including the Just Cause Eviction Act.",
    "Landlords must give you 14 days\u2019 notice before filing for eviction in most cases.",
    "You have the right to a habitable home \u2014 heat, water, and working locks are legally required.",
    "Retaliatory eviction (evicting you for complaining) is illegal in Minnesota.",
    "Security deposits must be returned within 21 days after you move out, with an itemized list of deductions.",
    "You can withhold rent for serious habitability issues, but you must follow specific legal procedures first.",
    "Landlords cannot enter your home without 24 hours\u2019 notice, except in emergencies.",
    "Discrimination based on race, disability, or having children is illegal under federal and state law.",
    "You have the right to organize with other tenants to address building-wide issues.",
    "Semptify stores all your documents in YOUR cloud storage \u2014 we never see your files.",
]


def _vault_step_shell(product_name: str, step_num: int, icon: str, headline: str, subline: str, body_html: str, script: str) -> str:
    """Shared HTML shell for all 3 vault setup steps."""
    import json as _json
    facts_js = _json.dumps(_VAULT_FACTS)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Step {step_num} of 3 \u2014 {product_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1rem; }}
.card {{ max-width: 520px; width: 100%; background: white; border-radius: 16px; box-shadow: 0 4px 32px rgba(0,0,0,0.09); padding: 2.5rem; text-align: center; }}
.step-badge {{ display: inline-block; background: #f0fdf4; color: #166534; font-size: 0.78rem; font-family: sans-serif; letter-spacing: .06em; text-transform: uppercase; padding: 0.3rem 0.9rem; border-radius: 20px; margin-bottom: 1.2rem; border: 1px solid #bbf7d0; }}
.icon {{ font-size: 3rem; margin-bottom: 1rem; }}
h1 {{ font-size: 1.45rem; font-weight: 400; color: #1e3a5f; margin-bottom: 0.4rem; }}
.subline {{ font-size: 0.92rem; color: #64748b; margin-bottom: 1.8rem; font-style: italic; }}
.progress-track {{ display: flex; gap: 6px; justify-content: center; margin-bottom: 2rem; }}
.pip {{ height: 5px; width: 48px; border-radius: 3px; background: #e2e8f0; }}
.pip.active {{ background: #1e3a5f; }}
.pip.done {{ background: #16a34a; }}
.body-area {{ margin-bottom: 1.5rem; }}
.status-line {{ display: flex; align-items: center; gap: 0.6rem; padding: 0.65rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; font-family: sans-serif; }}
.status-line:last-child {{ border: none; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; background: #e2e8f0; }}
.dot.running {{ background: #3b82f6; animation: pulse 1.2s infinite; }}
.dot.done {{ background: #16a34a; }}
.dot.error {{ background: #dc2626; }}
.fact-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.9rem 1rem; font-size: 0.85rem; color: #475569; line-height: 1.5; min-height: 54px; text-align: left; }}
.fact-label {{ font-weight: 600; color: #1e3a5f; font-family: sans-serif; font-size: 0.78rem; letter-spacing: .04em; text-transform: uppercase; display: block; margin-bottom: 0.3rem; }}
.error-box {{ margin-top: 1rem; padding: 0.85rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; font-size: 0.85rem; color: #dc2626; font-family: sans-serif; display: none; text-align: left; }}
.retry-btn {{ margin-top: 0.75rem; background: #1e3a5f; color: white; border: none; padding: 0.55rem 1.4rem; border-radius: 8px; font-size: 0.88rem; cursor: pointer; font-family: sans-serif; }}
.retry-btn:hover {{ background: #2d5a87; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }} }}
@keyframes fadeup {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
.fact-text {{ animation: fadeup 0.4s ease-out; }}
</style></head><body>
<div class="card">
    <div class="step-badge">Step {step_num} of 3</div>
    <div class="icon">{icon}</div>
    <h1>{headline}</h1>
    <div class="subline">{subline}</div>
    <div class="progress-track">
        <div class="pip {'done' if step_num > 1 else 'active'}" id="pip1"></div>
        <div class="pip {'done' if step_num > 2 else ('active' if step_num == 2 else '')}" id="pip2"></div>
        <div class="pip {'active' if step_num == 3 else ''}" id="pip3"></div>
    </div>
    <div class="body-area" id="body-area">
        {body_html}
    </div>
    <div class="fact-box">
        <span class="fact-label">Did you know?</span>
        <span class="fact-text" id="fact-text">Loading...</span>
    </div>
    <div class="error-box" id="error-box">
        <strong>Something went wrong:</strong><br>
        <span id="error-text"></span><br>
        <button class="retry-btn" onclick="window.location.reload()">Try Again</button>
    </div>
</div>
<script>
const FACTS = {facts_js};
let fi = 0;
function rotateFact() {{
    const el = document.getElementById('fact-text');
    el.style.opacity = '0';
    setTimeout(() => {{ el.textContent = FACTS[fi]; el.className = 'fact-text'; fi = (fi+1)%FACTS.length; }}, 180);
}}
rotateFact();
setInterval(rotateFact, 6000);

function dot(id, state) {{
    const el = document.getElementById('dot-' + id);
    if (el) el.className = 'dot ' + state;
}}
function showError(msg) {{
    document.getElementById('error-text').textContent = msg;
    document.getElementById('error-box').style.display = 'block';
}}
{script}
</script>
<script src="/js/unified-footer-loader.js"></script>
</body></html>"""


def _render_vault_step1(config: OnboardingConfig) -> str:
    """Step 1 — Building your vault (folder creation + seed files)."""
    body_html = """
        <div class="status-line"><div class="dot" id="dot-folders"></div><span>Building your vault folder structure</span></div>
        <div class="status-line"><div class="dot" id="dot-seed"></div><span>Planting your document library</span></div>
        <div class="status-line"><div class="dot" id="dot-timeline"></div><span>Preparing your timeline ledger</span></div>
    """
    script = f"""
async function run() {{
    try {{
        dot('folders', 'running');
        const r = await fetch('{config.route_prefix}/api/vault/init', {{method:'POST'}});
        const data = await r.json();
        if (!r.ok || !data.success) {{
            dot('folders', 'error');
            showError(data.error || data.errors?.[0] || 'Failed to create vault folders');
            return;
        }}
        dot('folders', 'done');
        dot('seed', 'running');
        await new Promise(res => setTimeout(res, 400));
        dot('seed', 'done');
        dot('timeline', 'running');
        await new Promise(res => setTimeout(res, 300));
        dot('timeline', 'done');
        await new Promise(res => setTimeout(res, 700));
        window.location.href = '{config.route_prefix}/vault-setup/security';
    }} catch(e) {{
        dot('folders', 'error');
        showError(e.message || 'Unexpected error');
    }}
}}
run();
"""
    return _vault_step_shell(
        config.product_name, 1, "🏗️",
        "Semptify is Building Your Vault",
        "Constructing your secure folder structure in the cloud...",
        body_html, script
    )


def _render_vault_step2(config: OnboardingConfig) -> str:
    """Step 2 — Wiring the security system (token backup + device keys)."""
    body_html = """
        <div class="status-line"><div class="dot" id="dot-keys"></div><span>Generating your encryption keys</span></div>
        <div class="status-line"><div class="dot" id="dot-backup"></div><span>Writing secure token backup</span></div>
        <div class="status-line"><div class="dot" id="dot-device"></div><span>Registering this device</span></div>
    """
    script = f"""
async function run() {{
    try {{
        dot('keys', 'running');
        await new Promise(res => setTimeout(res, 500));
        dot('keys', 'done');
        dot('backup', 'running');
        const r = await fetch('{config.route_prefix}/api/vault/security', {{method:'POST'}});
        const data = await r.json();
        if (!r.ok || !data.success) {{
            dot('backup', 'error');
            showError(data.error || 'Failed to write security files');
            return;
        }}
        dot('backup', 'done');
        dot('device', 'running');
        await new Promise(res => setTimeout(res, 400));
        dot('device', 'done');
        await new Promise(res => setTimeout(res, 700));
        window.location.href = '{config.route_prefix}/vault-setup/inspect';
    }} catch(e) {{
        dot('backup', 'error');
        showError(e.message || 'Unexpected error');
    }}
}}
run();
"""
    return _vault_step_shell(
        config.product_name, 2, "🔐",
        "Wiring Your Security System",
        "Installing encrypted keys and securing your access credentials...",
        body_html, script
    )


def _render_vault_step3(config: OnboardingConfig) -> str:
    """Step 3 — Mandatory first document upload. Finalises onboarding."""
    body_html = """
        <div id="upload-area">
            <p style="font-size:0.92rem;color:#475569;font-family:sans-serif;margin-bottom:0.6rem;line-height:1.6;">
                Your vault is ready. Now give it something to protect.
            </p>
            <p style="font-size:0.85rem;color:#64748b;font-family:sans-serif;margin-bottom:1.3rem;line-height:1.5;">
                A lease, a notice, an email, a photo of a repair request &mdash; anything related to your housing situation.
                This document completes your setup and gives Semptify a starting point.
            </p>
            <label id="drop-zone" for="file-input" style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0.5rem;border:2px dashed #cbd5e1;border-radius:10px;padding:2rem 1rem;cursor:pointer;background:#f8fafc;transition:border-color 0.2s,background 0.2s;margin-bottom:1rem;">
                <span style="font-size:2.2rem;">📄</span>
                <span style="font-family:sans-serif;font-size:0.9rem;color:#1e3a5f;font-weight:600;">Click to choose a file or drag &amp; drop</span>
                <span style="font-family:sans-serif;font-size:0.78rem;color:#94a3b8;">PDF, image, Word doc, email &mdash; any format accepted</span>
            </label>
            <input id="file-input" type="file" accept="*/*" style="display:none;">
            <div id="file-chosen" style="display:none;font-family:sans-serif;font-size:0.85rem;color:#166534;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:0.5rem 0.75rem;margin-bottom:0.75rem;"></div>
            <button id="upload-btn" disabled
                style="width:100%;background:#94a3b8;color:white;border:none;padding:0.8rem;border-radius:8px;font-size:0.95rem;font-family:sans-serif;cursor:not-allowed;transition:background 0.2s;">
                Upload &amp; Complete Setup
            </button>
            <p style="font-size:0.75rem;color:#cbd5e1;font-family:sans-serif;margin-top:0.6rem;text-align:center;">Saved directly to your cloud storage &mdash; Semptify never holds your files.</p>
        </div>
        <div id="saving-area" style="display:none;">
            <div class="status-line"><div class="dot" id="dot-check"></div><span>Confirming your vault is live</span></div>
            <div class="status-line"><div class="dot" id="dot-upload"></div><span>Securing your document</span></div>
            <div class="status-line"><div class="dot" id="dot-ready"></div><span>Setup complete &mdash; you&rsquo;re protected</span></div>
        </div>
    """
    script = f"""
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');
const dropZone  = document.getElementById('drop-zone');
const fileChosen = document.getElementById('file-chosen');
let chosenFile = null;

function setFile(f) {{
    chosenFile = f;
    fileChosen.textContent = '\u2713 ' + f.name + '  (' + (f.size / 1024).toFixed(1) + ' KB)';
    fileChosen.style.display = 'block';
    uploadBtn.disabled = false;
    uploadBtn.style.background = '#1e3a5f';
    uploadBtn.style.cursor = 'pointer';
}}

fileInput.addEventListener('change', () => {{ if (fileInput.files[0]) setFile(fileInput.files[0]); }});

dropZone.addEventListener('dragover', e => {{ e.preventDefault(); dropZone.style.borderColor='#1e3a5f'; dropZone.style.background='#f0f6ff'; }});
dropZone.addEventListener('dragleave', () => {{ dropZone.style.borderColor='#cbd5e1'; dropZone.style.background='#f8fafc'; }});
dropZone.addEventListener('drop', e => {{
    e.preventDefault();
    dropZone.style.borderColor='#cbd5e1'; dropZone.style.background='#f8fafc';
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
}});

async function doUpload(file) {{
    document.getElementById('upload-area').style.display = 'none';
    document.getElementById('saving-area').style.display = 'block';
    try {{
        dot('check', 'running');
        const fd = new FormData();
        if (file) fd.append('file', file);
        const r = await fetch('{config.route_prefix}/api/vault/verify', {{method:'POST', body: fd}});
        const data = await r.json();
        if (!r.ok || !data.ok) {{
            dot('check', 'error');
            document.getElementById('saving-area').style.display = 'none';
            document.getElementById('upload-area').style.display = 'block';
            showError(data.error || 'Could not reach your vault \u2014 please try again');
            return;
        }}
        dot('check', 'done');
        dot('upload', 'running');
        await new Promise(res => setTimeout(res, 700));
        dot('upload', 'done');
        dot('ready', 'running');
        await new Promise(res => setTimeout(res, 500));
        dot('ready', 'done');
        await new Promise(res => setTimeout(res, 900));
        window.location.href = '{config.route_prefix}/complete';
    }} catch(e) {{
        dot('check', 'error');
        document.getElementById('saving-area').style.display = 'none';
        document.getElementById('upload-area').style.display = 'block';
        showError(e.message || 'Unexpected error');
    }}
}}

uploadBtn.addEventListener('click', () => {{ if (chosenFile) doUpload(chosenFile); }});
"""
    return _vault_step_shell(
        config.product_name, 3, "📂",
        "Upload Your First Document",
        "One document to finish setup. Your vault needs something to protect.",
        body_html, script
    )


def _render_status_page(config: OnboardingConfig, incomplete_gate: str) -> str:
    """Render a page showing which gate the user needs to complete next."""
    gate_actions = {
        "storage_connected": (
            "Connect Your Storage",
            "You need to connect a cloud storage provider to continue.",
            f"{config.route_prefix}/providers",
        ),
        "vault_initialized": (
            "Set Up Your Vault",
            "Your storage is connected but vault folders haven't been created yet.",
            f"{config.route_prefix}/vault-setup",
        ),
        "document_uploaded": (
            "Upload Your First Document",
            "Your vault is ready but needs your first document to complete setup.",
            f"{config.route_prefix}/vault-setup/inspect",
        ),
    }
    title, message, action_url = gate_actions.get(
        incomplete_gate,
        ("Continue Setup", f"Complete the '{incomplete_gate}' step to continue.", f"{config.route_prefix}/"),
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {config.product_name}</title>
<style>
body {{ font-family: Georgia, serif; background: #fdfcfa; color: #1e293b; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
.card {{ max-width: 450px; background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }}
h1 {{ font-size: 1.4rem; color: #1e3a5f; margin-bottom: 1rem; }}
p {{ margin-bottom: 1.5rem; color: #475569; }}
a {{ display: inline-block; background: #1e3a5f; color: white; padding: 0.75rem 2rem; border-radius: 8px; text-decoration: none; }}
a:hover {{ background: #2d5a87; }}
</style></head><body>
<div class="card">
    <h1>{title}</h1>
    <p>{message}</p>
    <a href="{action_url}">Continue</a>
</div>
</body></html>"""
