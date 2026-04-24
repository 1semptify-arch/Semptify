@echo off
:: ============================================================================
:: SEMPTIFY ONE-CLICK LAUNCHER
:: DOUBLE-CLICK THIS FILE to start Semptify in Production Mode
::
:: This calls the SINGLE SOURCE OF TRUTH launcher:
::   start-semptify.ps1
::
:: For development mode, run: .\start-semptify.ps1 -DevMode
:: ============================================================================

title Semptify v5.0 - Production
color 0A

:: Change to script directory
cd /d "%~dp0"

:: Launch via the canonical SSOT launcher
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "start-semptify.ps1"

pause
