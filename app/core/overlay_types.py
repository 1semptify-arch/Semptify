"""
Unified Overlay Types
=====================
Single source of truth for overlay type definitions.
All overlay categories: traceability, processing, annotations, forms, queries, redactions.
"""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class OverlayType(str, Enum):
    """
    All overlay types for the unified overlay system.

    Design principle: Each type is a distinct mutation layer on top of
    immutable vault documents. Originals never change; overlays provide all
    mutable behavior.
    """

    # ==========================================================================
    # 1. UPLOAD TRACEABILITY
    # ==========================================================================
    VAULT_UPLOAD_MANIFEST = "vault_upload_manifest"
    """Records what was uploaded, when, by whom, with hash verification."""

    # ==========================================================================
    # 2. PROCESSING RESULTS (AI extraction, classification)
    # ==========================================================================
    DOCUMENT_EXTRACTION = "document_extraction"
    """AI-extracted dates, parties, key terms."""

    DOCUMENT_CLASSIFICATION = "document_classification"
    """Document type classification (lease, notice, correspondence, etc.)."""

    TIMELINE_EXTRACTION = "timeline_extraction"
    """Events extracted for timeline generation."""

    PARTY_EXTRACTION = "party_extraction"
    """Landlord, tenant, attorney names and roles."""

    # ==========================================================================
    # 3. ANNOTATIONS (User-created content)
    # ==========================================================================
    HIGHLIGHT = "highlight"
    """Text selection with color (yellow, green, blue, red)."""

    NOTE = "note"
    """Free-form note attached to document position or standalone."""

    STICKY_NOTE = "sticky_note"
    """User scratch-pad note (not attached to a specific document)."""

    FOOTNOTE = "footnote"
    """Numbered annotation with optional legal citation."""

    TRACKED_EDIT = "tracked_edit"
    """Suggested text change (insert, delete, replace)."""

    # ==========================================================================
    # 4. FORM-FILL (Jurisdiction-specific legal forms)
    # ==========================================================================
    FORM_FILL = "form_fill"
    """Form field values overlaid on blank legal form."""

    FORM_SIGNATURE = "form_signature"
    """Electronic signature overlay with timestamp and identity."""

    # ==========================================================================
    # 5. OUTPUT/QUERY (Court packets, evidence bundles)
    # ==========================================================================
    COURT_PACKET_QUERY = "court_packet_query"
    """Query definition for assembling court filing packet."""

    EVIDENCE_BUNDLE_QUERY = "evidence_bundle_query"
    """Query definition for evidence exhibit bundle."""

    WATERMARKED_VIEW = "watermarked_view"
    """Ephemeral watermarked render view (not persisted)."""

    # ==========================================================================
    # 6. REDACTION (PII and sensitive information)
    # ==========================================================================
    PII_REDACTION = "pii_redaction"
    """Redaction overlay for personally identifiable information."""

    SENSITIVE_REDACTION = "sensitive_reduction"
    """Redaction overlay for sensitive but non-PII content."""

    # ==========================================================================
    # 7. IDENTITY/ADAPTER (Linking and resolution)
    # ==========================================================================
    IDENTITY_ADAPTER = "identity_adapter"
    """Links mutable adapter records to vault artifacts."""

    COMMUNICATION = "communication"
    """Messages, conversations, and collaboration threads."""

    CASE_DATA = "case_data"
    """Tenant pattern-recognition signals, narrative, exhibit refs, and flag notes.

    Content is what the tenant said, wrote, or what was found in their documents.
    It never stores case-management fields (case number, motions, deadlines).
    """

    FILEDORED = "filedored"
    """Virtual folder organization for post-processing (sort, dedup, AI classification)."""

    DUPLICATE_DETECTION = "duplicate_detection"
    """Cross-vault duplicate identification and tracking."""

    # ==========================================================================
    # 8. TENANT RECORDS (vault-persistence migration)
    # ==========================================================================
    JOURNAL_ENTRY = "journal_entry"
    """Free-form tenant journal record (note, conversation, incident, repair request)."""

    RENT_LEDGER_ENTRY = "rent_ledger_entry"
    """Rent ledger record — payment, fee, deposit, credit, or charge with running balance."""

    CALENDAR_EVENT = "calendar_event"
    """Tenant calendar event or deadline (manual or auto-synced)."""

    CONTACT = "contact"
    """Case-related contact — landlord, attorney, witness, inspector, agency."""

    CONTACT_INTERACTION = "contact_interaction"
    """Logged interaction with a contact (call, email, meeting, court appearance)."""

    COMPLAINT = "complaint"
    """Formal complaint draft/filing record for a regulatory agency (complaint wizard)."""

    DISPUTE_RECORD = "dispute_record"
    """Property-management dispute record (fees, lease violation, retaliation, habitability)."""

    COMPARISON_ENTRY = "comparison_entry"
    """Fee/term comparison entry attached to a dispute record (amounts in cents)."""

    INCIDENT = "incident"
    """Incident/case grouping record — organizes related evidence, timeline events, activities."""

    THIRD_PARTY_CONTACT = "third_party_contact"
    """Third-party contact extracted from communication imports (landlord, agency, attorney)."""

    EVICTION_TIMELINE_EVENT = "eviction_timeline_event"
    """Eviction-specific timeline event — structure + pointers; narrative PII stays in content overlays."""

    TIMELINE_EVENT = "timeline_event"
    """Tenant timeline event (notices, payments, maintenance, communications, court, captures)."""

    PATTERN_RECORD = "pattern_record"
    """Derived housing-accountability pattern detection record (risk score + pattern JSON)."""

    DOCUMENT_SHARE = "document_share"
    """Owner-granted document share link (recipient, scope, token) — lives in the owner's vault."""

    EXTERNAL_MAPPING = "external_mapping"
    """Bridge between a tenant record and an external system ID (court, parcel, agency)."""

    COURT_CASE_MAPPING = "court_case_mapping"
    """Court case reference with legal detail (case number, parties, dates, status)."""

    PROPERTY_MAPPING = "property_mapping"
    """Property parcel/address reference (county, tax ID, primary-residence flag)."""

    AGENCY_MAPPING = "agency_mapping"
    """Agency complaint reference (agency code, complaint number, status, outcome)."""

    MNDES_PACKAGE = "mndes_package"
    """MNDES exhibit package (case number, exhibits, attestations, submission state)."""


# =============================================================================
# Overlay Type Categories (for filtering and validation)
# =============================================================================

UPLOAD_OVERLAYS: set[OverlayType] = {
    OverlayType.VAULT_UPLOAD_MANIFEST,
}

PROCESSING_OVERLAYS: set[OverlayType] = {
    OverlayType.DOCUMENT_EXTRACTION,
    OverlayType.DOCUMENT_CLASSIFICATION,
    OverlayType.TIMELINE_EXTRACTION,
    OverlayType.PARTY_EXTRACTION,
    OverlayType.FILEDORED,
    OverlayType.DUPLICATE_DETECTION,
}

ANNOTATION_OVERLAYS: set[OverlayType] = {
    OverlayType.HIGHLIGHT,
    OverlayType.NOTE,
    OverlayType.STICKY_NOTE,
    OverlayType.FOOTNOTE,
    OverlayType.TRACKED_EDIT,
}

FORM_OVERLAYS: set[OverlayType] = {
    OverlayType.FORM_FILL,
    OverlayType.FORM_SIGNATURE,
}

QUERY_OVERLAYS: set[OverlayType] = {
    OverlayType.COURT_PACKET_QUERY,
    OverlayType.EVIDENCE_BUNDLE_QUERY,
    OverlayType.WATERMARKED_VIEW,
}

REDACTION_OVERLAYS: set[OverlayType] = {
    OverlayType.PII_REDACTION,
    OverlayType.SENSITIVE_REDACTION,
}

IDENTITY_OVERLAYS: set[OverlayType] = {
    OverlayType.IDENTITY_ADAPTER,
}

CASE_OVERLAYS: set[OverlayType] = {
    OverlayType.CASE_DATA,
}

RECORD_OVERLAYS: set[OverlayType] = {
    OverlayType.JOURNAL_ENTRY,
    OverlayType.RENT_LEDGER_ENTRY,
    OverlayType.CALENDAR_EVENT,
    OverlayType.CONTACT,
    OverlayType.CONTACT_INTERACTION,
    OverlayType.COMPLAINT,
    OverlayType.DISPUTE_RECORD,
    OverlayType.COMPARISON_ENTRY,
    OverlayType.INCIDENT,
    OverlayType.THIRD_PARTY_CONTACT,
    OverlayType.EVICTION_TIMELINE_EVENT,
    OverlayType.TIMELINE_EVENT,
    OverlayType.PATTERN_RECORD,
    OverlayType.DOCUMENT_SHARE,
    OverlayType.EXTERNAL_MAPPING,
    OverlayType.COURT_CASE_MAPPING,
    OverlayType.PROPERTY_MAPPING,
    OverlayType.AGENCY_MAPPING,
    OverlayType.MNDES_PACKAGE,
}

# All overlay types (for validation)
ALL_OVERLAY_TYPES: set[OverlayType] = set(OverlayType)


def get_overlay_category(overlay_type: OverlayType) -> str:
    """Return the category name for an overlay type."""
    if overlay_type in UPLOAD_OVERLAYS:
        return "upload"
    if overlay_type in PROCESSING_OVERLAYS:
        return "processing"
    if overlay_type in ANNOTATION_OVERLAYS:
        return "annotation"
    if overlay_type in FORM_OVERLAYS:
        return "form"
    if overlay_type in QUERY_OVERLAYS:
        return "query"
    if overlay_type in REDACTION_OVERLAYS:
        return "redaction"
    if overlay_type in IDENTITY_OVERLAYS:
        return "identity"
    if overlay_type in CASE_OVERLAYS:
        return "case"
    if overlay_type in RECORD_OVERLAYS:
        return "record"
    return "unknown"
