$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop } catch {}
}
Start-Sleep -Seconds 2
Start-Process -FilePath 'C:\Semptify\Semptify-FastAPI\venv311\Scripts\pythonw.exe' `
    -ArgumentList '-m','uvicorn','app.main:app','--port','8000' `
    -WorkingDirectory 'C:\Semptify\Semptify-FastAPI' `
    -WindowStyle Hidden
Start-Sleep -Seconds 12
try {
    $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/page-shell/demo' -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 0
    Write-Host ("demo API: HTTP {0}" -f [int]$r.StatusCode)
} catch {
    if ($_.Exception.Response) {
        Write-Host ("demo API: HTTP {0}" -f [int]$_.Exception.Response.StatusCode)
    } else {
        Write-Host ("demo API: ERR {0}" -f $_.Exception.Message)
    }
}
