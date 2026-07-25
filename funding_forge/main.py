"""Funding Forge FastAPI entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from funding_forge.api import api_router
from funding_forge.auth import (
    admin_auth_enabled,
    admin_dependency,
    create_admin_token,
    get_admin_token_from_request,
    verify_admin_credentials,
    verify_admin_token,
)
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


@app.get("/api/health")
async def health():
    """Public health check used by startup probes."""
    return {"status": "healthy", "module": "funding_forge", "version": "1.0.0"}


@app.middleware("http")
async def admin_gate(request: Request, call_next):
    """Require admin authentication for all pages and API calls."""
    path = request.url.path
    if not admin_auth_enabled():
        return await call_next(request)
    if path.startswith("/static/") or path in {"/login", "/logout", "/favicon.ico", "/api/health"}:
        return await call_next(request)

    token = get_admin_token_from_request(request)
    if verify_admin_token(token):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Admin authentication required"}, status_code=401)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page app shell."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"auth_enabled": admin_auth_enabled()},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    """Serve the admin login page."""
    if admin_auth_enabled() and verify_admin_token(get_admin_token_from_request(request)):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str = Form(""),
):
    """Validate admin credentials and set a session cookie."""
    if verify_admin_credentials(username, password, totp_code or None):
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            "funding_forge_admin",
            value=create_admin_token(),
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@app.get("/logout")
async def logout():
    """Clear the admin session cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("funding_forge_admin", path="/")
    return response


@app.get("/api/admin/me")
async def admin_me(_: bool = Depends(admin_dependency)):
    """Return the current admin session status."""
    return {"admin": True}
