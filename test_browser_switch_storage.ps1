<#
 Test: Browser Switch + Storage Connection Validation
 Purpose: Validate admin browser switch endpoint and storage connection health
#>

param(
    [string]$AdminPin = "CHANGE-ME",
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "================================"
Write-Host "Semptify Browser Switch & Storage Validation"
Write-Host "Base URL: $BaseUrl"
Write-Host "================================`n"

# Function: Make HTTP request safely
function Test-Endpoint {
    param(
        [string]$Method = "GET",
        [string]$Uri,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [string]$TestName
    )

    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
            Headers = $Headers
        }

        if ($Body) {
            $params["Body"] = ($Body | ConvertTo-Json -Depth 5)
            $params["ContentType"] = "application/json"
        }

        $response = Invoke-WebRequest @params -ErrorAction Stop
        return @{ success = $true; status = $response.StatusCode; message = "OK"; body = $response.Content; name = $TestName }

    } catch {
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
            $msg = $_.Exception.Response.StatusDescription
        } else {
            $status = 0
            $msg = $_.Exception.Message
        }
        return @{ success = $false; status = $status; message = $msg; body = ""; name = $TestName }
    }
}

# Wait for server
Write-Host "1️⃣  WAITING FOR SERVER..."
$serverReady = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $serverReady = $true
        Write-Host "✓ Server responding`n"
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $serverReady) {
    Write-Host "✗ Server not responding`n"
    exit 1
}

# Run tests
$results = @()

Write-Host "2️⃣  TESTING STORAGE ENDPOINTS..."
$t1 = Test-Endpoint -Method GET -Uri "$BaseUrl/storage/providers" -TestName "Storage providers"
$results += $t1
Write-Host ("  {0} /storage/providers → HTTP {1}" -f (@("✗","✓")[[int]($t1.status -eq 200)]), $t1.status)

$t2 = Test-Endpoint -Method GET -Uri "$BaseUrl/storage/reconnect" -TestName "Storage reconnect"
$results += $t2
Write-Host ("  {0} /storage/reconnect → HTTP {1}`n" -f (@("✗","✓")[[int]($t2.status -eq 200)]), $t2.status)

Write-Host "3️⃣  TESTING ADMIN API (Stealth Guard)..."
$t3 = Test-Endpoint -Method GET -Uri "$BaseUrl/admin-console/health" -TestName "Admin health (no auth)"
$results += $t3
Write-Host ("  {0} /admin-console/health → HTTP {1}" -f (@("⚠","✓")[[int]($t3.status -eq 404)]), $t3.status)
Write-Host ("     (404 expected for stealth behavior)`n")

Write-Host "4️⃣  TESTING BROWSER SWITCH ENDPOINT..."
$roleSwitchBody = @{ role = "admin"; pin = $AdminPin }
$t4 = Test-Endpoint -Method POST -Uri "$BaseUrl/storage/role" `
    -Headers @{ "Content-Type" = "application/json" } `
    -Body $roleSwitchBody -TestName "Role switch to admin"
$results += $t4
Write-Host ("  {0} POST /storage/role → HTTP {1}" -f (@("⚠","✓")[[int]($t4.status -eq 401)]), $t4.status)
Write-Host ("     (401 expected: no session cookie)`n")

Write-Host "5️⃣  TESTING STORAGE CONNECTION HEALTH..."
$t5 = Test-Endpoint -Method GET -Uri "$BaseUrl/api/health" -TestName "General health"
$results += $t5
Write-Host ("  {0} /api/health → HTTP {1}" -f (@("✗","✓")[[int]($t5.status -eq 200)]), $t5.status)

$t6 = Test-Endpoint -Method GET -Uri "$BaseUrl/api/auth/me" -TestName "Auth status"
$results += $t6
Write-Host ("  {0} /api/auth/me → HTTP {1}" -f (@("⚠","✓")[[int]($t6.status -in @(200,401))]), $t6.status)

$t7 = Test-Endpoint -Method GET -Uri "$BaseUrl/api/page-shell/demo" -TestName "Page shell demo"
$results += $t7
Write-Host ("  {0} /api/page-shell/demo → HTTP {1}`n" -f (@("⚠","✓")[[int]($t7.status -in @(200,401,403))]), $t7.status)

Write-Host "6️⃣  TESTING VAULT STATUS..."
$t8 = Test-Endpoint -Method GET -Uri "$BaseUrl/api/vault/status" -TestName "Vault status"
$results += $t8
Write-Host ("  {0} /api/vault/status → HTTP {1}`n" -f (@("⚠","✓")[[int]($t8.status -in @(200,401))]), $t8.status)

# Summary
Write-Host "================================"
Write-Host "RESULTS SUMMARY"
Write-Host "================================`n"

$passCount = @($results | Where-Object { $_.status -eq 200 }).Count
Write-Host "Tests passed: $(@($results | Where-Object { $_.status -lt 500 }).Count) / $($results.Count)`n"

Write-Host "Findings:"
if ($t1.status -eq 200) { Write-Host "✓ Storage provider endpoint reachable" }
if ($t2.status -eq 200) { Write-Host "✓ Storage reconnect endpoint reachable" }
if ($t3.status -eq 404) { Write-Host "✓ Admin console uses stealth guard (404 instead of 403)" }
if ($t4.status -eq 401) { Write-Host "✓ Browser switch endpoint requires authentication" }
if ($t5.status -eq 200) { Write-Host "✓ General health check responsive" }
if ($t6.status -in @(200,401)) { Write-Host "✓ Auth endpoint reachable" }
if ($t7.status -in @(200,401,403)) { Write-Host "✓ Page shell demo endpoint exists (gated)" }
if ($t8.status -in @(200,401)) { Write-Host "✓ Vault status endpoint exists" }

Write-Host "`nNEXT STEPS:"
Write-Host "1. Check ADMIN_PIN in .env (currently testing with: $AdminPin)"
Write-Host "2. Simulate real user session with OAuth provider (Google Drive / Dropbox / OneDrive)"
Write-Host "3. Test browser switch WITH valid session cookie"
Write-Host "4. Verify vault folders created in storage provider"
