"""FEMS file ingestion — deduplication, classification, text extraction."""
import hashlib
import logging
import re
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fems.config import FEMS_QUARANTINE_DIR
from app.modules.fems.models import (
    FemsChunk,
    FemsDocument,
    FemsDocumentPhone,
    FemsPhoneNumber,
    FemsQuarantineFile,
)

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(
    r"(\+?1[\s\-.]?)?(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})"
)


def compute_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".txt":
            return file_path.read_text(errors="ignore")
        elif suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                return "\n".join(p.extract_text() or "" for p in reader.pages)
            except Exception as e:
                logger.warning("PDF extraction failed for %s: %s", file_path.name, e)
                return ""
        elif suffix in (".jpg", ".jpeg", ".png", ".tiff", ".bmp"):
            try:
                import pytesseract
                from PIL import Image
                return pytesseract.image_to_string(Image.open(str(file_path)))
            except Exception as e:
                logger.warning("OCR failed for %s: %s", file_path.name, e)
                return ""
        elif suffix == ".eml":
            try:
                import email
                msg = email.message_from_bytes(file_path.read_bytes())
                parts = []
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            parts.append(part.get_payload(decode=True).decode(errors="ignore"))
                else:
                    parts.append(msg.get_payload(decode=True).decode(errors="ignore"))
                return "\n".join(parts)
            except Exception as e:
                logger.warning("Email extraction failed for %s: %s", file_path.name, e)
                return ""
    except Exception as e:
        logger.warning("Text extraction error for %s: %s", file_path.name, e)
    return ""


def extract_phone_numbers(text: str) -> list[str]:
    found = set()
    for match in PHONE_RE.finditer(text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) in (10, 11):
            found.add(digits)
    return list(found)


def chunk_text(text: str, size: int = 1000) -> list[str]:
    words = text.split()
    chunks, current, current_len = [], [], 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= size:
            chunks.append(" ".join(current))
            current, current_len = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


async def ingest_file(file_path: Path, case_id: int | None, db: AsyncSession) -> dict:
    """Ingest a single file: dedup, extract text, store chunks, extract phones."""
    file_hash = compute_hash(file_path)

    # Check for duplicate
    existing = (await db.execute(
        select(FemsDocument).where(FemsDocument.file_hash == file_hash)
    )).scalar_one_or_none()

    if existing:
        FEMS_QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        dest = FEMS_QUARANTINE_DIR / file_path.name
        shutil.move(str(file_path), str(dest))
        q = FemsQuarantineFile(
            filename=file_path.name,
            file_hash=file_hash,
            file_size=dest.stat().st_size,
            reason="duplicate",
        )
        db.add(q)
        await db.commit()
        return {"status": "duplicate", "file": file_path.name, "original_id": existing.id}

    # Extract text
    text = extract_text(file_path)

    doc = FemsDocument(
        case_id=case_id,
        filename=file_path.name,
        file_type=file_path.suffix.lower().lstrip("."),
        file_hash=file_hash,
        file_size=file_path.stat().st_size,
        extracted_text=text,
    )
    db.add(doc)
    await db.flush()

    # Store text chunks
    for i, chunk_content in enumerate(chunk_text(text)):
        db.add(FemsChunk(document_id=doc.id, chunk_index=i, content=chunk_content))

    # Extract and link phone numbers
    phone_numbers = extract_phone_numbers(text)
    for number in phone_numbers:
        phone = (await db.execute(
            select(FemsPhoneNumber).where(FemsPhoneNumber.number == number)
        )).scalar_one_or_none()

        if not phone:
            phone = FemsPhoneNumber(number=number)
            db.add(phone)
            await db.flush()

        db.add(FemsDocumentPhone(document_id=doc.id, phone_id=phone.id))

    await db.commit()
    return {
        "status": "ingested",
        "file": file_path.name,
        "doc_id": doc.id,
        "phones_found": len(phone_numbers),
        "chunks": len(chunk_text(text)),
    }
