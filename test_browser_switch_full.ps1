<#
 Browser Switch + Storage Validation (Simplified)
#>

param([string]$BaseUrl = "http://localhost:8000")

Write-Host "========================================`nBrowser Switch & Storage Validation`n========================================`n"

# Test 1: Role switch WITHOUT session
Write-Host "TEST 1️⃣  Role Switch Without Session"
Write-Host "===================================="
$roleSwitchBody = @{ role = "admin"; pin = "CHANGE-ME" } | ConvertTo-Json
$status = $null
try {
    Invoke-WebRequest -Method POST -Uri "$BaseUrl/storage/role" `
        -Body $roleSwitchBody -ContentType "application/json" `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
    $status = 200
} catch {
    $status = [int]$_.Exception.Response.StatusCode
    $desc = $_.Exception.Response.StatusDescription
}

Write-Host "Status: HTTP $status $(if($status -eq 401) {'✅ EXPECTED'} elseif($status -eq 500) {'❌ ERROR'} else {'⚠️'})"
Write-Host ""

# Test 2: Admin console health WITHOUT auth
Write-Host "TEST 2️⃣  Admin Console Health (Stealth Guard)"
Write-Host "=============================================="
$adminStatus = $null
try {
    Invoke-WebRequest -Uri "$BaseUrl/admin-console/health" `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
    $adminStatus = 200
} catch {
    $adminStatus = [int]$_.Exception.Response.StatusCode
}

Write-Host "Status: HTTP $adminStatus $(if($adminStatus -eq 404) {'✅ EXPECTED (stealth)'} elseif($adminStatus -eq 200) {'❌ ISSUE'} else {'⚠️'})"
Write-Host ""

# Test 3: Storage endpoints
Write-Host "TEST 3️⃣  Storage Endpoints"
Write-Host "=========================="
$t3a = $null; $t3b = $null
try { Invoke-WebRequest -Uri "$BaseUrl/storage/providers" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null; $t3a = 200 } catch { $t3a = $_.Exception.Response.StatusCode }
try { Invoke-WebRequest -Uri "$BaseUrl/storage/reconnect" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null; $t3b = 200 } catch { $t3b = $_.Exception.Response.StatusCode }

Write-Host "Providers:  HTTP $t3a $(if($t3a -eq 200) {'✅'} else {'❌'})"
Write-Host "Reconnect:  HTTP $t3b $(if($t3b -eq 200) {'✅'} else {'❌'})"
Write-Host ""

# Summary
Write-Host "========================================"
Write-Host "FINDINGS"
Write-Host "========================================"
Write-Host ""

if ($status -eq 401) { Write-Host "✅ Browser switch rejects unauthenticated" } else { Write-Host "❌ Browser switch: HTTP $status (expected 401)" }
if ($adminStatus -eq 404) { Write-Host "✅ Admin API stealth guard active (404)" } else { Write-Host "❌ Admin stealth: HTTP $adminStatus (expected 404)" }
if ($t3a -eq 200 -and $t3b -eq 200) { Write-Host "✅ Storage endpoints accessible" }

Write-Host ""
Write-Host "NEXT: Test with valid session to exercise browser switch logic"
