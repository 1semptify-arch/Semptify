"""
Unified Overlay Models
======================
Data models for the unified overlay system.
All overlays are cloud-stored, stateless, and reference immutable vault documents.
"""

import logging
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.id_gen import make_id
from app.core.overlay_types import OverlayType, get_overlay_category
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Base Overlay Model
# =============================================================================


class UnifiedOverlay(BaseModel):
    """
    Single unified overlay model for all overlay types.

    All mutations on vault documents are stored as overlays, never modifying
    the original. Original documents in VAULT_DOCUMENTS remain immutable.
    """

    # Identity
    overlay_id: str = Field(default_factory=lambda: make_id("ovl"))
    overlay_type: OverlayType

    # Document reference (immutable original)
    document_id: str = Field(..., min_length=1, description="Vault document ID")
    vault_path: str = Field(..., min_length=1, description="Original document path")

    # Provenance
    created_by: str = Field(..., min_length=1, description="User ID who created overlay")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Content (type-specific payload)
    payload: dict = Field(default_factory=dict, description="Type-specific overlay data")

    # Security chain (for audit trail)
    prev_overlay_hash: str | None = Field(None, description="Hash of previous overlay for chain")
    overlay_hash: str | None = Field(None, description="Hash of this overlay's content")

    # Metadata
    metadata: dict = Field(default_factory=dict, description="Source, jurisdiction, reason, etc.")

    # Ephemeral flag (for watermarked views - not persisted)
    ephemeral: bool = Field(default=False, description="If True, not persisted to cloud storage")

    # Versioning
    version: str = Field(default="1.0", description="Overlay schema version")

    @field_validator("overlay_type")
    def validate_overlay_type(cls, v):
        """Ensure overlay_type is valid."""
        if not isinstance(v, OverlayType):
            raise ValueError(f"Invalid overlay type: {v}")
        return v

    def get_category(self) -> str:
        """Return the category for this overlay type."""
        return get_overlay_category(self.overlay_type)


# =============================================================================
# Type-Specific Payload Models
# =============================================================================


class TextRange(BaseModel):
    """Position reference in document."""

    start_offset: int
    end_offset: int
    text: str | None = None  # Selected text (for verification)
    page: int | None = None  # For PDFs
    paragraph: int | None = None  # For text documents
    line: int | None = None


# --- Upload Traceability ---


class UploadManifestPayload(BaseModel):
    """Payload for VAULT_UPLOAD_MANIFEST overlays."""

    original_filename: str
    mime_type: str
    file_size_bytes: int
    content_hash: str  # SHA-256 of uploaded content
    uploaded_at: datetime
    storage_provider: str  # google_drive, dropbox, etc.


# --- Processing Results ---


class DocumentExtractionPayload(BaseModel):
    """Payload for DOCUMENT_EXTRACTION overlays."""

    extracted_dates: list[dict] = Field(default_factory=list)
    extracted_parties: list[dict] = Field(default_factory=list)
    extracted_amounts: list[dict] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    confidence_score: float | None = None
    extraction_model: str | None = None


class DocumentClassificationPayload(BaseModel):
    """Payload for DOCUMENT_CLASSIFICATION overlays."""

    document_type: str  # lease, notice, correspondence, evidence
    confidence_score: float | None = None
    classification_model: str | None = None
    alternative_types: list[dict] = Field(default_factory=list)


class TimelineExtractionPayload(BaseModel):
    """Payload for TIMELINE_EXTRACTION overlays."""

    events: list[dict] = Field(default_factory=list)
    extraction_confidence: float | None = None


# --- Annotations ---


class HighlightPayload(BaseModel):
    """Payload for HIGHLIGHT overlays."""

    range: TextRange
    color: str = "yellow"  # yellow, green, blue, red
    note: str | None = None


class NotePayload(BaseModel):
    """Payload for NOTE overlays."""

    range: TextRange | None = None
    content: str
    note_type: str = "user"  # user, ai, system, legal
    priority: str = "normal"  # low, normal, high, critical
    tags: list[str] = Field(default_factory=list)
    resolved: bool = False


class FootnotePayload(BaseModel):
    """Payload for FOOTNOTE overlays."""

    number: int
    range: TextRange
    content: str
    citation: str | None = None  # Legal citation


class TrackedEditPayload(BaseModel):
    """Payload for TRACKED_EDIT overlays."""

    range: TextRange
    original_text: str
    new_text: str
    edit_type: str = "replace"  # insert, delete, replace
    reason: str | None = None
    status: str = "pending"  # pending, accepted, rejected


# --- Form-Fill ---


class FormFieldMapping(BaseModel):
    """Mapping from form field to data source."""

    field_name: str
    field_type: str  # text, date, signature, checkbox
    data_source: str  # vault://user/profile/name, etc.
    filled_value: str | None = None
    is_required: bool = True


class FormFillPayload(BaseModel):
    """Payload for FORM_FILL overlays."""

    jurisdiction: str  # "CA", "TX", "NY", etc.
    form_type: str  # "eviction_answer", "motion_to_dismiss", etc.
    field_mappings: list[FormFieldMapping] = Field(default_factory=list)
    filled_at: datetime | None = None
    completion_percentage: float = 0.0


class FormSignaturePayload(BaseModel):
    """Payload for FORM_SIGNATURE overlays."""

    signer_id: str
    signer_name: str
    signed_at: datetime
    signature_type: str  # "electronic", "typed", "uploaded"
    signature_hash: str  # Verification hash
    witness_id: str | None = None
    notarized: bool = False


# --- Query/Output ---


class DocumentReference(BaseModel):
    """Reference to document in query."""

    document_id: str
    overlay_ids: list[str] = Field(default_factory=list)  # Which overlays to apply
    page_range: tuple[int, int] | None = None  # (start, end) for partial inclusion


class CourtPacketQueryPayload(BaseModel):
    """Payload for COURT_PACKET_QUERY overlays."""

    case_id: str
    packet_type: str  # "eviction_answer", "motion", "counterclaim", etc.
    document_refs: list[DocumentReference] = Field(default_factory=list)
    include_annotations: bool = True
    redact_pii: bool = True
    watermark_text: str | None = None


class WatermarkedViewPayload(BaseModel):
    """Payload for WATERMARKED_VIEW overlays (ephemeral)."""

    view_id: str
    source_query_id: str | None = None
    watermark_text: str
    expiration_minutes: int = 30


# --- Redaction ---


class RedactionRegion(BaseModel):
    """Region to redact."""

    page: int
    x: float  # Top-left x coordinate
    y: float  # Top-left y coordinate
    width: float
    height: float
    reason: str | None = None  # Why this is redacted


class PIIRedactionPayload(BaseModel):
    """Payload for PII_REDACTION overlays."""

    redaction_type: str = "pii"  # pii, sensitive, custom
    regions: list[RedactionRegion] = Field(default_factory=list)
    detected_categories: list[str] = Field(default_factory=list)  # ssn, dob, address, etc.
    replacement_strategy: str = "black_box"  # black_box, asterisks, label
    content_verification_hash: str | None = None


# --- Identity ---


class IdentityAdapterPayload(BaseModel):
    """Payload for IDENTITY_ADAPTER overlays."""

    adapter_type: str  # "document", "timeline", "case"
    linked_artifact_ids: list[str] = Field(default_factory=list)
    resolution_logic: dict = Field(default_factory=dict)


# --- Case Pattern Signals ---


class CaseDataPayload(BaseModel):
    """Payload for CASE_DATA overlays.

    Holds pattern-recognition signals and tenant-provided narrative. It does NOT
    hold case-management fields (case number, motions, deadlines, party identity).
    """

    flag_category: str | None = None  # e.g. "possible retaliation pattern"
    narrative: str | None = None  # Tenant's own description / notes
    harm_description: str | None = None
    timeline: list[dict] = Field(default_factory=list)
    exhibit_refs: list[str] = Field(default_factory=list)
    flag_notes: dict[str, str] = Field(default_factory=dict)  # duress/misrepresentation/violation
    schema_version: str = "1.0"


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateOverlayRequest(BaseModel):
    """Request to create an overlay."""

    overlay_type: OverlayType
    document_id: str
    vault_path: str
    payload: dict
    metadata: dict | None = None
    ephemeral: bool = False


class CreateOverlayResponse(BaseModel):
    """Response after creating an overlay."""

    success: bool
    overlay_id: str | None = None
    overlay_type: OverlayType | None = None
    message: str


class GetOverlaysRequest(BaseModel):
    """Request to query overlays."""

    document_id: str | None = None
    overlay_type: OverlayType | None = None
    category: str | None = None  # upload, processing, annotation, etc.
    created_by: str | None = None
    include_ephemeral: bool = False


class GetOverlaysResponse(BaseModel):
    """Response with overlay list."""

    success: bool
    overlays: list[UnifiedOverlay] = Field(default_factory=list)
    count: int = 0
    filters_applied: dict = Field(default_factory=dict)


class UpdateOverlayRequest(BaseModel):
    """Request to update an overlay."""

    payload: dict | None = None
    metadata: dict | None = None


class DeleteOverlayResponse(BaseModel):
    """Response after deleting an overlay."""

    success: bool
    overlay_id: str
    message: str


class DocumentViewRequest(BaseModel):
    """Request to compose a document view with overlays."""

    document_id: str
    overlay_ids: list[str] = Field(default_factory=list)
    apply_redactions: bool = True
    watermark_text: str | None = None


class DocumentViewResponse(BaseModel):
    """Response with composed document view."""

    success: bool
    document_id: str
    view_url: str | None = None  # Ephemeral watermarked view URL
    applied_overlays: list[str] = Field(default_factory=list)
    message: str
