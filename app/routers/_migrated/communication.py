"""
Communication Router
====================

API endpoints for the Semptify communication system:
- Conversations between tenant and all roles
- Messaging with document references
- In-browser document filling and signing
"""

from typing import Optional, List
from app.core.id_gen import make_id
from fastapi import APIRouter, Depends, HTTPException, Form, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.core.security import require_user, StorageUser
from app.core.user_id import get_role_from_user_id
from app.models.communication_models import (
    ConversationListResponse, MessageThreadResponse,
    SendMessageRequest, SendMessageResponse,
    CreateConversationRequest, CreateConversationResponse,
    MarkReadRequest, ParticipantRole, DocumentFillResponse,
    MessageAttachment
)
from app.models.document_delivery_models import SignDocumentRequest
from app.services.communication_service import get_communication_service

router = APIRouter(prefix="/api/communications", tags=["Communications"])


async def get_storage_client(user: StorageUser, db: AsyncSession, settings: Settings):
    """Get cloud storage client."""
    from app.routers.cloud_sync import get_storage_client as get_cloud_storage
    return await get_cloud_storage(user, db, settings)


def _get_user_role(user: StorageUser) -> str:
    """Extract role from user ID."""
    return get_role_from_user_id(user.user_id) or "user"


def _get_participant_role(role_str: str) -> ParticipantRole:
    """Convert string role to ParticipantRole enum."""
    role_map = {
        "user": ParticipantRole.TENANT,
        "tenant": ParticipantRole.TENANT,
        "advocate": ParticipantRole.ADVOCATE,
        "manager": ParticipantRole.MANAGER,
        "legal": ParticipantRole.LEGAL,
        "admin": ParticipantRole.ADMIN,
    }
    return role_map.get(role_str.lower(), ParticipantRole.TENANT)


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "communication",
        "version": "1.0",
    }


# =============================================================================
# Conversations
# =============================================================================

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ConversationListResponse:
    """
    Get all conversations for the current user.
    
    Returns conversations with unread counts and last message previews.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    return await service.get_conversations()


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CreateConversationResponse:
    """
    Create a new conversation with participants.
    
    - `recipient_ids`: List of user IDs to include (besides yourself)
    - `title`: Optional conversation title
    - `topic`: Optional topic/subject
    - `case_id`: Optional associated case ID
    - `initial_message`: Optional first message to send
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    role = _get_participant_role(_get_user_role(user))
    
    return await service.create_conversation(request, role, user.user_id)


@router.get("/conversations/{conversation_id}", response_model=MessageThreadResponse)
async def get_conversation(
    conversation_id: str,
    before_message_id: Optional[str] = None,
    limit: int = 50,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageThreadResponse:
    """
    Get messages in a conversation with pagination.
    
    - `before_message_id`: Get messages before this ID (for pagination)
    - `limit`: Number of messages to return (default 50, max 100)
    """
    if limit > 100:
        limit = 100
    
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    return await service.get_conversation_messages(
        conversation_id,
        before_message_id=before_message_id,
        limit=limit
    )


# =============================================================================
# Messages
# =============================================================================

@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: str,
    content: str = Form(..., description="Message content"),
    message_type: str = Form("text", description="Message type: text, document, etc."),
    referenced_document_id: Optional[str] = Form(None, description="Referenced document ID"),
    referenced_delivery_id: Optional[str] = Form(None, description="Referenced delivery ID"),
    reply_to_message_id: Optional[str] = Form(None, description="Reply to message ID"),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SendMessageResponse:
    """
    Send a message in a conversation.
    
    Supports text messages, document references, and replies.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    role = _get_participant_role(_get_user_role(user))
    
    request = SendMessageRequest(
        conversation_id=conversation_id,
        content=content,
        message_type=message_type,
        referenced_document_id=referenced_document_id,
        referenced_delivery_id=referenced_delivery_id,
        reply_to_message_id=reply_to_message_id
    )
    
    return await service.send_message(request, role, user.user_id)


@router.post("/conversations/{conversation_id}/messages/{message_id}/read")
async def mark_message_read(
    conversation_id: str,
    message_id: str,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Mark a specific message as read."""
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    success = await service.mark_messages_read(
        MarkReadRequest(message_ids=[message_id])
    )
    
    return {"success": success, "message_id": message_id}


@router.post("/conversations/{conversation_id}/read-all")
async def mark_conversation_read(
    conversation_id: str,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Mark all messages in a conversation as read."""
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    success = await service.mark_messages_read(
        MarkReadRequest(conversation_id=conversation_id, mark_all=True)
    )
    
    return {"success": success, "conversation_id": conversation_id}


# =============================================================================
# Document Collaboration
# =============================================================================

@router.post("/documents/{delivery_id}/reject")
async def reject_document(
    delivery_id: str,
    reason: str = Form(..., description="Reason for rejecting the document"),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Reject a document that requires signature.
    
    This:
    1. Records the rejection reason in the delivery system
    2. Creates a rejection record in the user's vault (watermarked as REJECTED)
    3. Notifies the sender via conversation
    
    The rejection is permanent - the document cannot be re-signed.
    """
    from app.services.document_delivery_service import get_document_delivery_service
    from app.models.document_delivery_models import RejectDocumentRequest
    
    storage = await get_storage_client(user, db, settings)
    
    # First, reject via document delivery service
    delivery_service = await get_document_delivery_service(storage, user.user_id)
    reject_request = RejectDocumentRequest(reason=reason)
    
    delivery_result = await delivery_service.reject_document(
        delivery_id=delivery_id,
        request=reject_request
    )
    
    if not delivery_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=delivery_result.message or "Failed to reject document"
        )
    
    # Also create a communication record of the rejection
    comm_service = await get_communication_service(storage, user.user_id)
    
    # Save rejection record as communication overlay
    await comm_service._save_rejection_record(
        delivery_id=delivery_id,
        reason=reason,
        rejected_at=delivery_result.rejected_at
    )
    
    return {
        "success": True,
        "delivery_id": delivery_id,
        "rejected_at": delivery_result.rejected_at,
        "reason": reason,
        "message": "Document rejected and recorded in vault"
    }


@router.post("/documents/{delivery_id}/fill-and-sign", response_model=DocumentFillResponse)
async def fill_and_sign_document(
    delivery_id: str,
    signature_type: str = Form("typed", description="Signature type: typed, drawn, digital"),
    signature_value: str = Form(..., description="The signature value"),
    agree_to_terms: bool = Form(True, description="Must be True to sign"),
    field_1: Optional[str] = Form(None, description="Form field 1"),
    field_2: Optional[str] = Form(None, description="Form field 2"),
    field_3: Optional[str] = Form(None, description="Form field 3"),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DocumentFillResponse:
    """
    Fill out a document form and sign it in the browser.
    
    This endpoint:
    1. Saves filled form fields
    2. Applies the signature
    3. Creates a completed document in the user's vault
    4. Notifies the sender via conversation
    
    The completed document becomes the tenant's property in their vault.
    """
    storage = await get_storage_client(user, db, settings)
    service = await get_communication_service(storage, user.user_id)
    
    role = _get_participant_role(_get_user_role(user))
    
    # Build field values from form fields
    field_values = {}
    if field_1:
        field_values["field_1"] = field_1
    if field_2:
        field_values["field_2"] = field_2
    if field_3:
        field_values["field_3"] = field_3
    
    # Build signature request
    signature_request = SignDocumentRequest(
        signature_type=signature_type,
        signature_value=signature_value,
        agree_to_terms=agree_to_terms
    )
    
    return await service.fill_and_sign_document(
        delivery_id=delivery_id,
        field_values=field_values,
        signature_request=signature_request,
        sender_role=role,
        sender_name=user.user_id  # Simplified, should be name
    )


@router.post("/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(..., description="File to attach"),
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Upload a file attachment for a conversation.
    
    The file is stored in the user's cloud storage and referenced in messages.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Generate unique filename
        safe_filename = f"{make_id('att')}_{file.filename}"
        
        # Upload to storage
        storage = await get_storage_client(user, db, settings)
        from app.services.vault_upload_service import VaultUploadService
        upload_service = VaultUploadService(storage)
        
        # Create document in vault
        result = await upload_service.upload(
            user_id=user.user_id,
            filename=safe_filename,
            content=content,
            mime_type=file.content_type or "application/octet-stream",
            source_module="communication",
            document_type="attachment",
            access_token=access_token
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload attachment"
            )
        
        attachment = MessageAttachment(
            filename=file.filename,
            document_id=result.vault_id,
            file_size=len(content),
            mime_type=file.content_type
        )
        
        return {
            "success": True,
            "attachment_id": attachment.attachment_id,
            "document_id": result.vault_id,
            "filename": file.filename,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Upload attachment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload attachment: {str(e)}"
        )


# =============================================================================
# Integration with Document Delivery
# =============================================================================

@router.get("/deliveries/{delivery_id}/conversation")
async def get_delivery_conversation(
    delivery_id: str,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Get or create the conversation thread for a document delivery.
    
    This links document deliveries with the communication system,
    allowing parties to discuss the document before signing.
    """
    storage = await get_storage_client(user, db, settings)
    comm_service = await get_communication_service(storage, user.user_id)
    
    # Get delivery details to find participants
    from app.services.document_delivery_service import get_delivery_service
    delivery_service = await get_delivery_service(storage, user.user_id)
    
    delivery_detail = await delivery_service.get_delivery_detail(delivery_id)
    if not delivery_detail:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    delivery = delivery_detail.delivery
    
    # Check if user is part of this delivery
    if delivery.recipient_id != user.user_id and delivery.sender_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this delivery"
        )
    
    # Look for existing conversation about this delivery
    conversations = await comm_service.get_conversations()
    
    for conv in conversations.conversations:
        # Check if conversation is about this delivery
        # This would need a reference field in conversation metadata
        pass  # Implementation depends on metadata structure
    
    # If no conversation exists, create one
    participant_ids = [delivery.sender_id, delivery.recipient_id]
    participant_ids = list(set(participant_ids))  # Remove duplicates
    if user.user_id in participant_ids:
        participant_ids.remove(user.user_id)
    
    role = _get_participant_role(_get_user_role(user))
    
    conv_response = await comm_service.create_conversation(
        CreateConversationRequest(
            title=f"Document: {delivery.document_filename}",
            topic=f"Discussion about document delivery {delivery_id}",
            recipient_ids=participant_ids
        ),
        role,
        user.user_id
    )
    
    if not conv_response.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )
    
    return {
        "success": True,
        "conversation_id": conv_response.conversation_id,
        "delivery_id": delivery_id,
        "participants": participant_ids + [user.user_id]
    }


# =============================================================================
# WebSocket / Real-time (Placeholder)
# =============================================================================

@router.get("/conversations/{conversation_id}/typing")
async def send_typing_indicator(
    conversation_id: str,
    is_typing: bool = True,
    access_token: str = Form(..., description="Storage provider access token"),
    user: StorageUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Send typing indicator to conversation participants.
    
    This is a placeholder for real-time typing indicators.
    Full implementation would use WebSockets.
    """
    # In production, this would broadcast via WebSocket
    return {
        "success": True,
        "conversation_id": conversation_id,
        "user_id": user.user_id,
        "is_typing": is_typing
    }
