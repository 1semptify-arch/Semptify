<#
 Detailed health endpoint check (no redirect follow)
#>

Write-Host "Checking /admin-console/health endpoint`n"

# Use curl with -L to show location header without following
curl -i http://localhost:8000/admin-console/health 2>&1 | Select-String -Pattern "HTTP|location|status" | Select-Object -First 10

Write-Host ""
Write-Host "Full response:"
curl http://localhost:8000/admin-console/health 2>&1 | Select-Object -First 5
