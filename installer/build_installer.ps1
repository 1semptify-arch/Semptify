<#
.SYNOPSIS
    Semptify Windows Installer Builder
    
.DESCRIPTION
    Builds Semptify.exe Windows installer using PyInstaller
    Supports Windows 10/11/22 (Server 2022)
    
.NOTES
    Run from project root: .\installer\build_installer.ps1
#>

param(
    [switch]$Clean,      # Clean build (remove previous)
    [switch]$OneFile,    # Single EXE (slower startup, easier distribution)
    [switch]$NoConsole,  # Hide console window (use for GUI-only)
    [switch]$Debug       # Debug build with verbose output
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Color($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
}

Write-Color ""
Write-Color "============================================================" "Cyan"
Write-Color "  SEMPTIFY WINDOWS INSTALLER BUILDER" "Cyan"
Write-Color "  Version 5.0.0 - Windows 10/11/22 Compatible" "Cyan"  
Write-Color "============================================================" "Cyan"
Write-Color ""

# Get project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Color "[1/6] Checking Python environment..." "Yellow"

# Check Python
$PythonPath = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-Color "ERROR: Virtual environment not found at .venv\" "Red"
    Write-Color "Run: python -m venv .venv && .\.venv\Scripts\activate && pip install -r requirements.txt" "Gray"
    exit 1
}

$PythonVersion = & $PythonPath --version
Write-Color "  Python: $PythonVersion" "Green"

# Check/Install PyInstaller
Write-Color "[2/6] Checking PyInstaller..." "Yellow"
$HasPyInstaller = & $PythonPath -c "import PyInstaller; print('ok')" 2>$null
if ($HasPyInstaller -ne "ok") {
    Write-Color "  Installing PyInstaller..." "Gray"
    & $PythonPath -m pip install pyinstaller --quiet
}
$PyInstallerVersion = & $PythonPath -c "import PyInstaller; print(PyInstaller.__version__)"
Write-Color "  PyInstaller: $PyInstallerVersion" "Green"

# Clean previous build
if ($Clean) {
    Write-Color "[3/6] Cleaning previous build..." "Yellow"
    Remove-Item -Path ".\build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Color "  Cleaned build/ and dist/" "Green"
} else {
    Write-Color "[3/6] Skipping clean (use -Clean to remove previous build)" "Gray"
}

# Build arguments
$BuildArgs = @(
    "-m", "PyInstaller"
    "--clean"
    "--noconfirm"
)

if ($OneFile) {
    Write-Color "[4/6] Building ONE-FILE installer (slower startup)..." "Yellow"
    $BuildArgs += "--onefile"
} else {
    Write-Color "[4/6] Building FOLDER installer (faster startup)..." "Yellow"
    $BuildArgs += "--onedir"
}

if ($NoConsole) {
    $BuildArgs += "--noconsole"
    Write-Color "  Console: Hidden (GUI mode)" "Gray"
} else {
    $BuildArgs += "--console"
    Write-Color "  Console: Visible (server logs)" "Gray"
}

# Add spec file
$BuildArgs += ".\installer\semptify.spec"

if ($Debug) {
    $BuildArgs += "--debug=all"
    Write-Color "  Debug: Enabled" "Gray"
}

Write-Color "  Running PyInstaller..." "Gray"
Write-Color ""

# Run PyInstaller
& $PythonPath @BuildArgs

if ($LASTEXITCODE -ne 0) {
    Write-Color ""
    Write-Color "ERROR: PyInstaller build failed!" "Red"
    exit 1
}

Write-Color ""
Write-Color "[5/6] Build complete!" "Green"

# Check output
$DistPath = ".\dist\Semptify"
$ExePath = ".\dist\Semptify\Semptify.exe"

if ($OneFile) {
    $ExePath = ".\dist\Semptify.exe"
    $DistPath = ".\dist"
}

if (Test-Path $ExePath) {
    $ExeSize = (Get-Item $ExePath).Length / 1MB
    Write-Color "  Executable: $ExePath" "Green"
    Write-Color "  Size: $([math]::Round($ExeSize, 2)) MB" "Green"
} else {
    Write-Color "  WARNING: Executable not found at expected path" "Yellow"
}

# Create ZIP for distribution
Write-Color "[6/6] Creating distribution package..." "Yellow"

$ZipPath = ".\dist\Semptify-Windows-v5.0.0.zip"
Remove-Item $ZipPath -ErrorAction SilentlyContinue

if ($OneFile) {
    Compress-Archive -Path ".\dist\Semptify.exe" -DestinationPath $ZipPath
} else {
    Compress-Archive -Path ".\dist\Semptify\*" -DestinationPath $ZipPath
}

$ZipSize = (Get-Item $ZipPath).Length / 1MB
Write-Color "  Distribution: $ZipPath" "Green"
Write-Color "  Size: $([math]::Round($ZipSize, 2)) MB" "Green"

Write-Color ""
Write-Color "============================================================" "Cyan"
Write-Color "  BUILD SUCCESSFUL!" "Green"
Write-Color "============================================================" "Cyan"
Write-Color ""
Write-Color "To run Semptify:" "White"
if ($OneFile) {
    Write-Color "  .\dist\Semptify.exe" "Yellow"
} else {
    Write-Color "  .\dist\Semptify\Semptify.exe" "Yellow"
}
Write-Color ""
Write-Color "To distribute:" "White"
Write-Color "  Share: $ZipPath" "Yellow"
Write-Color ""
