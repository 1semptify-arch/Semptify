# Fix Python Environment - Remove 3.14, Use 3.11
# Run as Administrator

Write-Host "=== Fixing Python Environment ===" -ForegroundColor Green

# Get current user PATH
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$machinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

Write-Host "Current User PATH contains Python 3.14: $($currentPath -like '*Python314*')" -ForegroundColor Yellow
Write-Host "Current Machine PATH contains Python 3.14: $($machinePath -like '*Python314*')" -ForegroundColor Yellow

# Remove Python 3.14 from User PATH
$newUserPath = ($currentPath -split ';' | Where-Object { $_ -notmatch 'Python314' }) -join ';'
[Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")
Write-Host "Removed Python 3.14 from User PATH" -ForegroundColor Green

# Remove Python 3.14 from Machine PATH
$newMachinePath = ($machinePath -split ';' | Where-Object { $_ -notmatch 'Python314' }) -join ';'
[Environment]::SetEnvironmentVariable("PATH", $newMachinePath, "Machine")
Write-Host "Removed Python 3.14 from Machine PATH" -ForegroundColor Green

# Remove PYTHONPATH if it references 3.14
$pythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "User")
if ($pythonPath -and $pythonPath -match 'Python314') {
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "User")
    Write-Host "Removed PYTHONPATH referencing Python 3.14" -ForegroundColor Green
}

# Remove PYTHONHOME if it references 3.14
$pythonHome = [Environment]::GetEnvironmentVariable("PYTHONHOME", "User")
if ($pythonHome -and $pythonHome -match 'Python314') {
    [Environment]::SetEnvironmentVariable("PYTHONHOME", $null, "User")
    Write-Host "Removed PYTHONHOME referencing Python 3.14" -ForegroundColor Green
}

# Create new virtual environment with Python 3.11
Write-Host "`n=== Creating Fresh Virtual Environment with Python 3.11 ===" -ForegroundColor Green
$venvPath = "C:\Semptify\Semptify-FastAPI\venv311_clean"

# Remove old venv if exists
if (Test-Path $venvPath) {
    Remove-Item -Recurse -Force $venvPath
    Write-Host "Removed old virtual environment" -ForegroundColor Yellow
}

# Create new venv with Python 3.11
& py -3.11 -m venv $venvPath
Write-Host "Created new virtual environment at $venvPath" -ForegroundColor Green

Write-Host "`n=== Environment Fixed ===" -ForegroundColor Green
Write-Host "Python 3.14 references removed from PATH" -ForegroundColor Green
Write-Host "New virtual environment created with Python 3.11" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Close and reopen your terminal/IDE" -ForegroundColor Cyan
Write-Host "2. Activate the new virtual environment:" -ForegroundColor Cyan
Write-Host "   .\venv311_clean\Scripts\activate.bat" -ForegroundColor Cyan
Write-Host "3. Install packages:" -ForegroundColor Cyan
Write-Host "   pip install -r requirements.txt" -ForegroundColor Cyan
Write-Host "`nTo completely remove Python 3.14 from your system:" -ForegroundColor Yellow
Write-Host "1. Go to Windows Settings > Apps > Installed apps" -ForegroundColor Yellow
Write-Host "2. Find 'Python 3.14' and uninstall it" -ForegroundColor Yellow
Write-Host "3. Delete C:\Python314 folder if it remains" -ForegroundColor Yellow
