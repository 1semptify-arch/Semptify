$urls = @(
    'http://localhost:8000/admin/page_shell_demo.html',
    'http://localhost:8000/static/admin/page_shell_demo.html',
    'http://localhost:8000/admin/login',
    'http://localhost:8000/api/page-shell/demo'
)
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 0
        Write-Host ("{0} -> {1} (len={2})" -f $u, [int]$r.StatusCode, $r.Content.Length)
    } catch {
        if ($_.Exception.Response) {
            Write-Host ("{0} -> HTTP {1}" -f $u, [int]$_.Exception.Response.StatusCode)
        } else {
            Write-Host ("{0} -> ERR: {1}" -f $u, $_.Exception.Message)
        }
    }
}
