"""
Communication Service
=====================

Full-featured communication system for Semptify supporting:
- Direct messaging between tenant and all roles
- Document collaboration threads
- In-browser document filling and signing
- Vault integration for completed documents
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.models.communication_models import (
    Conversation, ConversationSummary, ConversationListResponse,
    Message, MessageThreadResponse, SendMessageRequest, SendMessageResponse,
    CreateConversationRequest, CreateConversationResponse,
    Participant, ParticipantRole, MessageStatus, ConversationStatus,
    MessageType, MarkReadRequest, DocumentFillRequest, DocumentFillResponse,
    DocumentSignatureRequest
)
from app.models.document_delivery_models import (
    DeliveryStatus, SignDocumentRequest, SignDocumentResponse
)
from app.services.unified_overlay_manager import get_unified_overlay_manager
from app.core.overlay_types import OverlayType
from app.models.unified_overlay_models import CreateOverlayRequest

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Service for managing communications between Semptify users.
    
    All data is stored as overlays in user's cloud storage (stateless).
    """
    
    def __init__(self, storage, user_id: str):
        self.storage = storage
        self.user_id = user_id
        self._manager = None
    
    async def _get_manager(self):
        """Get or create unified overlay manager."""
        if self._manager is None:
            self._manager = await get_unified_overlay_manager(self.storage, self.user_id)
        return self._manager
    
    # ==========================================================================
    # Conversation Management
    # ==========================================================================
    
    async def create_conversation(
        self, 
        request: CreateConversationRequest,
        creator_role: ParticipantRole,
        creator_name: str
    ) -> CreateConversationResponse:
        """Create a new conversation with participants."""
        try:
            manager = await self._get_manager()
            
            # Build participant list
            participants = [
                Participant(
                    user_id=self.user_id,
                    role=creator_role,
                    name=creator_name
                )
            ]
            
            # Add other participants
            for recipient_id in request.recipient_ids:
                # In production, look up user profile to get role and name
                participants.append(Participant(
                    user_id=recipient_id,
                    role=ParticipantRole.TENANT,  # Default, should look up
                    name=recipient_id  # Placeholder
                ))
            
            conversation = Conversation(
                title=request.title,
                topic=request.topic,
                case_id=request.case_id,
                participants=participants,
                created_by=self.user_id
            )
            
            # Store conversation as overlay
            conv_overlay = await manager.create_overlay(
                CreateOverlayRequest(
                    overlay_type=OverlayType.COMMUNICATION,
                    document_id=conversation.conversation_id,
                    vault_path=f"communications/{conversation.conversation_id}",
                    payload=conversation.dict(),
                    metadata={
                        "type": "conversation",
                        "participant_ids": [p.user_id for p in participants],
                        "case_id": request.case_id
                    }
                )
            )
            
            if not conv_overlay.success:
                return CreateConversationResponse(
                    success=False,
                    error="Failed to create conversation overlay"
                )
            
            # Send initial message if provided
            if request.initial_message:
                await self.send_message(
                    SendMessageRequest(
                        conversation_id=conversation.conversation_id,
                        content=request.initial_message
                    ),
                    sender_role=creator_role,
                    sender_name=creator_name
                )
            
            return CreateConversationResponse(
                success=True,
                conversation_id=conversation.conversation_id,
                created_at=conversation.created_at
            )
            
        except Exception as e:
            logger.error(f"Create conversation failed: {e}", exc_info=True)
            return CreateConversationResponse(success=False, error=str(e))
    
    async def get_conversations(self) -> ConversationListResponse:
        """Get all conversations for the current user."""
        try:
            manager = await self._get_manager()
            
            # Get all communication overlays
            overlays = await manager.get_overlays(overlay_type=OverlayType.COMMUNICATION)
            
            conversations = []
            unread_total = 0
            
            for overlay in overlays.overlays:
                if overlay.metadata.get("type") == "conversation":
                    conv_data = overlay.payload
                    conversation = Conversation(**conv_data)
                    
                    # Check if user is participant
                    participant_ids = overlay.metadata.get("participant_ids", [])
                    if self.user_id not in participant_ids:
                        continue
                    
                    # Get unread count for this user
                    participant = next(
                        (p for p in conversation.participants if p.user_id == self.user_id),
                        None
                    )
                    user_unread = 0
                    if participant and participant.last_read_at:
                        # Count messages after last_read_at
                        user_unread = sum(
                            1 for m in await self._get_messages_for_conversation(
                                conversation.conversation_id
                            )
                            if m.sent_at and m.sent_at > participant.last_read_at and m.sender_id != self.user_id
                        )
                    
                    summary = ConversationSummary(
                        conversation_id=conversation.conversation_id,
                        title=conversation.title,
                        topic=conversation.topic,
                        last_message_preview=await self._get_last_message_preview(
                            conversation.conversation_id
                        ),
                        last_message_at=conversation.last_message_at,
                        unread_count=user_unread,
                        participant_count=len(conversation.participants),
                        is_active=conversation.status == ConversationStatus.ACTIVE
                    )
                    
                    conversations.append(summary)
                    unread_total += user_unread
            
            # Sort by last_message_at desc
            conversations.sort(key=lambda x: x.last_message_at or datetime.min, reverse=True)
            
            return ConversationListResponse(
                conversations=conversations,
                total_count=len(conversations),
                unread_total=unread_total
            )
            
        except Exception as e:
            logger.error(f"Get conversations failed: {e}", exc_info=True)
            return ConversationListResponse(conversations=[], total_count=0, unread_total=0)
    
    async def get_conversation_messages(
        self, 
        conversation_id: str,
        before_message_id: Optional[str] = None,
        limit: int = 50
    ) -> MessageThreadResponse:
        """Get messages in a conversation with pagination."""
        try:
            manager = await self._get_manager()
            
            # Get conversation
            conv_overlay = await manager.get_overlay(conversation_id)
            if not conv_overlay:
                return MessageThreadResponse(
                    conversation=Conversation(
                        conversation_id=conversation_id,
                        participants=[],
                        created_by=""
                    ),
                    messages=[]
                )
            
            conversation = Conversation(**conv_overlay.payload)
            
            # Update last read for current user
            await self._update_last_read(conversation_id)
            
            # Get messages
            messages = await self._get_messages_for_conversation(conversation_id)
            
            # Sort by created_at desc
            messages.sort(key=lambda x: x.created_at, reverse=True)
            
            # Paginate
            if before_message_id:
                try:
                    idx = next(i for i, m in enumerate(messages) if m.message_id == before_message_id)
                    messages = messages[idx+1:idx+1+limit]
                except StopIteration:
                    messages = messages[:limit]
            else:
                messages = messages[:limit]
            
            # Reverse back to chronological order
            messages.reverse()
            
            return MessageThreadResponse(
                conversation=conversation,
                messages=messages,
                has_more=len(messages) == limit,
                next_cursor=messages[-1].message_id if messages else None
            )
            
        except Exception as e:
            logger.error(f"Get conversation messages failed: {e}", exc_info=True)
            return MessageThreadResponse(
                conversation=Conversation(
                    conversation_id=conversation_id,
                    participants=[],
                    created_by=""
                ),
                messages=[]
            )
    
    async def send_message(
        self,
        request: SendMessageRequest,
        sender_role: ParticipantRole,
        sender_name: str
    ) -> SendMessageResponse:
        """Send a message in a conversation."""
        try:
            manager = await self._get_manager()
            
            conversation_id = request.conversation_id
            
            # Create new conversation if needed
            if not conversation_id:
                conv_response = await self.create_conversation(
                    CreateConversationRequest(
                        recipient_ids=request.recipient_ids,
                        initial_message=None
                    ),
                    sender_role,
                    sender_name
                )
                if not conv_response.success:
                    return SendMessageResponse(success=False, error=conv_response.error)
                conversation_id = conv_response.conversation_id
            
            # Build message
            message = Message(
                conversation_id=conversation_id,
                sender_id=self.user_id,
                sender_role=sender_role,
                sender_name=sender_name,
                message_type=request.message_type,
                content=request.content,
                attachments=request.attachments,
                referenced_document_id=request.referenced_document_id,
                referenced_delivery_id=request.referenced_delivery_id,
                reply_to_message_id=request.reply_to_message_id,
                sent_at=datetime.utcnow(),
                status=MessageStatus.SENT
            )
            
            # Store message as overlay
            msg_overlay = await manager.create_overlay(
                CreateOverlayRequest(
                    overlay_type=OverlayType.COMMUNICATION,
                    document_id=message.message_id,
                    vault_path=f"communications/{conversation_id}/{message.message_id}",
                    payload=message.dict(),
                    metadata={
                        "type": "message",
                        "conversation_id": conversation_id,
                        "sender_id": self.user_id,
                        "sent_at": message.sent_at.isoformat()
                    }
                )
            )
            
            if not msg_overlay.success:
                return SendMessageResponse(success=False, error="Failed to store message")
            
            # Update conversation last_message_at
            await self._update_conversation_timestamp(conversation_id)
            
            return SendMessageResponse(
                success=True,
                message_id=message.message_id,
                conversation_id=conversation_id,
                sent_at=message.sent_at
            )
            
        except Exception as e:
            logger.error(f"Send message failed: {e}", exc_info=True)
            return SendMessageResponse(success=False, error=str(e))
    
    async def mark_messages_read(self, request: MarkReadRequest) -> bool:
        """Mark messages as read."""
        try:
            manager = await self._get_manager()
            
            if request.mark_all and request.conversation_id:
                # Update participant's last_read_at in conversation
                conv_overlay = await manager.get_overlay(request.conversation_id)
                if conv_overlay:
                    conversation = Conversation(**conv_overlay.payload)
                    for participant in conversation.participants:
                        if participant.user_id == self.user_id:
                            participant.last_read_at = datetime.utcnow()
                            break
                    
                    # Update conversation overlay
                    await manager.update_overlay(
                        request.conversation_id,
                        payload=conversation.dict()
                    )
                return True
            
            # Mark specific messages as read
            for message_id in request.message_ids:
                msg_overlay = await manager.get_overlay(message_id)
                if msg_overlay and msg_overlay.payload.get("recipient_id") == self.user_id:
                    message = Message(**msg_overlay.payload)
                    message.status = MessageStatus.READ
                    message.read_at = datetime.utcnow()
                    
                    await manager.update_overlay(
                        message_id,
                        payload=message.dict()
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Mark messages read failed: {e}", exc_info=True)
            return False
    
    # ==========================================================================
    # Document Collaboration
    # ==========================================================================
    
    async def fill_and_sign_document(
        self,
        delivery_id: str,
        field_values: Dict[str, Any],
        signature_request: SignDocumentRequest,
        sender_role: ParticipantRole,
        sender_name: str
    ) -> DocumentFillResponse:
        """
        Fill out a document form and sign it in the browser.
        Saves completed document to user's vault.
        """
        try:
            from app.services.document_delivery_service import get_delivery_service
            
            # Get delivery service to handle the signing
            delivery_service = await get_delivery_service(self.storage, self.user_id)
            
            # First, fill the document fields if any
            if field_values:
                # Store filled values as an overlay
                manager = await self._get_manager()
                fill_overlay = await manager.create_overlay(
                    CreateOverlayRequest(
                        overlay_type=OverlayType.DOCUMENT_EXTRACTION,
                        document_id=f"{delivery_id}_filled",
                        vault_path=f"communications/filled/{delivery_id}",
                        payload={
                            "delivery_id": delivery_id,
                            "field_values": field_values,
                            "filled_at": datetime.utcnow().isoformat(),
                            "filled_by": self.user_id
                        },
                        metadata={
                            "type": "document_filled",
                            "delivery_id": delivery_id
                        }
                    )
                )
                
                if not fill_overlay.success:
                    return DocumentFillResponse(
                        success=False,
                        error="Failed to save filled document"
                    )
            
            # Now sign the document
            sign_response = await delivery_service.sign_document(delivery_id, signature_request)
            
            if not sign_response.success:
                return DocumentFillResponse(
                    success=False,
                    error=sign_response.message
                )
            
            # Create a completed document in vault
            completed_doc_id = f"signed_doc_{uuid4().hex[:16]}"
            
            # Store the signed document reference
            manager = await self._get_manager()
            signed_overlay = await manager.create_overlay(
                CreateOverlayRequest(
                    overlay_type=OverlayType.DOCUMENT_EXTRACTION,
                    document_id=completed_doc_id,
                    vault_path=f"vault/documents/{completed_doc_id}",
                    payload={
                        "original_delivery_id": delivery_id,
                        "signed_at": sign_response.signed_at.isoformat() if sign_response.signed_at else None,
                        "signed_by": self.user_id,
                        "signature_type": signature_request.signature_type,
                        "field_values": field_values,
                        "document_type": "signed_agreement"
                    },
                    metadata={
                        "type": "signed_document",
                        "delivery_id": delivery_id
                    }
                )
            )
            
            if not signed_overlay.success:
                return DocumentFillResponse(
                    success=False,
                    error="Failed to save signed document to vault"
                )
            
            # Send completion message to conversation
            await self.send_message(
                SendMessageRequest(
                    content=f"Document signed and completed. Document ID: {completed_doc_id}",
                    message_type=MessageType.SIGNATURE_RESPONSE,
                    referenced_delivery_id=delivery_id
                ),
                sender_role=sender_role,
                sender_name=sender_name
            )
            
            return DocumentFillResponse(
                success=True,
                document_id=completed_doc_id,
                filled_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Fill and sign document failed: {e}", exc_info=True)
            return DocumentFillResponse(success=False, error=str(e))
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    async def _save_rejection_record(
        self,
        delivery_id: str,
        reason: str,
        rejected_at: datetime
    ) -> bool:
        """
        Save a rejection record to the vault as a communication overlay.
        This creates a permanent record that the document was rejected.
        """
        try:
            manager = await self._get_manager()
            
            rejection_overlay = await manager.create_overlay(
                CreateOverlayRequest(
                    overlay_type=OverlayType.COMMUNICATION,
                    document_id=f"{delivery_id}_rejected",
                    vault_path=f"communications/rejections/{delivery_id}",
                    payload={
                        "delivery_id": delivery_id,
                        "reason": reason,
                        "rejected_at": rejected_at.isoformat() if rejected_at else datetime.utcnow().isoformat(),
                        "rejected_by": self.user_id,
                        "status": "REJECTED",
                        "watermark": "DOCUMENT REJECTED - REFUSAL TO SIGN"
                    },
                    metadata={
                        "type": "document_rejected",
                        "delivery_id": delivery_id,
                        "rejected_by": self.user_id,
                        "watermarked": True
                    }
                )
            )
            
            if rejection_overlay.success:
                logger.info(f"Rejection record saved to vault for delivery {delivery_id}")
                return True
            else:
                logger.error(f"Failed to save rejection record for {delivery_id}")
                return False
                
        except Exception as e:
            logger.error(f"Save rejection record failed: {e}", exc_info=True)
            return False
    
    async def _get_messages_for_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation."""
        try:
            manager = await self._get_manager()
            overlays = await manager.get_overlays(overlay_type=OverlayType.COMMUNICATION)
            
            messages = []
            for overlay in overlays.overlays:
                if (overlay.metadata.get("type") == "message" and 
                    overlay.metadata.get("conversation_id") == conversation_id):
                    messages.append(Message(**overlay.payload))
            
            return messages
            
        except Exception as e:
            logger.error(f"Get messages for conversation failed: {e}")
            return []
    
    async def _get_last_message_preview(self, conversation_id: str) -> Optional[str]:
        """Get preview of last message in conversation."""
        try:
            messages = await self._get_messages_for_conversation(conversation_id)
            if not messages:
                return None
            
            # Sort by sent_at desc
            messages.sort(key=lambda x: x.sent_at or datetime.min, reverse=True)
            last_msg = messages[0]
            
            # Truncate content
            preview = last_msg.content[:100]
            if len(last_msg.content) > 100:
                preview += "..."
            return preview
            
        except Exception as e:
            logger.error(f"Get last message preview failed: {e}")
            return None
    
    async def _update_conversation_timestamp(self, conversation_id: str):
        """Update conversation's last_message_at timestamp."""
        try:
            manager = await self._get_manager()
            conv_overlay = await manager.get_overlay(conversation_id)
            
            if conv_overlay:
                conversation = Conversation(**conv_overlay.payload)
                conversation.last_message_at = datetime.utcnow()
                conversation.updated_at = datetime.utcnow()
                conversation.message_count += 1
                
                await manager.update_overlay(
                    conversation_id,
                    payload=conversation.dict()
                )
                
        except Exception as e:
            logger.error(f"Update conversation timestamp failed: {e}")
    
    async def _update_last_read(self, conversation_id: str):
        """Update user's last read timestamp for conversation."""
        try:
            manager = await self._get_manager()
            conv_overlay = await manager.get_overlay(conversation_id)
            
            if conv_overlay:
                conversation = Conversation(**conv_overlay.payload)
                for participant in conversation.participants:
                    if participant.user_id == self.user_id:
                        participant.last_read_at = datetime.utcnow()
                        break
                
                await manager.update_overlay(
                    conversation_id,
                    payload=conversation.dict()
                )
                
        except Exception as e:
            logger.error(f"Update last read failed: {e}")


async def get_communication_service(storage, user_id: str) -> CommunicationService:
    """Factory function to get communication service instance."""
    return CommunicationService(storage, user_id)
