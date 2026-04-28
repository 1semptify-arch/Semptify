# ====================================================================
#  SEMPTIFY 5.0 - SINGLE SOURCE OF TRUTH LAUNCHER
#  Canonical startup script for Semptify FastAPI application.
#
#  THIS IS THE ONLY SUPPORTED WAY TO START THE APPLICATION.
#  All other launchers must call this script.
#
#  Usage:
#    .\start-semptify.ps1              # Production mode (enforced security)
#    .\start-semptify.ps1 -DevMode     # Development mode (open security)
#
#  Environment:
#    - Python: venv311 (Python 3.11)
#    - Security: ENFORCED by default
#    - Database: SQLite (dev) or PostgreSQL (production with Docker)
# ====================================================================

[CmdletBinding()]
param(
    [switch]$DevMode,
    [switch]$WithPostgres,
    [switch]$WithDocker,
    [int]$Port = 8000,
    [string]$ListenHost = "127.0.0.1"
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# ------------------------------------------------------------------
# CONFIGURATION - SINGLE SOURCE OF TRUTH
# ------------------------------------------------------------------
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Try venv311 first, fall back to venv311_clean
$venvName = "venv311"
$VENV_PATH = Join-Path $SCRIPT_DIR "venv311\Scripts"
$PYTHON = Join-Path $VENV_PATH "python.exe"

if (-not (Test-Path $PYTHON)) {
    $venvName = "venv311_clean"
    $VENV_PATH = Join-Path $SCRIPT_DIR "venv311_clean\Scripts"
    $PYTHON = Join-Path $VENV_PATH "python.exe"
}
$MODULE = "app.main:create_app"

# Security mode: ENFORCED for production, open only with -DevMode switch
$SECURITY_MODE = if ($DevMode) { "open" } else { "enforced" }

# ------------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------------
function Test-Requirements {
    # Check venv exists
    if (!(Test-Path $PYTHON)) {
        throw "Python not found at $PYTHON. Run setup first."
    }

    # Check we're in the right directory
    if (!(Test-Path (Join-Path $SCRIPT_DIR "app\main.py"))) {
        throw "Not in Semptify root directory. app\main.py not found."
    }

    Write-Host "OK Requirements validated" -ForegroundColor Green
}

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
function Write-Header {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  SEMPTIFY 5.0 - Tenant Rights Platform" -ForegroundColor White
    Write-Host "  Mode: $(if ($DevMode) {'DEVELOPMENT'} else {'PRODUCTION'}) | Security: $SECURITY_MODE | VEnv: $venvName" -ForegroundColor $(if ($DevMode) { 'Yellow' } else { 'Green' })
    Write-Host "============================================================" -ForegroundColor Cyan
    if ($DevMode) {
        Write-Host "  WARNING: DevMode uses OPEN security - NOT for production!" -ForegroundColor Red
    }
    Write-Host ""
}

function Write-Step {
    param($Number, $Message)
    Write-Host "[$Number/3] $Message" -ForegroundColor Cyan
}

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
try {
    Set-Location $SCRIPT_DIR
    Write-Header

    # Step 1: Validate
    Write-Step 1 "Validating environment..."
    Test-Requirements

    # Step 2: Database & Configure
    Write-Step 2 "Configuring environment..."
    
    # Database setup
    if ($WithDocker) {
        Write-Host "  -> Starting Docker + PostgreSQL..." -ForegroundColor Gray
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker is not running. Start Docker Desktop first."
        }
        docker-compose up -d postgres 2>$null
        Write-Host "  -> Waiting for PostgreSQL..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
    elseif ($WithPostgres) {
        Write-Host "  -> Checking PostgreSQL service..." -ForegroundColor Gray
        
        # Dynamic PostgreSQL service detection
        $pgService = Get-Service | Where-Object {
            $_.Name -match 'postgresql|postgres' -or $_.DisplayName -match 'PostgreSQL'
        } | Sort-Object Name | Select-Object -First 1
        
        if (-not $pgService) {
            throw "No PostgreSQL service found. Install PostgreSQL or use -WithDocker."
        }
        
        if ($pgService.Status -ne 'Running') {
            Write-Host "  -> Starting $($pgService.Name)..." -ForegroundColor Gray
            Start-Service -Name $pgService.Name -ErrorAction Stop
        }
        
        # Wait for PostgreSQL to accept connections
        Write-Host "  -> Waiting for PostgreSQL to be ready..." -ForegroundColor Gray
        $pgReady = $false
        for ($i = 1; $i -le 30; $i++) {
            try {
                $tcp = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
                if ($tcp.TcpTestSucceeded) { $pgReady = $true; break }
            } catch {}
            Start-Sleep -Milliseconds 500
        }
        
        if (-not $pgReady) {
            throw "PostgreSQL did not become ready on port 5432"
        }
        
        $env:DATABASE_URL = "postgresql+asyncpg://semptify:semptify@localhost:5432/semptify"
        Write-Host "  -> PostgreSQL ready (service: $($pgService.Name))" -ForegroundColor Green
    }
    
    $env:SECURITY_MODE = $SECURITY_MODE
    $env:PYTHONPATH = $SCRIPT_DIR
    $env:PYTHONIOENCODING = 'utf-8'
    
    # Ensure SECRET_KEY is set (generate if missing)
    if (-not $env:SECRET_KEY -or $env:SECRET_KEY -eq 'change-me-in-production') {
        $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
        $bytes = New-Object byte[] 32
        $rng.GetBytes($bytes)
        $env:SECRET_KEY = [Convert]::ToBase64String($bytes)
        Write-Host "  -> SECRET_KEY: auto-generated" -ForegroundColor Gray
    }
    
    Write-Host "  -> Security mode: $SECURITY_MODE" -ForegroundColor Gray
    Write-Host "  -> Server: http://${ListenHost}:${Port}" -ForegroundColor Gray

    # Step 3: Start Server
    Write-Step 3 "Starting Uvicorn server..."
    Write-Host ""
    Write-Host "  Server starting..." -ForegroundColor Green
    Write-Host "  Welcome: http://${ListenHost}:${Port}/" -ForegroundColor Gray
    Write-Host "  API Docs: http://${ListenHost}:${Port}/api/docs" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""

    # Start the server (using factory pattern)
    & $PYTHON -m uvicorn $MODULE `
        --host $ListenHost `
        --port $Port `
        --loop asyncio `
        --http h11 `
        --factory

} catch {
    Write-Host ""
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}
