# app/main.py
from fastapi import FastAPI

from .db import Base, engine
from .routers import crawl, intel

app = FastAPI(title="Semptify Legal Intel")


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(crawl.router)
app.include_router(intel.router)
