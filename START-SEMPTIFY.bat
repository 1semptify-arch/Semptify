@echo off
:: ============================================================================
:: SEMPTIFY ONE-CLICK LAUNCHER
:: Double-click this file to start Semptify in Production/Secured Mode
:: ============================================================================

title Semptify v5.0 - Production
color 0A

:: Change to script directory
cd /d "%~dp0"

:: Launch the production launcher (Docker + DB + Security + Server)
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "LAUNCH-SEMPTIFY.ps1"

pause
