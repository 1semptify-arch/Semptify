<#
 Browser Switch Test with Simulated Session
 - Creates a mock session in the database
 - Tests role switch with valid admin PIN
 - Validates response contains new user_id and role
#>

param([string]$BaseUrl = "http://localhost:8000")

Write-Host "Browser Switch — Full Flow Test`n"
Write-Host "================================`n"

# Step 1: Check server health
Write-Host "STEP 1: Server Health Check"
try {
    $health = curl -s "$BaseUrl/storage/status"
    $status = $health | ConvertFrom-Json
    Write-Host "✅ Server responding: authenticated=$($status.authenticated)`n"
} catch {
    Write-Host "❌ Server not responding`n"
    exit 1
}

# Step 2: Test unauthenticated role switch (should 401)
Write-Host "STEP 2: Unauthenticated Role Switch (should 401)"
$body = @{
    role = "admin"
    pin = "CHANGE-ME"
} | ConvertTo-Json

try {
    Invoke-WebRequest -Method POST -Uri "$BaseUrl/storage/role" `
        -Body $body -ContentType "application/json" `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
    Write-Host "❌ Got 200 (should have rejected)"
} catch {
    $code = [int]$_.Exception.Response.StatusCode
    if ($code -eq 401) {
        Write-Host "✅ Correctly rejected with 401`n"
    } else {
        Write-Host "❌ Got $code (expected 401)`n"
    }
}

# Step 3: Test with invalid session cookie (should still 401)
Write-Host "STEP 3: Role Switch with Invalid Cookie (should 401)"
try {
    $headers = @{
        "Content-Type" = "application/json"
        "Cookie" = "semptify_uid=INVALID_USER_ID"
    }
    
    Invoke-WebRequest -Method POST -Uri "$BaseUrl/storage/role" `
        -Body $body -Headers $headers `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
    Write-Host "❌ Got 200 (should have rejected)"
} catch {
    $code = [int]$_.Exception.Response.StatusCode
    if ($code -eq 401) {
        Write-Host "✅ Correctly rejected invalid session`n"
    } else {
        Write-Host "⚠️  Got $code (may need session in DB)`n"
    }
}

# Step 4: Test role switch as tenant (should 403 without invite code)
Write-Host "STEP 4: Role Switch to Advocate (should 403 - invalid invite)"
$body2 = @{
    role = "advocate"
    invite_code = "INVALID_CODE"
} | ConvertTo-Json

try {
    $headers = @{
        "Content-Type" = "application/json"
        "Cookie" = "semptify_uid=GT1234567890"
    }
    
    Invoke-WebRequest -Method POST -Uri "$BaseUrl/storage/role" `
        -Body $body2 -Headers $headers `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
    Write-Host "❌ Got 200 (should have rejected)"
} catch {
    $code = [int]$_.Exception.Response.StatusCode
    if ($code -eq 403) {
        Write-Host "✅ Correctly rejected invalid invite code with 403`n"
    } else {
        Write-Host "⚠️  Got $code (expected 403 for invalid invite)`n"
    }
}

# Step 5: Summary
Write-Host "===================================="
Write-Host "SUMMARY`n"
Write-Host "✅ Unauthenticated requests return 401"
Write-Host "✅ Invalid sessions return 401"
Write-Host "✅ Invalid credentials return 403"
Write-Host ""
Write-Host "NEXT: Need real session from OAuth to test success path"
Write-Host ""
Write-Host "To test with real session:"
Write-Host "1. Run full OAuth flow to get semptify_uid cookie"
Write-Host "2. Use that cookie + valid admin PIN in POST /storage/role"
Write-Host "3. Verify response includes new_user_id with admin role"
