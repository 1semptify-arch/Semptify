"""
Semptify Tools API Router
=========================
Connects frontend tools (calculators, generators, checklists) to the vault.

Endpoints:
- POST /api/tools/save-letter    — save a generated letter to vault
- POST /api/tools/save-checklist — save checklist state to vault  
- POST /api/tools/save-calculation — save a calculation result to vault
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.oauth_token_manager import get_valid_token_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["Tools"])


# =============================================================================
# Request / Response Models
# =============================================================================

class SaveLetterRequest(BaseModel):
    letter_text: str = Field(..., description="Full text of the generated letter")
    letter_type: str = Field(..., description="repair | notice | deposit_demand")
    title: Optional[str] = Field(None, description="Custom title/filename")
    metadata: Optional[dict] = Field(default_factory=dict, description="Extra metadata")


class SaveChecklistRequest(BaseModel):
    checklist_data: dict = Field(..., description="Checklist items and checked state")
    checklist_type: str = Field(..., description="movein | moveout | evidence")
    title: Optional[str] = Field(None, description="Custom title/filename")


class SaveCalculationRequest(BaseModel):
    calc_type: str = Field(..., description="proration | deadline | late_fee | deposit_interest")
    inputs: dict = Field(default_factory=dict, description="Calculation input values")
    result: str = Field(..., description="Human-readable result string")
    notes: Optional[str] = Field(None, description="Optional notes")


class ToolsSaveResponse(BaseModel):
    success: bool
    vault_id: Optional[str] = None
    filename: Optional[str] = None
    message: str


# =============================================================================
# Helpers
# =============================================================================

def _get_access_token(user: StorageUser) -> Optional[str]:
    """Resolve cloud storage access token for the authenticated user."""
    # Try user object first
    token = getattr(user, "access_token", None)
    if token:
        return token
    # Fall back to token manager
    try:
        return get_valid_token_for_user(user.user_id)
    except Exception:
        return None


async def _save_text_to_vault(
    user: StorageUser,
    filename: str,
    content: str,
    document_type: str,
    description: str,
    metadata: Optional[dict] = None,
) -> ToolsSaveResponse:
    """Save text content to the user's vault via VaultUploadService."""
    try:
        from app.services.vault_upload_service import get_vault_service
        vault_service = get_vault_service()
    except ImportError:
        return ToolsSaveResponse(
            success=False,
            message="Vault upload service is not available. Please try again later.",
        )

    access_token = _get_access_token(user)
    provider = "local"
    if user.user_id.startswith("G"):
        provider = "google_drive"
    elif user.user_id.startswith("D"):
        provider = "dropbox"
    elif user.user_id.startswith("O"):
        provider = "onedrive"

    try:
        doc = await vault_service.upload(
            user_id=user.user_id,
            filename=filename,
            content=content.encode("utf-8"),
            mime_type="text/plain",
            document_type=document_type,
            description=description,
            tags=["generated", "tools"],
            source_module="tools_api",
            access_token=access_token,
            storage_provider=provider,
        )
        return ToolsSaveResponse(
            success=True,
            vault_id=doc.vault_id,
            filename=filename,
            message=f"Saved to vault as {filename}",
        )
    except Exception as e:
        logger.error("Failed to save text to vault: %s", e)
        return ToolsSaveResponse(
            success=False,
            message=f"Vault save failed: {str(e)}",
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/save-letter", response_model=ToolsSaveResponse)
async def save_letter(
    request: SaveLetterRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Save a generated letter (repair request, notice response, deposit demand)
    to the authenticated user's vault as a plain-text document.
    """
    type_map = {
        "repair": "repair_request_letter",
        "notice": "notice_response_letter",
        "deposit_demand": "deposit_demand_letter",
    }
    doc_type = type_map.get(request.letter_type, "letter")
    safe_type = request.letter_type.replace("_", "-")
    filename = request.title or f"{safe_type}-letter-{datetime.now(timezone.utc).strftime('%Y%m%d')}.txt"

    meta = request.metadata or {}
    meta["letter_type"] = request.letter_type
    meta["generated_at"] = datetime.now(timezone.utc).isoformat()

    result = await _save_text_to_vault(
        user=user,
        filename=filename,
        content=request.letter_text,
        document_type=doc_type,
        description=f"Generated {request.letter_type} letter via Tools",
        metadata=meta,
    )
    return result


@router.post("/save-checklist", response_model=ToolsSaveResponse)
async def save_checklist(
    request: SaveChecklistRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Save checklist state (move-in, move-out, evidence preservation)
    to the authenticated user's vault as a JSON document.
    """
    type_map = {
        "movein": "move_in_checklist",
        "moveout": "move_out_checklist",
        "evidence": "evidence_preservation_checklist",
    }
    doc_type = type_map.get(request.checklist_type, "checklist")
    safe_type = request.checklist_type.replace("_", "-")
    filename = request.title or f"{safe_type}-checklist-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    payload = {
        "checklist_type": request.checklist_type,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "items": request.checklist_data,
    }

    result = await _save_text_to_vault(
        user=user,
        filename=filename,
        content=json.dumps(payload, indent=2),
        document_type=doc_type,
        description=f"Saved {request.checklist_type} checklist via Tools",
        metadata={"checklist_type": request.checklist_type},
    )
    return result


@router.post("/save-calculation", response_model=ToolsSaveResponse)
async def save_calculation(
    request: SaveCalculationRequest,
    user: StorageUser = Depends(require_user),
):
    """
    Save a calculator result (proration, deadline, late fee, deposit interest)
    to the authenticated user's vault as a JSON document.
    """
    type_map = {
        "proration": "rent_proration",
        "deadline": "deadline_calculation",
        "late_fee": "late_fee_calculation",
        "deposit_interest": "deposit_interest_calculation",
    }
    doc_type = type_map.get(request.calc_type, "calculation")
    filename = f"{request.calc_type}-calc-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    payload = {
        "calc_type": request.calc_type,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "inputs": request.inputs,
        "result": request.result,
        "notes": request.notes,
    }

    result = await _save_text_to_vault(
        user=user,
        filename=filename,
        content=json.dumps(payload, indent=2),
        document_type=doc_type,
        description=f"Saved {request.calc_type} calculation via Tools",
        metadata={"calc_type": request.calc_type},
    )
    return result
