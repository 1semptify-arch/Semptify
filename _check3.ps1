Start-Sleep -Seconds 15
try {
    $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/page-shell/demo' -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 0
    Write-Host ("demo API: HTTP {0}, len={1}" -f [int]$r.StatusCode, $r.Content.Length)
} catch {
    if ($_.Exception.Response) {
        Write-Host ("demo API: HTTP {0}" -f [int]$_.Exception.Response.StatusCode)
    } else {
        Write-Host ("demo API: ERR {0}" -f $_.Exception.Message)
    }
}
