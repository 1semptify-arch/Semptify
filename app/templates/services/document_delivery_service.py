"""
Document Delivery Service
=========================
Service for sending, receiving, signing, and rejecting documents.

Uses unified overlay system for cloud-only storage.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.core.overlay_types import OverlayType
from app.models.document_delivery_models import (
    DocumentDelivery,
    DeliveryType,
    DeliveryStatus,
    DeliveryInboxItem,
    DeliveryDetailResponse,
    SendDocumentRequest,
    SendDocumentResponse,
    SignDocumentRequest,
    SignDocumentResponse,
    RejectDocumentRequest,
    RejectDocumentResponse,
    DeliveryListResponse,
)
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.unified_overlay_manager import get_unified_overlay_manager

logger = logging.getLogger(__name__)

# Who can send documents
SENDER_ROLES = {"advocate", "manager", "legal", "admin"}

# Default deadline (7 days)
DEFAULT_DEADLINE_DAYS = 7


class DocumentDeliveryService:
    """
    Manages document delivery between professionals and tenants.
    
    All delivery records stored as overlays in user's cloud storage.
    """
    
    def __init__(self, storage_provider, sender_user_id: str):
        """
        Initialize delivery service.
        
        Args:
            storage_provider: Cloud storage adapter
            sender_user_id: ID of the user initiating actions
        """
        self.storage = storage_provider
        self.user_id = sender_user_id
    
    # ==========================================================================
    # Send Document
    # ==========================================================================
    
    async def send_document(
        self,
        request: SendDocumentRequest,
        sender_name: str,
        sender_organization: Optional[str],
        sender_role: str,
        recipient_name: str,
        document_filename: str,
        document_hash: str,
    ) -> SendDocumentResponse:
        """
        Send a document to a tenant.
        
        Creates a delivery record in the recipient's vault overlays.
        """
        try:
            # Validate sender role
            if sender_role not in SENDER_ROLES:
                return SendDocumentResponse(
                    success=False,
                    message=f"Role '{sender_role}' cannot send documents. Only: {SENDER_ROLES}"
                )
            
            # Validate delivery type
            if request.delivery_type == DeliveryType.PROCESS_SERVER:
                return SendDocumentResponse(
                    success=False,
                    message="Process server delivery not yet implemented"
                )
            
            # Create delivery record
            delivery = DocumentDelivery(
                sender_id=self.user_id,
                sender_role=sender_role,
                sender_name=sender_name,
                sender_organization=sender_organization,
                recipient_id=request.recipient_id,
                recipient_name=recipient_name,
                document_id=request.document_id,
                document_filename=document_filename,
                document_hash=document_hash,
                delivery_type=request.delivery_type,
                requires_read_receipt=request.requires_read_receipt,
                deadline=request.deadline or datetime.utcnow() + timedelta(days=DEFAULT_DEADLINE_DAYS),
                message=request.message,
            )
            
            # Compute security hash
            delivery.security_hash = self._compute_delivery_hash(delivery)
            
            # Store as overlay in recipient's cloud storage
            manager = await get_unified_overlay_manager(self.storage, request.recipient_id)
            overlay_request = CreateOverlayRequest(
                overlay_type=OverlayType.IDENTITY_ADAPTER,  # Using adapter type for cross-user delivery
                document_id=request.document_id,
                vault_path=f"deliveries/{delivery.delivery_id}",
                payload=delivery.dict(),
                metadata={
                    "delivery_type": request.delivery_type.value,
                    "sender_id": self.user_id,
                    "recipient_id": request.recipient_id,
                    "status": DeliveryStatus.PENDING.value,
                },
            )
            
            result = await manager.create_overlay(overlay_request)
            
            if not result.success:
                logger.error(f"Failed to create delivery overlay: {result.message}")
                return SendDocumentResponse(
                    success=False,
                    message=f"Failed to store delivery: {result.message}"
                )
            
            logger.info(
                f"Document sent: {delivery.delivery_id} from {self.user_id} "
                f"to {request.recipient_id} ({request.delivery_type.value})"
            )
            
            return SendDocumentResponse(
                success=True,
                delivery_id=delivery.delivery_id,
                message="Document sent successfully"
            )
            
        except Exception as e:
            logger.error(f"Send document failed: {e}", exc_info=True)
            return SendDocumentResponse(
                success=False,
                message=f"Error sending document: {str(e)}"
            )
    
    # ==========================================================================
    # Tenant Inbox
    # ==========================================================================
    
    async def get_inbox(self) -> DeliveryListResponse:
        """
        Get all deliveries for the current user (tenant inbox).
        
        Returns PENDING and handled deliveries.
        """
        try:
            manager = await get_unified_overlay_manager(self.storage, self.user_id)
            
            # Query all delivery overlays for this user
            overlays = await manager.get_overlays(category="identity")  # Using identity category
            
            deliveries = []
            unread_count = 0
            pending_signature_count = 0
            
            for overlay in overlays.overlays:
                # Check if this is a delivery overlay
                if overlay.metadata.get("delivery_type"):
                    delivery_data = overlay.payload
                    delivery = DocumentDelivery(**delivery_data)
                    
                    # Only show if recipient matches current user
                    if delivery.recipient_id == self.user_id:
                        inbox_item = DeliveryInboxItem(
                            delivery_id=delivery.delivery_id,
                            sender_name=delivery.sender_name,
                            sender_organization=delivery.sender_organization,
                            sender_role=delivery.sender_role,
                            document_filename=delivery.document_filename,
                            delivery_type=delivery.delivery_type,
                            status=delivery.status,
                            sent_at=delivery.sent_at,
                            deadline=delivery.deadline,
                            requires_read_receipt=delivery.requires_read_receipt,
                            has_message=bool(delivery.message),
                        )
                        deliveries.append(inbox_item)
                        
                        if delivery.status == DeliveryStatus.PENDING:
                            unread_count += 1
                            if delivery.delivery_type == DeliveryType.SIGNATURE_REQUIRED:
                                pending_signature_count += 1
            
            # Sort by sent_at desc (newest first)
            deliveries.sort(key=lambda x: x.sent_at, reverse=True)
            
            return DeliveryListResponse(
                deliveries=deliveries,
                count=len(deliveries),
                unread_count=unread_count,
                pending_signature_count=pending_signature_count,
            )
            
        except Exception as e:
            logger.error(f"Get inbox failed: {e}", exc_info=True)
            return DeliveryListResponse(deliveries=[], count=0)
    
    async def get_delivery_detail(self, delivery_id: str) -> Optional[DeliveryDetailResponse]:
        """Get full details of a specific delivery."""
        try:
            delivery = await self._get_delivery_by_id(delivery_id)
            if not delivery:
                return None
            
            # Check permissions
            if delivery.recipient_id != self.user_id and delivery.sender_id != self.user_id:
                logger.warning(f"User {self.user_id} attempted to access delivery {delivery_id} without permission")
                return None
            
            is_expired = delivery.deadline and delivery.deadline < datetime.utcnow()
            
            return DeliveryDetailResponse(
                delivery=delivery,
                can_sign=(
                    delivery.delivery_type == DeliveryType.SIGNATURE_REQUIRED
                    and delivery.status == DeliveryStatus.PENDING
                    and not is_expired
                    and delivery.recipient_id == self.user_id
                ),
                can_reject=(
                    delivery.delivery_type == DeliveryType.SIGNATURE_REQUIRED
                    and delivery.status == DeliveryStatus.PENDING
                    and not is_expired
                    and delivery.recipient_id == self.user_id
                ),
                can_view=(
                    delivery.status not in {DeliveryStatus.WITHDRAWN, DeliveryStatus.EXPIRED}
                    and (delivery.recipient_id == self.user_id or delivery.sender_id == self.user_id)
                ),
                is_expired=is_expired,
            )
            
        except Exception as e:
            logger.error(f"Get delivery detail failed: {e}", exc_info=True)
            return None
    
    # ==========================================================================
    # Sign Document
    # ==========================================================================
    
    async def sign_document(
        self,
        delivery_id: str,
        request: SignDocumentRequest,
    ) -> SignDocumentResponse:
        """Tenant signs a document."""
        try:
            delivery = await self._get_delivery_by_id(delivery_id)
            if not delivery:
                return SignDocumentResponse(success=False, message="Delivery not found")
            
            # Validate
            if delivery.recipient_id != self.user_id:
                return SignDocumentResponse(success=False, message="Not authorized to sign this document")
            
            if delivery.status != DeliveryStatus.PENDING:
                return SignDocumentResponse(success=False, message=f"Cannot sign: status is {delivery.status.value}")
            
            if delivery.delivery_type != DeliveryType.SIGNATURE_REQUIRED:
                return SignDocumentResponse(success=False, message="This document does not require signature")
            
            if not request.agree_to_terms:
                return SignDocumentResponse(success=False, message="Must agree to terms to sign")
            
            # Update delivery
            delivery.status = DeliveryStatus.SIGNED
            delivery.signed_at = datetime.utcnow()
            delivery.signature_data = {
                "type": request.signature_type,
                "value_hash": hashlib.sha256(request.signature_value.encode()).hexdigest()[:16],
                "signed_at": delivery.signed_at.isoformat(),
            }
            delivery.security_hash = self._compute_delivery_hash(delivery)
            
            # Update overlay
            await self._update_delivery_overlay(delivery)
            
            logger.info(f"Document signed: {delivery_id} by {self.user_id}")
            
            return SignDocumentResponse(
                success=True,
                signed_at=delivery.signed_at,
                message="Document signed successfully"
            )
            
        except Exception as e:
            logger.error(f"Sign document failed: {e}", exc_info=True)
            return SignDocumentResponse(success=False, message=f"Error signing: {str(e)}")
    
    # ==========================================================================
    # Reject Document
    # ==========================================================================
    
    async def reject_document(
        self,
        delivery_id: str,
        request: RejectDocumentRequest,
    ) -> RejectDocumentResponse:
        """Tenant rejects a document."""
        try:
            delivery = await self._get_delivery_by_id(delivery_id)
            if not delivery:
                return RejectDocumentResponse(success=False, message="Delivery not found")
            
            # Validate
            if delivery.recipient_id != self.user_id:
                return RejectDocumentResponse(success=False, message="Not authorized to reject this document")
            
            if delivery.status != DeliveryStatus.PENDING:
                return RejectDocumentResponse(success=False, message=f"Cannot reject: status is {delivery.status.value}")
            
            if not request.reason or len(request.reason.strip()) < 10:
                return RejectDocumentResponse(success=False, message="Rejection reason must be at least 10 characters")
            
            # Update delivery
            delivery.status = DeliveryStatus.REJECTED
            delivery.rejected_at = datetime.utcnow()
            delivery.rejection_reason = request.reason
            delivery.security_hash = self._compute_delivery_hash(delivery)
            
            # Update overlay
            await self._update_delivery_overlay(delivery)
            
            logger.info(f"Document rejected: {delivery_id} by {self.user_id}")
            
            return RejectDocumentResponse(
                success=True,
                rejected_at=delivery.rejected_at,
                message="Document rejected"
            )
            
        except Exception as e:
            logger.error(f"Reject document failed: {e}", exc_info=True)
            return RejectDocumentResponse(success=False, message=f"Error rejecting: {str(e)}")
    
    # ==========================================================================
    # Mark Viewed
    # ==========================================================================
    
    async def mark_viewed(self, delivery_id: str) -> bool:
        """Mark a document as viewed (for read receipt tracking)."""
        try:
            delivery = await self._get_delivery_by_id(delivery_id)
            if not delivery:
                return False
            
            if delivery.recipient_id != self.user_id:
                return False
            
            if delivery.status == DeliveryStatus.PENDING and delivery.requires_read_receipt:
                delivery.status = DeliveryStatus.VIEWED
                delivery.viewed_at = datetime.utcnow()
                delivery.security_hash = self._compute_delivery_hash(delivery)
                await self._update_delivery_overlay(delivery)
                logger.info(f"Document viewed: {delivery_id} by {self.user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Mark viewed failed: {e}", exc_info=True)
            return False
    
    # ==========================================================================
    # Sender Outbox
    # ==========================================================================
    
    async def get_outbox(self) -> DeliveryListResponse:
        """Get all documents sent by the current user."""
        try:
            manager = await get_unified_overlay_manager(self.storage, self.user_id)
            overlays = await manager.get_overlays(category="identity")
            
            deliveries = []
            
            for overlay in overlays.overlays:
                if overlay.metadata.get("delivery_type"):
                    delivery_data = overlay.payload
                    delivery = DocumentDelivery(**delivery_data)
                    
                    # Only show if sender matches current user
                    if delivery.sender_id == self.user_id:
                        inbox_item = DeliveryInboxItem(
                            delivery_id=delivery.delivery_id,
                            sender_name=delivery.recipient_name,  # Show recipient in outbox
                            sender_organization=None,
                            sender_role="tenant",  # Recipients are always tenants
                            document_filename=delivery.document_filename,
                            delivery_type=delivery.delivery_type,
                            status=delivery.status,
                            sent_at=delivery.sent_at,
                            deadline=delivery.deadline,
                            requires_read_receipt=delivery.requires_read_receipt,
                            has_message=bool(delivery.message),
                        )
                        deliveries.append(inbox_item)
            
            deliveries.sort(key=lambda x: x.sent_at, reverse=True)
            
            return DeliveryListResponse(
                deliveries=deliveries,
                count=len(deliveries),
            )
            
        except Exception as e:
            logger.error(f"Get outbox failed: {e}", exc_info=True)
            return DeliveryListResponse(deliveries=[], count=0)
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    async def _get_delivery_by_id(self, delivery_id: str) -> Optional[DocumentDelivery]:
        """Fetch a delivery by ID from overlays."""
        try:
            manager = await get_unified_overlay_manager(self.storage, self.user_id)
            overlays = await manager.get_overlays(category="identity")
            
            for overlay in overlays.overlays:
                if overlay.metadata.get("delivery_type"):
                    delivery_data = overlay.payload
                    if delivery_data.get("delivery_id") == delivery_id:
                        return DocumentDelivery(**delivery_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Get delivery by ID failed: {e}", exc_info=True)
            return None
    
    async def _update_delivery_overlay(self, delivery: DocumentDelivery) -> bool:
        """Update the delivery overlay in cloud storage."""
        try:
            # Find and update the overlay
            manager = await get_unified_overlay_manager(self.storage, delivery.recipient_id)
            
            # We need to find the overlay ID first
            overlays = await manager.get_overlays(category="identity")
            target_overlay_id = None
            
            for overlay in overlays.overlays:
                if overlay.metadata.get("delivery_type"):
                    if overlay.payload.get("delivery_id") == delivery.delivery_id:
                        target_overlay_id = overlay.overlay_id
                        break
            
            if not target_overlay_id:
                logger.error(f"Could not find overlay for delivery {delivery.delivery_id}")
                return False
            
            # Update the overlay
            await manager.update_overlay(
                target_overlay_id,
                payload=delivery.dict(),
                metadata={
                    "delivery_type": delivery.delivery_type.value,
                    "sender_id": delivery.sender_id,
                    "recipient_id": delivery.recipient_id,
                    "status": delivery.status.value,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Update delivery overlay failed: {e}", exc_info=True)
            return False
    
    def _compute_delivery_hash(self, delivery: DocumentDelivery) -> str:
        """Compute security hash for delivery chain."""
        data = delivery.dict(exclude={"security_hash", "viewed_at", "signed_at", "rejected_at"})
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:32]


async def get_delivery_service(storage_provider, user_id: str) -> DocumentDeliveryService:
    """Factory function to create delivery service."""
    return DocumentDeliveryService(storage_provider, user_id)
