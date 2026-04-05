param(
    [switch]$SkipServer
)

$ErrorActionPreference = 'Stop'

Write-Host '[Semptify] Starting Docker Desktop check...'
$dockerDesktopExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
if (Test-Path $dockerDesktopExe) {
    Start-Process -FilePath $dockerDesktopExe | Out-Null
}

$dockerReady = $false
for ($i = 1; $i -le 90; $i++) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        break
    }
    ping -n 2 127.0.0.1 > $null
}

if (-not $dockerReady) {
    throw 'Docker daemon is not ready. Start Docker Desktop and retry.'
}

Write-Host '[Semptify] Docker ready.'

$containerName = 'semptify-pg-validate'
$exists = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $containerName }
if (-not $exists) {
    Write-Host '[Semptify] Creating local PostgreSQL container...'
    docker run -d --name $containerName -e POSTGRES_USER=semptify -e POSTGRES_PASSWORD=semptify -e POSTGRES_DB=semptify -p 54329:5432 postgres:16-alpine | Out-Null
} else {
    $running = docker ps --format '{{.Names}}' | Where-Object { $_ -eq $containerName }
    if (-not $running) {
        Write-Host '[Semptify] Starting existing PostgreSQL container...'
        docker start $containerName | Out-Null
    }
}

$pgReady = $false
for ($i = 1; $i -le 60; $i++) {
    docker exec $containerName pg_isready -U semptify -d semptify *> $null
    if ($LASTEXITCODE -eq 0) {
        $pgReady = $true
        break
    }
    ping -n 2 127.0.0.1 > $null
}

if (-not $pgReady) {
    throw 'PostgreSQL container is not ready.'
}

$env:DATABASE_URL = 'postgresql+asyncpg://semptify:semptify@localhost:54329/semptify'
Write-Host "[Semptify] DATABASE_URL set to $env:DATABASE_URL"

if ($SkipServer) {
    Write-Host '[Semptify] SkipServer set; startup checks completed.'
    exit 0
}

Write-Host '[Semptify] Starting FastAPI server on http://0.0.0.0:8000 ...'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
