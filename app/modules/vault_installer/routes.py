"""
Vault Installer Routes

Simple endpoints to install and activate the Semptify vault.
No complex onboarding - just install and go.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.user_context import get_user_context
from .installer import install_vault_for_user

router = APIRouter(prefix="/api/vault-installer", tags=["vault-installer"])


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
    try:
        # Get user's storage tokens from context
        user_context = await get_user_context(db, current_user["user_id"])
        
        if not user_context or not user_context.get("provider"):
            raise HTTPException(
                status_code=400,
                detail="No storage provider connected. Please connect storage first."
            )
        
        provider = user_context["provider"]
        access_token = user_context["access_token"]
        user_id = current_user["user_id"]
        
        # Install the vault
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
        raise HTTPException(
            status_code=500,
            detail=f"Installation error: {str(e)}"
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
        
        vault_initialized = await check_gate(db, current_user["user_id"], "vault_initialized")
        
        user_context = await get_user_context(db, current_user["user_id"])
        
        return {
            "vault_installed": vault_initialized,
            "storage_connected": bool(user_context and user_context.get("provider")),
            "provider": user_context.get("provider") if user_context else None,
            "next_action": (
                "install_vault" if not vault_initialized 
                else "upload_documents" if vault_initialized
                else "connect_storage"
            ),
        }
        
    except Exception as e:
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
