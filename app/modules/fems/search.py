"""FEMS search — full-text search across documents, chunks, and phone numbers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fems.models import (
    FemsChunk,
    FemsDocument,
    FemsDocumentPhone,
    FemsPhoneNumber,
)


async def search_evidence(keywords: str, db: AsyncSession) -> list[dict]:
    """Search documents and chunks for keywords."""
    results = []
    kw = f"%{keywords}%"

    docs = (await db.execute(select(FemsDocument).where(FemsDocument.extracted_text.ilike(kw)))).scalars().all()

    for doc in docs:
        results.append(
            {
                "type": "document",
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "snippet": (doc.extracted_text or "")[:300],
                "ingested_at": str(doc.ingested_at),
            }
        )

    chunks = (await db.execute(select(FemsChunk).where(FemsChunk.content.ilike(kw)))).scalars().all()

    seen_docs = {r["id"] for r in results}
    for chunk in chunks:
        if chunk.document_id not in seen_docs:
            results.append(
                {
                    "type": "chunk",
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "snippet": chunk.content[:300],
                }
            )

    return results


async def search_by_phone(number: str, db: AsyncSession) -> list[dict]:
    """Find all documents linked to a phone number."""
    phone = (
        (await db.execute(select(FemsPhoneNumber).where(FemsPhoneNumber.number.ilike(f"%{number}%")))).scalars().all()
    )

    results = []
    for p in phone:
        links = (await db.execute(select(FemsDocumentPhone).where(FemsDocumentPhone.phone_id == p.id))).scalars().all()

        for link in links:
            doc = (
                await db.execute(select(FemsDocument).where(FemsDocument.id == link.document_id))
            ).scalar_one_or_none()

            if doc:
                results.append(
                    {
                        "phone_number": p.number,
                        "document_id": doc.id,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "ingested_at": str(doc.ingested_at),
                    }
                )

    return results
