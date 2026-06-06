"""Tests for app.core.overlay_types — Unified overlay type definitions."""

from app.core.overlay_types import (
    ALL_OVERLAY_TYPES,
    ANNOTATION_OVERLAYS,
    FORM_OVERLAYS,
    IDENTITY_OVERLAYS,
    PROCESSING_OVERLAYS,
    QUERY_OVERLAYS,
    REDACTION_OVERLAYS,
    UPLOAD_OVERLAYS,
    OverlayType,
    get_overlay_category,
)


class TestOverlayTypeEnum:
    def test_is_str_enum(self):
        assert isinstance(OverlayType.HIGHLIGHT, str)
        assert OverlayType.HIGHLIGHT == "highlight"

    def test_vault_upload_manifest_value(self):
        assert OverlayType.VAULT_UPLOAD_MANIFEST == "vault_upload_manifest"

    def test_all_members_present(self):
        expected = {
            "VAULT_UPLOAD_MANIFEST",
            "DOCUMENT_EXTRACTION",
            "DOCUMENT_CLASSIFICATION",
            "TIMELINE_EXTRACTION",
            "PARTY_EXTRACTION",
            "HIGHLIGHT",
            "NOTE",
            "FOOTNOTE",
            "TRACKED_EDIT",
            "FORM_FILL",
            "FORM_SIGNATURE",
            "COURT_PACKET_QUERY",
            "EVIDENCE_BUNDLE_QUERY",
            "WATERMARKED_VIEW",
            "PII_REDACTION",
            "SENSITIVE_REDACTION",
            "IDENTITY_ADAPTER",
            "COMMUNICATION",
        }
        assert {m.name for m in OverlayType} == expected


class TestCategorySets:
    def test_upload_overlays(self):
        assert {OverlayType.VAULT_UPLOAD_MANIFEST} == UPLOAD_OVERLAYS

    def test_processing_overlays(self):
        assert OverlayType.DOCUMENT_EXTRACTION in PROCESSING_OVERLAYS
        assert OverlayType.DOCUMENT_CLASSIFICATION in PROCESSING_OVERLAYS
        assert OverlayType.TIMELINE_EXTRACTION in PROCESSING_OVERLAYS
        assert OverlayType.PARTY_EXTRACTION in PROCESSING_OVERLAYS
        assert len(PROCESSING_OVERLAYS) == 4

    def test_annotation_overlays(self):
        assert OverlayType.HIGHLIGHT in ANNOTATION_OVERLAYS
        assert OverlayType.NOTE in ANNOTATION_OVERLAYS
        assert OverlayType.FOOTNOTE in ANNOTATION_OVERLAYS
        assert OverlayType.TRACKED_EDIT in ANNOTATION_OVERLAYS
        assert len(ANNOTATION_OVERLAYS) == 4

    def test_form_overlays(self):
        assert OverlayType.FORM_FILL in FORM_OVERLAYS
        assert OverlayType.FORM_SIGNATURE in FORM_OVERLAYS
        assert len(FORM_OVERLAYS) == 2

    def test_query_overlays(self):
        assert OverlayType.COURT_PACKET_QUERY in QUERY_OVERLAYS
        assert OverlayType.EVIDENCE_BUNDLE_QUERY in QUERY_OVERLAYS
        assert OverlayType.WATERMARKED_VIEW in QUERY_OVERLAYS
        assert len(QUERY_OVERLAYS) == 3

    def test_redaction_overlays(self):
        assert OverlayType.PII_REDACTION in REDACTION_OVERLAYS
        assert OverlayType.SENSITIVE_REDACTION in REDACTION_OVERLAYS
        assert len(REDACTION_OVERLAYS) == 2

    def test_identity_overlays(self):
        assert {OverlayType.IDENTITY_ADAPTER} == IDENTITY_OVERLAYS

    def test_all_overlay_types_covers_enum(self):
        assert set(OverlayType) == ALL_OVERLAY_TYPES

    def test_no_overlap_between_categories(self):
        categories = [
            UPLOAD_OVERLAYS,
            PROCESSING_OVERLAYS,
            ANNOTATION_OVERLAYS,
            FORM_OVERLAYS,
            QUERY_OVERLAYS,
            REDACTION_OVERLAYS,
            IDENTITY_OVERLAYS,
        ]
        seen: set[OverlayType] = set()
        for cat in categories:
            overlap = seen & cat
            assert not overlap, f"Overlapping types: {overlap}"
            seen |= cat


class TestGetOverlayCategory:
    def test_upload(self):
        assert get_overlay_category(OverlayType.VAULT_UPLOAD_MANIFEST) == "upload"

    def test_processing(self):
        assert get_overlay_category(OverlayType.DOCUMENT_EXTRACTION) == "processing"
        assert get_overlay_category(OverlayType.TIMELINE_EXTRACTION) == "processing"

    def test_annotation(self):
        assert get_overlay_category(OverlayType.HIGHLIGHT) == "annotation"
        assert get_overlay_category(OverlayType.FOOTNOTE) == "annotation"

    def test_form(self):
        assert get_overlay_category(OverlayType.FORM_FILL) == "form"

    def test_query(self):
        assert get_overlay_category(OverlayType.COURT_PACKET_QUERY) == "query"

    def test_redaction(self):
        assert get_overlay_category(OverlayType.PII_REDACTION) == "redaction"

    def test_identity(self):
        assert get_overlay_category(OverlayType.IDENTITY_ADAPTER) == "identity"

    def test_communication_is_unknown(self):
        assert get_overlay_category(OverlayType.COMMUNICATION) == "unknown"
