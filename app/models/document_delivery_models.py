"""
Document Delivery Models
========================
Models for the document delivery system.

Three delivery types:
1. REVIEW_REQUIRED - Sender decides if read receipt required
2. SIGNATURE_REQUIRED - Always tracked, tenant must sign or reject
3. PROCESS_SERVER - Future: formal legal service of process

Documents appear as PENDING in tenant vault. Never become tenant-owned automatically.
"""

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.id_gen import make_id

logger = logging.getLogger(__name__)


class DeliveryType(StrEnum):
    """Types of document delivery."""

    REVIEW_REQUIRED = "review_required"
    SIGNATURE_REQUIRED = "signature_required"
    PROCESS_SERVER = "process_server"  # Future feature


class DeliveryStatus(StrEnum):
    """Status of a document delivery."""

    PENDING = "pending"  # Waiting for tenant action
    VIEWED = "viewed"  # Tenant opened (if read receipt enabled)
    SIGNED = "signed"  # Tenant signed
    REJECTED = "rejected"  # Tenant rejected
    EXPIRED = "expired"  # Past deadline
    WITHDRAWN = "withdrawn"  # Sender withdrew


class DocumentDelivery(BaseModel):
    """
    A document delivery from sender to recipient.

    Stored in cloud overlay system. Immutable audit trail.
    """

    # Identity
    delivery_id: str = Field(default_factory=lambda: make_id("del"))

    # Sender (who is sending)
    sender_id: str  # User ID of sender
    sender_role: str  # advocate, manager, legal, admin
    sender_name: str
    sender_organization: str | None = None

    # Recipient (who receives)
    recipient_id: str  # User ID of tenant
    recipient_name: str

    # Document reference
    document_id: str  # Vault document ID
    document_filename: str
    document_hash: str  # SHA-256 for integrity verification

    # Delivery configuration
    delivery_type: DeliveryType
    requires_read_receipt: bool = False  # Only for REVIEW_REQUIRED
    deadline: datetime | None = None  # When action is required by

    # Message from sender
    message: str | None = None

    # Status tracking
    status: DeliveryStatus = DeliveryStatus.PENDING

    # Timestamps
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    viewed_at: datetime | None = None
    signed_at: datetime | None = None
    rejected_at: datetime | None = None

    # Action details (for signature/rejection)
    signature_data: dict | None = None  # Signature image, typed name, etc.
    rejection_reason: str | None = None

    # Security chain
    security_hash: str | None = None  # Chain hash for audit


class DeliveryInboxItem(BaseModel):
    """Simplified view of a delivery for inbox display."""

    delivery_id: str
    sender_name: str
    sender_organization: str | None
    sender_role: str
    document_filename: str
    delivery_type: DeliveryType
    status: DeliveryStatus
    sent_at: datetime
    deadline: datetime | None
    requires_read_receipt: bool
    has_message: bool  # True if message field is not empty


class DeliveryDetailResponse(BaseModel):
    """Full delivery details for viewing."""

    delivery: DocumentDelivery
    can_sign: bool  # True if SIGNATURE_REQUIRED and not yet signed
    can_reject: bool  # True if SIGNATURE_REQUIRED and not yet rejected
    can_view: bool  # True if not withdrawn and not expired
    is_expired: bool


class SendDocumentRequest(BaseModel):
    """Request to send a document to a tenant."""

    recipient_id: str
    document_id: str
    delivery_type: DeliveryType
    requires_read_receipt: bool = False
    deadline: datetime | None = None
    message: str | None = None


class SendDocumentResponse(BaseModel):
    """Response after sending a document."""

    success: bool
    delivery_id: str | None = None
    message: str


class SignDocumentRequest(BaseModel):
    """Request for tenant to sign a document."""

    signature_type: str = "typed"  # typed, drawn, uploaded
    signature_value: str  # The actual signature (typed name or base64 image)
    agree_to_terms: bool = True  # Must be True


class SignDocumentResponse(BaseModel):
    """Response after signing."""

    success: bool
    signed_at: datetime | None = None
    message: str


class RejectDocumentRequest(BaseModel):
    """Request for tenant to reject a document."""

    reason: str  # Required explanation


class RejectDocumentResponse(BaseModel):
    """Response after rejecting."""

    success: bool
    rejected_at: datetime | None = None
    message: str


class DeliveryListResponse(BaseModel):
    """List of deliveries for inbox/outbox."""

    deliveries: list[DeliveryInboxItem]
    count: int
    unread_count: int = 0
    pending_signature_count: int = 0
