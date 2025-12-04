# ============================================================
# 🚀 SEMPTIFY ONE-BUTTON START
# ============================================================
# Run this script to start Semptify in production mode locally
# Usage: .\start.ps1
# ============================================================

$Host.UI.RawUI.WindowTitle = "Semptify v5.0.0"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🚀 SEMPTIFY FASTAPI - LOCAL PRODUCTION MODE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if virtual environment exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "   Then: .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Set production environment variables
Write-Host "⚙️  Setting production mode..." -ForegroundColor Yellow
$env:SECURITY_MODE = "enforced"
$env:DEBUG = "false"
$env:LOG_LEVEL = "INFO"

# Check if .env exists
if (Test-Path ".\.env") {
    Write-Host "✅ Loading .env configuration" -ForegroundColor Green
} else {
    Write-Host "⚠️  No .env file found - using defaults" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  🌐 Starting Semptify Server..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  📍 App:      http://localhost:8000" -ForegroundColor White
Write-Host "  🎛️  Command:  http://localhost:8000/static/command_center.html" -ForegroundColor Cyan
Write-Host "  📊 Dashboard: http://localhost:8000/static/dashboard.html" -ForegroundColor White
Write-Host "  📚 API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  ⚖️  Eviction: http://localhost:8000/eviction/" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor DarkGray
Write-Host ""

# Open Command Center after 2 second delay (in background)
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000/static/command_center.html"
} | Out-Null

# Start the server (stable mode - no reload)
python run_server.py
