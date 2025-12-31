# ============================================================
# 🖥️ CREATE SEMPTIFY DESKTOP SHORTCUT
# ============================================================
# Run this script once to create a desktop shortcut
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Semptify 5.0.lnk"
$TargetPath = Join-Path $ScriptDir "START-SEMPTIFY.bat"
$IconPath = Join-Path $ScriptDir "static\favicon.ico"

# Create WScript Shell object
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Configure shortcut
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Start Semptify 5.0 - Tenant Rights Platform"
$Shortcut.WindowStyle = 1  # Normal window

# Set icon (use favicon if exists, otherwise use default)
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
} else {
    # Use a system icon as fallback
    $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,13"
}

# Save the shortcut
$Shortcut.Save()

Write-Host ""
Write-Host "✅ Desktop shortcut created!" -ForegroundColor Green
Write-Host "   Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click 'Semptify 5.0' on your desktop to start the app!" -ForegroundColor Yellow
Write-Host ""
