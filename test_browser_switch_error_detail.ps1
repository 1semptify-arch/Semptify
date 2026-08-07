<#
 Detailed error capture for browser switch endpoint
#>

param([string]$BaseUrl = "http://localhost:8000")

Write-Host "Testing role switch with detailed error capture`n"

$roleSwitchBody = @{ role = "admin"; pin = "CHANGE-ME" } | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Method POST -Uri "$BaseUrl/storage/role" `
        -Body $roleSwitchBody -ContentType "application/json" `
        -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop

    Write-Host "✅ Response: $($response.StatusCode)"
    Write-Host $response.Content
}
catch {
    $statusCode = [int]$_.Exception.Response.StatusCode
    $statusDesc = $_.Exception.Response.StatusDescription

    try {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        Write-Host "❌ Status: HTTP $statusCode - $statusDesc`n"
        Write-Host "Response body:"
        Write-Host $body
    }
    catch {
        Write-Host "❌ Status: HTTP $statusCode - $statusDesc"
        Write-Host "Could not read response body"
    }
}
