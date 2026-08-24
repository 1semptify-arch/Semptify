"""Tests for app.core.document_types."""

import pytest

from app.core.document_types import (
    DOCUMENT_TYPES,
    get_all_document_types,
    get_document_type,
    get_fields_by_overlay,
    get_required_fields,
)


def test_document_types_keys():
    """DOCUMENT_TYPES contains the expected document type keys."""
    assert "lease" in DOCUMENT_TYPES
    assert "notice_to_vacate" in DOCUMENT_TYPES
    assert "repair_request" in DOCUMENT_TYPES
    assert "house_rules" in DOCUMENT_TYPES


def test_get_document_type_returns_definition():
    """get_document_type returns the definition for a known key."""
    lease = get_document_type("lease")
    assert lease is not None
    assert lease["key"] == "lease"
    assert lease["label"] == "Lease Agreement"
    assert isinstance(lease["fields"], list)


def test_house_rules_document_type():
    """house_rules is a registered document type with fields."""
    house_rules = get_document_type("house_rules")
    assert house_rules is not None
    assert house_rules["key"] == "house_rules"
    assert house_rules["label"] == "House Rules"
    assert isinstance(house_rules["fields"], list)


def test_get_document_type_missing_returns_none():
    """get_document_type returns None for an unknown key."""
    assert get_document_type("not_a_type") is None


def test_get_required_fields_for_lease():
    """get_required_fields returns only required fields for a lease."""
    fields = get_required_fields("lease")
    assert all(f["required"] for f in fields)
    assert "landlord_name" in {f["name"] for f in fields}


def test_get_required_fields_missing_type():
    """get_required_fields returns an empty list for an unknown type."""
    assert get_required_fields("missing") == []


def test_get_fields_by_overlay():
    """get_fields_by_overlay filters fields by overlay type."""
    party_fields = get_fields_by_overlay("lease", "party_extraction")
    assert all(f["overlay_type"] == "party_extraction" for f in party_fields)
    assert len(party_fields) > 0


def test_get_fields_by_overlay_missing_type():
    """get_fields_by_overlay returns an empty list for an unknown type."""
    assert get_fields_by_overlay("missing", "party_extraction") == []


def test_get_all_document_types():
    """get_all_document_types returns all definitions."""
    types = get_all_document_types()
    assert len(types) == len(DOCUMENT_TYPES)
    assert all(t["key"] in DOCUMENT_TYPES for t in types)


def test_field_definitions_have_required_keys():
    """Every field definition contains the expected keys."""
    for doc_type in DOCUMENT_TYPES.values():
        for field in doc_type["fields"]:
            assert "name" in field
            assert "label" in field
            assert "field_type" in field
            assert "required" in field
            assert "overlay_type" in field
            assert "ocr_target" in field
