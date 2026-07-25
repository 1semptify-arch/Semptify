#Requires -Version 5.1
<#
.SYNOPSIS
    Start the Funding Forge standalone app.
.DESCRIPTION
    Uses the Semptify venv311 environment. Generates a workspace key if none is set.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Test-Path "$RepoRoot\venv311")) {
    Write-Host "venv311 not found. Run: python -m venv venv311  (Python 3.11.9 required)" -ForegroundColor Red
    exit 1
}

if (-not $env:FUNDING_FORGE_KEY) {
    $generated = [Guid]::NewGuid().ToString("N")
    $env:FUNDING_FORGE_KEY = $generated
    Write-Host "Generated workspace key: $generated" -ForegroundColor Cyan
    Write-Host "Set FUNDING_FORGE_KEY in your environment to reuse this key."
}

if (-not $env:APP_HOST) { $env:APP_HOST = "127.0.0.1" }
if (-not $env:APP_PORT) { $env:APP_PORT = "8001" }

& "$RepoRoot\venv311\Scripts\python.exe" -m uvicorn funding_forge.main:app `
    --host $env:APP_HOST `
    --port $env:APP_PORT `
    --reload
