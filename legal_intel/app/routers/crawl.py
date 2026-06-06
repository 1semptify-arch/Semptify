# app/routers/crawl.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..services.unified_crawler import crawl_attorney_full, upsert_entity
from ..crawlers import sos
from ..models import Entity

router = APIRouter(prefix="/crawl", tags=["crawl"])

_thread_pool = ThreadPoolExecutor(max_workers=4)


def _run_sos_in_thread(entity_name: str, state: str):
    """
    Playwright must run in its own thread with a fresh event loop on Windows.
    uvicorn's event loop does not support subprocess creation (NotImplementedError).
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(sos.fetch_entity_from_sos(entity_name, state=state))
    finally:
        loop.close()


@router.post("/attorney/{bar_number}")
async def crawl_attorney_endpoint(
    bar_number: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(crawl_attorney_full, db, bar_number)
    return {"status": "started", "bar_number": bar_number}


@router.post("/entity/{entity_name}")
async def crawl_entity_endpoint(
    entity_name: str,
    state: str = "MN",
    db: AsyncSession = Depends(get_db),
):
    """
    Crawl entity information from Secretary of State.
    Playwright is run in a dedicated thread to avoid Windows asyncio subprocess restrictions.
    """
    try:
        loop = asyncio.get_event_loop()
        entity_data = await loop.run_in_executor(
            _thread_pool, _run_sos_in_thread, entity_name, state
        )
    except Exception as e:
        error_msg = str(e)
        if "ERR_CONNECTION_RESET" in error_msg or "net::" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot reach {state} SOS website. Try again in a moment."
            )
        raise HTTPException(status_code=500, detail=f"Crawl error: {error_msg}")

    if not entity_data:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found in {state} SOS")

    entity = await upsert_entity(db, entity_data)

    return {
        "status": "completed",
        "entity_id": entity.id if entity else None,
        "entity_name": entity_data.get("name"),
        "entity_type": entity_data.get("type"),
        "sos_id": entity_data.get("sos_id"),
        "address": entity_data.get("address"),
        "registered_agent": entity_data.get("registered_agent"),
        "filing_date": entity_data.get("filing_date"),
        "business_status": entity_data.get("status"),
    }
