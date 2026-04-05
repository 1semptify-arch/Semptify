@echo off
title Semptify - Tenant Defense System
color 0A

echo.
echo  ============================================================
echo.
echo    ███████╗███████╗███╗   ███╗██████╗ ████████╗██╗███████╗
echo    ██╔════╝██╔════╝████╗ ████║██╔══██╗╚══██╔══╝██║██╔════╝
echo    ███████╗█████╗  ██╔████╔██║██████╔╝   ██║   ██║█████╗  
echo    ╚════██║██╔══╝  ██║╚██╔╝██║██╔═══╝    ██║   ██║██╔══╝  
echo    ███████║███████╗██║ ╚═╝ ██║██║        ██║   ██║██║     
echo    ╚══════╝╚══════╝╚═╝     ╚═╝╚═╝        ╚═╝   ╚═╝╚═╝     
echo.
echo              Tenant Defense System v5.0
echo.
echo  ============================================================
echo.

cd /d "%~dp0"

:: Check if .venv exists
if not exist ".venv\Scripts\python.exe" (
    echo  [!] Python environment not found. Setting up...
    python -m venv .venv
    .venv\Scripts\pip.exe install -r requirements.txt
)

echo  [*] Starting Semptify...
echo  [*] Browser will open automatically in 3 seconds...
echo.
echo  Press Ctrl+C to stop the server
echo.

REM Fix Unicode encoding for emoji and special characters in logs
set PYTHONIOENCODING=utf-8

:: Start browser after delay
start /b cmd /c "timeout /t 3 >nul && start http://localhost:8000/static/welcome.html"

:: Run the server
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
