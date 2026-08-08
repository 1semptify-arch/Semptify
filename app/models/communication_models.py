"""
Communication System Models
===========================

Models for the Semptify communication system supporting:
- Direct messaging between tenant and all roles (advocate, manager, legal, admin)
- Document collaboration threads
- In-browser document filling and signing
- Message attachments and references
"""

import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_serializer

from app.core.id_gen import make_id

logger = logging.getLogger(__name__)


class MessageType(StrEnum):
    """Types of messages in the communication system."""

    TEXT = "text"  # Plain text message
    DOCUMENT = "document"  # Document reference with message
    SIGNATURE_REQUEST = "signature_request"  # Request for signature
    SIGNATURE_RESPONSE = "signature_response"  # Signature completed
    SYSTEM = "system"  # System-generated notification
    CASE_UPDATE = "case_update"  # Case status update


class ParticipantRole(StrEnum):
    """Roles of conversation participants."""

    TENANT = "tenant"
    ADVOCATE = "advocate"
    MANAGER = "manager"
    LEGAL = "legal"
    ADMIN = "admin"
    SYSTEM = "system"


class ConversationStatus(StrEnum):
    """Status of a conversation."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class MessageStatus(StrEnum):
    """Status of a message."""

    PENDING = "pending"  # Not yet sent (draft)
    SENT = "sent"  # Sent, not read
    DELIVERED = "delivered"  # Delivered to recipient
    READ = "read"  # Read by recipient
    FAILED = "failed"  # Failed to send


class Participant(BaseModel):
    """A participant in a conversation."""

    user_id: str
    role: ParticipantRole
    name: str
    organization: str | None = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_read_at: datetime | None = None
    is_active: bool = True


class MessageAttachment(BaseModel):
    """An attachment to a message (document, image, etc.)."""

    attachment_id: str = Field(default_factory=lambda: make_id("att"))
    filename: str
    document_id: str | None = None  # Reference to vault document
    file_size: int | None = None
    mime_type: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentSignatureRequest(BaseModel):
    """Embedded signature request within a message."""

    request_id: str = Field(default_factory=lambda: make_id("sigreq"))
    document_id: str  # Document to sign
    document_name: str
    signature_type: str = "typed"  # typed, drawn, digital
    required: bool = True
    signed_at: datetime | None = None
    signature_data: dict[str, Any] | None = None  # Signature image, metadata
    signed_by: str | None = None  # User ID who signed


class Message(BaseModel):
    """A message in a conversation."""

    message_id: str = Field(default_factory=lambda: make_id("msg"))
    conversation_id: str

    # Sender info
    sender_id: str
    sender_role: ParticipantRole
    sender_name: str

    # Message content
    message_type: MessageType = MessageType.TEXT
    content: str  # Message text content

    # Attachments and references
    attachments: list[MessageAttachment] = Field(default_factory=list)
    signature_request: DocumentSignatureRequest | None = None
    referenced_document_id: str | None = None  # Related document
    referenced_delivery_id: str | None = None  # Related delivery

    # Timestamps and status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: datetime | None = None
    read_at: datetime | None = None
    status: MessageStatus = MessageStatus.PENDING

    # Threading (for replies)
    reply_to_message_id: str | None = None
    thread_count: int = 0  # Number of replies to this message

    @field_serializer("created_at", "sent_at", "read_at", when_used="json")
    def serialize_dt(self, v: datetime | None) -> str | None:
        return v.isoformat() if v else None


class Conversation(BaseModel):
    """A conversation between participants."""

    conversation_id: str = Field(default_factory=lambda: make_id("conv"))

    # Conversation metadata
    title: str | None = None
    topic: str | None = None  # Subject/topic of conversation
    case_id: str | None = None  # Associated case (if any)

    # Participants
    participants: list[Participant] = Field(default_factory=list)
    created_by: str  # User ID who created conversation

    # Status
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = None

    # Message counts
    message_count: int = 0
    unread_count: int = 0


class ConversationSummary(BaseModel):
    """Summary view of a conversation for listing."""

    conversation_id: str
    title: str | None
    topic: str | None
    last_message_preview: str | None
    last_message_at: datetime | None
    unread_count: int
    participant_count: int
    is_active: bool


class ConversationListResponse(BaseModel):
    """Response with list of conversations."""

    conversations: list[ConversationSummary]
    total_count: int
    unread_total: int


class MessageThreadResponse(BaseModel):
    """Response with messages in a conversation."""

    conversation: Conversation
    messages: list[Message]
    has_more: bool = False
    next_cursor: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    conversation_id: str | None = None  # Create new if not provided
    recipient_ids: list[str] = Field(default_factory=list)  # For new conversations
    content: str
    message_type: MessageType = MessageType.TEXT
    attachments: list[MessageAttachment] = Field(default_factory=list)
    referenced_document_id: str | None = None
    referenced_delivery_id: str | None = None
    reply_to_message_id: str | None = None


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    success: bool
    message_id: str | None = None
    conversation_id: str | None = None
    sent_at: datetime | None = None
    error: str | None = None


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    title: str | None = None
    topic: str | None = None
    recipient_ids: list[str]  # Initial participants (besides creator)
    case_id: str | None = None
    initial_message: str | None = None


class CreateConversationResponse(BaseModel):
    """Response after creating a conversation."""

    success: bool
    conversation_id: str | None = None
    created_at: datetime | None = None
    error: str | None = None


class MarkReadRequest(BaseModel):
    """Request to mark messages as read."""

    message_ids: list[str] = Field(default_factory=list)
    # Or mark all in conversation as read
    conversation_id: str | None = None
    mark_all: bool = False


class TypingIndicator(BaseModel):
    """Typing indicator for real-time presence."""

    conversation_id: str
    user_id: str
    is_typing: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DocumentFillRequest(BaseModel):
    """Request for tenant to fill out a document form."""

    delivery_id: str
    field_values: dict[str, Any]  # Form field values
    completed: bool = False  # Is form complete?


class DocumentFillResponse(BaseModel):
    """Response after filling a document."""

    success: bool
    document_id: str | None = None  # New document ID in vault
    filled_at: datetime | None = None
    error: str | None = None


class CommunicationPreferences(BaseModel):
    """User preferences for communication."""

    user_id: str
    email_notifications: bool = True
    sms_notifications: bool = False
    notification_frequency: str = "immediate"  # immediate, digest, none
    auto_mark_read_on_open: bool = False
    typing_indicators_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)
