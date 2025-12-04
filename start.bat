@echo off
REM ============================================================
REM 🚀 SEMPTIFY ONE-BUTTON START (Windows Batch)
REM ============================================================
REM Double-click this file to start Semptify
REM ============================================================

title Semptify v5.0.0

echo.
echo ============================================================
echo   🚀 SEMPTIFY FASTAPI - LOCAL PRODUCTION MODE
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo    Run: python -m venv .venv
    echo    Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo 📦 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Set production environment variables
echo ⚙️  Setting production mode...
set SECURITY_MODE=enforced
set DEBUG=false
set LOG_LEVEL=INFO

echo.
echo ============================================================
echo   🌐 Starting Semptify Server...
echo ============================================================
echo.
echo   📍 App:       http://localhost:8000
echo   🎛️  Command:   http://localhost:8000/static/command_center.html
echo   📊 Dashboard: http://localhost:8000/static/dashboard.html
echo   📚 API Docs:  http://localhost:8000/docs
echo   ⚖️  Eviction:  http://localhost:8000/eviction/
echo.
echo   Press Ctrl+C to stop the server
echo.

REM Open Command Center after delay
start /b cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000/static/command_center.html"

REM Start the server (stable mode)
python run_server.py
