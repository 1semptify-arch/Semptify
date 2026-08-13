"""Vault Object + Page Envelopes (ADR-0008 pilot surface 2).

This module applies the Object Context Envelope (§2.1) and Page Envelope (§2.6)
schemas to the Vault upload page and to the documents produced by the Vault
upload flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.context_envelope import (
    EncounterContext,
    ObjectEnvelope,
    ObjectType,
    Pillar,
    Provenance,
    TemporalValidity,
    Who,
)
from app.core.page_envelope import PageEnvelope, PageRelation, resolve_page_actions

if TYPE_CHECKING:
    from app.services.vault_upload_service import VaultDocument

# Page Envelope for the Document Vault page.
VAULT_UPLOAD_PAGE = PageEnvelope(
    page_subject="Document Vault",
    page_objectives=[
        "Upload and organize documents for the tenant's case.",
        "Keep evidence in the tenant's own cloud storage, not on Semptify servers.",
    ],
    page_actions=[
        ObjectEnvelope(
            object_id="vault_upload_zone",
            object_type=ObjectType.BUTTON,
            pillar=Pillar.ACT,
            who=Who.TENANT,
            why="Opens the file picker so the tenant can choose documents to upload.",
            provenance=Provenance.USER_ENTERED,
            temporal_validity=TemporalValidity.EVENT_TRIGGERED,
            subject_tags=["vault", "upload", "document"],
        ),
        ObjectEnvelope(
            object_id="vault_file_input",
            object_type=ObjectType.FIELD,
            pillar=Pillar.RECORD,
            who=Who.TENANT,
            why="The actual file or files the tenant selects for upload.",
            provenance=Provenance.USER_ENTERED,
            temporal_validity=TemporalValidity.STATIC,
            subject_tags=["vault", "upload", "file"],
        ),
        ObjectEnvelope(
            object_id="vault_documents_list",
            object_type=ObjectType.BLOCK,
            pillar=Pillar.RECORD,
            who=Who.TENANT,
            why="Lists the tenant's stored documents with pointers to their cloud vault.",
            provenance=Provenance.SYSTEM_COMPUTED,
            temporal_validity=TemporalValidity.EVENT_TRIGGERED,
            subject_tags=["vault", "documents", "list"],
        ),
        ObjectEnvelope(
            object_id="vault_export_case_button",
            object_type=ObjectType.BUTTON,
            pillar=Pillar.GOVERN,
            who=Who.TENANT,
            why="Packages the tenant's documents into a downloadable case bundle.",
            provenance=Provenance.USER_ENTERED,
            temporal_validity=TemporalValidity.EVENT_TRIGGERED,
            subject_tags=["vault", "export", "case"],
        ),
    ],
    page_relations=[
        PageRelation(relation="stored_in", target="tenant cloud storage"),
        PageRelation(relation="used_for", target="case evidence"),
    ],
    page_state=[
        "tenant-facing",
        "cloud-backed",
        "evidence organizer",
    ],
)


def vault_document_to_object_envelope(doc: VaultDocument) -> ObjectEnvelope:
    """Return an Object Envelope for a VaultDocument produced by the upload flow.

    The envelope carries enough metadata for Layer 2 explanation retrieval and
    Familiarity Tapering without exposing document content.
    """
    return ObjectEnvelope(
        object_id=doc.vault_id,
        object_type=ObjectType.MODULE_OUTPUT,
        pillar=Pillar.RECORD,
        who=Who.TENANT,
        why=f"A '{doc.document_type or 'document'}' stored in the tenant's vault.",
        provenance=Provenance.USER_ENTERED,
        temporal_validity=TemporalValidity.TIME_BOUND,
        subject_tags=_subject_tags_for(doc),
    )


def _subject_tags_for(doc: VaultDocument) -> list[str]:
    """Derive subject tags from the document metadata for Layer 2 matching."""
    tags = ["vault", "document"]
    if doc.document_type:
        tags.append(doc.document_type)
    if doc.source_module:
        tags.append(doc.source_module)
    return tags


async def get_vault_upload_page(context: EncounterContext | None = None) -> PageEnvelope:
    """Return the Vault upload Page Envelope resolved for this encounter."""
    if context is None:
        context = EncounterContext()
    return resolve_page_actions(VAULT_UPLOAD_PAGE, context)


__all__ = [
    "VAULT_UPLOAD_PAGE",
    "vault_document_to_object_envelope",
    "get_vault_upload_page",
]
