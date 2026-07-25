"""Funding Forge FastAPI entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from funding_forge.api import api_router
from funding_forge.config import settings
from funding_forge.crud import ensure_uploads_dir
from funding_forge.database import create_tables, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create database tables and uploads directory on startup."""
    await create_tables()
    ensure_uploads_dir()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="Funding Forge",
    description="Semptify funding and contact manager",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)
app.include_router(api_router)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.middleware("http")
async def workspace_key_gate(request: Request, call_next):
    """Require the configured workspace key for all pages and API calls."""
    path = request.url.path
    if not settings.auth_enabled:
        return await call_next(request)
    if path.startswith("/static/") or path in {"/unlock", "/favicon.ico", "/api/health"}:
        return await call_next(request)

    key = request.cookies.get("funding_forge_key") or request.headers.get("x-funding-forge-key")
    if key == settings.funding_forge_key:
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Workspace key required"}, status_code=401)
    return RedirectResponse(url="/unlock", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page app shell."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "key_required": settings.auth_enabled},
    )


@app.get("/unlock", response_class=HTMLResponse)
async def unlock_page(request: Request, error: str = ""):
    """Serve the workspace key entry page."""
    if settings.auth_enabled and request.cookies.get("funding_forge_key") == settings.funding_forge_key:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("unlock.html", {"request": request, "error": error})


@app.post("/unlock")
async def unlock(request: Request, key: str = Form(...)):
    """Validate the workspace key and set a session cookie."""
    if key == settings.funding_forge_key:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            "funding_forge_key",
            value=key,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response
    return templates.TemplateResponse(
        "unlock.html",
        {"request": request, "error": "Invalid workspace key"},
        status_code=401,
    )
