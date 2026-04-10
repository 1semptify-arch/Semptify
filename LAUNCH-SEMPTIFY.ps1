# ====================================================================
#  SEMPTIFY - PRODUCTION LAUNCHER
#  This script starts EVERYTHING from scratch:
#    1.  Docker Desktop  (the database engine)
#    2.  PostgreSQL database  (stores your case data)
#    3.  Semptify server  (the app itself)
#    4.  Opens your browser automatically
#
#  Security is ALWAYS enforced.  You cannot turn it off from here.
# ====================================================================

$ErrorActionPreference = 'Continue'

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
function Step  { param($n,$msg) Write-Host ""
    Write-Host "  STEP $n  $msg" -ForegroundColor Cyan }
function OK    { param($msg) Write-Host "    [OK]   $msg" -ForegroundColor Green }
function WARN  { param($msg) Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function FAIL  { param($msg) Write-Host "    [FAIL] $msg" -ForegroundColor Red }
function INFO  { param($msg) Write-Host "           $msg" -ForegroundColor Gray }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Wait helper using ping (no Start-Sleep needed)
function Wait-Seconds { param($n) ping -n ($n + 1) 127.0.0.1 > $null }

Clear-Host
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Magenta
Write-Host "        SEMPTIFY 5.0  -  Tenant Rights Platform"           -ForegroundColor White
Write-Host "        Production Launch  |  Security: ENFORCED"          -ForegroundColor White
Write-Host "  ============================================================" -ForegroundColor Magenta
Write-Host ""

# ==================================================================
# STEP 1 - Docker Desktop
# ==================================================================
Step 1 "Starting Docker Desktop (database engine)..."

$dockerExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$dockerRunning = $false

# Check if daemon is already up
docker info *> $null
if ($LASTEXITCODE -eq 0) {
    $dockerRunning = $true
    OK "Docker is already running"
} elseif (Test-Path $dockerExe) {
    INFO "Launching Docker Desktop - this may take 30-60 seconds..."
    Start-Process -FilePath $dockerExe | Out-Null

    for ($i = 1; $i -le 90; $i++) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { $dockerRunning = $true; break }
        Write-Host "    Waiting for Docker... ($i/90)" -ForegroundColor DarkGray -NoNewline
        Write-Host "`r" -NoNewline
        Wait-Seconds 2
    }
    if ($dockerRunning) { OK "Docker Desktop is ready" }
} else {
    FAIL "Docker Desktop is not installed."
    INFO "Download it from: https://www.docker.com/products/docker-desktop/"
    INFO ""
    WARN "Will attempt to start without PostgreSQL (SQLite fallback)."
}

# ==================================================================
# STEP 2 - Core Data Services (PostgreSQL + Redis)
# ==================================================================
Step 2 "Starting core data services (PostgreSQL + Redis)..."

$pgContainerName = 'semptify-pg-validate'
$redisContainerName = 'semptify-redis-local'
$pgReady = $false
$redisReady = $false

# First preference: locally installed PostgreSQL Windows service
$localPgService = Get-Service | Where-Object {
    $_.Name -match 'postgresql|postgres' -or $_.DisplayName -match 'PostgreSQL'
} | Sort-Object Name | Select-Object -First 1

if ($localPgService) {
    INFO "Found local PostgreSQL service: $($localPgService.Name)"
    if ($localPgService.Status -ne 'Running') {
        INFO "Starting local PostgreSQL service..."
        Start-Service -Name $localPgService.Name -ErrorAction SilentlyContinue
    }

    $pgPort = $null
    $local5432 = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
    if ($local5432.TcpTestSucceeded) {
        $pgPort = 5432
    } else {
        $local54329 = Test-NetConnection -ComputerName localhost -Port 54329 -WarningAction SilentlyContinue
        if ($local54329.TcpTestSucceeded) {
            $pgPort = 54329
        }
    }

    if ($pgPort) {
        $env:DATABASE_URL = "postgresql+asyncpg://semptify:semptify@localhost:$pgPort/semptify"
        $pgReady = $true
        OK "Local PostgreSQL is ready  (localhost:$pgPort)"
    } else {
        WARN "Local PostgreSQL service found but no listener on 5432 or 54329."
    }
}

if (-not $pgReady -and $dockerRunning) {
    # Create container if it does not exist
    $exists = docker ps -a --format '{{.Names}}' 2>$null | Where-Object { $_ -eq $pgContainerName }
    if (-not $exists) {
        INFO "Creating new Semptify database container..."
        docker run -d `
            --name $pgContainerName `
            -e POSTGRES_USER=semptify `
            -e POSTGRES_PASSWORD=semptify `
            -e POSTGRES_DB=semptify `
            -p 54329:5432 `
            postgres:16-alpine *> $null
    } else {
        $running = docker ps --format '{{.Names}}' 2>$null | Where-Object { $_ -eq $pgContainerName }
        if (-not $running) {
            INFO "Starting existing database container..."
            docker start $pgContainerName *> $null
        }
    }

    # Create/start Redis container
    $redisExists = docker ps -a --format '{{.Names}}' 2>$null | Where-Object { $_ -eq $redisContainerName }
    if (-not $redisExists) {
        INFO "Creating new Semptify Redis container..."
        docker run -d `
            --name $redisContainerName `
            -p 6379:6379 `
            redis:7-alpine `
            redis-server --appendonly yes *> $null
    } else {
        $redisRunning = docker ps --format '{{.Names}}' 2>$null | Where-Object { $_ -eq $redisContainerName }
        if (-not $redisRunning) {
            INFO "Starting existing Redis container..."
            docker start $redisContainerName *> $null
        }
    }

    # Wait for Postgres to accept connections
    for ($i = 1; $i -le 60; $i++) {
        docker exec $pgContainerName pg_isready -U semptify -d semptify *> $null
        if ($LASTEXITCODE -eq 0) { $pgReady = $true; break }
        Write-Host "    Waiting for database... ($i/60)" -ForegroundColor DarkGray -NoNewline
        Write-Host "`r" -NoNewline
        Wait-Seconds 2
    }

    # Wait for Redis to accept connections
    for ($i = 1; $i -le 40; $i++) {
        docker exec $redisContainerName redis-cli ping *> $null
        if ($LASTEXITCODE -eq 0) { $redisReady = $true; break }
        Write-Host "    Waiting for Redis... ($i/40)" -ForegroundColor DarkGray -NoNewline
        Write-Host "`r" -NoNewline
        Wait-Seconds 1
    }

    if ($pgReady) {
        $env:DATABASE_URL = 'postgresql+asyncpg://semptify:semptify@localhost:54329/semptify'
        OK "Database is ready  (PostgreSQL on port 54329)"
    } else {
        FAIL "Database did not start in time."
        WARN "Falling back to local file-based database."
    }
    if ($redisReady) {
        $env:REDIS_URL = 'redis://localhost:6379/0'
        OK "Redis is ready  (redis://localhost:6379/0)"
    } else {
        WARN "Redis did not report healthy in time."
    }
} elseif (-not $pgReady) {
    WARN "Skipping database - Docker not available."
    INFO "Your data will be stored in a local file (semptify.db)."
    INFO "This is fine for testing but not recommended for real case data."
}

# ==================================================================
# STEP 3 - Security  (ALWAYS enforced - cannot be bypassed)
# ==================================================================
Step 3 "Enforcing security settings..."

$env:SECURITY_MODE   = 'enforced'
$env:ENFORCE_SECURITY = 'true'
$env:ENVIRONMENT     = 'production'
$env:DEBUG           = 'false'
$env:PYTHONIOENCODING = 'utf-8'

# Ensure production validation gets a non-default key
if (-not $env:SECRET_KEY -or $env:SECRET_KEY -eq 'change-me-in-production') {
    $env:SECRET_KEY = [Convert]::ToBase64String((1..64 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
}

OK "Security mode   : ENFORCED"
OK "Environment     : production"
OK "Debug logging   : off"

# ==================================================================
# STEP 4 - Clean up any previous server process on port 8000
# ==================================================================
Step 4 "Checking for an existing server on port 8000..."

try {
    $portCheck = netstat -ano | Select-String ':8000 '
    if ($portCheck) {
        $pid8000 = ($portCheck | Select-Object -First 1) -replace '.*\s+(\d+)$', '$1'
        $pid8000 = $pid8000.Trim()
        if ($pid8000 -and $pid8000 -match '^\d+$') {
            Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
            Wait-Seconds 2
            OK "Stopped old server (PID $pid8000)"
        }
    } else {
        OK "Port 8000 is free"
    }
} catch {
    INFO "Could not check port - continuing anyway"
}

# ==================================================================
# STEP 5 - Verify Python environment
# ==================================================================
Step 5 "Checking Python..."

$pythonPath = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    FAIL "Virtual environment not found."
    INFO "Run this command once in the project folder:"
    INFO "   python -m venv .venv"
    INFO "   .venv\Scripts\pip install -r requirements.txt"
    Read-Host "Press Enter to exit"
    exit 1
}
$pyVer = (& $pythonPath --version 2>&1).ToString().Trim()
OK "Python: $pyVer"

# ==================================================================
# STEP 6 - Open browser automatically
# ==================================================================
Step 6 "Will open Semptify in your browser in 5 seconds..."

Start-Job -ScriptBlock {
    ping -n 6 127.0.0.1 > $null       # ~5-second delay
    Start-Process "http://localhost:8000/static/command_center.html"
} | Out-Null

# ==================================================================
# STEP 7 - Launch the server
# ==================================================================
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "   Semptify is starting...  Open: http://localhost:8000"     -ForegroundColor Green
Write-Host "   Press  Ctrl + C  at any time to stop the server."         -ForegroundColor DarkGray
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""

& $pythonPath -m uvicorn app.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --log-level warning

# ==================================================================
# Server stopped
# ==================================================================
Write-Host ""
FAIL "Server has stopped."
INFO "If this was unexpected, scroll up to look for error messages."
Write-Host ""
Read-Host "Press Enter to close this window"
