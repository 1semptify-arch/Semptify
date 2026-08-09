"""Public-records research workflows for landlord and property research."""

from typing import Any


def lookup_llc_structure(entity_name: str, state: str = "MN") -> dict[str, Any]:
    """Return a structured request for LLC ownership research.

    Real lookups require state Secretary of State APIs; this helper returns
    the parameters and an empty placeholder result set for later wiring.
    """
    return {
        "entity_name": entity_name,
        "state": state,
        "lookup_type": "llc_structure",
        "members": [],
        "registered_agent": None,
        "status": "lookup_not_yet_implemented",
    }


def lookup_property_records(parcel_id: str, county: str = "Hennepin") -> dict[str, Any]:
    """Return a structured request for county property records."""
    return {
        "parcel_id": parcel_id,
        "county": county,
        "lookup_type": "property_records",
        "owner": None,
        "tax_status": None,
        "assessed_value": None,
        "status": "lookup_not_yet_implemented",
    }


def lookup_eviction_history(party_name: str, case_number: str = "") -> dict[str, Any]:
    """Return a structured request for eviction filing history."""
    return {
        "party_name": party_name,
        "case_number": case_number,
        "lookup_type": "eviction_history",
        "filings": [],
        "status": "lookup_not_yet_implemented",
    }


def lookup_subsidy_participation(property_address: str) -> dict[str, Any]:
    """Return a structured request for housing subsidy participation."""
    return {
        "property_address": property_address,
        "lookup_type": "subsidy_participation",
        "programs": [],
        "status": "lookup_not_yet_implemented",
    }


def generate_public_profile(
    entity_name: str,
    property_address: str = "",
    parcel_id: str = "",
) -> dict[str, Any]:
    """Generate a consolidated public-profile request from the lookups above."""
    return {
        "entity_name": entity_name,
        "property_address": property_address,
        "parcel_id": parcel_id,
        "llc_structure": lookup_llc_structure(entity_name),
        "property_records": lookup_property_records(parcel_id) if parcel_id else None,
        "eviction_history": lookup_eviction_history(entity_name),
        "subsidy_participation": lookup_subsidy_participation(property_address) if property_address else None,
    }
