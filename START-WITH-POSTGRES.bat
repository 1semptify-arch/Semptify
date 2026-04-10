@echo off
:: ============================================================================
:: SEMPTIFY WITH POSTGRESQL - ONE-CLICK START
:: ============================================================================
:: This script starts PostgreSQL and the Semptify app
:: Double-click to run
:: ============================================================================

title Semptify v5.0 - PostgreSQL + App

color 0B
cd /d "%~dp0"

echo.
echo ============================================================================
echo   SEMPTIFY - PostgreSQL + FastAPI Server
echo ============================================================================
echo.

:: Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo SETUP REQUIRED:
    echo   1. python -m venv .venv
    echo   2. .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Step 1: Start local PostgreSQL service (no Docker)
echo [1/3] Starting local PostgreSQL service...
set "PG_SERVICE=postgresql-x64-16"
sc query "%PG_SERVICE%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PostgreSQL Windows service "%PG_SERVICE%" was not found.
    echo.
    echo SETUP REQUIRED:
    echo   1. Install PostgreSQL for Windows
    echo   2. Ensure service name is "%PG_SERVICE%" or update this file
    echo.
    pause
    exit /b 1
)

sc query "%PG_SERVICE%" | findstr /i "RUNNING" >nul
if errorlevel 1 (
    echo   Starting service: %PG_SERVICE%
    net start "%PG_SERVICE%" >nul
) else (
    echo   PostgreSQL service is already running
)

:: Verify PostgreSQL is listening on 5432
echo   Waiting for PostgreSQL on localhost:5432...
for /l %%i in (1,1,30) do (
    netstat -ano | findstr ":5432" | findstr "LISTENING" >nul
    if not errorlevel 1 (
        echo   [OK] PostgreSQL is ready on port 5432
        goto PG_OK
    )
    timeout /t 1 /nobreak >nul
)
echo   ERROR: PostgreSQL did not come online on port 5432
pause
exit /b 1
:PG_OK

:: Step 2: Activate virtual environment
echo.
echo [2/3] Setting up Python environment...
call .venv\Scripts\activate.bat

:: Step 3: Start Semptify server
echo.
echo [3/3] Starting Semptify server...
echo.
echo   ============================================================================
echo   Server starting at: http://localhost:8000
echo   ============================================================================
echo   - App:      http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - Database: semptify @ localhost:5432
echo.
echo   Press CTRL+C to stop
echo   ============================================================================
echo.

set SECURITY_MODE=enforced
set DEBUG=false
set PYTHONIOENCODING=utf-8
set DATABASE_URL=postgresql+asyncpg://semptify:semptify@localhost:5432/semptify

.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info

pause
