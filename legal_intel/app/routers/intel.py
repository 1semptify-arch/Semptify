# app/routers/intel.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Attorney, Entity
from ..schemas import PatternSummary
from ..services.patterns import compute_attorney_patterns, compute_entity_patterns, detect_shell_llc_clusters

router = APIRouter(prefix="/intel", tags=["intel"])


@router.get("/attorney/by-bar/{bar_number}")
async def get_attorney_by_bar(bar_number: str, db: AsyncSession = Depends(get_db)):
    """Get attorney ID by bar number."""
    result = await db.execute(Attorney.__table__.select().where(Attorney.bar_number == bar_number))
    attorney = result.scalar_one_or_none()
    if not attorney:
        raise HTTPException(status_code=404, detail="Attorney not found")

    return {
        "id": attorney.id,
        "name": attorney.name,
        "bar_number": attorney.bar_number,
        "state": attorney.state,
    }


@router.get("/entity/by-name/{entity_name}")
async def get_entity_by_name(entity_name: str, db: AsyncSession = Depends(get_db)):
    """Get entity ID by name."""
    result = await db.execute(Entity.__table__.select().where(Entity.name == entity_name))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {
        "id": entity.id,
        "name": entity.name,
        "type": entity.type,
        "sos_id": entity.sos_id,
    }


@router.get("/patterns/attorney/{attorney_id}", response_model=PatternSummary)
async def get_attorney_patterns(attorney_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(Attorney.__table__.select().where(Attorney.id == attorney_id))
    attorney = result.scalar_one_or_none()
    if not attorney:
        raise HTTPException(status_code=404, detail="Attorney not found")

    return await compute_attorney_patterns(db, attorney_id)


@router.get("/patterns/entity/{entity_id}")
async def get_entity_patterns(entity_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(Entity.__table__.select().where(Entity.id == entity_id))
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return await compute_entity_patterns(db, entity_id)


@router.get("/clusters/shell-llcs")
async def get_shell_llc_clusters(db: AsyncSession = Depends(get_db)):
    """
    Detect potential shell LLC clusters based on shared registered agents and addresses.
    """
    return await detect_shell_llc_clusters(db)
