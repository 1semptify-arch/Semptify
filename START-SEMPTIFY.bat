@echo off
:: ============================================================================
:: SEMPTIFY ONE-CLICK LAUNCHER
:: Double-click this file to start Semptify in Production/Secured Mode
:: ============================================================================

title Semptify v5.0 - Production
color 0B

:: Change to script directory
cd /d "%~dp0"

echo.
echo ================================================================
echo       SEMPTIFY - Tenant Rights Platform
echo       Starting Production Server...
echo ================================================================
echo.

:: Launch PowerShell script
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "START.ps1"

pause
