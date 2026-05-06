# Environment Switcher for Semptify
# Usage: .\switch_env.ps1 [local|production]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("local", "production")]
    [string]$Environment
)

if ($Environment -eq "local") {
    $source = ".env.local"
    if (-not (Test-Path $source)) {
        Write-Host "ERROR: $source not found. Aborting." -ForegroundColor Red
        exit 1
    }
    Write-Host "Switching to LOCAL development environment..." -ForegroundColor Green
    if (Test-Path ".env") { Copy-Item .env ".env.backup" -Force }
    Copy-Item $source .env -Force
    Write-Host "Local config active. Database: SQLite" -ForegroundColor Yellow
    Write-Host "Run: python -m uvicorn app.main:app --reload" -ForegroundColor Cyan
}
elseif ($Environment -eq "production") {
    $source = ".env.production"
    if (-not (Test-Path $source)) {
        Write-Host "ERROR: $source not found. Aborting." -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "WARNING: This will overwrite .env with PRODUCTION credentials." -ForegroundColor Red
    Write-Host "         Your local server will connect to the live database." -ForegroundColor Red
    Write-Host ""
    $confirm = Read-Host "Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }
    if (Test-Path ".env") { Copy-Item .env ".env.backup" -Force }
    Copy-Item $source .env -Force
    Write-Host "Production config active. Database: Neon PostgreSQL" -ForegroundColor Yellow
    Write-Host "Deploy: git push render main" -ForegroundColor Cyan
}

Write-Host "Done. Previous .env backed up to .env.backup. Restart your server to apply changes." -ForegroundColor Green
