# ================================
# SEMPTIFY ALL-IN-ONE BOOTSTRAP
# ================================

$root = "C:\Semptify\Semptify-FastAPI"
$vscode = "$root\.vscode"
$scripts = "$root\scripts"

Write-Host "Bootstrapping Semptify workspace at $root..."

# -------------------------------
# 1. Ensure folders exist
# -------------------------------
New-Item -ItemType Directory -Force -Path $vscode | Out-Null
New-Item -ItemType Directory -Force -Path $scripts | Out-Null

# -------------------------------
# 2. Enable script execution
# -------------------------------
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force

# -------------------------------
# 3. Write VS Code settings.json
# -------------------------------
$settingsPath = "$env:APPDATA\Code\User\settings.json"
$settingsDir = Split-Path $settingsPath

if (!(Test-Path $settingsDir)) {
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
}

if (Test-Path $settingsPath) {
    $json = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $json = @{}
}

$json."security.workspace.trust.enabled" = $true
$json."copilot.agents.enable" = $true
$json."copilot.agents.terminalTools.enabled" = $true
$json."copilot.agents.workspaceTools.enabled" = $true
$json."copilot.agents.allowFileEdits" = $true
$json."terminal.integrated.defaultProfile.windows" = "PowerShell"
$json."terminal.integrated.enablePersistentSessions" = $true

$json | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8

Write-Host "VS Code settings updated."

# -------------------------------
# 4. Write tools.json
# -------------------------------
$toolsJson = @"
{
  "version": "1.0.0",
  "tools": {
    "semtify-build-backend": {
      "command": "pwsh ./scripts/build_backend.ps1",
      "description": "Builds the Semptify FastAPI backend."
    },
    "semtify-build-frontend": {
      "command": "pwsh ./scripts/build_frontend.ps1",
      "description": "Builds the Semptify frontend UI."
    },
    "semtify-zip-bundle": {
      "command": "pwsh ./scripts/zip_bundle.ps1",
      "description": "Creates a clean ZIP export of the Semptify bundle."
    },
    "semtify-deploy-local": {
      "command": "pwsh ./scripts/deploy_local.ps1",
      "description": "Starts backend + frontend locally."
    },
    "semtify-test-suite": {
      "command": "pwsh ./scripts/run_tests.ps1",
      "description": "Runs Semptify automated tests."
    },
    "semtify-clean": {
      "command": "pwsh ./scripts/clean_workspace.ps1",
      "description": "Cleans build artifacts and resets workspace."
    }
  }
}
"@

$toolsJson | Set-Content "$vscode\tools.json" -Encoding UTF8

Write-Host "tools.json created."

# -------------------------------
# 5. Write all Semptify scripts
# -------------------------------

@"
Write-Host 'Building Semptify backend...'
# Insert backend build steps here
"@ | Set-Content "$scripts\build_backend.ps1"

@"
Write-Host 'Building Semptify frontend...'
# Insert frontend build steps here
"@ | Set-Content "$scripts\build_frontend.ps1"

@"
Write-Host 'Zipping Semptify bundle...'
Compress-Archive -Path '$root\*' -DestinationPath '$root\SemptifyBundle.zip' -Force
"@ | Set-Content "$scripts\zip_bundle.ps1"

@"
Write-Host 'Deploying Semptify locally...'
Start-Process powershell -ArgumentList 'uvicorn main:app --port 3001'
Start-Process powershell -ArgumentList 'npm run dev'
"@ | Set-Content "$scripts\deploy_local.ps1"

@"
Write-Host 'Running Semptify tests...'
# Insert test commands here
"@ | Set-Content "$scripts\run_tests.ps1"

@"
Write-Host 'Cleaning workspace...'
Remove-Item '$root\SemptifyBundle.zip' -ErrorAction SilentlyContinue
"@ | Set-Content "$scripts\clean_workspace.ps1"

Write-Host "All scripts created."

# -------------------------------
# DONE
# -------------------------------
Write-Host "Semptify workspace fully bootstrapped. Restart VS Code."
