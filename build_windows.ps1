# Semptify Windows Build Script
# Creates a standalone .exe using PyInstaller

# Requirements: pip install pyinstaller

$ErrorActionPreference = "Stop"

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║         SEMPTIFY WINDOWS BUILD SCRIPT                     ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# Check if PyInstaller is installed
Write-Host "📦 Checking PyInstaller..." -ForegroundColor Yellow
$pyinstaller = & .\.venv\Scripts\python.exe -c "import PyInstaller; print('OK')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & .\.venv\Scripts\pip.exe install pyinstaller
}

# Create the spec file for better control
Write-Host "📝 Creating build specification..." -ForegroundColor Yellow

$specContent = @'
# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Collect all app files
added_files = [
    ('app', 'app'),
    ('static', 'static'),
    ('data', 'data'),
    ('plugins', 'plugins'),
]

# Hidden imports for FastAPI and dependencies
hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'pydantic',
    'sqlalchemy',
    'aiosqlite',
    'httpx',
    'jinja2',
    'multipart',
    'email_validator',
    'anyio',
    'sniffio',
    'h11',
    'httpcore',
    'certifi',
    'idna',
    'charset_normalizer',
]

a = Analysis(
    ['semptify_desktop.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Semptify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico' if os.path.exists('static/favicon.ico') else None,
)
'@

$specContent | Out-File -FilePath "semptify.spec" -Encoding UTF8

# Build the executable
Write-Host "🔨 Building executable (this may take a few minutes)..." -ForegroundColor Yellow
& .\.venv\Scripts\pyinstaller.exe semptify.spec --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host @"

✅ BUILD SUCCESSFUL!

Your standalone app is at:
   dist\Semptify.exe

To run:
   .\dist\Semptify.exe

To distribute:
   Copy the entire 'dist' folder to any Windows PC

"@ -ForegroundColor Green
} else {
    Write-Host "❌ Build failed. Check errors above." -ForegroundColor Red
}
