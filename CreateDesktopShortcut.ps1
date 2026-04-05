# ============================================================
#  CREATE SEMPTIFY DESKTOP SHORTCUT
#  Run this script ONCE to put a start button on your desktop.
#  After that — just double-click "Start Semptify" on your desktop.
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Start Semptify.lnk"
$TargetPath   = Join-Path $ScriptDir "START-SEMPTIFY.bat"
$IconPath     = Join-Path $ScriptDir "static\favicon.ico"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut  = $WshShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath      = $TargetPath
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description     = "Start Semptify 5.0 - Tenant Rights Platform (Production, Secured)"
$Shortcut.WindowStyle     = 1

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
} else {
    $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,13"
}

$Shortcut.Save()

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host "   Desktop shortcut created!" -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location : $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "  WHAT IT DOES WHEN YOU DOUBLE-CLICK IT:" -ForegroundColor Yellow
Write-Host "    1. Starts Docker Desktop (the database engine)"
Write-Host "    2. Starts the Semptify database (PostgreSQL)"
Write-Host "    3. Enforces all security settings"
Write-Host "    4. Starts the Semptify server"
Write-Host "    5. Opens your browser to the Semptify dashboard"
Write-Host ""
  Write-Host "  You do not need to do anything else - just double-click it." -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close this window"
