# ============================================================
# SEMPTIFY PRODUCTION START
# ============================================================
# One-click production launch with full GUI access
# Usage: Right-click - Run with PowerShell
#    or: .\START.ps1
# ============================================================

param(
    [switch]$NoBrowser,
    [switch]$Development
)

# Set window title
$Host.UI.RawUI.WindowTitle = "Semptify v5.0 - Production"

# Colors
function Write-Banner { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "   $msg" -ForegroundColor White }

Clear-Host

Write-Host ""
Write-Banner "============================================================"
Write-Banner "       SEMPTIFY - Tenant Rights Platform"
Write-Banner "           Production Server Launch"
Write-Banner "============================================================"
Write-Host ""

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Success "Working directory: $ScriptDir"

# ============================================================
# STEP 1: Check Python
# ============================================================
Write-Host ""
Write-Host "Checking Prerequisites..." -ForegroundColor Yellow
Write-Host ""

$pythonPath = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Err "Virtual environment not found at .venv\"
    Write-Info "Creating virtual environment..."
    python -m venv .venv
    if (-not (Test-Path $pythonPath)) {
        Write-Err "Failed to create virtual environment!"
        Write-Info "Make sure Python 3.10+ is installed"
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Success "Virtual environment created"
    
    Write-Info "Installing dependencies..."
    $pipPath = Join-Path $ScriptDir ".venv\Scripts\pip.exe"
    & $pipPath install -r requirements.txt
}
Write-Success "Python environment: .venv"

# Check Python version
$pyVersion = & $pythonPath --version 2>&1
Write-Success "Python version: $pyVersion"

# ============================================================
# STEP 2: Check .env Configuration
# ============================================================
Write-Host ""
$envPath = Join-Path $ScriptDir ".env"
if (Test-Path $envPath) {
    Write-Success "Configuration: .env loaded"
    
    # Read security mode from .env
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "SECURITY_MODE=(\w+)") {
        $securityMode = $Matches[1]
        Write-Success "Security Mode: $($securityMode.ToUpper())"
    }
} else {
    Write-Warn "No .env file found - using defaults"
    $securityMode = "enforced"
}

# Security is always enforced
$env:SECURITY_MODE = "enforced"
$env:ENFORCE_SECURITY = "true"
$env:ENVIRONMENT = "production"
if ($Development) {
    $env:DEBUG = "true"
    Write-Warn "Development mode enabled (debug=true)"
} else {
    $env:DEBUG = "false"
}

# ============================================================
# STEP 3: Kill any existing Semptify processes
# ============================================================
Write-Host ""
Write-Host "Checking for existing processes..." -ForegroundColor Yellow

$existingProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -match "uvicorn|semptify|8000" }

if ($existingProcesses) {
    Write-Warn "Found existing server process(es) - stopping..."
    $existingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Success "Existing processes stopped"
} else {
    Write-Success "No existing processes found"
}

# ============================================================
# STEP 4: Check Database
# ============================================================
Write-Host ""
Write-Host "Checking Database..." -ForegroundColor Yellow

# Try PostgreSQL first, fall back to SQLite
$dbFile = Join-Path $ScriptDir "semptify.db"
if (Test-Path $dbFile) {
    $dbSizeBytes = (Get-Item $dbFile).Length
    $dbSizeKB = [math]::Round($dbSizeBytes / 1024, 2)
    Write-Success "SQLite database: semptify.db ($dbSizeKB KB)"
} else {
    Write-Info "No local database - will be created on first run"
}

# ============================================================
# STEP 5: Display Access URLs
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "                    ACCESS POINTS                           " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  COMMAND CENTER (Main GUI)" -ForegroundColor Green
Write-Host "      http://localhost:8000/static/command_center.html" -ForegroundColor White
Write-Host ""
Write-Host "  Dashboard       -> /static/dashboard.html" -ForegroundColor White
Write-Host "  Document Intake -> /static/document_intake.html" -ForegroundColor White
Write-Host "  Timeline        -> /static/timeline.html" -ForegroundColor White
Write-Host "  Calendar        -> /static/calendar.html" -ForegroundColor White
Write-Host "  AI Brain        -> /static/brain.html" -ForegroundColor White
Write-Host "  Eviction        -> /eviction/" -ForegroundColor White
Write-Host "  Legal Analysis  -> /static/legal_analysis.html" -ForegroundColor White
Write-Host "  Mesh Network    -> /static/mesh_network.html" -ForegroundColor White
Write-Host ""
Write-Host "  API Docs        -> /docs" -ForegroundColor White
Write-Host "  API Schema      -> /openapi.json" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 6: Open Browser (unless disabled)
# ============================================================
if (-not $NoBrowser) {
    Write-Host "Opening Command Center in browser..." -ForegroundColor Cyan
    Start-Job -ScriptBlock {
        Start-Sleep -Seconds 3
        Start-Process "http://localhost:8000/static/command_center.html"
    } | Out-Null
}

# ============================================================
# STEP 7: Start the Server
# ============================================================
Write-Host ""
Write-Host "Starting Semptify Server..." -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray

# Activate venv and run
$activatePath = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
& $activatePath

# Start uvicorn directly for better control
& $pythonPath -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info

# If server exits, show message
Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host ""
Write-Err "Server stopped"
Write-Host ""
Read-Host "Press Enter to exit"

