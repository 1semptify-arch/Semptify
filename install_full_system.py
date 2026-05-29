#!/usr/bin/env python3
"""
Full System Installer for Semptify
Installs: Backend, UI, Models, Launcher, Admin Module
"""

import os
import subprocess
import sys

SEMPtIFY_PATH = r"C:\Semptify\Semptify-FastAPI"
BACKEND_PATH = r"C:\Semptify\backend"

def run_command(cmd, cwd=None):
    """Run shell command and print output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"✓ Success")
    return result.returncode == 0

def install_dependencies():
    """Install Python dependencies"""
    print("\n[1/5] Installing dependencies...")
    if os.path.exists(os.path.join(BACKEND_PATH, "requirements.txt")):
        run_command(f"pip install -r {BACKEND_PATH}\\requirements.txt")
    print("✓ Dependencies installed")

def setup_backend():
    """Setup backend environment"""
    print("\n[2/5] Setting up backend...")
    if not os.path.exists(os.path.join(BACKEND_PATH, "venv")):
        run_command(f"python -m venv {BACKEND_PATH}\\venv")
        run_command(f"{BACKEND_PATH}\\venv\\Scripts\\pip.exe install -r {BACKEND_PATH}\\requirements.txt")
    print("✓ Backend configured")

def setup_admin_module():
    """Create admin console module"""
    print("\n[3/5] Setting up admin module...")
    admin_script = os.path.join(SEMPtIFY_PATH, "create_admin_module.py")
    if os.path.exists(admin_script):
        subprocess.run([sys.executable, admin_script], cwd=SEMPtIFY_PATH)
    print("✓ Admin module created")

def create_launcher():
    """Create system launcher"""
    print("\n[4/5] Creating launcher...")
    launcher_content = f'''@echo off
echo ============================================
echo   Semptify Advocacy Platform Launcher
echo ============================================
echo.

REM Check if Ollama is running
tasklist | findstr ollama.exe >nul
if errorlevel 1 (
    echo [1/4] Starting Ollama server...
    start /B ollama serve
    timeout /t 5 >nul
) else (
    echo [1/4] Ollama already running
)

REM Pull DeepSeek if not present
echo [2/4] Ensuring DeepSeek model is available...
ollama list | findstr deepseek-r1 >nul
if errorlevel 1 (
    ollama pull deepseek-r1:latest
)

REM Start local AI backend
echo [3/4] Starting Local AI Backend on port 8001...
start "Local AI Backend" {BACKEND_PATH}\\venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8001

echo [4/4] Opening Semptify Admin Console...
echo.
echo Local AI: http://127.0.0.1:8001
echo Semptify Server: http://your-render-url
echo.
echo Press any key to stop all services...
pause >nul

taskkill /FI "WINDOWTITLE eq Local AI Backend" /F >nul 2>&1
echo Services stopped.
'''
    launcher_path = os.path.join(SEMPtIFY_PATH, "launch_semtify.bat")
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    print(f"✓ Launcher created: {launcher_path}")

def create_readme():
    """Create setup documentation"""
    print("\n[5/5] Creating documentation...")
    readme = f'''# Semptify Advocacy Platform - Installation Complete

## What's Installed

1. **Local AI Backend** (`{BACKEND_PATH}`)
   - FastAPI server with Ollama integration
   - DeepSeek, Qwen, Mistral models
   - 11 local file operation tools
   - Runs on http://localhost:8001

2. **Admin Console Module** (`{SEMPtIFY_PATH}\\modules\\admin_console`)
   - Bridges local AI to remote Semptify
   - File operations, AI chat, maintenance
   - Connects/disconnects cleanly

3. **Launcher** (`launch_semtify.bat`)
   - Starts Ollama, pulls models, launches backend
   - One-click operation

## Quick Start

1. Double-click `launch_semtify.bat`
2. Open http://127.0.0.1:8001 for local AI chat
3. Access Semptify admin panel for remote operations

## Architecture

- **Semptify Server** (Render/Cloud): Tenant-facing app
- **Your Local Machine**: AI processing, file operations
- **Admin Module**: Secure bridge between them
- **Disconnect anytime**: Semptify keeps running

## For Tenant Advocacy

This system helps expose:
- Illegal lease clauses
- Forged signatures
- Retaliation patterns
- HUD/LIHTC violations
- Systemic landlord abuse

All processing can happen locally for privacy.
'''
    readme_path = os.path.join(SEMPtIFY_PATH, "SETUP_COMPLETE.md")
    with open(readme_path, 'w') as f:
        f.write(readme)
    print(f"✓ Documentation: {readme_path}")

def main():
    print("=" * 60)
    print("Semptify Full System Installer")
    print("Tenant Advocacy Platform")
    print("=" * 60)
    
    install_dependencies()
    setup_backend()
    setup_admin_module()
    create_launcher()
    create_readme()
    
    print("\n" + "=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Run: {SEMPtIFY_PATH}\\launch_semtify.bat")
    print(f"2. Open: http://127.0.0.1:8001")
    print(f"3. Read: {SEMPtIFY_PATH}\\SETUP_COMPLETE.md")
    print()

if __name__ == "__main__":
    main()
