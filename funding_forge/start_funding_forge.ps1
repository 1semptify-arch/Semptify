#Requires -Version 5.1
<#
.SYNOPSIS
    Start the Funding Forge standalone app.
.DESCRIPTION
    Uses the Semptify venv311 environment. If admin credentials are not set,
    generates a random admin password. This tool is admin-only and can use
    Cloudflare R2 for persistent document storage.
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

if (-not (Test-Path "$RepoRoot\venv311")) {
    Write-Host "venv311 not found. Run: python -m venv venv311  (Python 3.11.9 required)" -ForegroundColor Red
    exit 1
}

if (-not $env:FUNDING_FORGE_ADMIN_USERNAME) {
    $env:FUNDING_FORGE_ADMIN_USERNAME = "admin"
}
if (-not $env:ADMIN_USERNAME) {
    $env:ADMIN_USERNAME = $env:FUNDING_FORGE_ADMIN_USERNAME
}

if (-not $env:FUNDING_FORGE_ADMIN_PASSWORD -and -not $env:ADMIN_PASSWORD) {
    $generated = -join ((1..24) | ForEach-Object { "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"[(Get-Random -Maximum 56)] })  # pragma: allowlist secret
    $env:FUNDING_FORGE_ADMIN_PASSWORD = $generated
    $env:ADMIN_PASSWORD = $generated
    Write-Host "Generated admin password: $generated" -ForegroundColor Cyan
    Write-Host "Set FUNDING_FORGE_ADMIN_PASSWORD in your environment to reuse this password."
}

if (-not $env:APP_HOST) { $env:APP_HOST = "127.0.0.1" }
if (-not $env:APP_PORT) { $env:APP_PORT = "8001" }

& "$RepoRoot\venv311\Scripts\python.exe" -m uvicorn funding_forge.main:app `
    --host $env:APP_HOST `
    --port $env:APP_PORT `
    --reload
