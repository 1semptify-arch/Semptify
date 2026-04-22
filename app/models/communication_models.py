"""
Communication System Models
===========================

Models for the Semptify communication system supporting:
- Direct messaging between tenant and all roles (advocate, manager, legal, admin)
- Document collaboration threads
- In-browser document filling and signing
- Message attachments and references
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.core.id_gen import make_id


class MessageType(str, Enum):
    """Types of messages in the communication system."""
    TEXT = "text"                    # Plain text message
    DOCUMENT = "document"            # Document reference with message
    SIGNATURE_REQUEST = "signature_request"  # Request for signature
    SIGNATURE_RESPONSE = "signature_response"  # Signature completed
    SYSTEM = "system"                # System-generated notification
    CASE_UPDATE = "case_update"       # Case status update


class ParticipantRole(str, Enum):
    """Roles of conversation participants."""
    TENANT = "tenant"
    ADVOCATE = "advocate"
    MANAGER = "manager"
    LEGAL = "legal"
    ADMIN = "admin"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class MessageStatus(str, Enum):
    """Status of a message."""
    PENDING = "pending"              # Not yet sent (draft)
    SENT = "sent"                    # Sent, not read
    DELIVERED = "delivered"          # Delivered to recipient
    READ = "read"                    # Read by recipient
    FAILED = "failed"                # Failed to send


class Participant(BaseModel):
    """A participant in a conversation."""
    user_id: str
    role: ParticipantRole
    name: str
    organization: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_read_at: Optional[datetime] = None
    is_active: bool = True


class MessageAttachment(BaseModel):
    """An attachment to a message (document, image, etc.)."""
    attachment_id: str = Field(default_factory=lambda: make_id("att"))
    filename: str
    document_id: Optional[str] = None  # Reference to vault document
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentSignatureRequest(BaseModel):
    """Embedded signature request within a message."""
    request_id: str = Field(default_factory=lambda: make_id("sigreq"))
    document_id: str                 # Document to sign
    document_name: str
    signature_type: str = "typed"    # typed, drawn, digital
    required: bool = True
    signed_at: Optional[datetime] = None
    signature_data: Optional[Dict[str, Any]] = None  # Signature image, metadata
    signed_by: Optional[str] = None   # User ID who signed


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
    content: str                     # Message text content
    
    # Attachments and references
    attachments: List[MessageAttachment] = Field(default_factory=list)
    signature_request: Optional[DocumentSignatureRequest] = None
    referenced_document_id: Optional[str] = None  # Related document
    referenced_delivery_id: Optional[str] = None  # Related delivery
    
    # Timestamps and status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.PENDING
    
    # Threading (for replies)
    reply_to_message_id: Optional[str] = None
    thread_count: int = 0            # Number of replies to this message
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(BaseModel):
    """A conversation between participants."""
    conversation_id: str = Field(default_factory=lambda: make_id("conv"))
    
    # Conversation metadata
    title: Optional[str] = None
    topic: Optional[str] = None       # Subject/topic of conversation
    case_id: Optional[str] = None    # Associated case (if any)
    
    # Participants
    participants: List[Participant] = Field(default_factory=list)
    created_by: str                   # User ID who created conversation
    
    # Status
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    
    # Message counts
    message_count: int = 0
    unread_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationSummary(BaseModel):
    """Summary view of a conversation for listing."""
    conversation_id: str
    title: Optional[str]
    topic: Optional[str]
    last_message_preview: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int
    participant_count: int
    is_active: bool


class ConversationListResponse(BaseModel):
    """Response with list of conversations."""
    conversations: List[ConversationSummary]
    total_count: int
    unread_total: int


class MessageThreadResponse(BaseModel):
    """Response with messages in a conversation."""
    conversation: Conversation
    messages: List[Message]
    has_more: bool = False
    next_cursor: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    conversation_id: Optional[str] = None  # Create new if not provided
    recipient_ids: List[str] = Field(default_factory=list)  # For new conversations
    content: str
    message_type: MessageType = MessageType.TEXT
    attachments: List[MessageAttachment] = Field(default_factory=list)
    referenced_document_id: Optional[str] = None
    referenced_delivery_id: Optional[str] = None
    reply_to_message_id: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Response after sending a message."""
    success: bool
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    error: Optional[str] = None


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = None
    topic: Optional[str] = None
    recipient_ids: List[str]               # Initial participants (besides creator)
    case_id: Optional[str] = None
    initial_message: Optional[str] = None


class CreateConversationResponse(BaseModel):
    """Response after creating a conversation."""
    success: bool
    conversation_id: Optional[str] = None
    created_at: Optional[datetime] = None
    error: Optional[str] = None


class MarkReadRequest(BaseModel):
    """Request to mark messages as read."""
    message_ids: List[str] = Field(default_factory=list)
    # Or mark all in conversation as read
    conversation_id: Optional[str] = None
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
    field_values: Dict[str, Any]         # Form field values
    completed: bool = False              # Is form complete?


class DocumentFillResponse(BaseModel):
    """Response after filling a document."""
    success: bool
    document_id: Optional[str] = None    # New document ID in vault
    filled_at: Optional[datetime] = None
    error: Optional[str] = None


class CommunicationPreferences(BaseModel):
    """User preferences for communication."""
    user_id: str
    email_notifications: bool = True
    sms_notifications: bool = False
    notification_frequency: str = "immediate"  # immediate, digest, none
    auto_mark_read_on_open: bool = False
    typing_indicators_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)
