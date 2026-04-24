@echo off
:: ============================================================================
:: SEMPTIFY WITH POSTGRESQL - DEPRECATED
:: ============================================================================
:: This script is kept for backwards compatibility.
:: It now calls the SINGLE SOURCE OF TRUTH launcher:
::   start-semptify.ps1 -WithPostgres
::
:: For new deployments, use: .\start-semptify.ps1 -WithPostgres
:: ============================================================================

title Semptify v5.0 - PostgreSQL + App

color 0B
echo.
echo [DEPRECATED] This launcher calls the canonical SSOT script.
echo.

:: Pass through critical environment variables
if not defined SECRET_KEY (
    echo [WARN] SECRET_KEY not set - will auto-generate
)
if not defined PYTHONIOENCODING (
    set PYTHONIOENCODING=utf-8
)

:: Launch via SSOT with PostgreSQL
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "start-semptify.ps1" -WithPostgres

pause
