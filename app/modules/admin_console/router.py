from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/panel", response_class=HTMLResponse)
def admin_panel():
    with open("app/modules/admin_console/ui/panel.html", "r", encoding="utf-8") as f:
        return f.read()

@router.get("/health")
def health_check():
    return {"status": "admin console online"}
