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
async def debug_vault_installer():
    """Simple debug endpoint to verify router is accessible."""
    return {"status": "vault_installer_router_ok", "timestamp": __import__('datetime').datetime.now().isoformat()}


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
    logger.info(f"=== VAULT INSTALL START for user {current_user.get('user_id', 'unknown')[:6]}*** ===")
    
    try:
        # Get user's storage tokens from database
        logger.info("Importing get_valid_session...")
        from app.modules.storage.router import get_valid_session
        
        user_id = current_user["user_id"]
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
        
        # Install vault folders only (fast, avoids Cloudflare timeout)
        logger.info("Calling install_vault_folders_only...")
        result = await install_vault_folders_only(
            db=db,
            user_id=user_id,
            provider_name=provider,
            access_token=access_token,
        )
        logger.info(f"install_vault_folders_only result: success={result.get('success')}, folders={len(result.get('folders_created', []))}")
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Vault installed and activated successfully",
                    "activation_code": result["activation_code"],
                    "folders_created": result["folders_created"],
                    "files_created": result["files_created"],
                    "next_step": "Your vault is ready. Start uploading documents.",
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
            detail={"error": error_detail, "type": type(e).__name__, "traceback": traceback.format_exc()}
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
):
    """
    Quick install for testing/debug - bypass auth checks.
    
    This endpoint allows direct vault installation with provided tokens.
    Useful for testing or admin operations.
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
