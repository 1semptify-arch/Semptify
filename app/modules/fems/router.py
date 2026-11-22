"""FEMS FastAPI router — Forensic Evidence Management System."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import auth_gate
from app.core.user_context import UserContext
from app.modules.fems.config import FEMS_INBOX_DIR, FEMS_MAX_UPLOAD_BYTES, ensure_dirs
from app.modules.fems.ingest import ingest_file
from app.modules.fems.models import (
    FemsCase,
    FemsChunk,
    FemsDocument,
    FemsDocumentPhone,
    FemsPhoneNumber,
    FemsQuarantineFile,
)
from app.modules.fems.search import search_by_phone, search_evidence

router = APIRouter(prefix="/api/fems", tags=["FEMS"])


@router.get("/health")
async def fems_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(func.count()).select_from(FemsDocument))
        return {"status": "healthy", "module": "FEMS", "version": "1.0.0"}
    except Exception as e:
        return {"status": "error", "module": "FEMS", "error": str(e)}


@router.get("/stats")
async def fems_stats(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    owner = FemsDocument.owner_user_id == user.user_id
    doc_count = (await db.execute(select(func.count()).select_from(FemsDocument).where(owner))).scalar()
    chunk_count = (
        await db.execute(
            select(func.count())
            .select_from(FemsChunk)
            .join(FemsDocument, FemsChunk.document_id == FemsDocument.id)
            .where(owner)
        )
    ).scalar()
    phone_count = (
        await db.execute(
            select(func.count(func.distinct(FemsDocumentPhone.phone_id)))
            .select_from(FemsDocumentPhone)
            .join(FemsDocument, FemsDocumentPhone.document_id == FemsDocument.id)
            .where(owner)
        )
    ).scalar()
    quarantine_count = (
        await db.execute(
            select(func.count()).select_from(FemsQuarantineFile).where(FemsQuarantineFile.owner_user_id == user.user_id)
        )
    ).scalar()
    case_count = (
        await db.execute(select(func.count()).select_from(FemsCase).where(FemsCase.owner_user_id == user.user_id))
    ).scalar()
    return {
        "cases": case_count,
        "documents": doc_count,
        "chunks": chunk_count,
        "phone_numbers": phone_count,
        "quarantined": quarantine_count,
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    ensure_dirs()

    raw_name = Path(file.filename or "").name
    if not raw_name or raw_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    dest = (FEMS_INBOX_DIR / raw_name).resolve()
    if not dest.is_relative_to(FEMS_INBOX_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if case_id is not None:
        case = (
            await db.execute(
                select(FemsCase).where(FemsCase.id == case_id, FemsCase.owner_user_id == user.user_id)
            )
        ).scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    size = 0
    try:
        with open(dest, "wb") as f:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > FEMS_MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large")
                f.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    result = await ingest_file(dest, case_id, db, user.user_id)
    return result


@router.get("/search")
async def search(
    q: str | None = None,
    phone: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    if not q and not phone:
        raise HTTPException(status_code=400, detail="Provide 'q' (keywords) or 'phone' parameter")
    results = []
    if q:
        results += await search_evidence(q, db, user.user_id)
    if phone:
        results += await search_by_phone(phone, db, user.user_id)
    return {"count": len(results), "results": results}


@router.get("/documents")
async def list_documents(
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    query = select(FemsDocument).where(FemsDocument.owner_user_id == user.user_id)
    query = query.order_by(FemsDocument.ingested_at.desc())
    if case_id:
        query = query.where(FemsDocument.case_id == case_id)
    docs = (await db.execute(query)).scalars().all()
    return [
        {
            "id": d.id,
            "case_id": d.case_id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "ingested_at": str(d.ingested_at),
        }
        for d in docs
    ]


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    doc = (
        await db.execute(
            select(FemsDocument).where(FemsDocument.id == doc_id, FemsDocument.owner_user_id == user.user_id)
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "case_id": doc.case_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "file_hash": doc.file_hash,
        "extracted_text": doc.extracted_text,
        "ingested_at": str(doc.ingested_at),
    }


@router.get("/phones")
async def list_phones(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    phones = (
        (
            await db.execute(
                select(FemsPhoneNumber)
                .join(FemsDocumentPhone, FemsDocumentPhone.phone_id == FemsPhoneNumber.id)
                .join(FemsDocument, FemsDocumentPhone.document_id == FemsDocument.id)
                .where(FemsDocument.owner_user_id == user.user_id)
                .distinct()
                .order_by(FemsPhoneNumber.first_seen.desc())
            )
        )
        .scalars()
        .all()
    )
    return [{"id": p.id, "number": p.number, "label": p.label, "first_seen": str(p.first_seen)} for p in phones]


@router.get("/quarantine")
async def list_quarantine(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    files = (
        (
            await db.execute(
                select(FemsQuarantineFile)
                .where(FemsQuarantineFile.owner_user_id == user.user_id)
                .order_by(FemsQuarantineFile.quarantined_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "file_size": f.file_size,
            "reason": f.reason,
            "quarantined_at": str(f.quarantined_at),
        }
        for f in files
    ]


@router.get("/cases")
async def list_cases(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    cases = (
        (
            await db.execute(
                select(FemsCase).where(FemsCase.owner_user_id == user.user_id).order_by(FemsCase.opened_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": c.id,
            "case_number": c.case_number,
            "title": c.title,
            "status": c.status,
            "opened_at": str(c.opened_at),
        }
        for c in cases
    ]


@router.post("/cases")
async def create_case(
    case_number: str,
    title: str = "",
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(auth_gate),
):
    existing = (await db.execute(select(FemsCase).where(FemsCase.case_number == case_number))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Case {case_number} already exists")
    case = FemsCase(case_number=case_number, title=title, owner_user_id=user.user_id)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return {"id": case.id, "case_number": case.case_number, "title": case.title}
