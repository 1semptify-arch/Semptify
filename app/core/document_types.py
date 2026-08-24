"""Document Type Definitions — SSOT for per-type required field checklists.

Used by the Document Center to render type-specific verification checklists
in the right pane. Each document type defines:
- required_fields: fields that must be confirmed for the doc to be "Verified"
- optional_fields: fields that are useful but not required
- overlay_mapping: which overlay type contains each field

Lifecycle: stable. Consumed by DC frontend via GET /api/dc/document-types.
"""

from __future__ import annotations

from typing import TypedDict


class FieldDef(TypedDict):
    name: str
    label: str
    field_type: str  # text, date, currency, boolean
    required: bool
    overlay_type: str  # which overlay this field lives in
    ocr_target: str  # hint for what OCR looks for


class DocumentTypeDef(TypedDict):
    key: str
    label: str
    description: str
    fields: list[FieldDef]


DOCUMENT_TYPES: dict[str, DocumentTypeDef] = {
    "lease": {
        "key": "lease",
        "label": "Lease Agreement",
        "description": "Rental contract between landlord and tenant.",
        "fields": [
            {
                "name": "landlord_name",
                "label": "Landlord name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "Landlord:, Owner:, signature block",
            },
            {
                "name": "tenant_name",
                "label": "Tenant name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "Tenant:, Lessee:, signature block",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "Premises:, Property Address:",
            },
            {
                "name": "lease_start_date",
                "label": "Lease start date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "commencing, beginning, start date",
            },
            {
                "name": "lease_end_date",
                "label": "Lease end date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "ending, terminating, expiration",
            },
            {
                "name": "monthly_rent",
                "label": "Monthly rent",
                "field_type": "currency",
                "required": True,
                "overlay_type": "amount_extraction",
                "ocr_target": "$, monthly rent, rent amount",
            },
            {
                "name": "security_deposit",
                "label": "Security deposit",
                "field_type": "currency",
                "required": True,
                "overlay_type": "amount_extraction",
                "ocr_target": "deposit, security deposit",
            },
            {
                "name": "signatures_present",
                "label": "Signatures present",
                "field_type": "boolean",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "signature lines detected",
            },
            {
                "name": "late_fee",
                "label": "Late fee",
                "field_type": "currency",
                "required": False,
                "overlay_type": "amount_extraction",
                "ocr_target": "late fee, late charge",
            },
            {
                "name": "pet_policy",
                "label": "Pet policy",
                "field_type": "text",
                "required": False,
                "overlay_type": "document_extraction",
                "ocr_target": "pets, animals",
            },
        ],
    },
    "notice_to_vacate": {
        "key": "notice_to_vacate",
        "label": "Notice to Vacate",
        "description": "Letter from landlord or tenant ending the tenancy.",
        "fields": [
            {
                "name": "sender_name",
                "label": "Sender name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "header, From:, signature",
            },
            {
                "name": "recipient_name",
                "label": "Recipient name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "To:, Dear",
            },
            {
                "name": "notice_date",
                "label": "Received Date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "document date, letterhead",
            },
            {
                "name": "vacate_by_date",
                "label": "Vacate by date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "vacate by, on or before, must leave",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "located at, premises at",
            },
            {
                "name": "reason_stated",
                "label": "Reason stated",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "reason for notice, body paragraph",
            },
            {
                "name": "delivery_method",
                "label": "Delivery method",
                "field_type": "text",
                "required": False,
                "overlay_type": "document_extraction",
                "ocr_target": "hand-delivered, certified mail",
            },
        ],
    },
    "repair_request": {
        "key": "repair_request",
        "label": "Repair Request",
        "description": "Tenant's request to landlord to fix a problem.",
        "fields": [
            {
                "name": "date_submitted",
                "label": "Date submitted",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "document date",
            },
            {
                "name": "tenant_name",
                "label": "Tenant name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "From:, submitted by",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "address block",
            },
            {
                "name": "issue_description",
                "label": "Issue description",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "body / issue description",
            },
            {
                "name": "landlord_notified",
                "label": "Landlord notified",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "sent to, submitted to, attention",
            },
            {
                "name": "response_deadline",
                "label": "Response deadline",
                "field_type": "date",
                "required": False,
                "overlay_type": "key_date_extraction",
                "ocr_target": "please respond by",
            },
        ],
    },
    "rent_receipt": {
        "key": "rent_receipt",
        "label": "Rent Receipt",
        "description": "Proof of rent payment.",
        "fields": [
            {
                "name": "payment_date",
                "label": "Payment date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "received, date",
            },
            {
                "name": "amount_paid",
                "label": "Amount paid",
                "field_type": "currency",
                "required": True,
                "overlay_type": "amount_extraction",
                "ocr_target": "$, amount",
            },
            {
                "name": "payer_name",
                "label": "Payer name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "received from, paid by",
            },
            {
                "name": "receiver_name",
                "label": "Receiver name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "received by, signature",
            },
            {
                "name": "period_covered",
                "label": "Period covered",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "for rent, for the month of",
            },
            {
                "name": "receipt_number",
                "label": "Receipt number",
                "field_type": "text",
                "required": False,
                "overlay_type": "document_extraction",
                "ocr_target": "receipt #, invoice #",
            },
        ],
    },
    "move_in_inspection": {
        "key": "move_in_inspection",
        "label": "Move-in Inspection",
        "description": "Condition checklist signed at move-in.",
        "fields": [
            {
                "name": "inspection_date",
                "label": "Inspection date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "document date",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "address block",
            },
            {
                "name": "tenant_name",
                "label": "Tenant name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "Tenant:",
            },
            {
                "name": "landlord_or_agent",
                "label": "Landlord or agent",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "Landlord:, Agent:",
            },
            {
                "name": "condition_notes",
                "label": "Condition notes",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "room-by-room entries, checkboxes",
            },
            {
                "name": "both_signed",
                "label": "Both parties signed",
                "field_type": "boolean",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "signature lines",
            },
        ],
    },
    "court_summons": {
        "key": "court_summons",
        "label": "Court Summons",
        "description": "Court document notifying tenant of a hearing.",
        "fields": [
            {
                "name": "court_name",
                "label": "Court name",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "court name, in the court of",
            },
            {
                "name": "case_number",
                "label": "Case number",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "case #, case no, docket",
            },
            {
                "name": "hearing_date",
                "label": "Hearing date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "hearing, appear on, date",
            },
            {
                "name": "plaintiff_name",
                "label": "Plaintiff name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "plaintiff, petitioner",
            },
            {
                "name": "defendant_name",
                "label": "Defendant name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "defendant, respondent",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "premises, property",
            },
            {
                "name": "response_deadline",
                "label": "Response deadline",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "respond by, answer by",
            },
        ],
    },
    "correspondence": {
        "key": "correspondence",
        "label": "Correspondence",
        "description": "Letter, email, or message between landlord and tenant.",
        "fields": [
            {
                "name": "sender_name",
                "label": "Sender name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "From:, sender",
            },
            {
                "name": "recipient_name",
                "label": "Recipient name",
                "field_type": "text",
                "required": True,
                "overlay_type": "party_extraction",
                "ocr_target": "To:, recipient",
            },
            {
                "name": "date",
                "label": "Date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "date",
            },
            {
                "name": "subject",
                "label": "Subject",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "re:, subject",
            },
            {
                "name": "property_address",
                "label": "Property address",
                "field_type": "text",
                "required": False,
                "overlay_type": "document_extraction",
                "ocr_target": "premises, property",
            },
        ],
    },
    "other": {
        "key": "other",
        "label": "Other",
        "description": "Document doesn't fit a specific category.",
        "fields": [
            {
                "name": "date",
                "label": "Date",
                "field_type": "date",
                "required": True,
                "overlay_type": "key_date_extraction",
                "ocr_target": "any date",
            },
            {
                "name": "description",
                "label": "Description",
                "field_type": "text",
                "required": True,
                "overlay_type": "document_extraction",
                "ocr_target": "title, subject",
            },
        ],
    },
}


def get_document_type(key: str) -> DocumentTypeDef | None:
    """Return the document type definition for a key, or None."""
    return DOCUMENT_TYPES.get(key)


def get_required_fields(key: str) -> list[FieldDef]:
    """Return only the required fields for a document type."""
    defn = DOCUMENT_TYPES.get(key)
    if not defn:
        return []
    return [f for f in defn["fields"] if f["required"]]


def get_fields_by_overlay(key: str, overlay_type: str) -> list[FieldDef]:
    """Return fields for a document type that belong to a specific overlay."""
    defn = DOCUMENT_TYPES.get(key)
    if not defn:
        return []
    return [f for f in defn["fields"] if f["overlay_type"] == overlay_type]


def get_all_document_types() -> list[DocumentTypeDef]:
    """Return all document type definitions as a list."""
    return list(DOCUMENT_TYPES.values())
