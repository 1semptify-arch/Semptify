# start_local_dev.ps1 — "Brad start": launch Semptify locally on the
# minimal local_dev runtime load profile with zero typing beyond running
# this script.
#
# Sets DEPLOY_TARGET=local. This is self-documenting only: runtime_profile.py
# treats any value other than "render_mvp" as local dev (see the reasoning
# comment at the top of app/core/runtime_profile.py), so "local" is not a
# new value read anywhere else in the codebase - it just makes intent
# visible in the process environment and in the startup log line
# ("Runtime Load Profile: local_dev").
#
# To test semantic search locally without the rest of the heavy stack:
#   $env:LOAD_PROFILE = "local_dev_semantic"; .\scripts\start_local_dev.ps1
# To force the full stack on locally for diagnosis:
#   $env:LOAD_PROFILE = "full"; .\scripts\start_local_dev.ps1
# Legacy emergency-rollback switch (still honored, forces everything off):
#   $env:ENABLE_HEAVY_SERVICES = "false"; .\scripts\start_local_dev.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:DEPLOY_TARGET = "local"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SEMPTIFY - local_dev profile" -ForegroundColor Cyan
Write-Host "  (heavy infra services off - see app/core/runtime_profile.py)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

& "$RepoRoot\venv311\Scripts\python.exe" -m uvicorn app.main:fastapi_app --host 127.0.0.1 --port 8001 --reload
