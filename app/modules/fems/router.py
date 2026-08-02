"""FEMS FastAPI router — Forensic Evidence Management System."""

import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.fems.config import FEMS_INBOX_DIR, ensure_dirs
from app.modules.fems.ingest import ingest_file
from app.modules.fems.models import (
    FemsCase,
    FemsChunk,
    FemsDocument,
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
async def fems_stats(db: AsyncSession = Depends(get_db)):
    doc_count = (await db.execute(select(func.count()).select_from(FemsDocument))).scalar()
    chunk_count = (await db.execute(select(func.count()).select_from(FemsChunk))).scalar()
    phone_count = (await db.execute(select(func.count()).select_from(FemsPhoneNumber))).scalar()
    quarantine_count = (await db.execute(select(func.count()).select_from(FemsQuarantineFile))).scalar()
    case_count = (await db.execute(select(func.count()).select_from(FemsCase))).scalar()
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
):
    ensure_dirs()
    dest = FEMS_INBOX_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    result = await ingest_file(dest, case_id, db)
    return result


@router.get("/search")
async def search(
    q: str | None = None,
    phone: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not q and not phone:
        raise HTTPException(status_code=400, detail="Provide 'q' (keywords) or 'phone' parameter")
    results = []
    if q:
        results += await search_evidence(q, db)
    if phone:
        results += await search_by_phone(phone, db)
    return {"count": len(results), "results": results}


@router.get("/documents")
async def list_documents(
    case_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(FemsDocument).order_by(FemsDocument.ingested_at.desc())
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
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = (await db.execute(select(FemsDocument).where(FemsDocument.id == doc_id))).scalar_one_or_none()
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
async def list_phones(db: AsyncSession = Depends(get_db)):
    phones = (await db.execute(select(FemsPhoneNumber).order_by(FemsPhoneNumber.first_seen.desc()))).scalars().all()
    return [{"id": p.id, "number": p.number, "label": p.label, "first_seen": str(p.first_seen)} for p in phones]


@router.get("/quarantine")
async def list_quarantine(db: AsyncSession = Depends(get_db)):
    files = (
        (await db.execute(select(FemsQuarantineFile).order_by(FemsQuarantineFile.quarantined_at.desc())))
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
async def list_cases(db: AsyncSession = Depends(get_db)):
    cases = (await db.execute(select(FemsCase).order_by(FemsCase.opened_at.desc()))).scalars().all()
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
):
    existing = (await db.execute(select(FemsCase).where(FemsCase.case_number == case_number))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Case {case_number} already exists")
    case = FemsCase(case_number=case_number, title=title)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return {"id": case.id, "case_number": case.case_number, "title": case.title}
