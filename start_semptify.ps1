# start_semptify.ps1 — Auto-restarting Semptify server
# Run this once; it will keep the app alive indefinitely.

$AppDir = "E:\master-repo\sources\app-semptify-fastapi"
$Uvicorn = "$AppDir\venv311\Scripts\uvicorn.exe"
Set-Location $AppDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SEMPTIFY - Auto-restart mode" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

while ($true) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting Semptify..." -ForegroundColor Green
    & $Uvicorn app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 75
    $exit = $LASTEXITCODE
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] App exited (code $exit). Restarting in 3s..." -ForegroundColor Yellow
    Start-Sleep 3
}
