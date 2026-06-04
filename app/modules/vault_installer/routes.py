"""
Vault Installer Routes

Simple endpoints to install and activate the Semptify vault.
No complex onboarding - just install and go.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from .installer import install_vault_for_user, install_vault_folders_only

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault-installer", tags=["vault-installer"])


@router.get("/debug")
async def debug_vault_installer(
    current_user: dict = Depends(get_current_user),
):
    """Debug endpoint to verify router is accessible. Requires authentication."""
    from app.core.utc import utc_now
    return {
        "status": "vault_installer_router_ok",
        "router_prefix": router.prefix,
        "routes": [r.path for r in router.routes],
        "timestamp": utc_now().isoformat()
    }


@router.post("/install")
async def install_vault(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Install Semptify vault using existing OAuth storage.
    
    This endpoint:
    1. Uses your existing OAuth tokens (from storage connection)
    2. Creates the complete vault folder structure
    3. Adds system files and initial data
    4. Marks vault as activated
    
    No complex onboarding required - just install and go.
    """
    logger.info(f"=== VAULT INSTALL START ===")
    logger.info(f"Current user: {current_user}")
    
    try:
        # Get user's storage tokens from database
        logger.info("Importing get_valid_session...")
        from app.modules.storage.router import get_valid_session
        
        if current_user is None:
            logger.error("current_user is None - authentication required")
            raise HTTPException(status_code=401, detail="Authentication required - please complete OAuth first")
        
        # UserContext is a dataclass - access user_id as attribute
        user_id = getattr(current_user, 'user_id', None)
        if not user_id:
            logger.error("No user_id in current_user!")
            raise HTTPException(status_code=401, detail="Authentication required")
            
        logger.info(f"Getting session for user {user_id[:6]}***...")
        session = await get_valid_session(db, user_id, auto_refresh=True)
        logger.info(f"Session result: {'found' if session else 'NOT FOUND'}")
        
        if not session:
            raise HTTPException(
                status_code=400,
                detail="No storage provider connected. Please connect storage first."
            )
        
        provider = session.get("provider")
        access_token = session.get("access_token")
        logger.info(f"Provider: {provider}, Token exists: {'yes' if access_token else 'NO'}")
        
        # Install the full vault structure and mark it active.
        logger.info("Calling install_vault_for_user...")
        result = await install_vault_for_user(
            db=db,
            user_id=user_id,
            provider_name=provider,
            access_token=access_token,
        )
        logger.info(f"install_vault_for_user result: success={result.get('success')}, folders={len(result.get('folders_created', []))}")
        
        if result["success"]:
            # Mark vault_initialized — folders are confirmed created.
            from app.modules.onboarding.gates import mark_gate, check_gate
            await mark_gate(db, user_id, "vault_initialized")

            # Mark document_uploaded if the user already has documents in vault
            # (reconnect/reinstall scenario — they completed onboarding before).
            already_has_docs = False
            try:
                from app.services.vault_upload_service import VaultUploadService
                svc = VaultUploadService()
                docs = await svc.get_user_documents(user_id)
                if docs:
                    await mark_gate(db, user_id, "document_uploaded")
                    already_has_docs = True
            except Exception as gate_exc:
                logger.warning("document_uploaded gate check failed for %s: %s", user_id[:6] + "***", gate_exc)

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Vault installed and activated successfully",
                    "activation_code": result["activation_code"],
                    "folders_created": result["folders_created"],
                    "files_created": result["files_created"],
                    "next_step": "Your vault is ready. Start uploading documents." if not already_has_docs else "Vault reinstalled. Your documents are accessible.",
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Vault installation failed",
                    "details": result["errors"],
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Installation error: {str(e)}"
        logger.error(f"VAULT INSTALLER ERROR: {error_detail}")
        logger.error(f"TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Vault installation failed. Check server logs for details.", "type": type(e).__name__}
        )


@router.get("/status")
async def get_vault_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Check if vault is installed and ready.
    """
    try:
        from app.modules.onboarding.gates import check_gate
        from app.modules.storage.router import get_valid_session
        
        user_id = current_user["user_id"]
        vault_initialized = await check_gate(db, user_id, "vault_initialized")
        
        # Check storage connection via session
        session = await get_valid_session(db, user_id, auto_refresh=False)
        
        return {
            "vault_installed": vault_initialized,
            "storage_connected": bool(session and session.get("provider")),
            "provider": session.get("provider") if session else None,
            "next_action": (
                "connect_storage" if not session
                else "install_vault" if not vault_initialized
                else "upload_documents"
            ),
        }
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Status check error: {str(e)}"
        )


@router.post("/quick-install")
async def quick_install(
    provider: str,
    access_token: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Quick install for admin operations. Requires authentication.
    """
    try:
        result = await install_vault_for_user(
            db=db,
            user_id=user_id,
            provider_name=provider,
            access_token=access_token,
        )
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Quick install successful",
                    "activation_code": result["activation_code"],
                    "summary": {
                        "folders": len(result["folders_created"]),
                        "files": len(result["files_created"]),
                    }
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Quick install failed",
                    "details": result["errors"],
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quick install error: {str(e)}"
        )


def create_router() -> APIRouter:
    """Create and return the vault installer router."""
    return router
