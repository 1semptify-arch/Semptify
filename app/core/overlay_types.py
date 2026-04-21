"""
Unified Overlay Types
=====================
Single source of truth for overlay type definitions.
All overlay categories: traceability, processing, annotations, forms, queries, redactions.
"""

from enum import Enum


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
}

ANNOTATION_OVERLAYS: set[OverlayType] = {
    OverlayType.HIGHLIGHT,
    OverlayType.NOTE,
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
    return "unknown"
